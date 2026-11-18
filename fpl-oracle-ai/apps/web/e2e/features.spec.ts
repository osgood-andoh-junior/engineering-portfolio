import {test,expect} from '@playwright/test';
// Pace full UI flows within the real API's 120 requests/minute allowance.
test.afterEach(async()=>{await new Promise(resolve=>setTimeout(resolve,12000))});

test.describe('All tabs against the real local API',()=>{
 const tabs=[['dashboard','Your edge starts here.'],['predictions','Player predictions'],['squad','Your squad, in focus.'],['optimizer','Find your strongest fifteen.'],['captaincy','Make the armband count.'],['fixtures','The road ahead.'],['transfers','Make every move matter.'],['transfers/live','The transfer centre.'],['managers','The minds behind the game.'],['tactics','Read the game differently.'],['ai-analyst','A second opinion, grounded.'],['historical','Six seasons. One perspective.'],['backtesting','Evidence over expectation.'],['model-lab','Inside the Oracle.'],['data-health','Know what you know.'],['settings','Make it your own.']];
 test('each navigation tab loads without runtime or API failures',async({page},testInfo)=>{
  test.setTimeout(120000);
  const errors:string[]=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('response',r=>{if(r.url().includes('/api/oracle/')&&r.status()>=400)errors.push(`${r.status()} ${r.url()}`)});
  await page.goto('/dashboard');
  for(const [path,title] of tabs){
   await page.locator(`aside a.nav-link[href="/${path}"]`).click();
   await expect(page.getByRole('heading',{level:1,name:title,exact:true})).toBeVisible();
   await expect(page.locator('.system')).toContainText('API connected');
   await expect(page.locator('.skeleton')).toHaveCount(0);
   await page.screenshot({path:testInfo.outputPath(path.replaceAll('/','-')+'.png'),fullPage:true});
  }
  expect(errors).toEqual([]);
 });
 test('prediction filters, horizons, context, sorting, and player profile',async({page})=>{
  await page.goto('/predictions');
  await expect(page.locator('tbody tr').first()).toBeVisible();
  const data=await (await page.request.get('/api/oracle/predictions?limit=1')).json();
  await expect(page.locator('tbody tr')).toHaveCount(Math.min(25,data.total));
  await page.getByLabel('Search players').fill('Haaland');
  await expect(page.locator('tbody tr')).toHaveCount(1);
  await page.getByLabel('Position',{exact:true}).selectOption('4');
  await page.getByLabel('Maximum price').fill('5');
  await expect(page.getByRole('heading',{name:'No published forecasts'})).toBeVisible();
  await page.getByLabel('Maximum price').fill('');
  await page.getByLabel('Horizon',{exact:true}).selectOption('3');
  await expect(page.locator('tbody tr')).toHaveCount(1);
  await page.getByLabel('Sort by').selectOption('p10');
  await page.getByLabel('Context',{exact:true}).check();
  await expect(page.getByRole('columnheader',{name:'TACTICAL FIT',exact:true})).toBeVisible();
  await page.locator('tbody .visual-player-name').first().click();
  await expect(page.getByRole('heading',{name:'Haaland',exact:true})).toBeVisible();
  await expect(page.getByRole('heading',{name:'Historical FPL points'})).toBeVisible();
  await expect(page.locator('.recharts-surface').first()).toBeVisible();
 });
 test('captain shortlist and manager timeline display real records',async({page})=>{
  await page.goto('/captaincy');await expect(page.locator('tbody tr')).toHaveCount(10);
  await page.goto('/managers');await expect(page.locator('.record')).toHaveCount(20);
  await page.getByRole('link',{name:'View coaching timeline'}).first().click();
  await expect(page.locator('.visual-timeline')).toBeVisible();
  await expect(page.getByRole('heading',{name:'Recorded match outcomes'})).toBeVisible();
 });
 test('fixture schedule, historical selection and rolling windows',async({page})=>{
  await page.goto('/fixtures');await expect(page.locator('.fixture-matrix tbody tr')).toHaveCount(20);await page.getByRole('button',{name:'Schedule',exact:true}).click();await expect(page.locator('tbody tr')).toHaveCount(380);
  await expect(page.locator('tbody tr').first()).not.toContainText('Invalid Date');
  await page.goto('/historical');await page.getByText('Advanced player lookup',{exact:true}).click();await page.getByLabel('Internal player ID').fill('493');
  await expect(page.getByRole('heading',{name:'Haaland',exact:true})).toBeVisible();
  await page.goto('/backtesting');
  for(const fold of ['0','1','2']){await page.getByLabel('Backtest fold').selectOption(fold);await expect(page.locator('section').first().locator('tbody tr')).toHaveCount(20)}
 });
 test('transfer comparison and evidence analyst',async({page})=>{
  await page.goto('/transfers');
  await expect(page.getByLabel('Transfer out').locator('option')).not.toHaveCount(1);
  await page.getByLabel('Find outgoing player').fill('Raya');await page.getByLabel('Transfer out').selectOption('1');
  await page.getByLabel('Find incoming player').fill('Haaland');await page.getByLabel('Transfer in').selectOption('493');
  await page.getByLabel('Your transfer point cost').fill('4');
  await page.getByRole('button',{name:'Compare forecasts'}).click();
  await expect(page.locator('.comparison-result')).toBeVisible();
  await expect(page.locator('.comparison-result strong')).toHaveCount(2);
  await page.goto('/ai-analyst');
  await page.getByLabel('Your question').fill('Compare the selected players for the next gameweek.');
  await page.getByLabel('Find players',{exact:true}).fill('Haaland');await page.getByLabel('Add a player').selectOption('493');
  await page.getByRole('button',{name:'Compare stored evidence'}).click();
  await expect(page.locator('.analyst-answer')).toContainText('Evidence-based comparison');
  await expect(page.locator('.analyst-answer')).toContainText('structured retrieval without LLM');
 });
 test('optimizer solves all strategies and reports unsupported chips',async({page})=>{
  test.setTimeout(90000);
  await page.goto('/optimizer');
  for(const strategy of ['BALANCED','CONSERVATIVE','AGGRESSIVE']){
   await page.getByLabel('Risk strategy').selectOption(strategy);
   const solved=page.waitForResponse(r=>r.url().endsWith('/api/oracle/optimizer/squad')&&r.request().method()==='POST');
   await page.getByRole('button',{name:'Optimize squad',exact:true}).click();
   const result=await solved;expect(result.status(),await result.text()).toBe(200);
   await expect(page.getByRole('button',{name:'Optimize squad',exact:true})).toBeEnabled();
   await expect(page.locator('.squad-pitch .jersey')).toHaveCount(11);
   await expect(page.locator('.error[role="alert"]')).toHaveCount(0);
  }
  await page.getByRole('combobox',{name:'Chip',exact:true}).selectOption('triple_captain');
  await page.getByRole('button',{name:'Optimize squad',exact:true}).click();
  await expect(page.locator('.error[role="alert"]')).toContainText('not yet verified');
 });
 test('manual builder adds, starts, removes players and blocks incomplete validation',async({page})=>{
  await page.goto('/squad');await page.getByLabel('Find squad player').fill('Haaland');
  await page.getByRole('button',{name:'Add Haaland',exact:true}).click();
  await expect(page.getByText(/1\/15 PLAYERS/)).toBeVisible();
  await expect(page.getByRole('button',{name:'Validate squad & starting XI'})).toBeDisabled();
  await page.getByLabel('Start Haaland',{exact:true}).uncheck();
  await expect(page.getByText('0/11 starters.',{exact:false})).toBeVisible();
  await page.getByRole('button',{name:'Remove Haaland',exact:true}).click();
  await expect(page.getByText(/0\/15 PLAYERS/)).toBeVisible();
  await page.getByLabel('Public manager ID').fill('invalid');
  await page.getByRole('button',{name:'Import squad'}).click();
  await expect(page.locator('.error[role="alert"]')).toContainText('Enter a public manager ID');
 });
 test('settings persist on reload and mobile navigation works',async({page})=>{
  await page.goto('/settings');await page.getByLabel('Public manager ID').fill('12345');
  await page.getByLabel('Default risk strategy').selectOption('CONSERVATIVE');
  await page.getByLabel('Forecast horizon').selectOption('5');await page.reload();
  await expect(page.getByLabel('Public manager ID')).toHaveValue('12345');
  await expect(page.getByLabel('Default risk strategy')).toHaveValue('CONSERVATIVE');
  await expect(page.getByLabel('Forecast horizon')).toHaveValue('5');
  await page.setViewportSize({width:390,height:844});
  await page.getByRole('button',{name:'Toggle navigation'}).click();
  await page.locator('aside a[href="/predictions"]').click();
  await expect(page.getByRole('heading',{level:1,name:'Player predictions',exact:true})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 });
 test('a complete manually built squad validates, and edits invalidate that result',async({page})=>{
  test.setTimeout(90000);
  const response=await page.request.post('/api/oracle/optimizer/squad',{data:{budget:1000,horizon:1,strategy:'BALANCED'}});
  expect(response.ok()).toBe(true);const squad=await response.json();
  await page.goto('/squad');
  for(const p of squad.squad){
   await page.getByLabel('Find squad player').fill(p.name);
   await page.locator(`.player-picker [data-player-id="${p.id}"] button`).click();
  }
  for(const p of squad.squad){await page.locator(`.selected-list [data-player-id="${p.id}"] input[type="checkbox"]`).setChecked(squad.starters.includes(p.id))}
  await page.getByRole('combobox',{name:'Captain',exact:true}).selectOption(String(squad.captain));
  await page.getByRole('combobox',{name:'Vice-captain',exact:true}).selectOption(String(squad.vice_captain));
  await page.getByRole('button',{name:'Validate squad & starting XI'}).click();
  await expect(page.locator('.manual-selection [role="status"]')).toContainText('pass the composition rules');
  await page.getByLabel('Budget (£m)').fill('1');
  await expect(page.locator('.manual-selection [role="status"]')).toHaveCount(0);
  await page.getByRole('button',{name:'Validate squad & starting XI'}).click();
  await expect(page.locator('.manual-selection [role="status"]')).toContainText('Budget exceeded');
 });
});
