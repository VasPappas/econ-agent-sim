// Exercise the read-only result statement without a browser or npm packages.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');

class Element {
  constructor(tag) { this.tag = tag; this.children = []; this.className = ''; this.attributes = {}; this.dataset = {}; this.value = ''; }
  append(...children) { for (const child of children) { child.parentElement = this; this.children.push(child); } }
  replaceChildren(...children) { this.children = []; this.append(...children); }
  setAttribute(key, value) { this.attributes[key] = value; }
  querySelectorAll(selector) {
    const matches = element => selector.startsWith('.')
      ? element.className.split(' ').includes(selector.slice(1)) : element.tag === selector;
    return this.children.flatMap(child => [...(matches(child) ? [child] : []), ...child.querySelectorAll(selector)]);
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0]; }
}
const context = vm.createContext({
  document: {
    createElement: tag => new Element(tag),
    createTextNode: text => Object.assign(new Element('text'), {textContent: text}),
  },
  encodeURIComponent,
});
const source = fs.readFileSync(path.join(__dirname, '../src/econ_agent_sim/results_component/component.js'), 'utf8');
vm.runInContext(source.replace('export default function', 'function'), context);
const host = new Element('host');
const root = new Element('div'); root.className = 'results-root'; host.append(root);
const data = {
  label:'Run 2', settings:{agent_count:2}, prices:{X:2/3,Y:1},
  previous_run:{prices:{X:1}}, price_x_change_percent:-100/3,
  agents:[
    {name:'Agent 1',opening:{X:2,Y:1,Money:10},closing:{X:1.75,Y:7/6,Money:10}},
    {name:'Agent 2',opening:{X:1,Y:1,Money:10},closing:{X:1.25,Y:5/6,Money:10}},
  ],
  totals:{opening:{X:3,Y:2,Money:20},closing:{X:3,Y:2,Money:20}},
  checks:{market:true,money:true,accounts:true}, market_error:5e-11,
  clearing_tolerance:1e-10, gross_money_payments:1/3,
  trades:[
    {seller:'Agent 1',buyer:'Agent 2',good:'X',quantity:.25,payment:1/6,unit_price:2/3},
    {seller:'Agent 2',buyer:'Agent 1',good:'Y',quantity:1/6,payment:1/6,unit_price:1},
  ],
};
context.render({data,parentElement:host});
const text = root.querySelectorAll('summary').map(node=>node.textContent);
assert(text.includes('✓ All checks passed · Verify this run'));
assert.equal(root.querySelectorAll('.agent-transactions').length, 2);
assert(root.querySelector('.outcome-card').querySelectorAll('p').some(n=>n.textContent==='Sold 0.2500 X to Agent 2'));
assert(root.querySelectorAll('.outcome-card')[1].querySelectorAll('p').some(n=>n.textContent==='Bought 0.2500 X from Agent 1'));
assert.equal(root.querySelectorAll('button').length, 0);
assert.equal(root.querySelectorAll('.outcome-card').length, 2);
assert.equal(root.querySelectorAll('.account-row').length, 0);
assert.equal(root.querySelectorAll('select').length, 0);
assert(root.querySelector('.download').href.startsWith('data:text/csv'));
assert.equal(source.includes('Replay trade'), false);
assert.equal(source.includes('setTriggerValue'), false);

data.trades=[];
data.agents=data.agents.map(agent=>({...agent,closing:agent.opening}));
context.render({data,parentElement:host});
assert(root.querySelectorAll('p').some(node=>node.textContent==='0 trades · starting balances unchanged.'));
assert.equal(root.querySelectorAll('.agent-transactions').length, 0);
assert(root.querySelectorAll('p').some(node=>node.textContent==='No transactions for this agent.'));
console.log('Static outcomes, account statement, receipts, and no-trade view passed.');

data.model='money_in_utility'; data.assets=['X','Money'];
data.run_rule='No borrowing or money creation.';
data.prices={X:1,Money:1};
data.totals={opening:{X:3,Money:20},closing:{X:3,Money:20}};
data.agents=data.agents.map(a=>({...a,opening:{X:a.opening.X,Money:10},closing:{X:a.opening.X,Money:10}}));
context.render({data,parentElement:host});
assert.equal(root.querySelectorAll('.outcome-row').length,4);
assert.equal(root.querySelectorAll('.account-row').length,0);
assert.equal(root.querySelectorAll('p').some(n=>String(n.textContent).includes('Y price')),false);
assert(root.querySelector('.boundary').textContent.includes('No borrowing'));
assert(!decodeURIComponent(root.querySelector('.download').href).includes('"Y"'));
console.log('One-good result has only X and Money, with the correct model boundary.');

data.model='production_consumption'; data.label='Period 2';
data.prices={X:2/3,Money:1};
data.agents=[
  {name:'Agent 1',opening:{X:2,Money:1},closing:{X:1.75,Money:7/6}},
  {name:'Agent 2',opening:{X:1,Money:1},closing:{X:1.25,Money:5/6}},
];
data.trades=[{seller:'Agent 1',buyer:'Agent 2',good:'X',quantity:.25,payment:1/6,unit_price:2/3}];
data.totals={opening:{X:3,Money:2},closing:{X:3,Money:2}};
data.period_opening={'Agent 1':{X:0,Money:1},'Agent 2':{X:0,Money:1}};
data.period_closing={'Agent 1':{X:0,Money:7/6},'Agent 2':{X:0,Money:5/6}};
data.produced={'Agent 1':2,'Agent 2':1};
data.consumed={'Agent 1':1.75,'Agent 2':1.25};
data.period_totals={opening:{X:0,Money:2},produced:{X:3,Money:0},consumed:{X:3,Money:0},closing:{X:0,Money:2}};
data.period_checks={goods:true,money:true,accounts:true};
context.render({data,parentElement:host});
assert.equal(root.querySelectorAll('.period-flow').length,2);
assert(root.querySelectorAll('strong').some(n=>n.textContent==='Consumed 1.75 X'));
assert.equal(root.querySelectorAll('.outcome-row').length,2);
assert(root.querySelector('.period-accounting').querySelector('p').textContent.includes('0.00 opening + 3.00 produced − 3.00 consumed = 0.00 remaining'));
const csv=decodeURIComponent(root.querySelector('.download').href);
assert(csv.includes('"opening","produced","received","sent","consumed","closing"'));
assert(csv.includes('"Period 2","Agent 1","X","0","2","0","0.25","1.75","0"'));
data.period_checks.accounts=false;
context.render({data,parentElement:host});
assert(root.querySelector('.failure'));
data.period_checks.accounts=true;
data.checks.accounts=false;
context.render({data,parentElement:host});
assert(root.querySelector('.failure'));
data.checks.accounts=true;
data.trades=[];
context.render({data,parentElement:host});
assert(root.querySelectorAll('p').some(n=>n.textContent==='0 trades · see production and consumption above.'));
assert(!root.querySelectorAll('p').some(n=>String(n.textContent).includes('starting balances unchanged')));
console.log('Production flows, period CSV, scoped receipts, and combined checks passed.');

data.model='work_leisure';
data.effort={'Agent 1':0.5,'Agent 2':0};
data.leisure_time={'Agent 1':0.5,'Agent 2':1};
data.settings.agents=[{name:'Agent 1',productivity:2},{name:'Agent 2',productivity:1}];
data.work_checks={effort_bounds:true,time_budget:true,optimal_work:true,joint_price:true};
data.solution={active_set_passes:2,resting_agents:1};
context.render({data,parentElement:host});
assert.equal(root.querySelectorAll('.work-time').length,2);
assert(root.querySelectorAll('strong').some(n=>n.textContent==='Work 0.0%'));
assert(root.querySelectorAll('span').some(n=>n.textContent==='Leisure 100.0%'));
const workCsv=decodeURIComponent(root.querySelector('.download').href);
assert(workCsv.includes('"work_fraction","leisure_fraction","productivity_x_per_full_work_period"'));
assert(workCsv.includes('"0.5","0.5","2"'));
assert(!root.querySelector('.failure'));
data.work_checks.optimal_work=false;
context.render({data,parentElement:host});
assert(root.querySelector('.failure'));
data.work_checks.optimal_work=true;
data.period_checks.accounts=false;
context.render({data,parentElement:host});
assert(root.querySelector('.failure'));
data.period_checks.accounts=true;
data.checks.accounts=false;
context.render({data,parentElement:host});
assert(root.querySelector('.failure'));
console.log('Work choices, zero-work corner, CSV units and all three check layers passed.');

data.checks.accounts=true;
data.trades=[];
data.reporting={
  scope:'period',label:'Period 2',period_count:1,through_period:2,
  opening:{X:0,Money:2},closing:{X:0,Money:2},produced:1.5,consumed:1.5,
  gross_x_exchanged:0.0000003,gross_money_exchanged:0.0000004,net_trade_cash:0,total_work:.75,
  average_work:.375,average_leisure:.625,
  checks:{goods_identity:true,money_identity:true,periods:true,work:true},
  agents:[
    {name:'Agent 1',opening:{X:0,Money:1},closing:{X:0,Money:.9999996},produced:1,consumed:1.0000003,
     sold_x:0,bought_x:.0000003,sales_received:0,purchases_paid:.0000004,net_trade_cash:-.0000004,
     transaction_count:1,total_work:.5,average_work:.5,average_leisure:.5,
     parameters:{alpha:.5,leisure:1/3,productivity:2,weights:{consumption:1/3,money:1/3,leisure:1/3}}},
    {name:'Agent 2',opening:{X:0,Money:1},closing:{X:0,Money:1.0000004},produced:.5,consumed:.4999997,
     sold_x:.0000003,bought_x:0,sales_received:.0000004,purchases_paid:0,net_trade_cash:.0000004,
     transaction_count:1,total_work:.25,average_work:.25,average_leisure:.75,
     parameters:{alpha:.5,leisure:.5,productivity:2,weights:{consumption:.25,money:.25,leisure:.5}}},
  ],
  trades:[{seller:'Agent 2',buyer:'Agent 1',good:'X',quantity:.0000003,payment:.0000004,unit_price:4/3,period:2}],
  rows:[
    {period:2,agent:'Agent 1',asset:'X',opening:0,produced:1,received:.0000003,sent:0,consumed:1.0000003,closing:0,work_fraction:.5,leisure_fraction:.5,productivity:2},
    {period:2,agent:'Agent 1',asset:'Money',opening:1,produced:0,received:0,sent:.0000004,consumed:0,closing:.9999996,work_fraction:.5,leisure_fraction:.5,productivity:2},
  ],
};
context.render({data,parentElement:host});
assert(root.querySelector('.economy-card'));
assert.equal(root.querySelectorAll('.agent-report').length,2);
assert.equal(root.querySelectorAll('.balance-sheet').length,3);
assert.equal(root.querySelectorAll('.activity-statement').length,3);
assert(!root.querySelectorAll('.statement-row').some(n=>(n.textContent||'').includes('Net internal cash flow')));
assert(root.querySelectorAll('.preference-line').some(n=>n.textContent.includes('33.3% consume')));
assert(root.querySelectorAll('.parameter-line').some(n=>n.textContent==='Full-effort output · 2.00 X'));
assert(root.querySelectorAll('p').some(n=>n.textContent==='Bought <0.0001 X from Agent 2'));
assert(root.querySelectorAll('p').some(n=>n.textContent==='Paid <0.0001 Money'));
assert(!root.querySelectorAll('strong').some(n=>n.textContent.includes('-0.00')));
const reportCsv=decodeURIComponent(root.querySelector('.download').href);
assert(reportCsv.includes('"2","Agent 1","X","0","1","3e-7"'));

data.reporting.scope='cumulative'; data.reporting.label='Periods 1–2'; data.reporting.period_count=2;
data.reporting.rows=[...data.reporting.rows,{...data.reporting.rows[0],period:1}];
context.render({data,parentElement:host});
assert(root.querySelector('.section-intro').textContent.includes('flows are added'));
assert(root.querySelectorAll('summary').some(n=>n.textContent==='Activity statement · 2 periods'));
assert.equal(root.querySelectorAll('.agent-transactions').length,0);
assert(root.querySelectorAll('p').some(n=>n.textContent.includes('select a single period for receipts')));
assert(decodeURIComponent(root.querySelector('.download').href).includes('"1","Agent 1","X"'));
console.log('Compact period and cumulative reports preserve stock-flow logic and clarify tiny receipts.');
