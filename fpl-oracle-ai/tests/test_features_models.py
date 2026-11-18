import numpy as np
import pandas as pd
import pytest
from ml.features.point_in_time import build_features,sequence_examples,FEATURES
from ml.features.intelligence import sustained_change
from ml.calibration.distribution import distribution

def frame():
    return pd.DataFrame([dict(season='2024-25',fpl_id=1,fixture=i,kickoff=f'2024-08-{i+1:02}T12:00:00Z',points=i,minutes=90,position=3,price=70,home=True,opponent=2,observed_at=None) for i in range(25)])

def test_target_changes_do_not_affect_own_features():
    data=frame();a=build_features(data);data.loc[12,'points']=10000;b=build_features(data)
    assert a.iloc[12].points_5==b.iloc[12].points_5
    assert a.iloc[13].points_5!=b.iloc[13].points_5

def test_post_deadline_observation_excluded():
    data=frame();data['observed_at']=None;data.loc[0,'observed_at']='2024-10-01T00:00:00Z'
    output=build_features(data)
    assert output.iloc[1].history_count==0
    strict=build_features(data,strict_observed=True)
    assert strict.iloc[-1].history_count==0

def test_future_manager_context_is_not_used():
    data=frame();data['manager_minutes']=99;data['context_observed_at']='2025-01-01T00:00:00Z'
    assert build_features(data).manager_minutes.isna().all()

@pytest.mark.parametrize('length',[5,10,15,20])
def test_sequences_have_historical_context(length):
    data=build_features(frame());x,y,t=sequence_examples(data,length)
    assert x.shape[1:]==(length,len(FEATURES))
    assert len(x)==len(y)==len(t)

@pytest.mark.parametrize('kind',['lstm','gru'])
def test_recurrent_backward(kind):
    import torch
    from ml.models.recurrent import RecurrentRegressor
    model=RecurrentRegressor(len(FEATURES),kind)
    x=torch.randn(4,5,len(FEATURES)); y=model(x)
    assert y.shape==(4,)
    (y**2).mean().backward()
    assert model.head.weight.grad is not None

def test_no_regime_change_from_single_match():
    assert not sustained_change([40]*10,[70])['detected']
    assert sustained_change([40,41,39,42,38,40],[70,71,69,72,68,70])['detected']

def test_cold_start_interval_is_wider():
    residuals=np.linspace(-4,4,100)
    regular=distribution(3,residuals);cold=distribution(3,residuals,True)
    assert cold['upper']-cold['lower']>regular['upper']-regular['lower']
    assert 0<=regular['p15']<=regular['p10']<=regular['p6']<=1

def test_unknown_manager_context_widens_spread_without_inventing_mean_impact():
    residuals=np.linspace(-3,6,100)
    regular=distribution(3,residuals);uncertain=distribution(3,residuals,context_uncertain=True)
    assert abs(regular['expected_points']-uncertain['expected_points'])<1e-10
    assert uncertain['upper']-uncertain['lower']>regular['upper']-regular['lower']
