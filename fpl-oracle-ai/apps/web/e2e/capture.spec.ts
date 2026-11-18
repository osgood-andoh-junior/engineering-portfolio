import {test,expect} from '@playwright/test';
test('capture the verified local dashboard',async({page})=>{
 test.skip(!process.env.ORACLE_CAPTURE_SCREENSHOT,'Opt-in local screenshot capture uses the running real backend');
 await page.setViewportSize({width:1440,height:1050});
 await page.goto('/dashboard');
 await expect(page.getByText('API connected',{exact:false})).toBeVisible();
 await expect(page.locator('.visual-player-card').first()).toBeVisible();
 const health=await (await page.request.get('/api/oracle/data-health')).json();
 const source=health.sources.find((s:{id:string;last_success:string})=>s.id==='fpl');
 const displayed=await page.evaluate((timestamp:string)=>new Date(timestamp).toLocaleString(),source.last_success);
 await expect(page.locator('footer')).toContainText('Source last synced '+displayed);
 await page.screenshot({path:'../../data/screenshots/dashboard.png',fullPage:true});
});
