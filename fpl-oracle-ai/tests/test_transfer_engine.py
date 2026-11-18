import pytest
from ml.optimization.transfers import plan,selling_price
from ml.optimization.squad import optimize,validate_squad
def sample():
    return [dict(id=i+1,name=f'Test {i}',position=pos,club_id=i%10+1,price=45,expected_points=2+i%7,lower=0,upper=12,status='a',registration_state='verified') for i,pos in enumerate([1]*5+[2]*12+[3]*12+[4]*8)]
def test_sale_profit_rounding_and_loss():
    assert selling_price(50,53)==51
    assert selling_price(50,54)==52
    assert selling_price(50,47)==47
@pytest.mark.parametrize('maximum',[0,1,2,15])
def test_exact_cash_formation_and_hits(maximum):
    rows=sample();current=[p['id'] for p in optimize(rows)['squad']];sales={i:40 for i in current}
    result=plan(rows,current,sales,20,0,maximum)
    assert result['remaining_bank']==20+sum(sales[t['outgoing']['id']]-t['buying_price'] for t in result['transfers'])
    assert result['transfer_count']<=maximum and result['hit_cost']==result['transfer_count']*4
    assert not validate_squad(result['squad'],10000,result['starters'])
    assert result['net_points']==result['gross_points']-result['hit_cost']
def test_missing_state_and_infeasible_constraints():
    rows=sample();current=[p['id'] for p in optimize(rows)['squad']]
    with pytest.raises(ValueError):plan(rows,current,{},0,1)
    with pytest.raises(ValueError):plan(rows,current,{i:45 for i in current},0,1,0,excluded=[current[0]])
def test_wildcard_and_freehit_no_hits():
    rows=sample();current=[p['id'] for p in optimize(rows)['squad']]
    for chip in ['wildcard','free_hit']:
        assert plan(rows,current,{i:45 for i in current},0,0,15,chip=chip)['hit_cost']==0

def test_forced_transfer_hits_free_allowance_and_unaffordable_rejection():
    rows=sample();current=[p['id'] for p in optimize(rows)['squad']];sales={i:40 for i in current}
    paid=plan(rows,current,sales,20,0,2,excluded=[current[0]])
    assert paid['transfer_count']>=1 and paid['hit_cost']==4*paid['transfer_count']
    free=plan(rows,current,sales,20,2,2,excluded=[current[0]])
    assert free['hit_cost']==0
    with pytest.raises(ValueError):plan(rows,current,{i:0 for i in current},0,2,2,excluded=[current[0]])

def test_keep_plan_does_not_invent_unknown_liquidation_values():
    rows=sample();current=[p['id'] for p in optimize(rows)['squad']]
    result=plan(rows,current,{},10,2,0)
    assert result['transfers']==[] and result['remaining_bank']==10
    assert result['liquidation_value'] is None
