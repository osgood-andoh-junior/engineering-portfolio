"""Single-deadline transfer planning with exact integer selling-value accounting."""
from collections import Counter
from ortools.sat.python import cp_model
from ml.optimization.squad import validate_squad

def selling_price(purchase,current):
    if purchase<0 or current<0:raise ValueError('Prices must be nonnegative')
    return current if current<=purchase else purchase+(current-purchase)//2

def plan(players,current,selling,bank,free_transfers,max_transfers=2,strategy='BALANCED',locked=(),excluded=(),chip=None):
    current=set(current);pool={p['id']:p for p in players if p.get('expected_points') is not None}
    if len(current)!=15 or current-pool.keys():raise ValueError('Fifteen distinct owned players with predictions required')
    if (max_transfers>0 and set(selling)!=current) or set(selling)-current or any(type(v)!=int or v<0 or v>pool[i]['price'] for i,v in selling.items()):raise ValueError('Confirm all fifteen exact selling prices')
    if type(bank)!=int or bank<0 or not 0<=free_transfers<=5:raise ValueError('Confirmed bank and free transfers required')
    if set(locked)&set(excluded) or set(locked)-pool.keys():raise ValueError('Invalid lock/exclusion constraints')
    model=cp_model.CpModel();s={i:model.new_bool_var(f's_{i}') for i in pool};x={i:model.new_bool_var(f'x_{i}') for i in pool};c={i:model.new_bool_var(f'c_{i}') for i in pool}
    model.add(sum(s.values())==15);model.add(sum(x.values())==11);model.add(sum(c.values())==1)
    for i,p in pool.items():
        model.add(x[i]<=s[i]);model.add(c[i]<=x[i])
        if i in locked:model.add(s[i]==1)
        if i in excluded:model.add(s[i]==0)
        if i not in current and (p.get('status')=='u' or p.get('registration_state')!='verified' or p.get('p_zero_minutes')==1):model.add(s[i]==0)
    for pos,n in {1:2,2:5,3:5,4:3}.items():model.add(sum(s[i] for i,p in pool.items() if p['position']==pos)==n)
    for club in {p['club_id'] for p in pool.values()}:model.add(sum(s[i] for i,p in pool.items() if p['club_id']==club)<=3)
    for pos,lo,hi in [(1,1,1),(2,3,5),(3,2,5),(4,1,3)]:
        count=sum(x[i] for i,p in pool.items() if p['position']==pos);model.add(count>=lo);model.add(count<=hi)
    arrivals=sum(s[i] for i in pool if i not in current)
    model.add(arrivals<=max_transfers)
    remaining=bank+sum(selling.get(i,0)*(1-s[i]) for i in current)-sum(p['price']*s[i] for i,p in pool.items() if i not in current)
    model.add(remaining>=0)
    paid=model.new_int_var(0,15,'paid');model.add_max_equality(paid,[arrivals-free_transfers,0])
    hit=0 if chip in ('wildcard','free_hit') else 4
    terms=[]
    for i,p in pool.items():
        mean=p['expected_points'];score=mean
        if strategy=='CONSERVATIVE':score-=.15*(mean-p.get('lower',mean))
        if strategy=='AGGRESSIVE':score+=.1*(p.get('upper',mean)-mean)
        terms.append(round(score*1000)*(x[i]+c[i]))
    model.maximize(sum(terms)-paid*hit*1000)
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=15;solver.parameters.num_search_workers=2
    status=solver.solve(model)
    if status not in (cp_model.OPTIMAL,cp_model.FEASIBLE):raise ValueError('No legal affordable plan under these constraints')
    chosen=[p for i,p in pool.items() if solver.value(s[i])];starters=[i for i in pool if solver.value(x[i])];captain=next(i for i in pool if solver.value(c[i]));vice=max((i for i in starters if i!=captain),key=lambda i:pool[i]['expected_points'])
    sold=sorted(current-{p['id'] for p in chosen});bought=sorted({p['id'] for p in chosen}-current)
    cash=bank+sum(selling[i] for i in sold)-sum(pool[i]['price'] for i in bought)
    errors=validate_squad(chosen,sum(p['price'] for p in chosen),starters)
    if errors or cash<0:raise RuntimeError('Independent transfer validation failed')
    transfers=[]
    for pos in (1,2,3,4):
        outs=[i for i in sold if pool[i]['position']==pos];ins=[i for i in bought if pool[i]['position']==pos]
        if len(outs)!=len(ins):raise RuntimeError('Position-matched transfers required')
        for out,into in zip(outs,ins):transfers.append({'outgoing':pool[out],'incoming':pool[into],'selling_price':selling[out],'buying_price':pool[into]['price'],'individual_points_difference':pool[into]['expected_points']-pool[out]['expected_points'],'explanation':'Constraint-optimized squad contribution; individual difference excludes captaincy and lineup interactions'})
    gross=sum(pool[i]['expected_points'] for i in starters)+pool[captain]['expected_points'];cost=max(0,len(bought)-free_transfers)*hit
    return {'squad':chosen,'starters':starters,'captain':captain,'vice_captain':vice,'bench':sorted((p['id'] for p in chosen if p['id'] not in starters),key=lambda i:(pool[i]['position']!=1,-pool[i]['expected_points'])),'transfers':transfers,'transfer_count':len(bought),'hit_cost':cost,'gross_points':gross,'net_points':gross-cost,'remaining_bank':cash,'liquidation_value':cash+sum(selling[p['id']] if p['id'] in current else p['price'] for p in chosen) if set(selling)==current else None,'solver_status':solver.status_name(status),'chip':chip,'risk':'Preference-weighted individual intervals; joint squad uncertainty uncalibrated','limitations':['One deadline of transfers; horizon aggregates do not simulate future transfers','Bench points excluded from expected XI; no automatic-substitution simulation','Future price changes unknown; liquidation value uses current prices','Free Hit restores original ownership after this gameweek']}
