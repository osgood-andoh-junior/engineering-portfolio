import asyncio
import hashlib
import io
import json
import httpx
import pandas as pd
from sqlalchemy import select
from apps.api.config import settings
from apps.api.db import utcnow
from apps.api.models import Source, Season, HistoricalStat, Identity, Player
from ml.ingestion.fpl import evidence, parse_date

SEASONS = [f'{y}-{str(y+1)[2:]}' for y in range(2020, 2026)]
BASE = 'https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master'

def validate_history(df,season):
    required={'element','fixture','kickoff_time','total_points','minutes'}
    if not required.issubset(df.columns): raise ValueError(f'{season}: missing {required-set(df.columns)}')
    removed=int(df.duplicated().sum())
    clean=df.drop_duplicates().copy()
    if clean.duplicated(['element','fixture']).any(): raise ValueError(f'{season}: conflicting player fixtures; review source')
    if not clean.minutes.between(0,150).all(): raise ValueError(f'{season}: invalid minutes')
    return clean,removed

async def sync_history(session, seasons=None):
    if not settings.historical_data_permitted:
        raise PermissionError('Set HISTORICAL_DATA_PERMITTED=true only after reviewing DATA_SOURCES.md and confirming your permitted use.')
    source = session.get(Source, 'vaastav')
    if not source:
        session.add(Source(id='vaastav', url=BASE, official=False, permitted=True, license='MIT code; underlying data rights retained by providers'))
        session.flush()
    report = []
    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
        raw_dir = settings.data_dir / 'raw' / 'vaastav'
        raw_dir.mkdir(parents=True, exist_ok=True)
        if not (raw_dir/'LICENSE').exists():
            license_response = await client.get(f'{BASE}/LICENSE')
            license_response.raise_for_status()
            (raw_dir / 'LICENSE').write_text(license_response.text, encoding='utf-8')
        for season in seasons or SEASONS:
            url = f'{BASE}/data/{season}/gws/merged_gw.csv'
            cached=[p for p in raw_dir.glob(f'{season}-*.csv') if len(p.stem.split('-')[-1])==64]
            if cached:
                raw=max(cached,key=lambda p:p.stat().st_mtime).read_bytes()
            else:
                response = await client.get(url)
                if response.status_code == 404:
                    report.append({'season': season, 'status': 'unavailable'})
                    continue
                response.raise_for_status()
                raw=response.content
            digest = hashlib.sha256(raw).hexdigest()
            (raw_dir / f'{season}-{digest}.csv').write_bytes(raw)
            df = pd.read_csv(io.BytesIO(raw), low_memory=False)
            df,removed=validate_history(df,season)
            if not session.get(Season, season):
                session.add(Season(id=season))
                session.flush()
            ev = evidence(session, 'vaastav', url, {'sha256': digest, 'rows': len(df), 'season': season, 'historical_observation_times': 'unavailable'})
            positions, codes = {}, {}
            meta_path=raw_dir/f'{season}-players_raw.csv'
            if meta_path.exists():
                meta_text=meta_path.read_text(encoding='utf-8')
            else:
                meta_response=await client.get(f'{BASE}/data/{season}/players_raw.csv')
                meta_text=meta_response.text if meta_response.status_code==200 else None
                if meta_text: meta_path.write_text(meta_text,encoding='utf-8')
            if meta_text:
                meta = pd.read_csv(io.StringIO(meta_text))
                positions = dict(zip(meta.id, meta.element_type))
                codes = dict(zip(meta.id, meta.code)) if 'code' in meta else {}
            current_codes = {p.code: p.id for p in session.scalars(select(Player))}
            existing = set(session.execute(select(HistoricalStat.fpl_id, HistoricalStat.fixture).where(HistoricalStat.season == season)).all())
            identities = set(session.scalars(select(Identity.fpl_id).where(Identity.season_id == season)))
            new_rows = []
            for row in df.to_dict('records'):
                pid = int(row['element'])
                if pid not in identities:
                    code = int(codes[pid]) if pid in codes and pd.notna(codes[pid]) else None
                    session.add(Identity(season_id=season, fpl_id=pid, code=code, player_id=current_codes.get(code), name=str(row.get('name', pid))))
                    identities.add(pid)
                if (pid, int(row['fixture'])) in existing:
                    continue
                def optional(name, cast=float):
                    value = row.get(name)
                    return cast(value) if value is not None and pd.notna(value) else None
                new_rows.append(dict(season=season, fpl_id=pid, fixture=int(row['fixture']), kickoff=parse_date(row['kickoff_time']), observed_at=None, points=float(row['total_points']), minutes=int(row['minutes']), position=positions.get(pid), team=optional('team', str), opponent=optional('opponent_team', int), home=str(row.get('was_home')).lower() == 'true', price=optional('value', int), xg=optional('expected_goals'), xa=optional('expected_assists'), evidence_id=ev.id))
            if new_rows:
                session.execute(__import__('sqlalchemy').insert(HistoricalStat), new_rows)
            session.commit()
            folder = settings.data_dir / 'warehouse'
            folder.mkdir(parents=True, exist_ok=True)
            try:
                df.to_parquet(folder / f'{season}.parquet', index=False)
                analytical='parquet'
            except ImportError:
                analytical='unavailable: PyArrow not installed; relational records and raw CSV preserved'
            report.append({'season': season, 'status': 'imported', 'analytical_format':analytical, 'rows': len(df), 'new_rows': len(new_rows), 'exact_duplicate_rows_removed':removed,'cached_raw_snapshot':bool(cached), 'sha256': digest})
            (settings.data_dir / 'coverage.json').write_text(json.dumps(report,indent=2))
            await asyncio.sleep(1)
    (settings.data_dir / 'coverage.json').write_text(json.dumps(report, indent=2))
    source=session.get(Source,'vaastav')
    if any(row['status']=='imported' for row in report):
        source.last_success=utcnow()
        source.last_error=None
        session.commit()
    return report
