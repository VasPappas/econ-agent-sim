// Render the real Python report through the phone component with no npm packages.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {execFileSync} = require('node:child_process');
const assert = require('node:assert/strict');

class Element {
  constructor(tag) {
    this.tag = tag; this.children = []; this.className = '';
    this.attributes = {}; this.style = {}; this.open = false;
  }
  append(...children) { for (const child of children) { child.parentElement = this; this.children.push(child); } }
  replaceChildren(...children) { this.children = []; this.append(...children); }
  setAttribute(key, value) { this.attributes[key] = value; }
  getAttribute(key) { return this.attributes[key]; }
  querySelectorAll(selector) {
    const matches = element => selector.startsWith('.')
      ? element.className.split(' ').includes(selector.slice(1)) : element.tag === selector;
    return this.children.flatMap(child => [...(matches(child) ? [child] : []), ...child.querySelectorAll(selector)]);
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0]; }
}

const repo = path.join(__dirname, '..');
const reports = JSON.parse(execFileSync('python', ['-c', `
import json
from econ_agent_sim.economy_0_9 import (
    Household, Firm, default_households, default_firm,
    advance_investment_period, investment_report,
)
from econ_agent_sim.investment_comparison import compare_investment_runs
households = tuple(Household(**item) for item in default_households())
firm = Firm(**default_firm())
first = advance_investment_period(households, firm)
second = advance_investment_period(households, firm, previous=first)
baseline_firm = Firm(reinvestment_rate=.2)
baseline_first = advance_investment_period(households, baseline_firm)
baseline_second = advance_investment_period(households, baseline_firm, baseline_first)
comparison = compare_investment_runs(
    (first, second), (baseline_first, baseline_second), selected_period=2,
    cumulative=True, current_name='Build capital', baseline_name='Consume today',
)
unavailable_comparison = compare_investment_runs(
    (first, second), (baseline_first,), selected_period=2,
)
print(json.dumps([
    investment_report((first,)), investment_report((first, second), cumulative=True),
    comparison, unavailable_comparison,
]))
`], {cwd: repo, env: {...process.env, PYTHONPATH: path.join(repo, 'src')}, encoding: 'utf8'}));

const context = vm.createContext({
  document: {
    createElement: tag => new Element(tag),
    createTextNode: text => Object.assign(new Element('text'), {textContent: text}),
  },
  encodeURIComponent,
});
const source = fs.readFileSync(path.join(repo, 'src/econ_agent_sim/results_0_9_component/component.js'), 'utf8');
vm.runInContext(source.replace('export default function', 'function'), context);
const host = new Element('host');
const root = new Element('div'); root.className = 'results-root'; host.append(root);
const allText = node => [node.textContent || '', ...node.children.map(allText)].join(' ');
const render = report => context.render({data: {reporting: report, diagnostics: {clearing_error: 1e-16}}, parentElement: host});

render(reports[0]);
assert(!/NaN|Unavailable|undefined/.test(allText(root)));
assert.equal(root.querySelectorAll('.metric').length, 3);
assert.equal(root.querySelectorAll('.household-card').length, 2);
assert.equal(root.querySelectorAll('.firm-card').length, 1);
assert.equal(root.querySelectorAll('.economy-card').length, 1);
assert.equal(root.querySelector('h2').textContent, 'Capital grew.');
assert(allText(root).includes('Next-period dividend · 0.55 M'));
assert(allText(root).includes('Net operating profit 0.81 M'));
assert(allText(root).includes('Capital made for own use 0.36 M'));
assert(allText(root).includes('not spendable cash'));
assert(allText(root).includes('Capital units 1.00 → 1.25'));
assert(root.querySelector('.allocation-bar').getAttribute('aria-label').includes('0.35 X installed'));
assert.equal(root.querySelectorAll('button').length, 0);

const firmDisclosure = root.querySelectorAll('details').find(node => node.getAttribute('data-disclosure') === 'firm-accounts');
firmDisclosure.open = true;
render(reports[1]);
assert(!/NaN|Unavailable|undefined/.test(allText(root)));
assert(allText(root).includes('Price and wage are for Period 2.'));
assert(allText(root).includes('Average work · leisure'));
assert(root.querySelectorAll('details').find(node => node.getAttribute('data-disclosure') === 'firm-accounts').open);
const csv = decodeURIComponent(root.querySelector('.download').href);
assert(csv.includes('"record_type"'));
assert(csv.includes('"unit"'));
assert(csv.includes('"capital_installation"'));
assert(csv.includes('"sender_id"'));
assert(csv.includes('"revaluation_reserve_close"'));
assert(csv.includes('"2"'));

// Preserve very small real amounts instead of the misleading "Bought 0" case.
const tiny = structuredClone(reports[0]);
tiny.price = 1.2e-14;
tiny.firm.next_dividend_budget = 9e-9;
tiny.households[0].closing_money = 2e-9;
render(tiny);
assert(allText(root).includes('1.20e−14'));
assert(allText(root).includes('9.00e−9 M'));
assert(allText(root).includes('2.00e−9 M'));
assert(!allText(root).includes('-0.00'));

const loss = structuredClone(reports[0]);
loss.firm.capital_close = .9;
loss.firm.net_operating_profit = -.1;
loss.firm.next_dividend_budget = 0;
loss.checks.money = false;
render(loss);
assert.equal(root.querySelector('h2').textContent, 'Capital declined.');
assert(allText(root).includes('No dividend available for next period.'));
assert(root.querySelector('.failure'));
assert(allText(root).includes('! Check failed · Evidence'));

// Compare actual experiments at the selected date, preserving independent
// values and the open comparison when a report rerenders.
context.render({data: {reporting: reports[1], comparison: reports[2]}, parentElement: host});
assert.equal(root.querySelectorAll('.comparison-metric').length, 6);
assert(allText(root).includes('Build capital'));
assert(allText(root).includes('Consume today'));
assert(allText(root).includes('Reinvest surplus'));
assert(allText(root).includes('pp vs baseline'));
assert(!/NaN|undefined/.test(allText(root)));
root.querySelectorAll('details').find(node => node.getAttribute('data-disclosure') === 'comparison').open = true;
context.render({data: {reporting: reports[1], comparison: reports[3]}, parentElement: host});
assert.equal(root.querySelectorAll('.comparison-metric').length, 0);
assert(allText(root).includes('Both experiments need Period 2'));
assert(allText(root).includes('Reinvest surplus'));
assert(!allText(root).includes('Both simulations have the same starting settings'));
assert(root.querySelectorAll('details').find(node => node.getAttribute('data-disclosure') === 'comparison').open);
console.log('Investment reports, comparison dates, disclosure state, tiny amounts, full evidence CSV passed.');
