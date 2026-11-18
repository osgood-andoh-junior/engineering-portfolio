import {create} from 'zustand';
import type {PublicSquad,ImportedOptimization} from './public-squad';
// Deliberately no persist middleware: public squad state exists only in this tab's memory.
export const useSquadSession=create<{squad:PublicSquad|null;recommendation:ImportedOptimization|null;setSquad:(squad:PublicSquad|null)=>void;setRecommendation:(recommendation:ImportedOptimization|null)=>void}>(set=>({squad:null,recommendation:null,setSquad:squad=>set({squad,recommendation:null}),setRecommendation:recommendation=>set({recommendation})}));
