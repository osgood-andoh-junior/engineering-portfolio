import {create} from 'zustand';
import {persist} from 'zustand/middleware';
type Preferences={strategy:'CONSERVATIVE'|'BALANCED'|'AGGRESSIVE';horizon:1|3|5;managerId:string;set:(p:Partial<Omit<Preferences,'set'>>)=>void};
export const usePreferences=create<Preferences>()(persist((set)=>({strategy:'BALANCED',horizon:1,managerId:'',set:(p)=>set(p)}),{name:'oracle-preferences'}));
