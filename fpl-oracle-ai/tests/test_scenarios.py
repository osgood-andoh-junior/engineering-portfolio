from ml.simulation.transfer_impact import transfer_scenarios

def test_no_invented_weights_for_unseen_context():
    result=transfer_scenarios([90,90,0])
    assert all(s['weight'] is None for s in result['scenarios'])

def test_evidence_weights_sum_to_one():
    result=transfer_scenarios([90]*10+[30]*5+[0]*5,comparable_context=True)
    assert sum(s['weight'] for s in result['scenarios'])==1
    assert result['scenarios'][0]['weight']==.5
