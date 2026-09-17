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
from econ_agent_sim.engine import (
    Household, Firm, default_households, default_firms, advance_period,
)
from econ_agent_sim.reporting import build_report
from econ_agent_sim.comparison import compare_runs
households = tuple(Household(**item) for item in default_households())
firms = tuple(Firm(**item) for item in default_firms())
first = advance_period(households, firms)
second = advance_period(households, firms, previous=first)
baseline_firms = (replace(firms[0], reinvestment_rate=.2), firms[1])
baseline_first = advance_period(households, baseline_firms)
baseline_second = advance_period(households, baseline_firms, baseline_first)
comparison = compare_runs(
    (first, second), (baseline_first, baseline_second), selected_period=2,
    cumulative=True, current_name='Build capital', baseline_name='Consume today',
)
unavailable_comparison = compare_runs(
    (first, second), (baseline_first,), selected_period=2,
)
asymmetric = advance_period(
    households, (replace(firms[0], productivity=2.4), firms[1]),
)
fractional = advance_period(households, (
    replace(firms[0], reinvestment_rate=.123456, depreciation_rate=.001),
    replace(firms[1], reinvestment_rate=1e-12, depreciation_rate=0),
))
renamed_identity = advance_period(
    households, (firms[0], replace(firms[1], id='imported_firm')),
)
forward_firms = (replace(firms[0], investment_policy='user_cost', required_return=.05), firms[1])
forward_first = advance_period(households, forward_firms)
forward_second = advance_period(households, forward_firms, forward_first)
print(json.dumps([
    build_report((first,)), build_report((first, second), cumulative=True),
    comparison, unavailable_comparison, build_report(asymmetric),
    build_report(advance_period(tuple(replace(h, consumption_target=0) for h in households), firms)),
    build_report(advance_period((replace(households[0], consumption_target=4), households[1]), firms)),
    build_report(fractional), build_report(renamed_identity),
    compare_runs((renamed_identity,), (first,), selected_period=1),
    build_report(forward_first), build_report((forward_first, forward_second), cumulative=True),
]))
`], {cwd: repo, env: {...process.env, PYTHONPATH: path.join(repo, 'src')}, encoding: 'utf8'}));

const context = vm.createContext({
  document: {
    createElement: tag => new Element(tag),
    createTextNode: text => Object.assign(new Element('text'), {textContent: text}),
  },
  encodeURIComponent,
});
const source = fs.readFileSync(path.join(repo, 'src/econ_agent_sim/results_component/component.js'), 'utf8');
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

// Editable policy fractions use their own precision, including tiny active values.
render(reports[7], {selected_firm: reports[7].firms[0].entity_id});
assert.equal(root.querySelector('.parameters').textContent, '12.3456% reinvest surplus · 0.1% capital wear');
assert(allText(root).includes('Reinvest surplus 12.3456%'));
assert(allText(root).includes('Capital wear 0.1%'));
render(reports[7], {selected_firm: reports[7].firms[1].entity_id});
assert.equal(root.querySelector('.parameters').textContent, '1e−10% reinvest surplus · 0% capital wear');
assert(allText(root).includes('Reinvest surplus 1e−10%'));

// Forward-looking choices expose their budget and selected-period forecasts.
render(reports[10], {selected_firm: reports[10].firms[0].entity_id});
assert(allText(root).includes('Forward-looking · user cost'));
assert(allText(root).includes('Maximum surplus invested'));
assert(allText(root).includes('Required return 5%'));
assert(allText(root).includes('INVESTMENT DECISION · PERIOD 1'));
assert(allText(root).includes('Investment budget'));
assert(allText(root).includes('Wear to replace'));
assert(allText(root).includes('not an interest payment'));
assert(!/NaN|Unavailable|undefined/.test(allText(root)));
const investmentDisclosure = `firm-${reports[10].firms[0].entity_id}-investment`;
assert(!disclosure(investmentDisclosure).open);
disclosure(investmentDisclosure).open = true;
render(reports[11], {selected_firm: reports[11].firms[0].entity_id});
assert(disclosure(investmentDisclosure).open);
assert(allText(root).includes('INVESTMENT DECISION · PERIOD 2'));
assert(allText(root).includes('forecasts are not added across periods'));
const forwardCsv = decodeURIComponent(root.querySelector('.download').href);
assert(forwardCsv.includes('"investment_policy"'));
assert(forwardCsv.includes('"required_return"'));
assert(forwardCsv.includes('"investment_decision_expected_marginal_return"'));
render(reports[11], {selected_firm: reports[11].firms[1].entity_id});
assert(!root.querySelector('.investment-decision'));
assert(allText(root).includes('Fixed percentage · benchmark'));

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

// A missing firm identity must explain its absence while economy metrics remain.
render(reports[8], {comparison: reports[9], selected_firm: 'imported_firm'});
const unmatched = disclosure('firm-imported_firm-comparison');
assert(allText(unmatched).includes('This firm has no matching identity in the baseline.'));
assert.equal(unmatched.querySelectorAll('.comparison-metric').length, 0);
assert.equal(root.querySelectorAll('.comparison-metric').length, reports[9].metrics.length);
render(reports[8], {comparison: reports[9], selected_firm: reports[8].firms[0].entity_id});
const matched = disclosure(`firm-${reports[8].firms[0].entity_id}-comparison`);
assert.equal(matched.querySelectorAll('.comparison-metric').length, reports[9].firms[0].metrics.length);
assert(!allText(matched).includes('no matching identity'));

const failed = structuredClone(reports[0]);
failed.checks.money = false;
render(failed);
assert(root.querySelector('.failure'));
assert(allText(root).includes('! Check failed · Evidence'));
// Targets are visible in every scope without changing preferences or hiding shortages.
render(reports[0]);
assert.equal(root.querySelectorAll('.target-summary').length, 3);
assert(allText(root).includes('Consumption target · 0.50 X each period'));
assert(root.querySelectorAll('.target-bar').every(node => node.tag === 'progress' && node.max === 1 && node.value >= 0 && node.value <= 1 && node.getAttribute('aria-valuenow') !== undefined));
assert.equal(root.querySelector('.download').download.startsWith('tiny-economy-'), true);
render(reports[1]);
assert(allText(root).includes('Sum of period target gaps'));
assert(allText(root).includes('Extra consumption cannot erase an earlier target gap.'));
assert(allText(root).includes('One household’s extra consumption cannot cover another’s target gap.'));
render(reports[5]);
assert.equal(root.querySelectorAll('.target-bar').length, 0);
assert.equal(root.querySelectorAll('.target-off').length, 3);
assert(!/NaN|Unavailable|undefined/.test(allText(root)));
render(reports[6]);
assert(root.querySelectorAll('.target-shortfall').length >= 2);
assert(allText(root).includes('households below target'));
assert(allText(root).includes('Target gap'));
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
// Detected alternatives and the actual continuation convention are visible.
render(reports[0], {diagnostics: {
  candidate_count: 3, candidate_prices: [32.76, 75.29, 571.84],
  selected_candidate: 1, selection_rule: 'nearest_target_free_price',
  reference_price: 30, root_search_complete: false,
}});
assert(root.querySelector('.selection-note'));
assert(allText(root).includes('Candidates found · 3'));
assert(allText(root).includes('Sampled search; additional roots may exist'));
assert(allText(root).includes('Closest proportional price to the target-free economy'));
render(reports[1], {diagnostics: {
  candidate_count: 2, selection_rule: 'nearest_previous_price',
}});
assert(allText(root.querySelector('.selection-note')).includes('previous period’s price'));
console.log('Consumption target mobile reports, zero targets, shortfalls, scopes, selection and CSV passed.');

const styles = fs.readFileSync(path.join(repo, 'src/econ_agent_sim/results_component/styles.css'), 'utf8');
assert(!/font-size:\s*(?:9|10|11)px/.test(styles));
