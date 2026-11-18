export type Row=Record<string,unknown>;
export type Collection={items:Row[];total?:number;reason?:string};
export async function allPredictions(horizon:number):Promise<Collection>{
 const first=await api<Collection>(`predictions?horizon=${horizon}&limit=500`);
 const items=[...first.items];
 while(first.total!==undefined&&items.length<first.total){
  const next=await api<Collection>(`predictions?horizon=${horizon}&limit=500&offset=${items.length}`);
  if(!next.items.length)break;
  items.push(...next.items);
 }
 return {...first,items};
}
export async function api<T>(path:string,body?:unknown):Promise<T>{
 const response=await fetch('/api/oracle/'+path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:undefined,body:body?JSON.stringify(body):undefined});
 const value=await response.json();
 if(!response.ok)throw new Error(value.error?.message||value.error||'Service unavailable');
 return value as T;
}
export function number(value:unknown,digits=1){return typeof value==='number'&&Number.isFinite(value)?value.toFixed(digits):'—'}
export function percent(value:unknown){return typeof value==='number'&&Number.isFinite(value)?(value*100).toFixed(0)+'%':'—'}
export const position=(value:unknown)=>({1:'GK',2:'DEF',3:'MID',4:'FWD'}[Number(value)]||'—');
