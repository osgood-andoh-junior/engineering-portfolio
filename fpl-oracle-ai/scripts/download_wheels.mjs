// Official PyPI wheels only, verified against PyPI's published SHA256.
// A workaround for slow streaming wheel extraction on this Windows workstation.
import {mkdir,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
await mkdir('data/wheels',{recursive:true});
for (const [name,version] of [['numpy','2.5.4'],['pandas','2.3.3'],['pyarrow',null],['scikit-learn',null],['catboost',null],['torch',null],['ortools',null],['plotly',null]]) {
 const meta=await fetch(`https://pypi.org/pypi/${name}${version?'/'+version:''}/json`).then(r=>r.json());
 const candidates=meta.urls.filter(x=>x.filename.endsWith('.whl')&&(x.filename.includes('cp312-cp312-win_amd64')||x.filename.includes('cp312-none-win_amd64')||x.filename.includes('py3-none-any')));
 const wheel=candidates[0];if(!wheel){console.log(name,'no compatible wheel');continue;}
 const started=Date.now();console.log(JSON.stringify({name,status:'downloading',size:wheel.size}));
 const parts=[];const size=1024*1024;
 for(let offset=0;offset<wheel.size;offset+=size){
  let part;
  for(let attempt=0;attempt<4;attempt++){
   try{const response=await fetch(wheel.url,{headers:{Range:`bytes=${offset}-${Math.min(offset+size-1,wheel.size-1)}`},signal:AbortSignal.timeout(30000)});if(response.status!==206)throw new Error(`Expected HTTP 206, got ${response.status}`);part=Buffer.from(await response.arrayBuffer());break;}catch(e){if(attempt===3)throw e;}
  }
  parts.push(part);if(offset%(size*10)===0)console.log(name,Math.round(offset/wheel.size*100)+'%');
 }
 const bytes=Buffer.concat(parts);const digest=createHash('sha256').update(bytes).digest('hex');
 if(digest!==wheel.digests.sha256)throw new Error(`${name}: SHA256 mismatch`);
 await writeFile('data/wheels/'+wheel.filename,bytes);
 console.log(JSON.stringify({name,file:wheel.filename,bytes:bytes.length,seconds:(Date.now()-started)/1000,sha256:digest}));
}
