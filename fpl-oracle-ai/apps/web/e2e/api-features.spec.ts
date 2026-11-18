import {test,expect} from '@playwright/test';
type SolvedSquad={squad:{id:number;position:number}[];starters:number[];cost:number;captain:number;vice_captain:number;bench:number[]};

test('all forecast horizons return coherent stored probabilities and complete pagination',async({request})=>{
 for(const horizon of [1,3,5]){
  // Native keep-alive sockets can close while the previous large payload is checked.
  // Playwright retries ECONNRESET only; HTTP error responses still fail below.
  const response=await request.get(`/api/oracle/predictions?horizon=${horizon}&limit=500`,{maxRetries:1});
  expect(response.status()).toBe(200);const data=await response.json();
  const secondResponse=await request.get(`/api/oracle/predictions?horizon=${horizon}&limit=500&offset=500`,{maxRetries:1});
  expect(secondResponse.status()).toBe(200);const second=await secondResponse.json();
  const rows=[...data.items,...second.items];expect(rows).toHaveLength(data.total);
  expect(new Set(rows.map(r=>r.id)).size).toBe(data.total);
  for(const p of rows.filter(p=>p.expected_points!==null)){
   expect(p.horizon).toBe(horizon);expect(p.lower).toBeLessThanOrEqual(p.upper);
   for(const key of ['p6','p10','p15','p60','p_zero_minutes']){expect(p[key]).toBeGreaterThanOrEqual(0);expect(p[key]).toBeLessThanOrEqual(1)}
   expect(p.p15).toBeLessThanOrEqual(p.p10);expect(p.p10).toBeLessThanOrEqual(p.p6);
   expect(p.p60+p.p_zero_minutes).toBeLessThanOrEqual(1.000001);
  }
 }
});
test('legal-squad constraints, locked/excluded players, captain and unavailable planning modes',async({request})=>{
 test.setTimeout(60000);
 const base={budget:1000,horizon:1,strategy:'BALANCED'};
 let response=await request.post('/api/oracle/optimizer/squad',{data:base});expect(response.status()).toBe(200);
 const original=await response.json() as SolvedSquad;const locked=original.captain,excluded=original.bench[0];
 response=await request.post('/api/oracle/optimizer/squad',{data:{...base,locked:[locked],excluded:[excluded]}});
 expect(response.status()).toBe(200);const result=await response.json() as SolvedSquad;
 expect(result.squad).toHaveLength(15);expect(result.starters).toHaveLength(11);expect(result.cost).toBeLessThanOrEqual(base.budget);
 expect(result.squad.map(p=>p.id)).toContain(locked);expect(result.squad.map(p=>p.id)).not.toContain(excluded);
 expect(result.starters).toContain(result.captain);expect(result.starters).toContain(result.vice_captain);expect(result.captain).not.toBe(result.vice_captain);
 expect(result.bench).toHaveLength(4);expect(result.squad.find(p=>p.id===result.bench[0])?.position).toBe(1);
 const valid=await request.post('/api/oracle/squad/validate',{data:{player_ids:result.squad.map(p=>p.id),starters:result.starters,captain:result.captain,vice_captain:result.vice_captain,budget:1000}});
 expect((await valid.json()).valid).toBe(true);
 for(const chip of ['wildcard','free_hit','bench_boost','triple_captain']){
  expect((await request.post('/api/oracle/optimizer/squad',{data:{...base,chip}})).status()).toBe(409);
 }
 expect((await request.post('/api/oracle/optimizer/transfers',{data:{...base,current:result.squad.map(p=>p.id)}})).status()).toBe(409);
 expect((await request.post('/api/oracle/optimizer/squad',{data:{...base,budget:1}})).status()).toBe(422);
 expect((await request.post('/api/oracle/optimizer/squad',{data:{...base,locked:[locked],excluded:[locked]}})).status()).toBe(422);
 expect((await request.post('/api/oracle/optimizer/captain',{data:base})).status()).toBe(200);
});
test('invalid inputs, missing records and internal routes are rejected safely',async({request})=>{
 for(const route of ['players/999999999','managers/999999999','internal/events','not-a-resource']){
  expect((await request.get('/api/oracle/'+route)).status()).toBe(404);
 }
 for(const route of ['players?limit=10000','predictions?horizon=2','fixtures?limit=-1']){
  expect((await request.get('/api/oracle/'+route)).status()).toBe(422);
 }
 expect((await request.post('/api/oracle/analyst/query',{data:{question:'x'}})).status()).toBe(422);
 expect((await request.post('/api/oracle/transfers/compare',{data:{outgoing:493,incoming:493}})).status()).toBe(409);
 expect((await request.post('http://127.0.0.1:8000/api/v1/internal/managers',{data:{name:'Must not be created'}})).status()).toBe(401);
});
test('public manager import renders a real squad without shared caching',async({page})=>{
 test.setTimeout(60000);await page.goto('/squad');
 await page.getByLabel('Public manager ID').fill('1');await page.getByLabel('Gameweek',{exact:true}).fill('1');
 const returned=page.waitForResponse(r=>r.url().includes('/api/oracle/managers/fpl/1/squad'));
 await page.getByRole('button',{name:'Import squad'}).click();const response=await returned;
 expect(response.status()).toBe(200);expect(response.headers()['cache-control']).toBe('no-store');
 const data=await response.json();expect(data.picks.picks).toHaveLength(15);
 await expect(page.getByRole('region',{name:'Squad snapshot'}).locator('.import-player')).toHaveCount(15);
 await expect(page.getByRole('region',{name:'Squad snapshot'}).locator('.facts,pre')).toHaveCount(0);
});
