import {describe,it,expect} from 'vitest';
import {parsePublicSquad,snapshotPlayers,formation,publicFinances,recommendedPlayers,importedOptimizationSchema} from './public-squad';

function fixture(){
 const positions=[1,2,2,2,2,3,3,3,3,4,4,1,4,3,2];
 const picks=positions.map((pos,i)=>({element:(i+1)*10,position:i+1,multiplier:i===9?2:i<11?1:0,is_captain:i===12,is_vice_captain:i===9,element_type:pos}));
 const prediction={expected_points:4,lower:0,upper:8,p60:.8,p_zero_minutes:.1,model_id:'test-only',generated_at:'2026-10-29T12:00:00Z',stale:false};
 return {entry:{id:12345,name:'Test-only team',current_event:8,last_deadline_bank:99,last_deadline_value:1000},picks:{active_chip:'wildcard',automatic_subs:[{element_in:50,element_out:130,event:8}],entry_history:{event:8,bank:0,value:1020,points:43},picks},resolved:{manager_id:12345,gameweek:8,season:'2026-27',imported_at:'2026-10-29T12:00:00Z',forecast_event:9,unresolved_fpl_ids:[],limitations:[],players:picks.map(p=>({fpl_id:p.element,slot:p.position,multiplier:p.multiplier,is_captain:p.is_captain,is_vice_captain:p.is_vice_captain,position:p.element_type,id:1000+p.position,name:`Test player ${p.position}`,club_id:1,club:'Test club',club_short:'TEST',price:50,status:'a',registration_state:'verified',predictions:{'1':prediction,'3':{...prediction,expected_points:12,upper:24},'5':{...prediction,expected_points:20,upper:40}}}))}};
}

describe('typed public squad',()=>{
 it('retains all fifteen resolved IDs and distinguishes the final XI, bench and inherited captaincy',()=>{
  const squad=parsePublicSquad(fixture());const players=snapshotPlayers(squad);
  expect(players).toHaveLength(15);expect(players.filter(p=>p.slot<=11)).toHaveLength(11);
  expect(players.filter(p=>p.slot>11)).toHaveLength(4);expect(formation(players)).toBe('4-4-2');
  expect(players[12].is_captain).toBe(true);expect(players[12].slot).toBe(13);
  expect(players[9].is_vice_captain).toBe(true);expect(players[9].multiplier).toBe(2);
  expect(players[0].id).toBe(1001);expect(players[0].fpl_id).toBe(10);
 });
 it('reconstructs the submitted formation without mutating source picks',()=>{
  const squad=parsePublicSquad(fixture());const before=JSON.stringify(squad);
  const submitted=snapshotPlayers(squad,true);expect(formation(submitted)).toBe('3-4-3');
  expect(submitted.find(p=>p.fpl_id===130)?.slot).toBe(5);expect(submitted.find(p=>p.fpl_id===50)?.slot).toBe(13);
  expect(JSON.stringify(squad)).toBe(before);
 });
 it('does not confuse zero bank or historic finances with the latest entry data',()=>{
  const raw=fixture();expect(publicFinances(parsePublicSquad(raw))).toEqual({bank:0,value:1020});
  const missing={...raw,picks:{...raw.picks,entry_history:{event:8}},entry:{...raw.entry,current_event:9}};
  expect(publicFinances(parsePublicSquad(missing))).toEqual({bank:null,value:null});
 });
 it('rejects duplicate picks, inconsistent mappings and incomplete fifteen-player responses',()=>{
  const raw=fixture();raw.picks.picks[1].element=raw.picks.picks[0].element;expect(()=>parsePublicSquad(raw)).toThrow('incomplete or inconsistent');
  const mismatch=fixture();mismatch.resolved.players[0].fpl_id=999;expect(()=>parsePublicSquad(mismatch)).toThrow();
  const short=fixture();short.resolved.players.pop();expect(()=>parsePublicSquad(short)).toThrow();
 });
 it('uses the requested stored horizon and preserves null forecasts',()=>{
  const raw=fixture();const squad=parsePublicSquad(raw);
  expect(squad.resolved.players[0].predictions['3']?.expected_points).toBe(12);
  const missing={...raw,resolved:{...raw.resolved,players:raw.resolved.players.map((p,i)=>i===0?{...p,predictions:{'1':null,'3':null,'5':null}}:p)}};
  expect(parsePublicSquad(missing).resolved.players[0].predictions['1']).toBeNull();
 });
 it('renders an optimized lineup from canonical IDs with four ordered substitutes',()=>{
  const squad=parsePublicSquad(fixture());const result=importedOptimizationSchema.parse({scope:'lineup_only',horizon:3,forecast_event:9,source_gameweek:8,strategy:'BALANCED',squad:squad.resolved.players.map(p=>({...p.predictions["3"],id:p.id,name:p.name,club:p.club,club_short:p.club_short,position:p.position,price:p.price,expected_points:15})),starters:squad.resolved.players.slice(0,11).map(p=>p.id),captain:1010,vice_captain:1006,bench:[1012,1013,1014,1015],expected_net_points:180,solver_status:'OPTIMAL',transfers:[],transfer_status:'unavailable_private_state',limitations:[]});
  const players=recommendedPlayers(squad,result);expect(players.filter(p=>p.slot<=11)).toHaveLength(11);
  expect(players.find(p=>p.is_captain)?.id).toBe(1010);expect(players.find(p=>p.is_vice_captain)?.id).toBe(1006);
  expect(players.filter(p=>p.slot>11).map(p=>p.id)).toEqual(result.bench);expect(players[0].predictions['3']?.expected_points).toBe(15);
 });
});
