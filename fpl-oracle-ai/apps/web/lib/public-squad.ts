import {z} from 'zod';

const nullableNumber=z.number().finite().nullable();
const pick=z.object({element:z.number().int().positive(),position:z.number().int().min(1).max(15),multiplier:z.number().int().min(0).max(3),is_captain:z.boolean(),is_vice_captain:z.boolean(),element_type:z.number().int().min(1).max(4).optional()});
const forecast=z.object({expected_points:nullableNumber,lower:nullableNumber,upper:nullableNumber,p60:nullableNumber.optional(),p_zero_minutes:nullableNumber.optional(),model_id:z.string().nullable(),generated_at:z.string().nullable(),stale:z.boolean(),unavailable_reason:z.string().nullable().optional()});
const resolvedPick=z.object({fpl_id:z.number().int().positive(),slot:z.number().int().min(1).max(15),multiplier:z.number().int(),is_captain:z.boolean(),is_vice_captain:z.boolean(),position:z.number().int().min(1).max(4).nullable(),id:z.number().int().positive().nullable(),name:z.string().nullable(),club_id:z.number().nullable(),club:z.string().nullable(),club_short:z.string().nullable(),price:nullableNumber,status:z.string().nullable(),registration_state:z.string().nullable(),predictions:z.object({'1':forecast.nullable(),'3':forecast.nullable(),'5':forecast.nullable()})});
export const publicSquadSchema=z.object({
 entry:z.object({id:z.number().int().positive(),name:z.string(),player_first_name:z.string().optional(),player_last_name:z.string().optional(),current_event:z.number().nullable().optional(),last_deadline_bank:nullableNumber.optional(),last_deadline_value:nullableNumber.optional(),summary_overall_points:nullableNumber.optional()}),
 picks:z.object({active_chip:z.string().nullable(),automatic_subs:z.array(z.object({element_in:z.number(),element_out:z.number(),event:z.number()})).default([]),entry_history:z.object({event:z.number().int(),points:nullableNumber.optional(),total_points:nullableNumber.optional(),overall_rank:nullableNumber.optional(),bank:nullableNumber.optional(),value:nullableNumber.optional(),event_transfers:nullableNumber.optional(),event_transfers_cost:nullableNumber.optional(),points_on_bench:nullableNumber.optional()}),picks:z.array(pick).length(15)}),
 resolved:z.object({manager_id:z.number(),gameweek:z.number(),season:z.string(),imported_at:z.string(),forecast_event:z.number().nullable(),players:z.array(resolvedPick).length(15),unresolved_fpl_ids:z.array(z.number()),limitations:z.array(z.string())}),
}).superRefine((data,context)=>{
 const raw=data.picks.picks;
 const ids=new Set(raw.map(p=>p.element));
 if(ids.size!==15||new Set(raw.map(p=>p.position)).size!==15)context.addIssue({code:'custom',message:'Expected 15 distinct picks and squad slots'});
 if(raw.filter(p=>p.is_captain).length!==1||raw.filter(p=>p.is_vice_captain).length!==1||raw.some(p=>p.is_captain&&p.is_vice_captain))context.addIssue({code:'custom',message:'Captain and vice-captain flags are inconsistent'});
 if(data.entry.id!==data.resolved.manager_id||data.picks.entry_history.event!==data.resolved.gameweek)context.addIssue({code:'custom',message:'Snapshot identity does not match the request'});
 const resolvedIds=new Set(data.resolved.players.map(p=>p.fpl_id));
 if(resolvedIds.size!==15||data.resolved.players.some(p=>!ids.has(p.fpl_id)))context.addIssue({code:'custom',message:'Resolved player IDs do not match the public picks'});
 for(const sub of data.picks.automatic_subs)if(sub.event!==data.resolved.gameweek||!ids.has(sub.element_in)||!ids.has(sub.element_out))context.addIssue({code:'custom',message:'Automatic substitution does not belong to this snapshot'});
 const unresolved=data.resolved.players.filter(p=>p.id===null).map(p=>p.fpl_id).sort((a,b)=>a-b);
 if(JSON.stringify(unresolved)!==JSON.stringify([...data.resolved.unresolved_fpl_ids].sort((a,b)=>a-b)))context.addIssue({code:'custom',message:'Unresolved identity list is inconsistent'});
 for(const p of data.resolved.players){const original=raw.find(r=>r.element===p.fpl_id);if(!original||original.position!==p.slot||original.is_captain!==p.is_captain||original.is_vice_captain!==p.is_vice_captain||original.multiplier!==p.multiplier)context.addIssue({code:'custom',message:'Resolved player slot or captaincy differs from the source'})}
});
export type PublicSquad=z.infer<typeof publicSquadSchema>;
export type SquadPlayer=z.infer<typeof resolvedPick>;
export type Horizon=1|3|5;
export type Strategy='CONSERVATIVE'|'BALANCED'|'AGGRESSIVE';

export function parsePublicSquad(value:unknown):PublicSquad{
 const result=publicSquadSchema.safeParse(value);
 if(!result.success)throw new Error('The public squad response is incomplete or inconsistent. Refresh current-season data and try again.');
 return result.data;
}
export function snapshotPlayers(squad:PublicSquad,submitted=false):SquadPlayer[]{
 const players=squad.resolved.players.map(p=>({...p}));
 if(submitted)for(const substitution of [...squad.picks.automatic_subs].reverse()){
  const incoming=players.find(p=>p.fpl_id===substitution.element_in),outgoing=players.find(p=>p.fpl_id===substitution.element_out);
  if(incoming&&outgoing)[incoming.slot,outgoing.slot]=[outgoing.slot,incoming.slot];
 }
 return players.sort((a,b)=>a.slot-b.slot);
}
export function formation(players:SquadPlayer[]):string{
 return [2,3,4].map(position=>players.filter(p=>p.slot<=11&&p.position===position).length).join('-');
}
export function publicFinances(squad:PublicSquad){
 const history=squad.picks.entry_history;
 const sameDeadline=squad.entry.current_event===squad.resolved.gameweek;
 return {bank:history.bank??(sameDeadline?squad.entry.last_deadline_bank:null)??null,value:history.value??(sameDeadline?squad.entry.last_deadline_value:null)??null};
}

const optimizedRow=forecast.extend({id:z.number().int(),expected_points:z.number().finite(),price:z.number(),position:z.number().int().min(1).max(4),name:z.string(),club:z.string().nullable(),club_short:z.string().nullable()});
export const importedOptimizationSchema=z.object({scope:z.literal('lineup_only'),horizon:z.union([z.literal(1),z.literal(3),z.literal(5)]),forecast_event:z.number().nullable(),source_gameweek:z.number(),strategy:z.enum(['CONSERVATIVE','BALANCED','AGGRESSIVE']),squad:z.array(optimizedRow).length(15),starters:z.array(z.number()).length(11),captain:z.number(),vice_captain:z.number(),bench:z.array(z.number()).length(4),expected_net_points:z.number(),solver_status:z.string(),transfers:z.array(z.unknown()).length(0),transfer_status:z.literal('unavailable_private_state'),limitations:z.array(z.string())});
export type ImportedOptimization=z.infer<typeof importedOptimizationSchema>;
export function recommendedPlayers(squad:PublicSquad,result:ImportedOptimization):SquadPlayer[]{
 return squad.resolved.players.map(p=>{const row=result.squad.find(r=>r.id===p.id);return {...p,name:row?.name??p.name,club:row?.club??p.club,club_short:row?.club_short??p.club_short,price:row?.price??p.price,position:row?.position??p.position,predictions:row?{...p.predictions,[String(result.horizon)]:row}:p.predictions,slot:result.starters.includes(p.id??-1)?result.starters.indexOf(p.id!)+1:12+result.bench.indexOf(p.id!),is_captain:p.id===result.captain,is_vice_captain:p.id===result.vice_captain,multiplier:p.id===result.captain?2:result.starters.includes(p.id??-1)?1:0}}).sort((a,b)=>a.slot-b.slot);
}
