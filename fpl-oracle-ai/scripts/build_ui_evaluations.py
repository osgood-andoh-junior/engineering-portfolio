"""Export bounded visualization data from real saved evaluation cohorts, never retrain."""
import gc
import hashlib
import json
import pickle
from pathlib import Path
import numpy as np
import pandas as pd
from sqlalchemy import select
from threadpoolctl import threadpool_limits
from apps.api.db import Session
from apps.api.models import ModelVersion
from apps.api.config import settings
from ml.features.point_in_time import sequence_examples,SEQUENCE_FEATURES


def export(version):
    path=Path(version.artifact).resolve()
    if not path.is_relative_to(settings.artifact_dir.resolve()):raise ValueError('Untrusted artifact path')
    bundle=pickle.loads(path.read_bytes())
    if bundle['kind']=='minutes':return None
    code=bundle.get('code_sha256_prefix')
    feature_path=path.parent/f'features-{code}.parquet'
    if not feature_path.exists():return None
    frame=pd.read_parquet(feature_path)
    cutoff=pd.Timestamp(bundle['calibration_until'])
    if bundle['kind'] in ('lstm','gru'):
        import torch
        from ml.models.recurrent import RecurrentRegressor
        x,y,times=sequence_examples(frame,bundle['length'],SEQUENCE_FEATURES)
        mask=pd.to_datetime(times,utc=True)>=cutoff;x=x[mask];actual=y[mask]
        shaped=bundle['model']['pre'].transform(x.reshape(-1,len(SEQUENCE_FEATURES))).astype('float32').reshape(len(x),bundle['length'],-1)
        model=RecurrentRegressor(bundle['model']['input_size'],bundle['kind']);model.load_state_dict(bundle['model']['state']);model.eval()
        with torch.no_grad():predicted=np.concatenate([model(torch.tensor(shaped[i:i+512])).numpy() for i in range(0,len(shaped),512)])
        importance=[]
    else:
        test=frame[pd.to_datetime(frame.cutoff,utc=True)>=cutoff];actual=test.points.to_numpy(float)
        if bundle['kind']=='baseline':
            predicted=test.points_5.fillna(test.position.map(bundle['positions'])).fillna(bundle['overall']).to_numpy();importance=[]
        else:
            model=bundle['model'];predicted=model.predict(test[bundle['features']])
            raw=model.steps[-1][1].feature_importances_
            names=model.steps[0][1].get_feature_names_out(bundle['features'])
            total=float(np.sum(raw))
            importance=sorted([{'name':str(name),'value':float(value/total*100)} for name,value in zip(names,raw)],key=lambda r:r['value'],reverse=True)[:12] if total else []
    mae=float(np.mean(np.abs(actual-predicted)))
    if len(actual)!=version.metrics.get('n') or abs(mae-version.metrics['mae'])>1e-5:
        raise ValueError(f'{version.id}: reconstructed cohort does not match saved metrics')
    residual=np.asarray(bundle['residuals'],dtype=float)
    probabilities=(len(residual)-np.searchsorted(np.sort(residual),10-predicted,side='left'))/len(residual)
    calibration=[]
    for lo in np.arange(0,1,.1):
        mask=(probabilities>=lo)&(probabilities<(lo+.1) if lo<.9 else probabilities<=1)
        if mask.any():calibration.append({'predicted':float(probabilities[mask].mean()),'observed':float((actual[mask]>=10).mean()),'n':int(mask.sum())})
    counts,edges=np.histogram(actual-predicted,bins=20)
    indices=np.linspace(0,len(actual)-1,min(220,len(actual)),dtype=int)
    return {'available':True,'n':len(actual),'verified_mae':mae,'scatter':[{'actual':float(actual[i]),'predicted':float(predicted[i])} for i in indices],'errors':[{'bin':f'{a:.1f} to {b:.1f}','count':int(n)} for a,b,n in zip(edges[:-1],edges[1:],counts)],'calibration':calibration,'importance':importance,'scope':'Reconstructed saved out-of-time research cohort; count and MAE verified against registered run. Historical deadline/observation coverage is incomplete.'}


def main():
    import torch
    torch.set_num_threads(2)
    with Session() as session:versions=session.scalars(select(ModelVersion).order_by(ModelVersion.created_at.desc())).all()
    selected={}
    for v in versions:
        length=v.id.split('-')[1] if v.kind in ('lstm','gru') else '0'
        selected.setdefault((v.kind,length),v)
    folder=settings.artifact_dir/'ui-evaluations';folder.mkdir(exist_ok=True)
    report=[]
    with threadpool_limits(2):
        for v in selected.values():
            try:
                data=export(v)
                if data:
                    (folder/(hashlib.sha256(v.id.encode()).hexdigest()+'.json')).write_text(json.dumps(data,allow_nan=False))
                    report.append({'model':v.id,'status':'verified','n':data['n'],'mae':data['verified_mae']})
            except Exception as exc:report.append({'model':v.id,'status':'unavailable','reason':str(exc)})
            gc.collect()
    (settings.data_dir/'ui-evaluation-export.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))


if __name__=='__main__':main()
