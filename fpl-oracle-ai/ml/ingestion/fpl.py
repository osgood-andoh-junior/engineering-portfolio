"""Rate-limited public JSON adapter; raw payloads are immutable evidence."""
import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import httpx
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from apps.api.config import settings
from apps.api.db import utcnow
from apps.api.models import Source, Evidence, Season, Club, Player, Identity, Fixture, Gameweek, Audit,PriceSnapshot,AvailabilitySnapshot,Job,Membership

class Element(BaseModel):
    model_config = ConfigDict(extra='allow')
    id: int
    code: int
    team: int
    web_name: str
    element_type: int = Field(ge=1, le=4)
    now_cost: int = Field(ge=0)
    status: str

class Bootstrap(BaseModel):
    elements: list[Element]
    teams: list[dict]
    events: list[dict]

def parse_date(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')) if value else None

class FPLClient:
    def __init__(self, transport=None):
        self.transport = transport
        self.last_request = 0.0
        self.http = None

    async def __aenter__(self):
        self.http = httpx.AsyncClient(base_url='https://fantasy.premierleague.com/api', timeout=30, transport=self.transport, follow_redirects=False)
        return self

    async def __aexit__(self, *_):
        await self.http.aclose()
        self.http = None

    async def get(self, path: str):
        # Paths are constructed by trusted callers, never arbitrary remote URLs.
        if not path.startswith('/') or '..' in path or '://' in path:
            raise ValueError('Invalid FPL path')
        if self.http is not None:
            return await self._fetch(self.http,path)
        async with httpx.AsyncClient(base_url='https://fantasy.premierleague.com/api', timeout=30, transport=self.transport, follow_redirects=False) as client:
            return await self._fetch(client,path)

    async def _fetch(self,client,path):
        for attempt in range(4):
            await asyncio.sleep(max(0, 1 - (asyncio.get_running_loop().time() - self.last_request)))
            self.last_request = asyncio.get_running_loop().time()
            try:
                response = await client.get(path, headers={'User-Agent': 'FPL-Oracle/0.1 (personal analytics)'})
                response.raise_for_status()
                return response.json()
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code not in {429, 500, 502, 503, 504}:
                    raise
                if attempt == 3:
                    raise
                await asyncio.sleep(2 ** attempt)

    async def manager_squad(self, manager_id: int, gameweek: int):
        entry = await self.get(f'/entry/{manager_id}/')
        picks = await self.get(f'/entry/{manager_id}/event/{gameweek}/picks/')
        return {'entry': entry, 'picks': picks}

def evidence(session, source_id, uri, payload,observed_at=None):
    raw = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
    digest = hashlib.sha256(raw).hexdigest()
    existing = session.scalar(select(Evidence).where(Evidence.digest == digest))
    if existing:
        return existing
    folder = settings.data_dir / 'raw' / source_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f'{digest}.json').write_bytes(raw)
    row = Evidence(source_id=source_id, digest=digest, uri=uri, payload=payload,observed_at=observed_at or utcnow())
    session.add(row)
    session.flush()
    return row

async def sync_fpl(session, client=None):
    client = client or FPLClient()
    source = session.get(Source, 'fpl')
    if not source:
        source = Source(id='fpl', url='https://fantasy.premierleague.com/api/', official=True, permitted=True, license='Public unofficial API; redistribution rights unverified')
        session.add(source)
        session.flush()
    raw = await client.get('/bootstrap-static/')
    data = Bootstrap.model_validate(raw)
    fixtures = await client.get('/fixtures/')
    if not isinstance(fixtures, list):
        raise ValueError('Unexpected fixture schema')
    # Determine the season from actual gameweek deadlines, not the local calendar.
    deadlines = [parse_date(e['deadline_time']) for e in data.events]
    if not deadlines:
        raise ValueError('Cannot establish upstream season')
    first = min(deadlines)
    year = first.year if first.month >= 7 else first.year - 1
    season_id = f'{year}-{str(year + 1)[2:]}'
    if not session.get(Season, season_id):
        session.add(Season(id=season_id))
        session.flush()
    ev = evidence(session, 'fpl', 'https://fantasy.premierleague.com/api/bootstrap-static/', raw)
    # Verify only the supported squad-constraint subset against the live official schema.
    rules=raw.get('game_settings',{})
    types=raw.get('element_types',[])
    supported=rules.get('squad_squadsize')==15 and rules.get('squad_squadplay')==11 and rules.get('squad_team_limit')==3 and {t['id']:t.get('squad_select') for t in types}=={1:2,2:5,3:5,4:3}
    season=session.get(Season,season_id)
    season.rules={'source_evidence_id':ev.id,'squad_constraints':rules,'positions':types,'scoring':raw.get('game_config',{}).get('scoring'),'verified_scope':'Squad composition, XI size, position limits, club cap and initial budget only','transfer_rollover_verified':False,'chip_availability_verified':False}
    season.rules_verified=supported
    evidence(session, 'fpl', 'https://fantasy.premierleague.com/api/fixtures/', {'fixtures': fixtures})
    clubs = {}
    for item in data.teams:
        club = session.scalar(select(Club).where(Club.code == item['code']))
        if not club:
            club = Club(code=item['code'], name=item['name'], short_name=item['short_name'])
            session.add(club)
            session.flush()
        else:
            club.name, club.short_name = item['name'], item['short_name']
        clubs[item['id']] = club.id
    for item in data.elements:
        player = session.scalar(select(Player).where(Player.code == item.code))
        if not player:
            player = Player(code=item.code, name=item.web_name, club_id=clubs[item.team], position=item.element_type, price=item.now_cost, status=item.status,registration_state='verified')
            session.add(player)
            session.flush()
        else:
            old_club=player.club_id
            waiting=player.registration_state in {'awaiting_fpl_verification','conflict','unavailable'}
            conflict=waiting and old_club!=clubs[item.team]
            if conflict:
                player.registration_state='unavailable' if item.status=='u' else 'conflict'
                session.add(Audit(action='registration.conflict',payload={'player_id':player.id,'confirmed_football_club':old_club,'fpl_registered_club':clubs[item.team],'evidence_id':ev.id,'resolution':'Confirmed membership retained; forecasts and optimization gated until FPL registration agrees'}))
            else:player.registration_state='verified'
            if old_club!=clubs[item.team] and not conflict:
                # FPL verifies registration/club membership, not whether the deal is a loan or permanent.
                changed={'player_id':player.id,'from_club':old_club,'to_club':clubs[item.team],'observed_at':ev.observed_at.isoformat(),'evidence_id':ev.id,'classification':'official_fpl_club_assignment_change','effective_date_precision':'first observed; actual transfer date unknown'}
                session.add(Audit(action='fpl.club_assignment_changed',payload=changed))
                existing_job=session.scalar(select(Job).where(Job.key==f'fpl-club:{ev.id}:{player.id}'))
                if not existing_job:
                    session.add(Job(key=f'fpl-club:{ev.id}:{player.id}',kind='refresh',payload={'clubs':[c for c in (old_club,clubs[item.team]) if c],'player_id':player.id,'event_id':None}))
                membership=session.scalar(select(Membership).where(Membership.player_id==player.id,Membership.ends_at.is_(None)))
                if membership:
                    membership.ends_at=ev.observed_at;membership.ends_observed_at=ev.observed_at;membership.end_evidence_id=ev.id;session.flush()
                session.add(Membership(player_id=player.id,club_id=clubs[item.team],starts_at=ev.observed_at,evidence_id=ev.id))
            player.name, player.position, player.price, player.status = item.web_name, item.element_type, item.now_cost, item.status
            if not conflict:player.club_id = clubs[item.team]
            player.updated_at = utcnow()
        identity = session.scalar(select(Identity).where(Identity.season_id == season_id, Identity.fpl_id == item.id))
        if identity and identity.code not in (None, item.code):
            raise ValueError('Conflicting seasonal player identity')
        if not identity:
            session.add(Identity(season_id=season_id, fpl_id=item.id, code=item.code, player_id=player.id, name=item.web_name))
        else:
            identity.player_id, identity.code = player.id, item.code
        if not session.scalar(select(Membership).where(Membership.player_id==player.id,Membership.ends_at.is_(None))):
            # This is a first-observed membership boundary, not an invented transfer date.
            session.add(Membership(player_id=player.id,club_id=player.club_id,starts_at=ev.observed_at,evidence_id=ev.id))
        if not session.scalar(select(PriceSnapshot).where(PriceSnapshot.player_id==player.id,PriceSnapshot.evidence_id==ev.id)):
            session.add(PriceSnapshot(player_id=player.id,price=item.now_cost,observed_at=ev.observed_at,evidence_id=ev.id))
        if not session.scalar(select(AvailabilitySnapshot).where(AvailabilitySnapshot.player_id==player.id,AvailabilitySnapshot.evidence_id==ev.id)):
            session.add(AvailabilitySnapshot(player_id=player.id,status=item.status,chance=item.model_extra.get('chance_of_playing_next_round'),news=item.model_extra.get('news'),observed_at=ev.observed_at,evidence_id=ev.id))
    for item in fixtures:
        fixture = session.scalar(select(Fixture).where(Fixture.season_id == season_id, Fixture.provider_id == item['id']))
        values = dict(season_id=season_id, provider_id=item['id'], event=item.get('event'), home_id=clubs[item['team_h']], away_id=clubs[item['team_a']], kickoff=parse_date(item.get('kickoff_time')), finished=item.get('finished', False), home_score=item.get('team_h_score'), away_score=item.get('team_a_score'))
        if fixture:
            for k, v in values.items():
                setattr(fixture, k, v)
        else:
            session.add(Fixture(**values))
    for item in data.events:
        gw = session.scalar(select(Gameweek).where(Gameweek.season_id == season_id, Gameweek.event == item['id']))
        if not gw:
            gw = Gameweek(season_id=season_id, event=item['id'], deadline=parse_date(item['deadline_time']))
            session.add(gw)
        gw.deadline=parse_date(item['deadline_time'])
        gw.current, gw.finished = item.get('is_current', False), item.get('finished', False)
    source.last_success, source.last_error = utcnow(), None
    session.add(Audit(action='fpl.sync', payload={'season': season_id, 'players': len(data.elements), 'fixtures': len(fixtures), 'evidence': ev.id}))
    session.commit()
    return {'season': season_id, 'players': len(data.elements), 'fixtures': len(fixtures)}
