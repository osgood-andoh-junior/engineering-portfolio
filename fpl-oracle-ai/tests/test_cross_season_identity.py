import pandas as pd
from ml.features.point_in_time import build_features,sequence_examples

def test_only_verified_entity_codes_join_history_across_seasons():
    rows=[{'season':'2024-25','fpl_id':1,'entity_key':'code:123','kickoff':'2025-05-01T12:00:00Z','points':7,'minutes':90,'price':60,'position':3},{'season':'2025-26','fpl_id':999,'entity_key':'code:123','kickoff':'2025-08-01T12:00:00Z','points':4,'minutes':90,'price':65,'position':3},{'season':'2025-26','fpl_id':1,'entity_key':'code:456','kickoff':'2025-08-01T12:00:00Z','points':3,'minutes':90,'price':45,'position':3}]
    frame=build_features(pd.DataFrame(rows))
    same=frame[(frame.season=='2025-26')&(frame.fpl_id==999)].iloc[0]
    unrelated=frame[(frame.season=='2025-26')&(frame.fpl_id==1)].iloc[0]
    assert same.points_3==7 and same.history_count==1
    assert unrelated.history_count==0
    x,y,_=sequence_examples(frame,1,features=['points'])
    assert y.tolist()==[4] and x[:,0,0].tolist()==[7]
