import numpy as np
from ml.evaluation.metrics import metrics

def test_empirical_tail_probability_matches_exact_bounded_calculation():
    y=np.array([0,10,15]);pred=np.array([1,8,12]);residuals=np.array([-2,-1,0,2,5])
    probability=((pred[:,None]+residuals[None,:])>=10).mean(axis=1)
    expected=float(np.mean((probability-(y>=10))**2))
    assert abs(metrics(y,pred,residuals)['brier_10']-expected)<1e-12
