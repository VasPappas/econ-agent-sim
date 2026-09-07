// Exercise component event/state transitions without a browser or npm packages.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');

class Element {
  constructor(tag) { this.tag = tag; this.children = []; this.className = ''; this.dataset = {}; this.attributes = {}; }
  append(...children) { for (const child of children) { child.parentElement = this; this.children.push(child); } }
  replaceChildren() { this.children = []; }
  setAttribute(key, value) { this.attributes[key] = value; }
  focus() {}
  get classList() { return { add: name => { this.className += ' ' + name; }, contains: name => this.className.split(' ').includes(name) }; }
  querySelectorAll(selector) {
    const matches = element => selector.startsWith('.')
      ? element.className.split(' ').includes(selector.slice(1)) : element.tag === selector;
    return this.children.flatMap(child => [...(matches(child) ? [child] : []), ...child.querySelectorAll(selector)]);
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0]; }
}
const context = vm.createContext({
  document: { createElement: tag => new Element(tag), createTextNode: text => Object.assign(new Element('text'), { textContent: text }) },
  crypto: { randomUUID: (() => { let id = 0; return () => `event-${++id}`; })() },
  window: { matchMedia: () => ({ matches: true }) },
});
const source = fs.readFileSync(path.join(__dirname, '../src/econ_agent_sim/playground_component/component.js'), 'utf8');
vm.runInContext(source.replace('export default function', 'function'), context);
const host = new Element('host');
const root = new Element('div'); root.className = 'playground-root'; host.append(root);
const stocks = { 'Agent 1': {X:1.8,Y:.2,Money:10}, 'Agent 2': {X:.2,Y:1.8,Money:10} };
const data = {
  revision:0, selected_index:0, label:'Run 1', setup_summary:'Run 1 · submitted setup',
  agent_count:2, price:1, previous_price:null,
  opening:stocks, closing:stocks, checks:{market:true,money:true,accounts:true},
  explanations:{'Why did X change but not Y?':'Baseline explanation'},
  trades:[
    {seller:'Agent 1',buyer:'Agent 2',good:'X',quantity:1.4,payment:1.4,unit_price:1},
    {seller:'Agent 2',buyer:'Agent 1',good:'Y',quantity:1.4,payment:1.4,unit_price:1},
  ],
};
const events=[];
const render = () => context.render({data,parentElement:host,setTriggerValue:(name,value)=>events.push([name,value]),setStateValue:(name,value)=>events.push([name,value])});
render();
root.querySelector('.next-trade').onclick();
assert.equal(events.at(-1)[0],'selection');
assert.equal(events.at(-1)[1].trade_index,1);
// The Python rerun can briefly echo the preceding selection. Do not rewind.
data.selected_trade=0; render();
assert.equal(root.playgroundState.tradeIndex,1);
root.querySelectorAll('button').find(b=>b.textContent==='Ask about this trade').onclick();
assert.equal(events.at(-1)[0],'question');
assert.equal(events.at(-1)[1].trade_index,1);
assert.equal(root.querySelector('.try-again'),undefined);
assert.equal(root.querySelectorAll('summary').some(e=>e.textContent==='Why did the price move?'),false);
// A remount restores the server's remembered trade.
delete root.playgroundState; data.selected_trade=1; render();
assert.equal(root.playgroundState.tradeIndex,1);
assert.equal(root.querySelector('.next-trade').disabled,true);
// Zero-trade Results show the outcome, not the explanation or a duplicate CTA.
data.trades=[];
data.explanations['Why is there no trade?']='Detailed no-trade explanation';
render();
assert.equal(root.querySelectorAll('p').some(e=>e.textContent==='0 trades · starting balances unchanged.'),true);
assert.equal(root.querySelectorAll('p').some(e=>e.textContent==='Detailed no-trade explanation'),false);
assert.equal(root.querySelectorAll('button').some(e=>e.textContent==='Ask why no trade is needed'),false);
console.log('Component selection, remount, and no-trade checks passed.');
