"""Coherent calibrated playing-time buckets from observed minutes, not inferred starts."""
import hashlib
import pickle
import numpy as np
from scipy.optimize import minimize_scalar
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.metrics import log_loss
from apps.api.config import settings
from apps.api.models import ModelVersion,Audit
from ml.training.train import load_frame
from ml.features.point_in_time import build_features,FEATURES
from ml.features.intelligence import enrich_history

def temperature_scale(probabilities,temperature):
    scores=np.log(np.clip(probabilities,1e-9,1))/temperature
    scores-=scores.max(axis=1,keepdims=True)
    exp=np.exp(scores)
    return exp/exp.sum(axis=1,keepdims=True)

def train_minutes(session):
    raw=load_frame(session);session.commit()
    if len(raw)<500: raise ValueError('At least 500 real match observations required')
    frame=build_features(enrich_history(session,raw))
    dates=sorted(frame.cutoff.unique());a,b=dates[int(len(dates)*.65)],dates[int(len(dates)*.8)]
    tr=(frame.cutoff<a)&(frame.available_at<a);ca=(frame.cutoff>=a)&(frame.cutoff<b)&(frame.available_at<b);te=frame.cutoff>=b
    labels=np.where(frame.minutes==0,0,np.where(frame.minutes<60,1,2))
    if len(np.unique(labels[tr]))!=3: raise ValueError('All playing-time buckets must be observed in training')
    model=make_pipeline(SimpleImputer(keep_empty_features=True,add_indicator=True),HistGradientBoostingClassifier(max_iter=100,max_leaf_nodes=15,random_state=42))
    model.fit(frame.loc[tr,FEATURES],labels[tr])
    cal=model.predict_proba(frame.loc[ca,FEATURES])
    optimum=minimize_scalar(lambda t:log_loss(labels[ca],temperature_scale(cal,t),labels=[0,1,2]),bounds=(.25,4),method='bounded')
    temperature=float(optimum.x)
    probabilities=temperature_scale(model.predict_proba(frame.loc[te,FEATURES]),temperature)
    score={'n':int(te.sum()),'log_loss':float(log_loss(labels[te],probabilities,labels=[0,1,2])),'brier_zero_minutes':float(np.mean((probabilities[:,0]-(labels[te]==0))**2)),'brier_60_plus':float(np.mean((probabilities[:,2]-(labels[te]==2))**2)),'temperature':temperature,'start_probability':'unavailable: actual starting-XI labels not warehoused'}
    digest=hashlib.sha256(__import__('pandas').util.hash_pandas_object(raw,index=False).values.tobytes()).hexdigest()
    identifier='minutes-'+digest[:12]+'-'+hashlib.sha256(__import__('pathlib').Path(__file__).read_bytes()).hexdigest()[:8]
    means=[float(frame.loc[tr&(labels==i),'minutes'].mean()) for i in range(3)]
    bundle={'kind':'minutes','model':model,'features':FEATURES,'temperature':temperature,'bucket_minutes':means,'metrics':score,'train_until':str(a),'calibration_until':str(b),'dataset_sha256':digest}
    settings.artifact_dir.mkdir(exist_ok=True,parents=True)
    path=settings.artifact_dir/f'{identifier}.pkl';path.write_bytes(pickle.dumps(bundle))
    if not session.get(ModelVersion,identifier):session.add(ModelVersion(id=identifier,kind='minutes',trained_until=b.to_pydatetime(),metrics=score,artifact=str(path),promoted=False))
    session.add(Audit(action='minutes.training.complete',payload={'model':identifier,'metrics':score}));session.commit()
    return {'model':identifier,**score}
