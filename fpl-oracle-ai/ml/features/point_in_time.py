"""Shared numerical schema for trees and recurrent models; missing observations stay NaN."""
import numpy as np
import pandas as pd

PLAYER = ['points_3','points_5','points_10','minutes_5','sixty_minute_rate_5','price','position']
FIXTURE = ['home']  # Season-local opponent IDs are identities, not numerical strength ratings.
MANAGER = ['manager_tenure_days','manager_matches','manager_60_rate','manager_minutes']
TACTICAL = ['possession_5','formation_changes','regime_matches']
TRANSFER = ['arrivals_30','competition','cold_start']
FEATURES = PLAYER + FIXTURE + MANAGER + TACTICAL + TRANSFER
SEQUENCE_FEATURES = FEATURES + ['points','minutes','xg','xa']

def datetime_ns(values):
    # Pandas/Parquet can mix microsecond and nanosecond resolutions. Normalize before searchsorted.
    return pd.to_datetime(values,utc=True).astype('datetime64[ns, UTC]').astype('int64').to_numpy()

def build_features(frame: pd.DataFrame, strict_observed=False):
    df = frame.copy().sort_values(['entity_key','kickoff'] if 'entity_key' in frame else ['season','fpl_id','kickoff'])
    df['kickoff'] = pd.to_datetime(df.kickoff, utc=True)
    # A conservative three-hour availability lag prevents unfinished matches entering history.
    df['available_at'] = df.kickoff + pd.Timedelta(hours=3)
    if 'observed_at' in df:
        observed = pd.to_datetime(df.observed_at, utc=True)
        df['available_at'] = df.available_at.where(observed.isna() | (df.available_at >= observed), observed)
        if strict_observed:
            df.loc[observed.isna(), 'available_at'] = pd.NaT
    output = []
    for _, group in df.groupby('entity_key' if 'entity_key' in df else ['season','fpl_id'], sort=False):
        cutoffs=pd.to_datetime(group['deadline'],utc=True) if 'deadline' in group else group.kickoff
        # For monotone availability, prefix sums reconstruct every cutoff exactly in O(n).
        # Late, out-of-order observations use the general filtered implementation below.
        if group.available_at.notna().all() and group.available_at.is_monotonic_increasing:
            available=datetime_ns(group.available_at)
            k=np.minimum(np.searchsorted(available,datetime_ns(cutoffs),side='left'),np.arange(len(group)))
            result=group.copy()
            for feature in FEATURES: result[feature]=np.nan
            points=np.r_[0,np.cumsum(group.points.to_numpy(float))]
            mins=np.r_[0,np.cumsum(group.minutes.to_numpy(float))]
            starts=np.r_[0,np.cumsum((group.minutes>=60).to_numpy(float))]
            for n in (3,5,10):
                left=np.maximum(0,k-n);denom=np.minimum(k,n).astype(float);denom[denom==0]=np.nan
                result[f'points_{n}']=(points[k]-points[left])/denom
            left=np.maximum(0,k-5);denom=np.minimum(k,5).astype(float);denom[denom==0]=np.nan
            result['minutes_5']=(mins[k]-mins[left])/denom
            result['sixty_minute_rate_5']=(starts[k]-starts[left])/denom
            for f in ('position','home','opponent'):
                if f in group: result[f]=group[f].astype(float)
            if 'price' in group:
                previous_price=group.price.to_numpy(dtype=float,na_value=np.nan)[np.maximum(k-1,0)]
                result['price']=np.where(k>0,previous_price,np.nan)
            result['cold_start']=(k<3).astype(int)
            if 'context_observed_at' in group:
                observed_context=pd.to_datetime(group.context_observed_at,utc=True)
                valid=observed_context.notna()&(observed_context<cutoffs)
                for f in MANAGER+TACTICAL+TRANSFER[:-1]:
                    if f in group: result[f]=group[f].where(valid,np.nan)
            result['cutoff']=cutoffs
            result['history_count']=k
            output.extend(result.to_dict('records'))
            continue
        for _, row in group.iterrows():
            cutoff = pd.to_datetime(row.get('deadline', row.kickoff), utc=True)
            past = group[(group.available_at < cutoff) & (group.kickoff < row.kickoff)]
            values = {f: np.nan for f in FEATURES}
            for n in (3,5,10):
                values[f'points_{n}'] = past.tail(n).points.mean()
            values.update(minutes_5=past.tail(5).minutes.mean(), sixty_minute_rate_5=(past.tail(5).minutes >= 60).mean() if len(past) else np.nan, price=past.iloc[-1].get('price',np.nan) if len(past) else np.nan, position=row.get('position', np.nan), home=float(row.get('home', False)), opponent=row.get('opponent', np.nan), cold_start=int(len(past) < 3))
            # Supplied context must already carry its observed timestamp and be available before cutoff.
            context_at = row.get('context_observed_at')
            if context_at is not None and pd.notna(context_at) and pd.to_datetime(context_at, utc=True) < cutoff:
                for f in MANAGER + TACTICAL + TRANSFER[:-1]:
                    values[f] = row.get(f, np.nan)
            output.append({**row.to_dict(), **values, 'cutoff': cutoff, 'history_count': len(past)})
    return pd.DataFrame(output).sort_values('kickoff',kind='stable').reset_index(drop=True)

def sequence_examples(frame, length, features=FEATURES,return_availability=False):
    xs, ys, times,availability = [], [], [],[]
    # Context belongs to each historical row; never broadcast the current coach backwards.
    for _, group in frame.groupby('entity_key' if 'entity_key' in frame else ['season','fpl_id']):
        group = group.sort_values('kickoff')
        if len(group)>length and group.available_at.notna().all() and group.available_at.is_monotonic_increasing:
            arr=group.reindex(columns=features).to_numpy(float)
            windows=np.lib.stride_tricks.sliding_window_view(arr,window_shape=length,axis=0).transpose(0,2,1)
            cutoff=group.cutoff.to_numpy()
            known=np.minimum(np.searchsorted(datetime_ns(group.available_at),datetime_ns(group.cutoff),side='left'),np.arange(len(group)))
            valid=known>=length
            xs.extend(windows[known[valid]-length]);ys.extend(group.points.to_numpy(float)[valid]);times.extend(cutoff[valid])
            availability.extend(group.available_at.to_numpy()[valid])
            continue
        for i in range(length, len(group)):
            target = group.iloc[i]
            previous = group.iloc[:i]
            previous = previous[previous.available_at < target.cutoff].tail(length)
            if len(previous) == length:
                xs.append(previous[features].to_numpy(float))
                ys.append(float(target.points))
                times.append(target.cutoff)
                availability.append(target.available_at)
    result=np.asarray(xs),np.asarray(ys),np.asarray(times)
    return (*result,np.asarray(availability)) if return_availability else result
