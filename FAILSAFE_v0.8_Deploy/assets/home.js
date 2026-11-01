'use strict';
(() => {
  const menu = document.querySelector('.menu-toggle');
  const nav = document.querySelector('.nav-links');
  if (menu && nav) {
    const closeMenu = () => {document.body.classList.remove('menu-open'); menu.setAttribute('aria-expanded', 'false'); menu.setAttribute('aria-label','Open navigation');};
    menu.addEventListener('click', () => {
      const open = !document.body.classList.contains('menu-open');
      document.body.classList.toggle('menu-open', open);
      menu.setAttribute('aria-expanded',String(open));
      menu.setAttribute('aria-label',open?'Close navigation':'Open navigation');
    });
    nav.addEventListener('click', e => {if (e.target.closest('a')) closeMenu();});
    document.addEventListener('keydown', e => {if(e.key === 'Escape') closeMenu();});
    window.addEventListener('resize', () => {if (window.innerWidth>750) closeMenu();});
  }
  const steps = [
    { overline:'STEP 01 / INPUTS', title:'Start with a scenario.', description:'Choose patient volume, language or transport barriers, staffing levels and an available resource budget. Everything happens using fictional inputs.', note:'Editable assumptions, not hospital records.', a:'500 virtual patients', b:'350 credits', v1:'63%',v2:'45%', status:'Scenario configured' },
    { overline:'STEP 02 / SIMULATION', title:'Watch the workflow unfold.', description:'Run a discrete-event simulation of discharge and follow-up booking. See where synthetic requests wait and how staffing changes queue pressure.', note:'Event-driven replay with fictional timestamps.', a:'Discharge queue', b:'Follow-up booking', v1:'76%',v2:'51%', status:'Synthetic events replayed' },
    { overline:'STEP 03 / ANALYSIS', title:'Make the bottlenecks visible.', description:'Examine waiting stages, incomplete fictional pathways and the points where a modeled process becomes congested.', note:'Operational delay is not evidence of medical harm.', a:'Queue pressure', b:'Pathway disruptions', v1:'81%',v2:'36%', status:'Bottlenecks inspected' },
    { overline:'STEP 04 / OPTIMIZATION', title:'Compare possible improvements.', description:'Search up to 72 combinations of support and additional staffing, then compare outcomes under the same synthetic assumptions and resource constraints.', note:'Exact combinatorial search, not a trained predictor.', a:'Candidate plans examined', b:'Budget-constrained search', v1:'100%',v2:'67%', status:'Transparent options compared' }
  ];
  const tabs = [...document.querySelectorAll('.step-tab')];
  const get = id => document.getElementById(id);
  function selectStep(index, focus=false) {
    tabs.forEach((tab,i)=>{tab.classList.toggle('active',i===index);tab.setAttribute('aria-selected',String(i===index));tab.tabIndex=i===index?0:-1;});
    const step=steps[index];
    if(!step) return;
    get('step-panel').setAttribute('aria-labelledby',`tab-${index}`);
    get('step-overline').textContent=step.overline;
    get('step-title').textContent=step.title;
    get('step-text').textContent=step.description;
    get('step-note').textContent=step.note;
    get('mini-label-1').textContent=step.a;
    get('mini-label-2').textContent=step.b;
    get('mini-bar-1').style.width=step.v1;
    get('mini-bar-2').style.width=step.v2;
    get('mini-status').textContent=step.status;
    document.querySelector('.demo-heading span:last-child').textContent=`0${index+1} / 04`;
    if(focus) tabs[index].focus();
  }
  tabs.forEach((tab,index)=>{
    tab.addEventListener('click',()=>selectStep(index));
    tab.addEventListener('keydown', e=>{
      let next=index;
      if(e.key==='ArrowRight'||e.key==='ArrowDown')next=(index+1)%tabs.length;
      else if(e.key==='ArrowLeft'||e.key==='ArrowUp')next=(index+tabs.length-1)%tabs.length;
      else if(e.key==='Home')next=0;
      else if(e.key==='End')next=tabs.length-1;
      else return;
      e.preventDefault();selectStep(next,true);
    });
  });
})();
