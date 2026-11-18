import numpy as np

def distribution(mean, residuals, cold_start=False,context_uncertain=False):
    r = np.asarray(residuals, float)
    if len(r) < 30:
        raise ValueError('Insufficient held-out calibration observations')
    samples = mean+r.mean()+(r-r.mean())*(1.5 if cold_start or context_uncertain else 1)
    return {'expected_points': float(samples.mean()), 'median': float(np.median(samples)), 'lower': float(np.quantile(samples,.05)), 'upper': float(np.quantile(samples,.95)), 'p6': float((samples >= 6).mean()), 'p10': float((samples >= 10).mean()), 'p15': float((samples >= 15).mean()), 'cold_start': cold_start,'context_uncertain':context_uncertain, 'interval_level': .90, 'calibration': 'held-out empirical residuals; marginal coverage only; sparse/new-manager spread inflation is a conservative policy, not conditionally validated coverage'}
