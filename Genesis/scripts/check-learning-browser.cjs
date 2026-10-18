// Real controlled-fixture API actions, confined to isolated test collections. Zero model calls.
const assert=require('node:assert/strict'),fs=require('node:fs');
const {expect}=require('@playwright/test');
module.exports=async(browser,base)=>{
 const page=await browser.newPage({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 try{
  const originalPolicy=(await(await page.request.get(base+'/api/demo/bulk/summary')).json()).policy;
  const originalUsage=await(await page.request.get(base+'/api/demo/usage')).json();
  await page.goto(base);
  await expect(page.locator('.synthetic-learning')).toHaveCount(0);
  await page.getByRole('button',{name:/Public visitor/}).click();
  await page.getByRole('button',{name:'Sign in locally',exact:true}).click();
  await page.getByRole('button',{name:/Operator.*Sign out/}).waitFor();
  await page.getByRole('button',{name:'Evolution lab',exact:true}).click();
  await page.locator('.evo-practice > summary').click();
  const panel=page.getByRole('region',{name:'Cutoff learning and controlled exercise',exact:true});
  await expect(panel).toBeVisible();
  async function action(label){
   await panel.getByRole('button',{name:label,exact:true}).click();
   await page.getByRole('dialog').getByRole('button',{name:'Confirm learning action',exact:true}).click();
  }
  await action('Prepare exercise candidate');
  await expect(panel.locator('.learning-table tbody tr')).toHaveCount(1);
  await expect(panel.locator('.learning-table')).toContainText('Candidate: TP ≤ 0.25 / FP ≥ 0.4');
  await expect(panel.getByRole('button',{name:'Approve candidate',exact:true})).toBeDisabled();
  await action('Validate candidate');
  await expect(panel.locator('.learning-table')).toContainText('Passed safety checks');
  await expect(panel.getByRole('button',{name:'Apply cutoffs',exact:true})).toBeDisabled();
  await action('Approve candidate');
  await expect(panel.getByRole('button',{name:'Apply cutoffs',exact:true})).toBeEnabled();
  await action('Apply cutoffs');
  await expect(panel.getByRole('button',{name:'Test 100 cases',exact:true})).toBeEnabled();
  await action('Test 100 cases');
  const result=panel.getByRole('region',{name:'Controlled 100-case comparison',exact:true});
  await expect(result).toBeVisible();
  const fp=result.getByRole('row').filter({has:page.getByRole('rowheader',{name:'auto fp',exact:true})});
  await expect(fp).toContainText('25');await expect(fp).toContainText('50');
  await expect(panel.getByRole('button',{name:'Test 100 cases',exact:true})).toBeDisabled();
  await panel.getByRole('button',{name:'Refresh learning',exact:true}).click();
  await expect(result).toBeVisible();
  await panel.screenshot({path:'.cache/preview/cutoff-exercise-desktop.png'});
  await page.setViewportSize({width:390,height:844});
  await panel.screenshot({path:'.cache/preview/cutoff-exercise-mobile.png'});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await panel.getByLabel('Learning dataset',{exact:true}).selectOption('corpus');
  await action('Prepare synthetic candidates');
  await expect(panel.locator('.learning-table tbody tr')).toHaveCount(9);
  await expect(panel.getByText('Not evaluated—no candidate',{exact:true})).toHaveCount(7);
  await expect(panel.getByText('Not applicable—protected',{exact:true})).toHaveCount(2);
  for(const label of ['Validate candidate','Approve candidate','Apply cutoffs']) await expect(panel.getByRole('button',{name:label,exact:true})).toBeDisabled();
  await panel.screenshot({path:'.cache/preview/cutoff-no-candidate-mobile.png'});
  assert.deepEqual((await(await page.request.get(base+'/api/demo/bulk/summary')).json()).policy,originalPolicy);
  assert.deepEqual(await(await page.request.get(base+'/api/demo/usage')).json(),originalUsage);
  assert.deepEqual(errors,[]);
  console.log('Controlled cutoff exercise passed: actual prepare/validate/approve/apply/100-case comparison, persisted result, no-candidate controls, unchanged corpus policy and usage.');
 }finally{await page.close();}
};
