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
assert(text.includes('✓ All checks passed · Check the accounts'));
assert(text.some(value=>value.includes('Agent 1 → Agent 2')));
assert.equal(root.querySelectorAll('button').length, 0);
assert.equal(root.querySelectorAll('.outcome-card').length, 2);
assert.equal(root.querySelectorAll('.account-row').length, 8);
assert.equal(root.querySelector('.agent-select').children[0].textContent, 'All agents');
assert(root.querySelector('.download').href.startsWith('data:text/csv'));
assert.equal(source.includes('Replay trade'), false);
assert.equal(source.includes('setTriggerValue'), false);

data.trades=[];
data.agents=data.agents.map(agent=>({...agent,closing:agent.opening}));
context.render({data,parentElement:host});
assert(root.querySelectorAll('p').some(node=>node.textContent==='0 trades · starting balances unchanged.'));
assert(root.querySelectorAll('p').some(node=>node.textContent==='No transactions were needed.'));
console.log('Static outcomes, account statement, receipts, and no-trade view passed.');
