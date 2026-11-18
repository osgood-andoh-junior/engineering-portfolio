"""Integer-price CP-SAT optimization with an independent legality validator."""
from collections import Counter
from ortools.sat.python import cp_model

def validate_squad(players,budget,starters=None):
    errors=[]
    if len(players)!=15 or len({p['id'] for p in players})!=15:
        errors.append('Exactly 15 distinct players required')
    if Counter(p['position'] for p in players)!=Counter({1:2,2:5,3:5,4:3}):
        errors.append('Squad must contain 2 GK, 5 DEF, 5 MID, 3 FWD')
    if any(n>3 for n in Counter(p['club_id'] for p in players).values()):
        errors.append('Maximum three players per club')
    if sum(p['price'] for p in players)>budget:
        errors.append('Budget exceeded')
    if starters is not None:
        xi=[p for p in players if p['id'] in starters]
        counts=Counter(p['position'] for p in xi)
        if len(xi)!=11 or len(set(starters))!=11 or counts[1]!=1 or not 3<=counts[2]<=5 or not 2<=counts[3]<=5 or not 1<=counts[4]<=3:
            errors.append('Illegal starting XI')
    return errors

def optimize(players,budget=1000,strategy='BALANCED',locked=(),excluded=(),current=(),free_transfers=1,hit_cost=4,chip=None):
    if set(locked)&set(excluded):
        raise ValueError('Locked and excluded players overlap')
    if any(p.get('expected_points') is None for p in players):
        raise ValueError('Real prediction batch required')
    candidates={p['id']:p for p in players}
    if set(locked)-candidates.keys():
        raise ValueError('Locked player unavailable')
    model=cp_model.CpModel()
    squad={i:model.new_bool_var(f'squad_{i}') for i in candidates}
    xi={i:model.new_bool_var(f'xi_{i}') for i in candidates}
    captain={i:model.new_bool_var(f'captain_{i}') for i in candidates}
    model.add(sum(squad.values())==15)
    model.add(sum(xi.values())==11)
    model.add(sum(captain.values())==1)
    for i in candidates:
        model.add(xi[i]<=squad[i]); model.add(captain[i]<=xi[i])
        if i in locked: model.add(squad[i]==1)
        if i in excluded: model.add(squad[i]==0)
    for position,number in {1:2,2:5,3:5,4:3}.items():
        model.add(sum(squad[i] for i,p in candidates.items() if p['position']==position)==number)
    for club in {p['club_id'] for p in players}:
        model.add(sum(squad[i] for i,p in candidates.items() if p['club_id']==club)<=3)
    model.add(sum(xi[i] for i,p in candidates.items() if p['position']==1)==1)
    for pos,low,high in [(2,3,5),(3,2,5),(4,1,3)]:
        number=sum(xi[i] for i,p in candidates.items() if p['position']==pos)
        model.add(number>=low); model.add(number<=high)
    model.add(sum(p['price']*squad[i] for i,p in candidates.items())<=budget)
    paid=model.new_int_var(0,15,'paid_transfers')
    arrivals=sum(squad[i] for i in candidates if i not in current)
    if current and chip not in {'wildcard','free_hit'}:
        model.add(paid>=arrivals-free_transfers)
    else:
        model.add(paid==0)
    terms=[]
    for i,p in candidates.items():
        mean=p['expected_points']
        score=mean-(mean-p.get('lower',mean))*.15 if strategy=='CONSERVATIVE' else mean+(p.get('upper',mean)-mean)*.10 if strategy=='AGGRESSIVE' else mean
        value=int(round(score*1000))
        terms.extend([value*(squad[i] if chip=='bench_boost' else xi[i]),value*(2 if chip=='triple_captain' else 1)*captain[i]])
    model.maximize(sum(terms)-paid*hit_cost*1000)
    solver=cp_model.CpSolver(); solver.parameters.max_time_in_seconds=10; solver.parameters.num_search_workers=2
    status=solver.solve(model)
    if status not in {cp_model.OPTIMAL,cp_model.FEASIBLE}:
        raise ValueError('No legal squad within the supplied constraints')
    chosen=[p for i,p in candidates.items() if solver.value(squad[i])]
    starters=[i for i in candidates if solver.value(xi[i])]
    errors=validate_squad(chosen,budget,starters)
    if errors: raise RuntimeError('; '.join(errors))
    captain_id=next(i for i in candidates if solver.value(captain[i]))
    vice=max((i for i in starters if i!=captain_id),key=lambda i:candidates[i]['expected_points'])
    bench=sorted((p for p in chosen if p['id'] not in starters),key=lambda p:(p['position']!=1,-p['expected_points']))
    gross=sum(p['expected_points'] for p in chosen if p['id'] in starters or chip=='bench_boost')+candidates[captain_id]['expected_points']*(2 if chip=='triple_captain' else 1)
    return {'squad':chosen,'starters':starters,'captain':captain_id,'vice_captain':vice,'bench':[p['id'] for p in bench],'cost':sum(p['price'] for p in chosen),'paid_transfers':solver.value(paid),'expected_net_points':gross-solver.value(paid)*hit_cost,'solver_status':solver.status_name(status),'strategy':strategy,'limitations':['Bench order uses expected points, not automatic-substitution simulation','Risk coefficients are user preference weights, not learned tactical ratings']}
