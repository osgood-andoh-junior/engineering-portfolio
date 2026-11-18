import numpy as np
import pandas as pd

def metrics(y, pred, residuals=None):
    y, pred = np.asarray(y), np.asarray(pred)
    rank = pd.Series(y).rank().corr(pd.Series(pred).rank()) if len(set(pred)) > 1 else 0.0
    result = {'mae': float(np.mean(np.abs(y-pred))), 'rmse': float(np.sqrt(np.mean((y-pred)**2))), 'bias': float(np.mean(pred-y)), 'spearman': float(rank) if np.isfinite(rank) else None, 'n': len(y)}
    if residuals is not None:
        low, high = np.quantile(residuals, [.05,.95])
        result['interval_coverage_90'] = float(((y >= pred+low) & (y <= pred+high)).mean())
        result['pinball_05'] = float(np.maximum(.05*(y-pred-low), -.95*(y-pred-low)).mean())
        ordered=np.sort(np.asarray(residuals))
        probability=1-np.searchsorted(ordered,10-pred,side='left')/len(ordered)
        result['brier_10'] = float(np.mean((probability - (y>=10))**2))
        result['calibrated_expected_mae']=float(np.mean(np.abs(y-(pred+np.mean(residuals)))))
    return result
