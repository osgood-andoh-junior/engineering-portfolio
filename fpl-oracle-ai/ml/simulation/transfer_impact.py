"""Evidence-weighted scenarios; unobserved contexts produce unknown weights."""
import numpy as np

def transfer_scenarios(minutes,comparable_context=False,minimum=20):
    observations=np.asarray(minutes,dtype=float)
    observations=observations[np.isfinite(observations)]
    scenarios=[{'scenario':'starts','minutes_condition':'60 or more'},{'scenario':'rotates','minutes_condition':'1 to 59'},{'scenario':'unused','minutes_condition':'0'}]
    if not comparable_context or len(observations)<minimum:
        return {'scenarios':[{**s,'weight':None,'expected_minutes':None} for s in scenarios],'sample_size':len(observations),'reason':'Insufficient comparable same-league role/selection evidence; weights not invented'}
    masks=[observations>=60,(observations>0)&(observations<60),observations==0]
    for scenario,mask in zip(scenarios,masks):
        scenario['weight']=float(mask.mean())
        scenario['expected_minutes']=float(observations[mask].mean()) if mask.any() else None
    return {'scenarios':scenarios,'sample_size':len(observations),'method':'Empirical observed selection frequencies in an explicitly comparable cohort','limitation':'Historical association; a signing is not guaranteed to start'}
