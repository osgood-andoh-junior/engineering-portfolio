import {expect,it} from 'vitest';
import {transferStateReady,sellingPrice} from './transfer-state';
it('never permits unknown free transfers or selling prices',()=>{const ids=Array.from({length:15},(_,i)=>i+1);const prices=Object.fromEntries(ids.map(i=>[i,'4.5']));expect(transferStateReady(ids,prices,'1','',true)).toBe(false);expect(transferStateReady(ids,{},'1','1',true)).toBe(false);expect(transferStateReady(ids,prices,'1','1',false)).toBe(false);expect(transferStateReady(ids,prices,'1','0',true)).toBe(true);expect(transferStateReady(ids,prices,'1','1.5',true)).toBe(false)});
it('rounds only half the profit and preserves all losses',()=>{expect(sellingPrice(50,53)).toBe(51);expect(sellingPrice(50,54)).toBe(52);expect(sellingPrice(50,47)).toBe(47)});
