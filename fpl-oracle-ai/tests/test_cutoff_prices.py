import pandas as pd
from ml.features.point_in_time import build_features,sequence_examples

def test_target_price_is_not_read_from_post_match_snapshot():
    frame=pd.DataFrame([{'season':'test','fpl_id':1,'kickoff':'2025-01-01T12:00:00Z','points':3,'minutes':90,'price':50,'position':3},{'season':'test','fpl_id':1,'kickoff':'2025-01-08T12:00:00Z','points':20,'minutes':90,'price':999,'position':3}])
    result=build_features(frame)
    assert pd.isna(result.iloc[0].price)
    assert result.iloc[1].price==50
