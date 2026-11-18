import {NextRequest,NextResponse} from 'next/server';
const allowed=/^(planning\/(?:transfers|latest-squad\/\d+)|presentation\/(changes|fixtures|predictions|events|tactics|history\/\d+|club-history|managers\/\d+|models\/[a-zA-Z0-9_-]+\/evaluation)|health|players(?:\/\d+)?|clubs|fixtures|gameweeks\/current|predictions(?:\/\d+)?|prediction-changes|backtesting|managers(?:\/\d+|\/fpl\/\d+\/squad)?|tactics\/teams|transfers\/(events|compare)|historical\/players\/\d+|models\/metrics|data-health|squad\/validate|optimizer\/(squad|imported|transfers|captain|wildcard)|analyst\/query)$/;
async function proxy(request:NextRequest,context:{params:Promise<{path:string[]}>}){
 const {path}=await context.params;const route=path.join('/');
 if(!allowed.test(route))return NextResponse.json({error:{message:'Unknown public resource'}},{status:404});
 const target=new URL('/api/v1/'+route,process.env.API_BASE_URL||'http://127.0.0.1:8000');
 target.search=request.nextUrl.search;
 try{
  const body=request.method==='POST'?await request.text():undefined;
  if(body&&body.length>16000)return NextResponse.json({error:{message:'Request too large'}},{status:413});
  const response=await fetch(target,{method:request.method,body,headers:body?{'Content-Type':'application/json'}:undefined,cache:'no-store',signal:AbortSignal.timeout(route.startsWith('planning/')?90000:20000)});
  return new NextResponse(await response.text(),{status:response.status,headers:{'Content-Type':'application/json','Cache-Control':'no-store','X-Request-ID':response.headers.get('X-Request-ID')||''}});
 }catch{return NextResponse.json({error:{message:'Oracle API is unavailable. Start the backend and apply migrations.'}},{status:503});}
}
export const GET=proxy;export const POST=proxy;
