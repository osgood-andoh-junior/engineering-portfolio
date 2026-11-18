import {test,expect} from '@playwright/test';
test('forecast pages render backend data and source coverage',async({page})=>{
 await page.goto('/dashboard');
 await expect(page.getByRole('heading',{name:'Your edge starts here.'})).toBeVisible();
 await page.getByRole('link',{name:'Data health',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Know what you know.'})).toBeVisible();
 await expect(page.getByRole('heading',{name:'Source registry'})).toBeVisible();
 await page.getByRole('link',{name:'Model lab',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Chronological model comparison'})).toBeVisible();
});
