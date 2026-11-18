'use client';
import {useState} from 'react';
import dynamic from 'next/dynamic';
const ExpectedPointsChart=dynamic(()=>import('./charts').then(m=>m.ExpectedPointsChart));
import {useQuery} from '@tanstack/react-query';
import {api,number,type Collection} from '@/lib/api';
export function BacktestResults(){
 const [fold,setFold]=useState('0');const q=useQuery({queryKey:['backtesting'],queryFn:()=>api<Collection>('backtesting')});
 const rows=(q.data?.items||[]).filter(r=>String(r.fold)===fold);
 return <section className="panel"><div className="panel-head"><h2>Rolling chronological ablations</h2><select aria-label="Backtest fold" value={fold} onChange={e=>setFold(e.target.value)}>{[0,1,2].map(i=><option key={i} value={i}>Window {i+1}</option>)}</select></div><p className="notice">A: player statistics · B: + home fixture context · C: + managers · D: + tactics · E: + transfers. Missing groups cannot demonstrate useful lift. Each fold uses the same held-out player-fixture cohort.</p>{q.error?<div className="error">{q.error.message}</div>:rows.length?<><ExpectedPointsChart data={rows.map(r=>({name:String(r.window)+'y · '+r.ablation,value:typeof r.mae==='number'?r.mae:null}))} label="Measured held-out mean absolute error" unit="Error (points)"/><div className="table-scroll"><table><thead><tr><th>HISTORY</th><th>FEATURE GROUP</th><th>MAE</th><th>RMSE</th><th>RANK CORRELATION</th><th>TEST ROWS</th><th>MISSING FEATURES</th></tr></thead><tbody>{rows.map((r,i)=><tr key={i}><td>{String(r.window)==='weighted6'?'6 seasons · recency weighted':String(r.window)+' seasons'}</td><td>{String(r.ablation)}</td><td className="points">{number(r.mae,3)}</td><td>{number(r.rmse,3)}</td><td>{number(r.spearman,3)}</td><td>{String(r.n)}</td><td>{(r.unavailable_features as string[]).join(', ')||'None'}</td></tr>)}</tbody></table></div></>:<div className="empty"><h3>No rolling results available</h3><p>Run the offline backtest command against a validated warehouse.</p></div>}</section>
}
