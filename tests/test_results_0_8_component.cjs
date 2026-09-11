// Exercise the read-only Economy 0.8 statements without a browser or npm packages.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');

class Element {
  constructor(tag) { this.tag = tag; this.children = []; this.className = ''; this.attributes = {}; }
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
const source = fs.readFileSync(path.join(__dirname, '../src/econ_agent_sim/results_0_8_component/component.js'), 'utf8');
vm.runInContext(source.replace('export default function', 'function'), context);
const host = new Element('host');
const root = new Element('div'); root.className = 'results-root'; host.append(root);

const report = {
  scope: 'period', label: 'Period 1', period_count: 1, through_period: 1,
  price: 0.816496580927726, wage: 1,
  households: [1, 2].map(index => ({
    name: `Household ${index}`, opening_money: 1, closing_money: 2 / 3,
    wages_received: 1 / 3, dividends_received: 0, purchases_paid: 2 / 3,
    net_cash_change: -1 / 3, consumed_x: Math.sqrt(2 / 3), total_work: 1 / 3,
    average_work: 1 / 3, average_leisure: 2 / 3, ownership: .5,
    parameters: {scores:{consumption:1,money:1,leisure:1},
      weights:{consumption:1/3,money:1/3,leisure:1/3},alpha:.5},
  })),
  firm: {name:'Firm',opening_money:1,closing_money:5/3,sales_received:4/3,
    wages_paid:2/3,profit:2/3,dividends_paid:0,net_cash_change:2/3,
    profit_awaiting_distribution:2/3,produced_x:Math.sqrt(8/3),sold_x:Math.sqrt(8/3),
    parameters:{productivity:2,theta:.5}},
  economy: {opening_money:3,closing_money:3,produced_x:Math.sqrt(8/3),
    consumed_x:Math.sqrt(8/3),output_value:4/3,wages:2/3,profit:2/3,
    dividends:0,average_work:1/3,average_leisure:2/3},
  checks:{periods:true,goods:true,money:true,income:true},
  transfers:[{period:1,sender:'Firm',receiver:'Household 1',quantity:1/3,asset:'Money',kind:'wage'}],
  rows:[{period:1,account_type:'household',entity:'Household 1',opening_money:1,
    dividends_received:0,wages_received:1/3,purchases_paid:2/3,sales_received:0,
    dividends_paid:0,wages_paid:0,closing_money:2/3,produced_x:0,
    consumed_x:Math.sqrt(2/3),work_fraction:1/3,leisure_fraction:2/3,
    price:0.816496580927726,wage:1}],
};
const data = {reporting:report, run_rule:'Linked periods. No borrowing.',
  diagnostics:{method:'bracketed_scalar',iterations:160,funding_binding:false}};
context.render({data,parentElement:host});

assert.equal(root.querySelectorAll('.metric').length, 3);
assert(root.querySelectorAll('.metric')[0].querySelector('strong').textContent === '0.8165');
assert.equal(root.querySelectorAll('.household-card').length, 2);
assert.equal(root.querySelectorAll('.firm-card').length, 1);
assert.equal(root.querySelectorAll('.economy-card').length, 1);
assert(root.querySelector('.production-line').textContent === 'Produced 1.63 X · Sold 1.63 X');
assert(root.querySelectorAll('.preference-line').some(node => node.textContent.includes('33% consume')));
assert(root.querySelectorAll('.statement-heading').some(node => node.textContent === 'INCOME STATEMENT'));
assert(root.querySelectorAll('.profit-note').some(node => node.textContent.includes('awaits next-period distribution')));
assert(!source.includes('Net internal cash flow'));
assert(root.querySelectorAll('summary').some(node => node.textContent === '✓ All checks passed · Inspect the evidence'));
assert(root.querySelectorAll('summary').some(node => node.textContent === 'Settlement ledger · 1 transfer'));
assert(root.querySelector('.download').href.startsWith('data:text/csv'));
const csv = decodeURIComponent(root.querySelector('.download').href);
assert(csv.includes('"account_type"'));
assert(csv.includes('"Household 1"'));
assert.equal(root.querySelectorAll('button').length, 0);

report.scope = 'cumulative'; report.label = 'Periods 1–2'; report.period_count = 2;
context.render({data,parentElement:host});
assert(root.querySelector('h2').textContent === 'The economy so far.');
assert(root.querySelectorAll('.eyebrow').some(node => node.textContent === 'TOTAL OUTPUT'));
assert(root.querySelectorAll('span').some(node => node.textContent === 'Cumulative profit'));
assert(root.querySelectorAll('summary').some(node => node.textContent === 'Activity · 2 periods'));
assert(root.querySelectorAll('.statement-heading').some(node => node.textContent === 'CUMULATIVE CASH ACCOUNT'));

report.checks.money = false;
context.render({data,parentElement:host});
assert(root.querySelector('.failure'));
assert(root.querySelectorAll('summary').some(node => node.textContent === '! Check failed · Inspect the evidence'));
console.log('Economy 0.8 phone statements, cumulative scope, CSV and evidence passed.');
