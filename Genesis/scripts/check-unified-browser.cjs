// Completed model/review states below are intercepted display fixtures, never stored evidence.
const assert = require('node:assert/strict');
const { expect } = require('@playwright/test');
module.exports = async (browser, base) => {
  const page = await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[]; page.on('pageerror',e=>errors.push(e.message));
  try {
    await page.goto(base);
    await expect(page.getByLabel('Investigation workspace',{exact:true})).toHaveCount(0);
    await expect(page.locator('.bulk-table tbody tr')).toHaveCount(50);
    await expect(page.locator('.reference-overview tbody tr')).toHaveCount(9);
    await page.getByRole('button',{name:'View reference',exact:true}).first().click();
    await expect(page.getByRole('dialog',{name:'Synthetic reference review',exact:true})).toContainText('not a human verdict');
    await expect(page.getByRole('button',{name:'Save feedback',exact:true})).toHaveCount(0);
    await page.keyboard.press('Escape');
    await expect(page.getByRole('button',{name:'View reference',exact:true}).first()).toBeFocused();
    const geometry = await page.evaluate(()=>({batch:document.querySelector('.batch-toolbar').getBoundingClientRect().top,filters:document.querySelector('.bulk-filters').getBoundingClientRect().top}));
    assert(geometry.batch<geometry.filters,'Batch controls must lead the queue');
    await page.getByLabel('Search identities',{exact:true}).fill('no-matching-fictional-name');
    await expect(page.getByText('No matching cases.',{exact:false})).toBeVisible();
    await page.getByRole('button',{name:'Clear filters',exact:true}).click();
    await page.getByRole('button',{name:/Public visitor/}).click();
    await page.getByLabel('Email',{exact:true}).fill('invalid');
    await page.getByRole('button',{name:'Sign in locally',exact:true}).click();
    await expect(page.getByText('Enter a valid email address.',{exact:true})).toBeVisible();
    await page.getByLabel('Email',{exact:true}).fill('operator@aml-insight.test');
    await page.getByRole('button',{name:'Sign in locally',exact:true}).click();
    await page.getByRole('button',{name:/Operator.*Sign out/}).waitFor();
    const pending=await (await page.request.get(base+'/api/demo/bulk/cases?status=awaiting_triage&limit=100')).json();
    const row=pending.items.find(r=>r.rules.length===1);
    const source=await (await page.request.get(base+'/api/demo/bulk/cases/'+row.id)).json();
    const alert=source.alerts[0], finding={text:'BROWSER_ONLY evidence; not a provider result',evidence_ids:[source.evidence.trigger.id]};
    let frozen=false,posts=0, conflict=false;
    const feedback={id:'BROWSER_ONLY',revision:1,verdict:'TRUE_POSITIVE',notes:'BROWSER_ONLY note never persisted',provenance:'BROWSER_FIXTURE_ONLY',submitted_at:'2026-10-18T00:00:00Z'};
    await page.route('**/api/operator/bulk/cases?*',route=>route.fulfill({json:{items:[{...row,triaged:true,reviewed:frozen}],total:1,next_cursor:null}}));
    await page.route('**/api/operator/bulk/cases/'+row.id,route=>route.fulfill({json:{...source,alerts:[{...alert,status:'COMPLETE',frozen,actionable:false}]}}));
    await page.route('**/api/operator/alerts/'+alert.id,route=>route.fulfill({json:{alert:{...alert,status:'COMPLETE',current_run_id:'BROWSER_ONLY',feedback_revision:frozen?1:0},latest_run:null,outputs:{A0:{predicted_verdict:'AUTO_TP',heuristic_score:0,label_policy_version:'BROWSER_ONLY',label_signals:[]},A3:{primary_typology:'OTHER',suggested_action:'REVIEW',uncertainty:'LOW',rationale:finding},A4:{overview:finding,key_findings:[],counter_evidence:[],missing_information:[],next_steps:[],limitations:['Display only']}}}}));
    await page.route('**/api/operator/alerts/'+alert.id+'/feedback',route=>{
      if(route.request().method()==='POST') { posts++; if(conflict)return route.fulfill({status:409,json:{detail:'BROWSER_ONLY conflict'}}); frozen=true;return route.fulfill({json:feedback}); }
      return route.fulfill({json:{items:frozen?[feedback]:[],next_cursor:null}});
    });
    await page.getByRole('button',{name:'Show cases awaiting analyst review',exact:true}).click();
    await expect(page.locator('.bulk-table')).toContainText('Awaiting analyst review');
    await page.getByRole('button',{name:'Review',exact:true}).click();
    const dialog=page.getByRole('dialog',{name:'Analyst review',exact:true});
    await expect(dialog.getByRole('button',{name:'Save feedback',exact:true})).toBeEnabled();
    await expect(dialog.locator('.validated-investigation')).toHaveCount(0);
    await dialog.getByRole('button',{name:'Agree with AI suggestion',exact:true}).click();
    await expect(dialog.getByLabel('Verdict',{exact:true})).toHaveValue('TRUE_POSITIVE');
    await dialog.getByRole('button',{name:'Choose my own verdict',exact:true}).click();
    await expect(dialog.getByLabel('Verdict',{exact:true})).toBeFocused();
    await dialog.getByLabel('Review notes',{exact:true}).fill('Unsaved browser note');
    await dialog.getByRole('button',{name:'Close dialog',exact:true}).click();
    await expect(page.getByRole('dialog',{name:'Discard unsaved review?',exact:true})).toBeVisible();
    await page.getByRole('button',{name:'Keep editing',exact:true}).click();
    await expect(dialog.getByLabel('Review notes',{exact:true})).toHaveValue('Unsaved browser note');
    conflict=true;
    await dialog.getByRole('button',{name:'Save feedback',exact:true}).click();
    await expect(dialog.getByText('Feedback changed or triage is incomplete. Refresh status before submitting again.',{exact:true})).toBeVisible();
    await expect(dialog.getByLabel('Review notes',{exact:true})).toHaveValue('Unsaved browser note');
    conflict=false;
    await dialog.getByRole('button',{name:'Save feedback',exact:true}).click();
    await expect(dialog.locator('.frozen-review')).toBeVisible();
    await expect(dialog.getByRole('button',{name:'Save feedback',exact:true})).toHaveCount(0);
    await dialog.getByRole('button',{name:'Refresh status',exact:true}).click();
    await expect(dialog.locator('.frozen-review')).toBeVisible();
    assert.equal(posts,2,'One rejected and one successful intercepted save');
    await page.keyboard.press('Escape');
    await expect(dialog).toHaveCount(0);
    for(const width of [1440,1024,768,390,320]) {
      await page.setViewportSize({width,height:1000});
      for(const screen of ['Investigations','Evolution lab','System design','Admin']) {
        await page.getByRole('button',{name:screen,exact:true}).click();
        assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`${screen}/${width} overflow`);
      }
    }
    await page.emulateMedia({reducedMotion:'reduce'});
    assert.equal(await page.locator('.rolling-letter-track').first().evaluate(e=>getComputedStyle(e).animationName),'none');
    await page.getByRole('button',{name:'Investigations',exact:true}).click();
    await page.getByRole('button',{name:/^View details for/}).first().click();
    await expect(page.getByRole('dialog',{name:'View details',exact:true}).locator('.validated-investigation')).toBeVisible();
    await page.route('**/api/operator/alerts/'+alert.id,route=>route.fulfill({status:401,json:{detail:'BROWSER_ONLY expired session'}}));
    await page.getByRole('button',{name:'Refresh status',exact:true}).click();
    await expect(page.getByRole('alert')).toContainText('Your operator session expired.');
    await expect(page.locator('.validated-investigation')).toHaveCount(0);
    assert.deepEqual(await page.evaluate(()=>[localStorage.length,sessionStorage.length]),[0,0]);
    assert.deepEqual(errors,[]);
    console.log('Unified queue passed: reference separation, batch-first layout, review-only modal, guarded drafts, conflict recovery, frozen save, responsive screens. No model/human evidence stored.');
  } finally { await page.close(); }
};
