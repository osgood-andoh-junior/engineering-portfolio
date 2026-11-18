import pandas as pd
from ml.features.point_in_time import build_features,sequence_examples

def test_second_double_gameweek_fixture_cannot_use_first_result():
    rows=[{'season':'test','fpl_id':1,'fixture':1,'kickoff':'2025-01-01T12:00:00Z','deadline':'2025-01-01T10:30:00Z','points':20,'minutes':90,'price':50,'position':3},{'season':'test','fpl_id':1,'fixture':2,'kickoff':'2025-01-04T12:00:00Z','deadline':'2025-01-01T10:30:00Z','points':10,'minutes':90,'price':51,'position':3},{'season':'test','fpl_id':1,'fixture':3,'kickoff':'2025-01-08T12:00:00Z','deadline':'2025-01-08T10:30:00Z','points':3,'minutes':90,'price':52,'position':3}]
    frame=build_features(pd.DataFrame(rows))
    assert frame.iloc[1].history_count==0
    assert frame.iloc[2].points_3==15
    x,y,_=sequence_examples(frame,1)
    assert len(y)==1 and y[0]==3

def test_both_double_gameweek_targets_reuse_the_available_prior_sequence():
    rows=[{'season':'test','fpl_id':1,'fixture':0,'kickoff':'2024-12-20T12:00:00Z','deadline':'2024-12-20T10:30:00Z','points':2,'minutes':90,'price':50,'position':3},{'season':'test','fpl_id':1,'fixture':1,'kickoff':'2025-01-01T12:00:00Z','deadline':'2025-01-01T10:30:00Z','points':20,'minutes':90,'price':50,'position':3},{'season':'test','fpl_id':1,'fixture':2,'kickoff':'2025-01-04T12:00:00Z','deadline':'2025-01-01T10:30:00Z','points':10,'minutes':90,'price':51,'position':3}]
    frame=build_features(pd.DataFrame(rows));x,y,_=sequence_examples(frame,1,features=['points'])
    assert y.tolist()==[20,10]
    assert x[:,0,0].tolist()==[2,2]

def test_mixed_parquet_timestamp_resolutions_preserve_cutoff():
    frame=pd.DataFrame({'season':['test']*2,'fpl_id':[1]*2,'kickoff':pd.to_datetime(['2025-01-01T12:00:00Z','2025-01-04T12:00:00Z'],utc=True).astype('datetime64[us, UTC]'),'deadline':pd.to_datetime(['2025-01-01T10:30:00Z']*2,utc=True).astype('datetime64[ns, UTC]'),'points':[20,10],'minutes':[90,90],'price':[50,51],'position':[3,3]})
    assert build_features(frame).iloc[1].history_count==0
