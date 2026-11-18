import {describe,it,expect} from 'vitest';
import {number,position} from './api';
describe('forecast presentation',()=>{it('does not fabricate missing values',()=>{expect(number(null)).toBe('—');expect(number(NaN)).toBe('—');expect(number(0)).toBe('0.0')});it('maps FPL positions',()=>{expect(position(1)).toBe('GK');expect(position(4)).toBe('FWD');expect(position(null)).toBe('—')})});
