import numpy as np
from ml.training.minutes import temperature_scale

def test_temperature_probabilities_are_coherent():
    p=temperature_scale(np.array([[.8,.1,.1],[.01,.09,.9]]),1.5)
    assert np.allclose(p.sum(axis=1),1)
    assert np.all((p>=0)&(p<=1))
    assert np.all(p[:,2]<=1-p[:,0]+1e-10)
