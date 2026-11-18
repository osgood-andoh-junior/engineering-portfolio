import {test,expect} from '@playwright/test';
test('audited changes resolve identities, preserve signed intervals and label provenance',async({page},testInfo)=>{
 await page.goto('/transfers');await expect(page.locator('.forecast-comparison')).toHaveCount(6);
 const card=page.locator('.forecast-comparison').first();await expect(card.locator('.visual-player-name')).toContainText('Raya');
 await expect(card.locator('.comparison-bars')).toBeVisible();await expect(card.locator('.interval-chart')).toBeVisible();
 await expect(card).toContainText('No verified football-event attribution');await expect(card).toContainText('Model version changed');
 await expect(card.locator('details')).not.toHaveAttribute('open');await card.locator('summary').click();await expect(card).toContainText('lightgbm-');
 await page.getByLabel('Filter forecast changes by player').fill('Arrizabalaga');await expect(page.locator('.forecast-comparison')).toHaveCount(1);
 await expect(page.locator('.interval-chart svg')).toHaveAttribute('aria-label',/range -/);
 await page.getByLabel('Change forecast horizon').selectOption('5');await expect(page.locator('.forecast-comparison')).toContainText('5 GW aggregate');
 await page.getByLabel('Filter forecast changes by player').fill('no-such-player');await expect(page.getByRole('heading',{name:'No audited forecast changes match'})).toBeVisible();
 await page.screenshot({path:testInfo.outputPath('truthful-empty-comparison.png'),fullPage:true});
});
test('paginated explorer, actual history, official fixture cells and verified model evaluation',async({page})=>{
 test.setTimeout(90000);await page.goto('/predictions');await expect(page.locator('tbody tr')).toHaveCount(25);
 const first=await page.locator('tbody tr').first().textContent();await page.getByRole('button',{name:'Next players'}).click();await expect(page.locator('.pagination')).toContainText('26–50');expect(await page.locator('tbody tr').first().textContent()).not.toBe(first);
 await page.goto('/players/493');await expect(page.getByRole('heading',{name:'Haaland',exact:true})).toBeVisible();await page.getByLabel('Historical metric').selectOption('goals');await expect(page.locator('tbody tr').first()).toBeVisible();
 await page.goto('/fixtures');await expect(page.locator('.fixture-matrix tbody tr')).toHaveCount(20);await expect(page.locator('.fixture-cell').first()).toContainText(/\([HA]\)/);await page.getByLabel('Start gameweek').fill('1');await expect(page.locator('.fixture-matrix th').nth(1)).toHaveText('GW 1');
 await page.goto('/model-lab');await expect(page.getByRole('heading',{name:'Actual vs predicted'})).toBeVisible();await expect(page.locator('.evaluation-grid .chart-slot')).toHaveCount(3);
 await page.getByLabel('Model run').selectOption({label:'GRU · 10 matches'});await expect(page.getByRole('heading',{name:'GRU · 10 matches · evaluation'})).toBeVisible();await expect(page.getByText('This model has no exported tree importance.',{exact:false})).toBeVisible();
 await page.getByLabel('Model run').selectOption({label:'Minutes classifier'});await expect(page.getByText('No-minutes Brier score',{exact:true})).toBeVisible();
});
for(const viewport of [{name:'desktop',width:1440,height:1050},{name:'laptop',width:1280,height:900},{name:'tablet',width:768,height:1024},{name:'mobile',width:390,height:844}])test('responsive charts and tables · '+viewport.name,async({page},testInfo)=>{
 test.setTimeout(120000);await page.setViewportSize(viewport);
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 for(const route of ['transfers','predictions','fixtures','model-lab','squad']){
  await page.goto('/'+route);await expect(page.locator('h1')).toBeVisible();await expect(page.locator('.skeleton')).toHaveCount(0);
  await expect(page.locator('pre,.facts')).toHaveCount(0);expect(await page.locator('main').innerText()).not.toContain('[object Object]');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),route+' document fits viewport').toBe(true);
  const badCharts=await page.locator('.chart-slot svg').evaluateAll(elements=>elements.filter(e=>e.getBoundingClientRect().width<10).length);expect(badCharts).toBe(0);
  if(route==='transfers'||route==='fixtures')await page.screenshot({path:testInfo.outputPath(route+'-'+viewport.name+'.png'),fullPage:true});
 }
 expect(errors).toEqual([]);
});
