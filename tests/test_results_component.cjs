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
