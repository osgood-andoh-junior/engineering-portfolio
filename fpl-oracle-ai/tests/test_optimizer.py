import pytest
from ml.optimization.squad import optimize,validate_squad

def pool():
    return [dict(id=i+1,name=f'Test {i}',position=pos,club_id=(i%10)+1,price=45,expected_points=2+(i%7)*.7,lower=0,upper=10) for i,pos in enumerate([1]*5+[2]*12+[3]*12+[4]*8)]

def test_solver_squad_legality_captain_and_budget():
    result=optimize(pool(),budget=1000,locked=[1],excluded=[2])
    assert not validate_squad(result['squad'],1000,result['starters'])
    assert 1 in [p['id'] for p in result['squad']]
    assert 2 not in [p['id'] for p in result['squad']]
    assert result['captain'] in result['starters']
    assert result['vice_captain']!=result['captain']
    by_id={p['id']:p for p in result['squad']}
    assert by_id[result['bench'][0]]['position']==1

def test_infeasible_budget():
    with pytest.raises(ValueError,match='No legal'): optimize(pool(),budget=100)

def test_separate_validator_rejects_duplicate_players():
    assert validate_squad([pool()[0]]*15,1000)
