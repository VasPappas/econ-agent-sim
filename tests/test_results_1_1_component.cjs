// Render the real Python report through the phone component with no npm packages.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {execFileSync} = require('node:child_process');
const assert = require('node:assert/strict');

class Element {
  constructor(tag) {
    this.tag = tag; this.children = []; this.className = '';
    this.attributes = {}; this.style = {}; this.open = false; this.listeners = {};
  }
  addEventListener(event, handler) { this.listeners[event] = handler; }
  click() { this.listeners.click?.(); }
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
from dataclasses import replace
from econ_agent_sim.economy_1_1 import (
    Household, Firm, default_households, default_firms, advance_target_period,
)
from econ_agent_sim.target_reporting import target_report
from econ_agent_sim.target_comparison import compare_target_runs
households = tuple(Household(**item) for item in default_households())
firms = tuple(Firm(**item) for item in default_firms())
first = advance_target_period(households, firms)
second = advance_target_period(households, firms, previous=first)
baseline_firms = (replace(firms[0], reinvestment_rate=.2), firms[1])
baseline_first = advance_target_period(households, baseline_firms)
baseline_second = advance_target_period(households, baseline_firms, baseline_first)
comparison = compare_target_runs(
    (first, second), (baseline_first, baseline_second), selected_period=2,
    cumulative=True, current_name='Build capital', baseline_name='Consume today',
)
unavailable_comparison = compare_target_runs(
    (first, second), (baseline_first,), selected_period=2,
)
asymmetric = advance_target_period(
    households, (replace(firms[0], productivity=2.4), firms[1]),
)
print(json.dumps([
    target_report((first,)), target_report((first, second), cumulative=True),
    comparison, unavailable_comparison, target_report(asymmetric),
    target_report(advance_target_period(tuple(replace(h, consumption_target=0) for h in households), firms)),
    target_report(advance_target_period((replace(households[0], consumption_target=4), households[1]), firms)),
]))
`], {cwd: repo, env: {...process.env, PYTHONPATH: path.join(repo, 'src')}, encoding: 'utf8'}));

const context = vm.createContext({
  document: {
    createElement: tag => new Element(tag),
    createTextNode: text => Object.assign(new Element('text'), {textContent: text}),
  },
  encodeURIComponent,
});
const source = fs.readFileSync(path.join(repo, 'src/econ_agent_sim/results_1_1_component/component.js'), 'utf8');
vm.runInContext(source.replace('export default function', 'function'), context);
const host = new Element('host');
const root = new Element('div'); root.className = 'results-root'; host.append(root);
const allText = node => [node.textContent || '', ...node.children.map(allText)].join(' ');
let selected = reports[0].firms[0].entity_id;
const changes = [];
const render = (report, extra = {}) => context.render({
  data: {reporting: report, diagnostics: {clearing_error: 1e-16}, selected_firm: selected, ...extra},
  parentElement: host,
  setStateValue: (key, value) => { changes.push([key, value]); selected = value; },
});
const disclosure = id => root.querySelectorAll('details').find(node => node.getAttribute('data-disclosure') === id);



render(reports[0]);
assert(!/NaN|Unavailable|undefined/.test(allText(root)));
assert.equal(root.querySelectorAll('.metric').length, 2);
assert.equal(root.querySelectorAll('.firm-overview').length, 2);
assert.equal(root.querySelectorAll('.firm-card').length, 1);
assert.equal(root.querySelectorAll('.household-card').length, 2);
assert.equal(root.querySelectorAll('.economy-card').length, 1);
assert.equal(root.querySelector('h2').textContent, 'Capital grew.');
assert.equal(root.querySelectorAll('.sales-summary').filter(node => allText(node).includes('50.0% share of sales')).length, 2);
assert(allText(root).includes('Ownership of both firms'));
assert(allText(root).includes('not spendable cash'));
assert(!disclosure('firm-accounts').open);

// Both identities stay visible while only the selected firm has full accounts.
disclosure('firm-accounts').open = true;
const firmB = reports[0].firms[1].entity_id;
root.querySelector('.firm-selector').querySelectorAll('button')[1].click();
assert.deepEqual(changes, [['selected_firm', firmB]]);
assert(allText(root.querySelector('.selected-firm')).includes('Firm B'));
assert.equal(root.querySelectorAll('.firm-card').length, 1);
assert(disclosure('firm-accounts').open);
render(reports[1]);
assert(!/NaN|Unavailable|undefined/.test(allText(root)));
assert(disclosure('firm-accounts').open);
assert.equal(root.querySelector('.firm-selector').querySelectorAll('button')[1].getAttribute('aria-pressed'), 'true');
assert(allText(root).includes('Price and wage are for Period 2.'));
assert(allText(root).includes('original prices'));
assert(allText(root).includes('Average work · leisure'));
assert(allText(root).includes('Work-periods used'));
const csv = decodeURIComponent(root.querySelector('.download').href);
assert(csv.includes('"record_type"'));
assert(csv.includes('"capital_installation"'));
assert(csv.includes('"sender_id"'));
assert(csv.includes('"revaluation_reserve_close"'));
assert(csv.includes('"firm_a"') && csv.includes('"firm_b"'));
assert(csv.includes('"labor_delivery"'));

// Capped hiring is firm specific; it does not mark the other firm as constrained.
render(reports[4]);
assert.equal(root.querySelector('.firm-overview').getAttribute('data-firm'), reports[4].firms[0].entity_id);
assert(!/NaN|Unavailable|undefined/.test(allText(root)));

// Preserve positive tiny values instead of displaying a false zero or closure.
const tiny = structuredClone(reports[0]);
tiny.price = 1.2e-14;
tiny.firms[1].next_dividend_budget = 9e-9;
tiny.firms[1].produced_x = 2e-12;
tiny.households[0].closing_money = 2e-9;
render(tiny);
assert(allText(root).includes('1.20e−14'));
assert(allText(root).includes('9.00e−9 M'));
assert(allText(root).includes('2.00e−12 X'));
assert(allText(root).includes('2.00e−9 M'));
assert(!allText(root).includes('-0.00'));

// Names are always plain text, including imported labels that resemble markup.
const renamed = structuredClone(reports[0]);
renamed.firms[1].name = '<script>unsafe()</script>';
render(renamed);
assert(allText(root).includes('<script>unsafe()</script>'));
assert.equal(root.querySelectorAll('script').length, 0);
assert.equal(root.querySelector('.firm-selector').querySelectorAll('button')[1].getAttribute('data-firm'), firmB);

render(reports[1], {comparison: reports[2]});
assert.equal(root.querySelectorAll('.comparison-metric').length, reports[2].metrics.length + reports[2].firms[1].metrics.length);
assert(allText(root).includes('Build capital'));
assert(allText(root).includes('Consume today'));
assert(allText(root).includes('pp vs baseline'));
assert(allText(root).includes('Firm B vs baseline'));
assert(!/NaN|Unavailable|undefined/.test(allText(root)));
disclosure('comparison').open = true;
render(reports[1], {comparison: reports[3]});
assert.equal(root.querySelectorAll('.comparison-metric').length, 0);
assert(disclosure('comparison').open);
assert(allText(root).includes('Both experiments need Period 2'));

const failed = structuredClone(reports[0]);
failed.checks.money = false;
render(failed);
assert(root.querySelector('.failure'));
assert(allText(root).includes('! Check failed · Evidence'));
// Targets are visible in every scope without changing preferences or hiding shortages.
render(reports[0]);
assert.equal(root.querySelectorAll('.target-summary').length, 3);
assert(allText(root).includes('Consumption target · 0.50 X each period'));
assert(root.querySelectorAll('.target-bar').every(node => node.getAttribute('role') === 'img'));
assert.equal(root.querySelector('.download').download.startsWith('economy-11-'), true);
render(reports[1]);
assert(allText(root).includes('Sum of period shortfalls'));
assert(allText(root).includes('Extra consumption cannot erase an earlier shortfall.'));
assert(allText(root).includes('One household’s extra consumption cannot cover another’s shortfall.'));
render(reports[5]);
assert.equal(root.querySelectorAll('.target-bar').length, 0);
assert.equal(root.querySelectorAll('.target-off').length, 3);
assert(!/NaN|Unavailable|undefined/.test(allText(root)));
render(reports[6]);
assert(root.querySelectorAll('.target-shortfall').length >= 2);
assert(allText(root).includes('households below target'));
assert(allText(root).includes('Shortfall'));
assert(!/NaN|Unavailable|undefined/.test(allText(root)));

// Genuine shortages remain visible when their coverage rounds to 100 percent.
const nearTarget = structuredClone(reports[0]);
nearTarget.households[0].needed_x = .5;
nearTarget.households[0].shortfall_x = .0001;
nearTarget.households[0].target_coverage = .9998;
nearTarget.households[0].below_target_periods = 1;
render(nearTarget);
assert(allText(root).includes('1.00e−4 X'));
assert(root.querySelector('.target-shortfall'));
console.log('Consumption target mobile reports, zero targets, shortfalls, scopes, selection and CSV passed.');
