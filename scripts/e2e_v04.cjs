const { chromium } = require('/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const url=process.argv[2]||'http://127.0.0.1:8770/app/';
 const browser=await chromium.launch({headless:true,executablePath:'/usr/bin/chromium',args:['--no-sandbox']});
 const context=await browser.newContext({viewport:{width:1440,height:1000},ignoreHTTPSErrors:true,permissions:['clipboard-read','clipboard-write']});
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text())});
 await page.goto(url,{waitUntil:'load',timeout:120000});await page.waitForSelector('h1:text("Объявления")');
 if(!await page.locator('td.idcol').first().innerText())errors.push('Ad ID missing');
 const firstId=(await page.locator('td.idcol').first().innerText()).match(/\d{18}/)?.[0];await page.locator('[data-copy]').first().click();if(await page.evaluate(()=>navigator.clipboard.readText())!==firstId)errors.push('copy mismatch');
 if(!await page.locator('td').filter({hasText:/₸/}).count()||!await page.locator('td').filter({hasText:/\$/}).count())errors.push('dual currency missing');
 await page.locator('[data-view="ads"]').click();await page.locator('[data-view="quality"]').click();await page.locator('[data-view="sales"]').click();await page.locator('[data-view="main"]').click();
 await page.click('#columns');await page.locator('[data-col="campaign"]').check();await page.click('#closeConfig');await page.reload({waitUntil:'load'});if(!await page.locator('th[data-sort="campaign"]').count())errors.push('columns not persisted');
 await page.fill('#from','2026-09-01');await page.fill('#to','2026-09-30');await page.click('#advancedBtn');await page.fill('#minSpend','50');await page.locator('[data-quick="wastesales"]').click();await page.locator('th[data-sort="cpqlU"]').click();
 await page.locator('tbody tr[data-row]').first().click();await page.waitForSelector('#panel.open');if(!await page.locator('#detail').getByText('Last spend не является').count())errors.push('activity caveat missing');await page.click('#closePanel');
 await page.getByRole('button',{name:'Кампании'}).click();await page.locator('tbody tr[data-group]').first().click();await page.waitForSelector('h1:text("Объявления")');
 await page.getByRole('button',{name:'Качество данных'}).click();await page.waitForSelector('text=Creative URL policy');
 for(const vp of [{width:768,height:1024},{width:390,height:844}]){await page.setViewportSize(vp);await page.reload({waitUntil:'load'});let o=await page.evaluate(()=>({b:document.body.scrollWidth,v:document.documentElement.clientWidth}));if(o.b>o.v)errors.push(`overflow ${vp.width}: ${JSON.stringify(o)}`)}
 await page.setViewportSize({width:1440,height:1000});await page.goto(url,{waitUntil:'load'});await page.evaluate(()=>localStorage.clear());await page.reload({waitUntil:'load'});await page.screenshot({path:'/tmp/skvoz_v04.png',fullPage:true});console.log(JSON.stringify({ok:!errors.length,errors},null,2));await browser.close();if(errors.length)process.exit(1)
})().catch(e=>{console.error(e);process.exit(1)});
