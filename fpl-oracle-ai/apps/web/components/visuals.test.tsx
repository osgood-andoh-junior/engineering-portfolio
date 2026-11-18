import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {describe,it,expect} from 'vitest';
import {EmptyState,MetricCard,PredictionIntervalChart,ForecastComparison,ComparisonBars} from './visuals';
import type {Comparison} from '../lib/presentation';
describe('visual components and unavailable states',()=>{
 it('explains an empty source without fabricating metrics',()=>{const html=renderToStaticMarkup(<EmptyState title="No tactical observations" detail="No source loaded"/>);expect(html).toContain('No tactical observations');expect(html).toContain('No source loaded');expect(html).not.toContain('0%')});
 it('has accessible negative intervals and missing values',()=>{const html=renderToStaticMarkup(<PredictionIntervalChart rows={[{label:'Known',mean:1,interval:[-5,9]},{label:'Missing',mean:null,interval:null}]}/>);expect(html).toContain('range -5.0 to 9.0');expect(html).toContain('Unavailable');expect(html).toContain('role="img"');expect(html).not.toContain('NaN')});
 it('labels model/feature changes and refuses null-event attribution',()=>{const c={id:'test',player:{id:1,name:'Test Player',club:'Test Club',club_short:'TC',position:3,price:60,club_id:1},horizon:3,before:{mean:0,interval:[-3,5],timestamp:null,event:9,model:'old',feature_snapshot:null},after:{mean:1,interval:[-2,6],timestamp:null,event:10,model:'new',feature_snapshot:2},delta:1,percent_change:null,model_changed:true,feature_changed:true,same_target:false,event:null,recorded_at:''} satisfies Comparison;const html=renderToStaticMarkup(<ForecastComparison comparison={c}/>);for(const text of ['Test Player','Test Club','Model version changed','Input provenance differs','No verified football-event attribution','Percentage unavailable','Technical provenance','Different or unknown forecast target'])expect(html).toContain(text);expect(html).not.toContain('<pre');expect(html).not.toContain('<details open');expect(html).not.toContain('player_id')});
 it('shows signed comparison bars and text alternatives',()=>{const html=renderToStaticMarkup(<ComparisonBars before={-2} after={3}/>);expect(html).toContain('Previous -2.0 points; updated 3.0 points');expect(html).not.toContain('width="-')});
 it('keeps missing metrics visible',()=>{expect(renderToStaticMarkup(<MetricCard label="Untrained ensemble" value="Unavailable"/>)).toContain('Unavailable')});
});
