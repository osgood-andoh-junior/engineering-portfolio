"""Offline chronological training. Never called by a public HTTP route."""
import hashlib
import json
import pickle
from datetime import timezone
import numpy as np
import pandas as pd
from sqlalchemy import select
from apps.api.config import settings
from apps.api.models import HistoricalStat, ModelVersion, Audit,Gameweek,Fixture,Identity
from ml.features.point_in_time import build_features, sequence_examples, FEATURES,SEQUENCE_FEATURES,datetime_ns
from ml.evaluation.metrics import metrics

def load_frame(session):
    frame=pd.read_sql(select(HistoricalStat),session.connection())
    if frame.empty:return frame
    codes={(i.season_id,i.fpl_id):i.code for i in session.scalars(select(Identity))}
    frame['entity_key']=[f'code:{codes[(s,p)]}' if codes.get((s,p)) and codes[(s,p)]>0 else f'unresolved:{s}:{p}' for s,p in zip(frame.season,frame.fpl_id)]
    # Assistant-manager FPL entries use different scoring rules and are not footballer targets.
    frame=frame[frame.position.isna()|frame.position.isin([1,2,3,4])].copy()
    from pathlib import Path
    calendars=[]
    for season in frame.season.unique():
        path=settings.data_dir/'warehouse'/f'{season}.parquet'
        if path.exists():
            import pyarrow.parquet as pq
            fields=pq.ParquetFile(path).schema.names
            event_column='round' if 'round' in fields else 'GW' if 'GW' in fields else None
            if event_column:
                meta=pd.read_parquet(path,columns=['element','fixture',event_column]).rename(columns={'element':'fpl_id',event_column:'gameweek'})
                meta['season']=season;calendars.append(meta.drop_duplicates(['season','fpl_id','fixture']))
    if calendars:frame=frame.merge(pd.concat(calendars),on=['season','fpl_id','fixture'],how='left')
    else:frame['gameweek']=np.nan
    fixtures={(f.season_id,f.provider_id):f.event for f in session.scalars(select(Fixture))}
    frame['gameweek']=[fixtures.get((s,f),g) for s,f,g in zip(frame.season,frame.fixture,frame.gameweek)]
    deadlines={(g.season_id,g.event):pd.Timestamp(g.deadline).tz_localize('UTC') if g.deadline.tzinfo is None else pd.Timestamp(g.deadline) for g in session.scalars(select(Gameweek))}
    exact=pd.Series([deadlines.get((s,g),pd.NaT) for s,g in zip(frame.season,frame.gameweek)],index=frame.index,dtype='datetime64[ns, UTC]')
    kickoff=pd.to_datetime(frame.kickoff,utc=True)
    # Unknown historical deadlines are never invented. This conservative match-boundary
    # proxy excludes all same-GW outcomes, and is explicitly labelled retrospective.
    first=kickoff.groupby([frame.season,frame.gameweek]).transform('min').fillna(kickoff)
    frame['deadline']=exact.fillna(first)
    frame['deadline_verified']=exact.notna()
    return frame

def train(session, kinds=('baseline','catboost','lightgbm','lstm','gru'), epochs=5, lengths=(5,10,15,20), max_rows=None,strict_point_in_time=False):
    np.random.seed(42)
    if any(k!='baseline' for k in kinds):
        from sklearn.impute import SimpleImputer
        from sklearn.preprocessing import StandardScaler
        from sklearn.pipeline import make_pipeline
    if any(k in {'lstm','gru'} for k in kinds):
        import torch
        from torch.utils.data import DataLoader
        from ml.models.recurrent import RecurrentRegressor, MatchSequenceDataset
        torch.manual_seed(42)
        torch.set_num_threads(2)
    raw = load_frame(session)
    session.commit()  # Release the warehouse read transaction before offline fitting.
    if len(raw) < 500:
        raise ValueError('At least 500 real historical observations required')
    if strict_point_in_time and not raw.deadline_verified.all():
        raise ValueError('Strict training requires verified historical gameweek deadlines; kickoff proxies are retrospective research only')
    if max_rows:
        # Whole players rather than arbitrary shuffled rows preserves sequences.
        raw = raw.sort_values(['season','fpl_id','kickoff']).head(max_rows)
    from ml.features.intelligence import enrich_history
    frame = build_features(enrich_history(session,raw),strict_observed=strict_point_in_time)
    dates = sorted(frame.cutoff.unique())
    cut1, cut2 = dates[int(len(dates)*.65)], dates[int(len(dates)*.8)]
    train_mask, cal_mask, test_mask = (frame.cutoff < cut1)&(frame.available_at<cut1), (frame.cutoff >= cut1) & (frame.cutoff < cut2)&(frame.available_at<cut2), frame.cutoff >= cut2
    if min(train_mask.sum(),cal_mask.sum(),test_mask.sum()) < 30:
        raise ValueError('Insufficient chronological train/calibration/test windows')
    digest = hashlib.sha256(pd.util.hash_pandas_object(raw, index=False).values.tobytes()).hexdigest()
    from pathlib import Path
    code_paths=sorted(Path('ml').rglob('*.py'))+[Path('apps/api/models.py'),Path('apps/api/db.py'),Path('apps/api/config.py')]
    configuration={'features':FEATURES,'epochs':epochs,'lengths':lengths,'kinds':kinds,'strict_point_in_time':strict_point_in_time,'seed':42}
    code_digest=hashlib.sha256(b''.join(p.read_bytes() for p in code_paths)+json.dumps(configuration,sort_keys=True).encode()).hexdigest()[:8]
    folder = settings.artifact_dir / digest[:12]
    folder.mkdir(parents=True, exist_ok=True)
    for path in code_paths:
        copy=folder/'code'/code_digest/path
        copy.parent.mkdir(parents=True,exist_ok=True);copy.write_bytes(path.read_bytes())
    (folder/f'configuration-{code_digest}.json').write_text(json.dumps(configuration,indent=2))
    frame.to_parquet(folder/f'features-{code_digest}.parquet',index=False)
    results, bundles = [], []
    for kind in kinds:
        for length in (lengths if kind in {'lstm','gru'} else (0,)):
            if kind in {'lstm','gru'}:
                x, y, times, label_available = sequence_examples(frame, length,SEQUENCE_FEATURES,return_availability=True)
                if not len(y):
                    continue
                times = pd.to_datetime(times, utc=True)
                label_available=pd.to_datetime(label_available,utc=True)
                tr, ca, te = (times < cut1)&(label_available<cut1), (times >= cut1)&(times < cut2)&(label_available<cut2), times >= cut2
                if min(tr.sum(),ca.sum(),te.sum()) < 30:
                    continue
                pre = make_pipeline(SimpleImputer(strategy='median', keep_empty_features=True, add_indicator=True), StandardScaler())
                pre.fit(x[tr].reshape(-1,len(SEQUENCE_FEATURES)))
                def transform(a):
                    shaped = pre.transform(a.reshape(-1,len(SEQUENCE_FEATURES))).astype('float32')
                    return shaped.reshape(len(a),length,-1)
                xt, xc, xe = transform(x[tr]), transform(x[ca]), transform(x[te])
                torch.manual_seed(42+length+(100 if kind=='gru' else 0))
                model = RecurrentRegressor(xt.shape[-1],kind)
                opt = torch.optim.Adam(model.parameters(), lr=.002)
                loader = DataLoader(MatchSequenceDataset(xt,y[tr]),batch_size=256,shuffle=True,generator=torch.Generator().manual_seed(42))
                model.train()
                for _ in range(epochs):
                    for batch, target in loader:
                        opt.zero_grad()
                        loss = ((model(batch)-target)**2).mean()
                        loss.backward()
                        opt.step()
                model.eval()
                with torch.no_grad():
                    pc = model(torch.tensor(xc)).numpy()
                    pt = model(torch.tensor(xe)).numpy()
                yc, yt = y[ca], y[te]
                fitted = {'state': model.state_dict(), 'input_size':xt.shape[-1], 'pre':pre}
            else:
                x = frame[FEATURES].astype(float)
                y = frame.points.to_numpy(float)
                if kind == 'baseline':
                    prior = frame.loc[train_mask].groupby('position').points.mean().to_dict()
                    overall = float(y[train_mask].mean())
                    all_pred = frame.points_5.fillna(frame.position.map(prior)).fillna(overall).to_numpy()
                    pc, pt = all_pred[cal_mask], all_pred[test_mask]
                    fitted = {'position_prior':prior,'overall':overall}
                else:
                    if kind == 'catboost':
                        from catboost import CatBoostRegressor
                        regressor = CatBoostRegressor(iterations=150, depth=5, learning_rate=.06, random_seed=42, verbose=False, thread_count=2, allow_writing_files=False)
                    elif kind == 'lightgbm':
                        from lightgbm import LGBMRegressor
                        regressor = LGBMRegressor(n_estimators=150, num_leaves=20, random_state=42, n_jobs=2, verbosity=-1)
                    else:
                        raise ValueError(kind)
                    fitted = make_pipeline(SimpleImputer(strategy='median', keep_empty_features=True, add_indicator=True),regressor)
                    age = (frame.cutoff.max()-frame.loc[train_mask,'cutoff']).dt.days.to_numpy()
                    weights = np.exp(-np.log(2)*age/730)
                    name = list(fitted.named_steps)[-1]
                    fitted.fit(x[train_mask],y[train_mask],**{f'{name}__sample_weight':weights})
                    pc, pt = fitted.predict(x[cal_mask]), fitted.predict(x[test_mask])
                yc, yt = y[cal_mask], y[test_mask]
            residuals = yc-pc
            score = metrics(yt,pt,residuals)
            score['exact_deadline_fraction']=float(raw.deadline_verified.mean())
            score['evaluation_scope']='Retrospective archive; unknown deadlines use first-GW-fixture boundary, not a verified FPL deadline'
            if kind in {'lstm','gru'}:
                # Target keys follow the same grouping/eligibility rules as sequence_examples.
                matched=[]
                for _,group in frame.groupby('entity_key' if 'entity_key' in frame else ['season','fpl_id']):
                    group=group.sort_values('kickoff')
                    if len(group)>length and group.available_at.notna().all() and group.available_at.is_monotonic_increasing:
                        known=np.minimum(np.searchsorted(datetime_ns(group.available_at),datetime_ns(group.cutoff),side='left'),np.arange(len(group)))
                        matched.extend(group[known>=length].to_dict('records'))
                        continue
                    for i in range(length,len(group)):
                        target=group.iloc[i]
                        previous=group.iloc[:i]
                        if len(previous[previous.available_at<target.cutoff])>=length:
                            matched.append(target)
                matched_frame=pd.DataFrame(matched)
                matched_test=matched_frame[pd.to_datetime(matched_frame.cutoff,utc=True)>=cut2]
                if len(matched_test)!=len(yt): raise ValueError('Recurrent comparison cohort mismatch')
                comparisons={}
                for candidate in bundles:
                    if candidate['kind'] not in {'baseline','catboost','lightgbm'}:continue
                    if candidate['kind']=='baseline':
                        paired=matched_test.points_5.fillna(matched_test.position.map(candidate['positions'])).fillna(candidate['overall']).to_numpy()
                    else:
                        paired=candidate['model'].predict(matched_test[FEATURES])
                    comparisons[candidate['kind']]=metrics(matched_test.points,paired)
                score['matched_tabular_comparison']=comparisons
            if kind not in {'lstm','gru'}:
                active=frame.loc[test_mask,'minutes'].to_numpy()>0
                score['active_player_mae']=float(np.mean(np.abs(yt[active]-pt[active]))) if active.any() else None
                score['active_player_n']=int(active.sum())
            identifier = f'{kind}-{length}-{digest[:12]}-{code_digest}'
            bundle = {'kind':kind,'length':length,'features':SEQUENCE_FEATURES if kind in {'lstm','gru'} else FEATURES,'code_sha256_prefix':code_digest,'model':fitted,'residuals':residuals.tolist(),'dataset_sha256':digest,'train_until':str(cut1),'calibration_until':str(cut2),'metrics':score,'historical_observation_times':'unavailable; retrospective archive simulation','positions':frame.loc[train_mask].groupby('position').points.mean().to_dict(),'overall':float(frame.loc[train_mask].points.mean())}
            path = folder / f'{identifier}.pkl'
            path.write_bytes(pickle.dumps(bundle))
            (folder / f'{identifier}.json').write_text(json.dumps({k:v for k,v in bundle.items() if k not in {'model','residuals'}},indent=2,default=str))
            row = session.get(ModelVersion,identifier)
            if not row:
                session.add(ModelVersion(id=identifier,kind=kind,trained_until=pd.Timestamp(cut2).to_pydatetime(),metrics=score,artifact=str(path),promoted=False))
            results.append({'id':identifier,'kind':kind,'sequence_length':length,**score})
            bundles.append(bundle)
    # Different recurrent lengths have different eligible examples; no cross-model promotion claim.
    eligible = [r for r in results if r['kind'] in {'baseline','catboost','lightgbm'}]
    if eligible:
        best = min(eligible,key=lambda r:r['mae'])
        for row in session.scalars(select(ModelVersion)):
            row.promoted = row.id == best['id']
    session.add(Audit(action='training.complete',payload={'dataset':digest,'results':results,'promotion':'tabular holdout MAE only; no ensemble enabled'}))
    session.commit()
    (folder / 'leaderboard.json').write_text(json.dumps(results,indent=2))
    return results
