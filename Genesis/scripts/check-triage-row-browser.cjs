// Exercises source reads and preview only; never confirms a job or sends a model request.
const assert = require('node:assert/strict');
const path = require('node:path');
process.env.PLAYWRIGHT_BROWSERS_PATH ||= path.resolve('.cache/playwright');
const {chromium, expect} = require('@playwright/test');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({baseURL:process.env.GENESIS_BROWSER_BASE_URL || 'http://127.0.0.1:5173',viewport:{width:1440,height:1000},reducedMotion:'reduce'});
  const errors=[], confirmed=[];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => {
    if (request.method()==='POST' && new URL(request.url()).pathname==='/api/operator/triage-batches') confirmed.push(request.url());
  });
  try {
    await expect.poll(async()=>{try{return (await page.request.get('/api/health')).status();}catch{return 0;}},{timeout:15000}).toBe(200);
    await page.goto('/');
    await expect(page.getByRole('button',{name:/Triage now/})).toHaveCount(0);
    async function checkClearFilters(statusLabel,status) {
      await page.getByLabel(statusLabel,{exact:true}).selectOption(status);
      await page.getByLabel('Identity type',{exact:true}).selectOption('INDIVIDUAL');
      const identity=page.getByLabel('Identity',{exact:true});
      await expect.poll(()=>identity.locator('option').count()).toBeGreaterThan(1);
      await identity.selectOption({index:1});
      await page.getByLabel('Detector rule',{exact:true}).selectOption('HIGH_VALUE');
      await page.getByLabel('Search identities',{exact:true}).fill('no such fictional identity');
      await page.getByRole('button',{name:'Clear filters',exact:true}).click();
      await expect(page.getByLabel('Search identities',{exact:true})).toHaveValue('');
      for(const label of ['Identity type','Identity','Detector rule']) await expect(page.getByLabel(label,{exact:true})).toHaveValue('');
      await expect(page.getByLabel(statusLabel,{exact:true})).toHaveValue('all');
      await expect(page.locator('.bulk-table tbody tr').first()).toBeVisible();
    }
    await checkClearFilters('Case status','reference');
    await page.getByRole('button',{name:/Public visitor/}).click();
    await page.getByRole('button',{name:'Sign in locally',exact:true}).click();
    await expect(page.getByRole('button',{name:/Operator/}).first()).toBeVisible();
    await checkClearFilters('Triage status','frozen');
    const queueResponse=page.waitForResponse(response=>response.url().includes('/api/operator/bulk/cases?')&&response.url().includes('status=awaiting_triage'));
    await page.getByLabel('Triage status',{exact:true}).selectOption('awaiting_triage');
    const queue=await (await queueResponse).json();
    const pending=queue.items.filter(row=>!row.reference&&!row.triaged&&!row.batch_state);
    assert(pending.length>1,'Need two unqueued pending cases to test row selection');
    const target=pending[1];
    const action=page.getByRole('button',{name:`Triage now for ${target.name} / ${target.id.slice(0,6)}`,exact:true});
    await expect(action).toBeEnabled();
    const previewRequest=page.waitForRequest(request=>request.url().endsWith('/api/operator/triage-batches/preview')&&request.method()==='POST');
    await action.click();
    const request=await previewRequest;
    assert.deepEqual(request.postDataJSON().case_ids,[target.id]);
    assert.equal(request.postDataJSON().dataset_id,queue.dataset_id);
    const dialog=page.getByRole('dialog',{name:'Start genuine case batch?',exact:true});
    await expect(dialog).toContainText('1 selected cases');
    await expect(dialog.getByRole('button',{name:'Start batch',exact:true})).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(dialog).toHaveCount(0);
    // Browser-only state doubles: never create jobs, provider output or feedback.
    let phase='QUEUED';
    const fixtureId='c'.repeat(24);
    await page.route('**/api/operator/bulk/cases?*', async route=>{
      const response=await route.fetch(), body=await response.json();
      body.items=[{...target,requires_review:true,batch_id:fixtureId,batch_state:phase,triaged:phase==='COMPLETE',reviewed:false}];
      body.total=1; body.next_cursor=null;
      await route.fulfill({response,json:body});
    });
    await page.route('**/api/operator/triage-batches/'+fixtureId,route=>route.fulfill({json:{
      id:fixtureId,state:'QUEUED',revision:0,can_resume:false,
      waiting_message:"Today's AI switch is off in Admin.",counts:{PENDING:1,RUNNING:0,COMPLETE:0},
      members:[{case_id:target.id,state:'PENDING',parent_id:null}]
    }}));
    await page.getByRole('button',{name:'Refresh queue',exact:true}).click();
    await expect(page.getByText('Queued for triage',{exact:true})).toBeVisible();
    await expect(page.getByRole('button',{name:/Triage now/})).toHaveCount(0);
    await page.getByRole('button',{name:`View triage batch for ${target.name} / ${target.id.slice(0,6)}`,exact:true}).click();
    await expect(page.locator('.batch-progress')).toContainText("Today's AI switch is off in Admin.");
    await expect(page.locator('.batch-progress').getByRole('button',{name:'resume',exact:true})).toBeDisabled();
    phase='RUNNING';
    await page.getByRole('button',{name:'Refresh queue',exact:true}).click();
    await expect(page.locator('.bulk-table .bulk-state .badge')).toHaveText('running');
    phase='COMPLETE';
    await page.getByRole('button',{name:'Refresh queue',exact:true}).click();
    await expect(page.locator('.bulk-table').getByRole('button',{name:'Review',exact:true})).toBeVisible();
    for(const width of [320,390,768,1440]){
      await page.setViewportSize({width,height:1000});
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Overflow at ${width}`);
      const layout=await page.locator('.bulk-table tbody tr').first().evaluate(row=>{
        const cells=Array.from(row.cells), risk=cells[2].querySelector('.bulk-source-risk');
        const [label,pill]=Array.from(risk.children).map(element=>element.getBoundingClientRect());
        const cell=cells[2].getBoundingClientRect();
        return {centered:[cells[1],cells[2]].every(element=>getComputedStyle(element).textAlign==='center'),
          below:pill.top>=label.bottom+7,contained:pill.left>=cell.left&&pill.right<=cell.right&&pill.bottom<=cell.bottom,
          actions:getComputedStyle(cells[3]).textAlign==='left'&&getComputedStyle(cells[4]).textAlign==='left'};
      });
      assert(layout.centered&&layout.below&&layout.contained&&layout.actions,`Risk pill or alignment at ${width}: ${JSON.stringify(layout)}`);
    }
    require('node:fs').mkdirSync('.cache/preview',{recursive:true});
    await page.locator('.bulk-table').screenshot({path:'.cache/preview/ci013-triage-row.png'});
    assert.deepEqual(confirmed,[]); assert.deepEqual(errors,[]);
    console.log('Row preview, queued/running/review states, blocked reason, disabled resume, explicit refresh, private boundary and responsive checks passed. No job or model request submitted by this browser check.');
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
