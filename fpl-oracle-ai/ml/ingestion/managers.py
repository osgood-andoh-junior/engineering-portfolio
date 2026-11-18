"""Reviewed official fact import; no bulk site scraping or invented announcement timestamps."""
import json
from pathlib import Path
from datetime import datetime,timezone
from sqlalchemy import select
from apps.api.db import utcnow
from apps.api.models import Source,Club,Manager,Tenure,ExternalMapping,TacticalRegime,Job,Audit,Fixture,ManagerMatchStat,Evidence
from ml.ingestion.fpl import evidence

def import_reviewed_directory(session,path=Path('docs/verified_managers_2026-10-28.json')):
    data=json.loads(path.read_text(encoding='utf-8'))
    if data['source_url']!='https://www.premierleague.com/en/news/4325264':raise ValueError('Unreviewed directory source')
    source=session.get(Source,'pl-reviewed')
    if not source:
        source=Source(id='pl-reviewed',url='https://www.premierleague.com',official=True,permitted=True,license='Manually reviewed factual directory references. Website content rights retained; automated bulk access not configured.')
        session.add(source);session.flush()
    ev=evidence(session,'pl-reviewed',data['source_url'],data)
    changed=[]
    for item in data['records']:
        club=session.scalar(select(Club).where(Club.code==item['club_code']))
        if not club:raise ValueError(f"Unresolved official club code {item['club_code']}")
        mapping=session.scalar(select(ExternalMapping).where(ExternalMapping.source_id=='pl-reviewed',ExternalMapping.external_id==item['external_id'],ExternalMapping.entity_kind=='manager'))
        if not mapping:
            manager=Manager(name=item['name']);session.add(manager);session.flush()
            mapping=ExternalMapping(source_id='pl-reviewed',external_id=item['external_id'],entity_kind='manager',manager_id=manager.id)
            session.add(mapping);session.flush()
        manager_id=mapping.manager_id
        start=datetime.fromisoformat(item['start']).replace(tzinfo=timezone.utc)
        current=session.scalar(select(Tenure).where(Tenure.club_id==club.id,Tenure.ends_at.is_(None)))
        if current and current.manager_id==manager_id and current.starts_at.replace(tzinfo=timezone.utc)==start:continue
        if current:
            if current.starts_at.replace(tzinfo=timezone.utc)>=start:raise ValueError('Conflicting directory tenure requires review')
            current.ends_at=start;current.ends_observed_at=ev.observed_at;current.end_evidence_id=ev.id;session.flush()
        tenure=Tenure(manager_id=manager_id,club_id=club.id,starts_at=start,evidence_id=ev.id)
        session.add(tenure);session.flush()
        session.add(TacticalRegime(club_id=club.id,tenure_id=tenure.id,effective_at=start,reason='Verified official directory; day precision'))
        changed.append(club.id)
    source.last_success=utcnow()
    if changed and not session.scalar(select(Job).where(Job.key==f'manager-directory:{ev.digest}')):
        session.add(Job(key=f'manager-directory:{ev.digest}',kind='refresh',payload={'clubs':changed,'event_id':None,'source_evidence_id':ev.id}))
    session.add(Audit(action='managers.directory_imported',payload={'evidence_id':ev.id,'clubs_changed':changed,'date_precision':'day','announcement_timestamps':'unknown; no fabricated news events'}))
    session.commit()
    return {'verified_managers':len(data['records']),'clubs_changed':len(changed),'source':data['source_url'],'date_precision':'day'}

def refresh_manager_match_facts(session):
    fixtures_evidence=session.scalars(select(Evidence).where(Evidence.source_id=='fpl').order_by(Evidence.observed_at.desc())).all()
    ev=next((e for e in fixtures_evidence if e.uri.endswith('/fixtures/')),None)
    if not ev:return {'matches':0,'reason':'No official fixture evidence'}
    added=0;corrected=0
    for tenure in session.scalars(select(Tenure)):
        tenure_evidence=session.get(Evidence,tenure.evidence_id)
        known_at=max(ev.observed_at,tenure_evidence.observed_at)
        query=select(Fixture).where(Fixture.finished.is_(True),Fixture.kickoff>=tenure.starts_at,(Fixture.home_id==tenure.club_id)|(Fixture.away_id==tenure.club_id),Fixture.home_score.is_not(None),Fixture.away_score.is_not(None))
        if tenure.ends_at:query=query.where(Fixture.kickoff<tenure.ends_at)
        for fixture in session.scalars(query):
            existing=session.scalar(select(ManagerMatchStat).where(ManagerMatchStat.tenure_id==tenure.id,ManagerMatchStat.fixture_id==fixture.id))
            if existing:
                if existing.observed_at<known_at:
                    existing.observed_at=known_at;corrected+=1
                continue
            home=fixture.home_id==tenure.club_id
            session.add(ManagerMatchStat(tenure_id=tenure.id,fixture_id=fixture.id,played_at=fixture.kickoff,observed_at=known_at,goals_for=fixture.home_score if home else fixture.away_score,goals_against=fixture.away_score if home else fixture.home_score,home=home,evidence_id=ev.id));added+=1
    if corrected:session.add(Audit(action='manager_match.provenance_corrected',payload={'count':corrected,'reason':'Derived facts cannot precede both fixture and tenure verification'}))
    session.commit()
    return {'new_manager_match_records':added,'source_evidence_id':ev.id,'tactical_fields':'unavailable; not inferred from results'}
