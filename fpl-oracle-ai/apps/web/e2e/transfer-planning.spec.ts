import {test,expect} from '@playwright/test';
test('latest real public snapshot becomes editable ownership while private values remain gated',async({page})=>{
 test.setTimeout(60000);await page.goto('/transfers');
 await page.getByRole('button',{name:'Import latest public squad'}).click();
 await expect(page.getByText('15/15 owned players',{exact:false})).toBeVisible({timeout:20000});
 await expect(page.getByLabel('Current bank (£m)',{exact:true})).toHaveValue('');
 await expect(page.getByLabel('Free transfers available')).toHaveValue('');
 await expect(page.getByRole('button',{name:'Generate transfer recommendations'})).toBeDisabled();
 await page.getByLabel('Current bank (£m)',{exact:true}).fill('1');
 await expect(page.getByRole('button',{name:'Generate transfer recommendations'})).toBeDisabled();
 await expect(page.getByLabel('Selling price Haaland',{exact:true})).toHaveValue('');
 await expect(page.locator('pre,.facts')).toHaveCount(0);
});
test('actual manager keep-squad plans use confirmed bank/free transfers without inventing selling prices',async({page})=>{
 test.setTimeout(120000);await page.goto('/transfers');await page.getByRole('button',{name:'Import latest public squad'}).click();
 await expect(page.getByText('15/15 owned players',{exact:false})).toBeVisible({timeout:30000});
 await page.getByLabel('Current bank (£m)',{exact:true}).fill('1');await page.getByLabel('Free transfers available').fill('2');
 await page.getByLabel('Maximum transfers').fill('0');await page.getByRole('checkbox',{name:/I checked current ownership/}).check();
 for(const horizon of ['1','3','5']){
  await page.getByLabel('Planning horizon').selectOption(horizon);
  const response=page.waitForResponse(r=>r.url().endsWith('/api/oracle/planning/transfers')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Generate transfer recommendations'}).click();const r=await response;expect(r.status(),await r.text()).toBe(200);
  const result=await r.json();expect(result.recommended.transfers).toEqual([]);expect(result.recommended.hit_cost).toBe(0);expect(result.recommended.remaining_bank).toBe(10);expect(result.recommended.liquidation_value).toBeNull();
  expect(result.recommended.starters).toHaveLength(11);expect(result.recommended.bench).toHaveLength(4);await expect(page.getByRole('heading',{name:'Keep your squad',exact:true})).toBeVisible();
 }
});
