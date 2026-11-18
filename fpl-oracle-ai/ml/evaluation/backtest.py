"""Reproducible rolling chronological tabular ablations; no random cross-validation."""
import hashlib
import json
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from catboost import CatBoostRegressor
from ml.features.point_in_time import PLAYER,FIXTURE,MANAGER,TACTICAL,TRANSFER
from ml.evaluation.metrics import metrics

ABLATIONS={'A':PLAYER,'B':PLAYER+FIXTURE,'C':PLAYER+FIXTURE+MANAGER,'D':PLAYER+FIXTURE+MANAGER+TACTICAL,'E':PLAYER+FIXTURE+MANAGER+TACTICAL+TRANSFER}

def rolling_backtest(frame,folds=3,iterations=100):
    times=sorted(frame.cutoff.unique())
    if len(times)<30: raise ValueError('At least 30 distinct time cutoffs required')
    boundaries=np.linspace(.5,1,folds+1)
    results=[]
    for fold in range(folds):
        start=times[int(len(times)*boundaries[fold])]
        end=times[min(len(times)-1,int(len(times)*boundaries[fold+1]))]
        train=frame[(frame.cutoff<start)&(frame.available_at<start)]
        test=frame[(frame.cutoff>=start)&(frame.cutoff<end)]
        if len(test)<30: continue
        for window in (1,3,6,'weighted6'):
            years=6 if window=='weighted6' else window
            import pandas as pd
            subset=train[train.cutoff>=pd.Timestamp(start)-pd.DateOffset(years=years)]
            if len(subset)<100: continue
            for ablation,features in ABLATIONS.items():
                available=[f for f in features if subset[f].notna().any()]
                unavailable=[f for f in features if f not in available]
                model=make_pipeline(SimpleImputer(keep_empty_features=True,add_indicator=True),CatBoostRegressor(iterations=iterations,depth=4,verbose=False,random_seed=42,thread_count=2,allow_writing_files=False))
                weight=np.exp(-np.log(2)*(pd.Timestamp(start)-subset.cutoff).dt.days/730) if window=='weighted6' else np.ones(len(subset))
                model.fit(subset[features],subset.points,catboostregressor__sample_weight=weight)
                pred=model.predict(test[features])
                result={'fold':fold,'window':str(window),'ablation':ablation,'train_before':str(start),'test_before':str(end),'available_features':available,'unavailable_features':unavailable,'cohort_sha256':hashlib.sha256(test[['season','fpl_id','fixture']].to_json().encode()).hexdigest(),**metrics(test.points,pred)}
                result['positions']={str(p):metrics(test.loc[test.position==p,'points'],pred[(test.position==p).to_numpy()]) for p in test.position.dropna().unique() if (test.position==p).sum()>10}
                result['note']='Missing context groups cannot demonstrate improvement; identical available features yield equivalent ablations.'
                results.append(result)
    return results
