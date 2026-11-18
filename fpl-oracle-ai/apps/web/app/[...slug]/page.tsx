import {notFound} from 'next/navigation';
import {Oracle} from '@/components/oracle';
const pages=['dashboard','predictions','players','squad','optimizer','transfers','captaincy','fixtures','managers','tactics','historical','backtesting','model-lab','ai-analyst','settings','data-health'];
export default async function Page({params}:{params:Promise<{slug:string[]}>}){const {slug}=await params;if(!pages.includes(slug[0])||slug.length>2||slug.length===2&&!(slug[0]==='transfers'&&slug[1]==='live'||['players','managers'].includes(slug[0])&&/^\d+$/.test(slug[1])))notFound();return <Oracle path={slug.join('/')}/>}
