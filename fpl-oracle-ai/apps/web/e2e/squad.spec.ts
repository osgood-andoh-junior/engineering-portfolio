import {test,expect} from '@playwright/test';
test('manual squad builder uses the player service',async({page})=>{
 await page.route('**/api/oracle/players?*',route=>route.fulfill({json:{items:[{id:900001,name:'Test-only goalkeeper',position:1,club_id:1,price:45,status:'a',registration_state:'verified'}],total:1}}));
 await page.goto('/squad');
 await expect(page.getByRole('heading',{name:'Manual squad builder'})).toBeVisible();
 await expect(page.getByLabel('Find squad player')).toBeVisible();
 const add=page.locator('button[aria-label^="Add "]:not([disabled])').first();
 await expect(add).toBeVisible();
 await add.click();
 await expect(page.getByText(/1\/15 PLAYERS/)).toBeVisible();
});
