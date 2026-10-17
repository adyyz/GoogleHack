// Browser-only success fixtures. Every feedback/policy mutation is intercepted;
// none becomes model output, human evidence or an applied Firestore policy.
const assert=require('node:assert/strict');
const {expect}=require('@playwright/test');
module.exports=async(browser,base)=>{
 const page=await browser.newPage({viewport:{width:1280,height:900}});
 try {
  const cases=(await(await page.request.get(base+'/api/demo/alerts')).json()).cases;
  const current=cases.find(row=>row.alerts.length===1), alertId=current.alerts[0].id;
  let optionalUsage=false;
 let frozen=false, feedbackPosts=0, approvals=0, applications=0, rollbacks=0;
  const record={id:alertId+'-1',verdict:'TRUE_POSITIVE',notes:'BROWSER_ONLY no stored human decision',revision:1,provenance:'BROWSER_FIXTURE_ONLY',submitted_at:'2026-10-18T00:00:00Z'};
  const finding={text:'BROWSER_ONLY analysis display fixture',evidence_ids:[current.evidence.trigger.id]};
  const item={id:'d'.repeat(24),state:'PROPOSED',revision:0,priority:'P1',hypothesis:'BROWSER_ONLY detector proposal, not a genuine result',
   candidate:{id:'hv-20000',threshold_aud_minor:2000000},sample_sizes:{conclusive_reviews:30,target_rule_reviews:15},support_feedback_ids:['fixture'],
   eligible_to_apply:true,application_block_reason:null,active_policy:{revision:0,policy_version_id:'detector-v1'},expected_effects:'Future outcomes unknown',
   measured_what_if:{benign_alerts_removed:2,suspicious_alerts_removed:0,baseline:{recall:.9},candidate_metrics:{recall:.9}},
   post_apply:{status:'NOT_YET_OBSERVED',reviewed_alerts:0,true_positive:0,false_positive:0}};
  await page.route('**/api/demo/usage', route=>route.fulfill({json:{categories:optionalUsage?{uncached_prompt_tokens:8,cached_prompt_tokens:2,candidate_tokens:3,thought_tokens:1,tool_prompt_tokens:1}:null,known_categories:{prompt_tokens:10,candidate_tokens:5,cached_prompt_tokens:null,thought_tokens:null,tool_prompt_tokens:null,total_tokens:15},total_tokens:15,known_estimated_usd_micros:0,provider_attempts:1,unknown_attempts:0,not_applicable_attempts:0}}));
  await page.route('**/api/operator/**',async route=>{
   const path=new URL(route.request().url()).pathname, method=route.request().method();
   if(path==='/api/operator/cases')return route.fulfill({json:{cases,policy_version_id:'detector-v1'}});
   if(path==='/api/operator/session')return route.fulfill({json:{uid:'operator-demo',is_admin:false,live_ai_eligible:false}});
   if(path==='/api/operator/alerts/'+alertId)return route.fulfill({json:{alert:{id:alertId,status:'COMPLETE',current_run_id:'BROWSER_ONLY',feedback_revision:frozen?1:0},latest_run:null,outputs:{
    A0:{predicted_verdict:'AUTO_TP',heuristic_score:0,label_policy_version:'auto-label-v1',label_signals:[]},
    A3:{primary_typology:'OTHER',suggested_action:'REVIEW',uncertainty:'LOW',rationale:finding},
    A4:{overview:finding,key_findings:[],counter_evidence:[],missing_information:[],next_steps:['Inspect source'],limitations:['Browser fixture only']}}}});
   if(path==='/api/operator/alerts/'+alertId+'/feedback'){
    if(method==='POST'){feedbackPosts++;frozen=true;return route.fulfill({json:record});}
    return route.fulfill({json:{items:frozen?[record]:[],next_cursor:null}});
   }
   if(path==='/api/operator/evolution/recommendations')return route.fulfill({json:{items:[item],next_cursor:null}});
   if(path.endsWith('/'+item.id+'/review')){assert.equal(route.request().postDataJSON().state,'APPROVED');approvals++;item.state='APPROVED';item.revision++;return route.fulfill({json:item});}
   if(path.endsWith('/'+item.id+'/apply')){applications++;assert.equal(route.request().postDataJSON().expected_revision,1);item.state='APPLIED';item.revision++;item.applied_policy_id='f'.repeat(64);item.active_policy={revision:1,policy_version_id:item.applied_policy_id};item.eligible_to_apply=false;return route.fulfill({json:item});}
   if(path.endsWith('/'+item.id+'/rollback')){rollbacks++;item.state='ROLLED_BACK';item.revision++;item.active_policy={revision:2,policy_version_id:'detector-v1'};return route.fulfill({json:item});}
   return route.continue();
  });
  await page.goto(base);
  await page.getByLabel('Search cases',{exact:true}).fill(current.name);
  await page.locator('.case-item').click();
  const sharedHeader = () => page.locator('.investigation-header').evaluate(node => { const copy = node.cloneNode(true); copy.querySelector('.case-workflow')?.remove(); return copy.textContent; });
  const publicHeader=await sharedHeader();
  await expect(page.getByRole('list',{name:'Case workflow',exact:true}).locator('li')).toHaveCount(4);
  await expect(page.locator('.case-workflow').getByText('Operator-only status',{exact:true})).toHaveCount(2);
  assert.equal(await page.locator('.case-workflow li').first().evaluate(node=>getComputedStyle(node,'::after').content),'""','The stage connector must exist for public visitors');
  const publicRisk=await page.locator('.risk-panel').innerText();
  await expect(page.locator('.case-workflow .workflow-step:nth-child(n+3).complete')).toHaveCount(0);
  await page.getByRole('button',{name:/Public visitor/}).click();
  await page.getByRole('button',{name:'Sign in locally',exact:true}).click();
  await page.getByRole('button',{name:/Operator.*Sign out/}).waitFor();
  await page.getByLabel('Search cases',{exact:true}).fill(current.name);
  await page.locator('.case-item').click();
  await expect(page.getByText('auto tp',{exact:true})).toBeVisible();
  const brief = page.getByRole('region', {name:'Investigation brief',exact:true});
  await expect(brief.getByRole('heading')).toHaveText([/Overview/, /Key findings/, /Counter-evidence/, /Missing information/, /Next steps/, /Limitations/]);
  const stages = await brief.locator('.brief-snake>li').evaluateAll(nodes=>nodes.map(node=>{const r=node.getBoundingClientRect();return {x:r.x,y:r.y};}));
  assert(stages[0].x<stages[1].x && stages[2].x===stages[1].x && stages[3].x===stages[0].x && stages[2].y>stages[1].y,'Desktop brief follows a winding evidence-to-action trail');
  await page.setViewportSize({width:320,height:900});
  const mobileStages = await brief.locator('.brief-snake>li').evaluateAll(nodes=>nodes.map(node=>node.getBoundingClientRect().y));
  assert(mobileStages.every((y,index)=>index===0 || y>mobileStages[index-1]),'Mobile brief preserves the reading order in one column');
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Brief trail fits mobile');
  await page.setViewportSize({width:1280,height:900});

  assert.equal(await sharedHeader(),publicHeader,'Shared source header must not change on sign-in');
  assert.equal(await page.locator('.risk-panel').innerText(),publicRisk,'Deterministic risk display must not change on sign-in');
  const layout=await page.evaluate(()=>{const queue=document.querySelector('.case-list').getBoundingClientRect(), area=document.querySelector('.investigation-workspace').getBoundingClientRect(), evidence=document.querySelector('.case-detail').getBoundingClientRect();return{queueLeft:queue.left,areaLeft:area.left,areaRight:area.right,evidenceRight:evidence.right,areaTop:area.top,evidenceBottom:evidence.bottom};});
  assert(Math.abs(layout.queueLeft-layout.areaLeft)<1 && Math.abs(layout.areaRight-layout.evidenceRight)<1 && layout.areaTop>=layout.evidenceBottom,'Investigation must span the whole content area below evidence');
  await expect(page.locator('.workflow-strip').getByText('Completed',{exact:true})).toBeVisible();
  const trail=page.getByRole('region',{name:'Transaction trail',exact:true});
  assert(await trail.evaluate(el=>el.clientHeight<=524 && el.scrollHeight>el.clientHeight),'Transaction trail must scroll after ten records');
  const usage=page.locator('.public-usage');
  await expect(usage.getByText('Cached prompt',{exact:true})).toHaveCount(0);
  await expect(usage.getByText('Thought / reasoning',{exact:true})).toHaveCount(0);
  await expect(usage.getByText('Tool prompt',{exact:true})).toHaveCount(0);
  optionalUsage=true;await usage.getByRole('button',{name:'Refresh usage',exact:true}).click();
  await expect(usage.getByText('Cached prompt',{exact:true})).toBeVisible();
  await expect(usage.getByText('Thought / reasoning',{exact:true})).toBeVisible();
  await expect(usage.getByText('Tool prompt',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Agree with AI suggestion',exact:true}).click();
  await expect(page.getByLabel('Verdict',{exact:true})).toHaveValue('TRUE_POSITIVE');
  await page.getByLabel('Review notes',{exact:true}).fill(record.notes);
  await page.getByRole('button',{name:'Save feedback',exact:true}).click();
  await expect(page.getByRole('article',{name:'Saved analyst verdict',exact:true})).toBeVisible();
  await expect(page.getByLabel('Verdict',{exact:true})).toHaveCount(0);
  await page.getByRole('button',{name:'Refresh status',exact:true}).click();
  await expect(page.getByRole('article',{name:'Saved analyst verdict',exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Save feedback',exact:true})).toHaveCount(0);
  await expect(page.locator('.workflow-strip').getByText('Saved and frozen',{exact:true})).toBeVisible();
  assert.equal(feedbackPosts,1);
  await page.getByRole('button',{name:'Evolution lab',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Review outcomes',exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Apply approved policy',exact:true})).toBeDisabled();
  await page.getByLabel('Recommendation decision notes',{exact:true}).fill('BROWSER_ONLY approval rationale');
  await page.getByRole('button',{name:'Approve recommendation',exact:true}).click();
  await page.getByRole('dialog').getByRole('button',{name:'Confirm decision',exact:true}).click();
  await expect(page.getByRole('button',{name:'Apply approved policy',exact:true})).toBeEnabled();
  await page.getByLabel('Recommendation decision notes',{exact:true}).fill('BROWSER_ONLY apply rationale');
  await page.getByRole('button',{name:'Apply approved policy',exact:true}).click();
  await expect(page.getByRole('dialog',{name:'Apply detector policy?',exact:true})).toBeVisible();
  await page.getByRole('dialog').getByRole('button',{name:'Confirm decision',exact:true}).click();
  await expect(page.getByRole('button',{name:'Roll back policy',exact:true})).toBeEnabled();
  await page.getByLabel('Recommendation decision notes',{exact:true}).fill('BROWSER_ONLY rollback rationale');
  await page.getByRole('button',{name:'Roll back policy',exact:true}).click();
  await page.getByRole('dialog').getByRole('button',{name:'Confirm decision',exact:true}).click();
  await expect(page.getByRole('button',{name:'Roll back policy',exact:true})).toBeDisabled();
  assert.equal(approvals,1);assert.equal(applications,1);assert.equal(rollbacks,1);
  await page.getByLabel('Break down reviews by',{exact:true}).selectOption('identity_type');
  await page.setViewportSize({width:390,height:844});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Review/policy workflow must fit mobile');
 }finally{await page.close();}
};
