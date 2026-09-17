// All report values are inserted as text. Only disclosure state is local to this view.
export default function render({ data, parentElement, setStateValue }) {
  const root = parentElement.querySelector('.results-root');
  const report = data.reporting;
  const opened = new Set([...root.querySelectorAll('details')]
    .filter(node => node.open).map(node => node.getAttribute('data-disclosure')));
  const fmt = (value, places = 2) => {
    const number = Number(value);
    if (!Number.isFinite(number)) return 'Unavailable';
    if (number !== 0 && (Math.abs(number) < .5 * 10 ** -places || Math.abs(number) >= 1e7)) {
      return number.toExponential(2).replace('e-', 'e−');
    }
    return (Object.is(number, -0) ? 0 : number).toLocaleString('en-US', {
      minimumFractionDigits: places, maximumFractionDigits: places,
    });
  };
  const money = value => `${fmt(value)} M`;
  const signed = value => `${value > 0 ? '+' : ''}${fmt(value)}`;
  const percent = (value, places = 0) => `${fmt(100 * value, places)}%`;
  const policyPercent = value => {
    const number = 100 * Number(value);
    if (!Number.isFinite(number)) return 'Unavailable';
    // Keep editable fractions and tiny positive policies visible without padding.
    return `${String(Number(number.toPrecision(12))).replace('e-', 'e−')}%`;
  };
  const el = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const row = (label, value, cls = '') => {
    const item = el('div', `statement-row ${cls}`.trim());
    item.append(el('span', '', label), el('strong', '', value));
    return item;
  };
  const statement = (title, rows, cls = '') => {
    const section = el('section', `statement ${cls}`.trim());
    section.append(el('div', 'statement-heading', title));
    for (const [label, value, tone] of rows) section.append(row(label, value, tone));
    return section;
  };
  const details = (id, label, body, cls = '') => {
    const section = el('details', cls);
    section.setAttribute('data-disclosure', id);
    section.open = opened.has(id);
    section.append(el('summary', '', label), body);
    return section;
  };
  const partyHeading = (name, index) => {
    const heading = el('h3', 'party-heading');
    heading.append(el('span', index === null ? 'firm-marker' : `party-marker tone-${index % 6}`,
      index === null ? 'F' : String(index + 1)), document.createTextNode(name));
    return heading;
  };
  const cumulative = report.scope === 'cumulative';
  const economy = report.economy;
  const firms = report.firms;
  let selectedFirm = firms.find(firm => firm.entity_id === data.selected_firm) || firms[0];

  const targetSummary = (account, wholeEconomy = false) => {
    const section = el('section', 'target-summary');
    section.setAttribute('aria-label', wholeEconomy ? 'Economy consumption targets' : 'Household consumption target');
    if (account.needed_x === 0) {
      section.append(el('p', 'target-off', wholeEconomy ? 'Consumption targets are off.' : 'Consumption target off.'));
      return section;
    }
    const below = wholeEconomy ? account.household_periods_below_target : account.below_target_periods;
    const coverage = Math.min(1, Math.max(0, account.target_coverage));
    const header = el('div', 'target-heading');
    header.append(el('span', '', cumulative ? 'TARGETS ACROSS PERIODS' : 'CONSUMPTION TARGET'));
    header.append(el('strong', below ? 'target-shortfall' : 'target-met',
      below ? cumulative ? 'Target gaps occurred' : 'Below target'
        : account.shortfall_x > 0 ? 'Within tolerance' : 'Target met'));
    section.append(header);
    const bar = el('progress', 'target-bar');
    bar.max = 1;
    bar.value = coverage;
    bar.setAttribute('aria-valuemin', '0');
    bar.setAttribute('aria-valuemax', '1');
    bar.setAttribute('aria-valuenow', String(coverage));
    bar.setAttribute('aria-valuetext', `${percent(coverage, 1)} of consumption targets covered`);
    bar.setAttribute('aria-label', `${percent(coverage, 1)} of consumption targets covered; ${fmt(account.shortfall_x)} X target gap`);
    if (below) bar.className += ' target-gap-bar';
    section.append(bar);
    section.append(row(cumulative ? 'Total targets' : wholeEconomy ? 'Combined targets' : 'Target this period', `${fmt(account.needed_x)} X`));
    section.append(row(cumulative ? 'Sum of period target gaps' : 'Target gap', `${fmt(account.shortfall_x)} X`, below ? 'target-gap' : ''));
    if (cumulative) {
      section.append(el('p', 'note', 'Extra consumption cannot erase an earlier target gap.'
        + (wholeEconomy ? ' One household’s extra consumption cannot cover another’s target gap.' : '')));
    } else if (wholeEconomy && below) {
      section.append(el('p', 'note', `${account.households_below_target} of ${report.households.length} households below target. Extra consumption by others does not cover their target gap.`));
    }
    return section;
  };

  root.replaceChildren();
  const shell = el('section', 'results');
  shell.setAttribute('aria-label', 'Tiny Economy results');
  shell.append(el('div', 'topline', `${report.label} · ${report.households.length} HOUSEHOLDS · ${firms.length} FIRMS`));
  const change = economy.capital_close - economy.capital_open;
  const maintained = Math.abs(change) <= 1e-9 * Math.max(economy.capital_open, economy.capital_close);
  shell.append(el('h2', '', maintained ? 'Capital held steady.' : change > 0 ? 'Capital grew.' : 'Capital declined.'));
  shell.append(el('p', 'intro', maintained
    ? economy.investment_quantity === 0 && economy.depreciation_quantity === 0
      ? 'There was no new investment or capital wear.'
      : 'New capital replaced the units that wore out.'
    : change > 0 ? 'Investment added more capital than wear removed.' : 'Wear removed more capital than investment added.'));
  if (cumulative) shell.append(el('p', 'scope-note', 'Activity adds at each period’s original prices. Balances show the first opening and selected closing.'));

  const metrics = el('div', 'headline-metrics');
  for (const [label, value, unit] of [
    ['X PRICE', report.price, 'M / X'],
    ['WAGE', report.wage, 'M / WORK'],
  ]) {
    const metric = el('div', 'metric');
    metric.append(el('span', 'eyebrow', label), el('strong', '', fmt(value, 4)), el('small', '', unit));
    metrics.append(metric);
  }
  shell.append(metrics);
  if (cumulative) shell.append(el('p', 'scope-note', `Price and wage are for Period ${report.through_period}.`));
  if (data.diagnostics?.candidate_count > 1) {
    const previous = data.diagnostics.selection_rule === 'nearest_previous_price';
    shell.append(el('p', 'selection-note', `The search found ${data.diagnostics.candidate_count} clearing prices for Period ${report.through_period}. This run follows the price closest in proportional terms to ${previous ? 'the previous period’s price' : 'the price with consumption targets off'}. See Ask why for the selection rule.`));
  }

  const appendComparisonLegend = (body, comparison) => {
    const legend = el('div', 'comparison-legend');
    for (const [label, name] of [['BASELINE', comparison.baseline_name], ['CURRENT', comparison.current_name]]) {
      const item = el('div', '');
      item.append(el('span', 'eyebrow', label), el('strong', '', name));
      legend.append(item);
    }
    body.append(legend);
  };
  const appendComparisonMetrics = (body, metrics) => {
    for (const metric of metrics) {
      const places = ['price', 'real_wage'].includes(metric.key) ? 4 : 2;
      const item = el('div', 'comparison-metric');
      item.append(el('div', 'comparison-label', `${metric.label} · ${metric.unit}`));
      item.append(el('strong', 'baseline-value', fmt(metric.baseline, places)));
      const current = el('div', 'current-value');
      current.append(el('strong', '', fmt(metric.current, places)));
      current.append(el('small', '', `${signed(metric.change)} ${metric.change_unit} vs baseline`));
      item.append(current);
      body.append(item);
    }
  };

  if (data.comparison) {
    const comparison = data.comparison;
    const body = el('div', 'comparison-body');
    body.append(el('p', 'scope-note', comparison.label));
    if (comparison.available) {
      appendComparisonLegend(body, comparison);
      appendComparisonMetrics(body, comparison.metrics);
    }
    body.append(el('p', 'note', comparison.note));
    const changes = el('div', 'comparison-changes');
    if (comparison.settings_changes.length) {
      for (const setting of comparison.settings_changes) {
        const value = number => typeof number === 'number' ? fmt(number) : String(number);
        changes.append(row(`${setting.entity} · ${setting.label}`,
          `${value(setting.baseline)} → ${value(setting.current)}${setting.unit ? ` ${setting.unit}` : ''}`));
      }
    } else {
      changes.append(el('p', 'note', 'Both simulations use the same starting settings.'));
    }
    body.append(details('comparison-settings', `Changed settings · ${comparison.settings_changes.length}`, changes, 'activity'));
    shell.append(details('comparison', 'Compare with baseline', body, 'comparison'));
  }

  const economyCard = el('article', 'card economy-card');
  economyCard.append(el('h3', 'card-heading', 'Whole economy'));
  const production = el('div', 'production-allocation');
  production.append(el('div', 'statement-heading', 'WHERE THE OUTPUT WENT'));
  production.append(el('div', 'output-total', `${fmt(economy.produced_x)} X produced`));
  const bar = el('div', 'allocation-bar');
  bar.setAttribute('role', 'img');
  bar.setAttribute('aria-label', `${fmt(economy.consumed_x)} X consumed; ${fmt(economy.investment_quantity)} X installed as capital`);
  const consumedBar = el('span', 'consumed-bar');
  const investedBar = el('span', 'invested-bar');
  const consumedShare = economy.produced_x > 0 ? economy.consumed_x / economy.produced_x : 0;
  consumedBar.style.width = `${100 * consumedShare}%`;
  investedBar.style.width = `${100 * (1 - consumedShare)}%`;
  bar.append(consumedBar, investedBar);
  production.append(bar);
  const allocation = el('div', 'allocation-labels');
  const consumedLabel = el('div', 'consumed-label');
  consumedLabel.append(el('span', '', 'Consumed'), el('strong', '', `${fmt(economy.consumed_x)} X`));
  const investedLabel = el('div', 'invested-label');
  investedLabel.append(el('span', '', 'Added to capital'), el('strong', '', `${fmt(economy.investment_quantity)} X`));
  allocation.append(consumedLabel, investedLabel);
  production.append(allocation);
  economyCard.append(production);
  economyCard.append(targetSummary(economy, true));
  economyCard.append(row('Capital units', `${fmt(economy.capital_open)} → ${fmt(economy.capital_close)}`, 'total'));
  economyCard.append(row('Total money', money(economy.closing_money)));
  economyCard.append(statement('INCOME · MONEY VALUE', [
    ['Wages earned', money(economy.wages)],
    ['Firms’ net profit', money(economy.net_operating_profit)],
    ['Net economy income', money(economy.net_income), 'total'],
  ]));
  const economyBody = el('div', 'statement-body');
  economyBody.append(statement('FROM OUTPUT TO NET INCOME', [
    ['Output value', money(economy.production_value)],
    ['Less capital wear', `−${money(economy.depreciation_value)}`],
    ['Net economy income', money(economy.net_income), 'total'],
  ]));
  economyBody.append(el('p', 'note', 'Dividends move income between firms and their owners; they are not added to economy income again.'));
  economyBody.append(el('p', 'note', 'Amounts are rounded for display. Totals use full precision, so rounded rows may not add exactly.'));
  economyBody.append(statement('RESOURCES', [
    ['Money at opening', money(economy.opening_money)],
    ['Money at closing', money(economy.closing_money)],
    ['Produced', `${fmt(economy.produced_x)} X`],
    ['Consumed', `${fmt(economy.consumed_x)} X`],
    ['Installed as capital', `${fmt(economy.investment_quantity)} X`],
  ]));
  economyBody.append(statement('BALANCE SHEET · CLOSING', [
    ['Money', money(economy.closing_money)],
    ['Capital at replacement price', money(economy.capital_value_close)],
    ['Assets within this model', money(economy.assets_close), 'total'],
  ]));
  economyBody.append(el('p', 'note', 'Ownership claims are excluded here so the same firms’ assets are not counted twice.'));
  economyCard.append(details('economy', 'Income and resource details', economyBody, 'activity'));
  shell.append(economyCard);

  const firmHeading = firm => {
    const heading = el('h3', 'party-heading');
    const index = firms.findIndex(item => item.entity_id === firm.entity_id);
    heading.append(el('span', `firm-marker firm-tone-${index}`, String.fromCharCode(65 + index)), document.createTextNode(firm.name));
    return heading;
  };
  shell.append(el('h3', 'section-heading', 'Firms in this economy'));
  shell.append(el('p', 'note', 'Share of sales counts X sold to households. Output kept as new capital is shown separately.'));
  const overviews = el('div', 'firm-overviews');
  for (const firm of firms) {
    const card = el('article', 'card firm-overview');
    card.setAttribute('data-firm', firm.entity_id);
    card.append(firmHeading(firm));
    const sales = el('div', 'sales-summary');
    sales.append(el('span', '', `${fmt(firm.sold_x)} X sold`), el('strong', '', `${percent(firm.sales_share, 1)} share of sales`));
    card.append(sales);
    const grid = el('div', 'firm-metrics');
    for (const [label, value] of [
      ['Produced', `${fmt(firm.produced_x)} X`],
      [cumulative ? 'Work-periods used' : 'Work used', fmt(firm.work_used)],
      ['Net profit', money(firm.net_operating_profit)],
      ['Closing capital', fmt(firm.capital_close)],
    ]) {
      const metric = el('div', 'firm-metric');
      metric.append(el('span', '', label), el('strong', '', value));
      grid.append(metric);
    }
    card.append(grid);
    if (firm.funding_binding) card.append(el('p', 'funding-note',
      `Hiring limited by available cash${cumulative ? ` · Period ${firm.funding_period}` : ''}.`));
    overviews.append(card);
  }
  shell.append(overviews);
  shell.append(el('p', 'note', 'One work unit is one household working for a full period.'));

  const renderFirmCard = firm => {
    const firmCard = el('article', 'card firm-card');
    firmCard.append(firmHeading(firm));
    const forwardLooking = firm.parameters.investment_policy === 'user_cost';
    firmCard.append(el('p', 'parameters', forwardLooking
      ? `Forward-looking · user cost · ${policyPercent(firm.parameters.reinvestment_rate)} maximum surplus invested · ${policyPercent(firm.parameters.depreciation_rate)} capital wear`
      : `${policyPercent(firm.parameters.reinvestment_rate)} reinvest surplus · ${policyPercent(firm.parameters.depreciation_rate)} capital wear`));
    firmCard.append(statement('PRODUCTION · X', [
      ['Produced', fmt(firm.produced_x)],
      ['Sold to households', fmt(firm.sold_x)],
      ['Added to capital', fmt(firm.investment_quantity)],
      ['Share of production', percent(firm.production_share, 1)],
      ['Share of sales', percent(firm.sales_share, 1)],
    ], 'production-statement'));
    const capitalBridge = el('div', 'capital-bridge');
    capitalBridge.append(row('Capital units', `${fmt(firm.capital_open)} → ${fmt(firm.capital_close)}`, 'total'));
    capitalBridge.append(el('p', 'note', `Added ${fmt(firm.investment_quantity)} · Wear ${fmt(firm.depreciation_quantity)}. Closing capital works next period.`));
    firmCard.append(capitalBridge);
    const decision = firm.investment_decision;
    if (decision) {
      const reasons = {
        returns_below_cost: 'Expected returns do not justify adding capital at the required return and wear rate.',
        budget_limited: 'Investment reaches the chosen budget ceiling.',
        interior: 'Expected marginal return meets user cost at the chosen closing capital.',
        indifferent: 'Several investment amounts earn the same forecast score; this amount clears the goods market.',
      };
      const decisionBody = el('div', 'investment-decision');
      decisionBody.append(statement(`INVESTMENT DECISION · PERIOD ${decision.period}`, [
        ['Invested', `${fmt(decision.investment_quantity)} X`],
        ['Investment budget', `${fmt(decision.investment_budget_quantity)} X`],
        ['Wear to replace', `${fmt(decision.replacement_quantity)} X`],
        ['Expected marginal return', policyPercent(decision.expected_marginal_return)],
        ['User cost · return + wear', policyPercent(decision.user_cost)],
      ]));
      decisionBody.append(el('p', 'note', reasons[decision.reason] || 'Investment follows the submitted user-cost policy.'));
      decisionBody.append(el('p', 'note', `Forecast at unchanged prices, wage and payroll cash. Required return is a decision threshold, not an interest payment. These figures describe Period ${decision.period}; forecasts are not added across periods.`));
      firmCard.append(details(`firm-${firm.entity_id}-investment`, 'Why this investment?', decisionBody));
    }
    firmCard.append(statement('INCOME · MONEY VALUE', [
      ['Output value¹', money(firm.production_value)],
      ['Wages', `−${money(firm.wages_paid)}`],
      ['Surplus before wear', money(firm.gross_operating_surplus)],
      ['Capital wear', `−${money(firm.depreciation_value)}`],
      ['Net operating profit', money(firm.net_operating_profit), 'total'],
    ], 'income-statement'));
    firmCard.append(el('p', 'note output-note', '¹ Includes capital the firm made for itself.'));
    const firmBody = el('div', 'statement-body');
    firmBody.append(statement('CASH ACCOUNT', [
      ['Opening money', money(firm.opening_money)],
      ['Dividends paid', `−${money(firm.dividends_paid)}`],
      ['Wages paid', `−${money(firm.wages_paid)}`],
      ['Cash sales', `+${money(firm.sales_received)}`],
      ['Closing money', money(firm.closing_money), 'total'],
    ]));
    firmBody.append(el('p', 'note', 'Installing the firm’s own output uses goods, not a cash payment.'));
    firmBody.append(statement('CAPITAL · UNITS', [
      ['Opening capital', fmt(firm.capital_open)],
      ['Wear', `−${fmt(firm.depreciation_quantity)}`],
      ['New capital', `+${fmt(firm.investment_quantity)}`],
      ['Capital for next period', fmt(firm.capital_close), 'total'],
    ]));
    firmBody.append(statement('OUTPUT VALUE', [
      ['Cash sales', money(firm.sales_received)],
      ['Capital made for own use', money(firm.investment_value)],
      ['Output value', money(firm.production_value), 'total'],
    ]));
    firmBody.append(statement('BALANCE SHEET · CLOSING', [
      ['Money', money(firm.closing_money)],
      ['Capital at replacement price', money(firm.capital_value_close)],
      ['Equity · no debt', money(firm.equity_close), 'total'],
    ]));
    firmBody.append(statement('CHANGE IN EQUITY', [
      ['Opening equity', money(firm.equity_open)],
      ['Net operating profit', `${signed(firm.net_operating_profit)} M`],
      ['Dividends paid', `−${money(firm.dividends_paid)}`],
      ['Capital revaluation', `${signed(firm.holding_gain)} M`],
      ['Closing equity', money(firm.equity_close), 'total'],
    ]));
    firmBody.append(statement('EQUITY ACCOUNTS · CLOSING', [
      ['Initial contributed equity', money(firm.contributed_equity)],
      ['Retained earnings', money(firm.retained_earnings_close)],
      ['Revaluation reserve', money(firm.revaluation_reserve_close)],
    ]));
    firmBody.append(el('p', 'note', 'Capital uses the current replacement price of X. Revaluation changes asset value, not cash or operating profit.'));
    firmBody.append(statement('SUBMITTED SETTINGS', [
      ['Productivity', fmt(firm.parameters.productivity)],
      ['Investment policy', forwardLooking ? 'Forward-looking · user cost' : 'Fixed percentage · benchmark'],
      [forwardLooking ? 'Maximum surplus invested' : 'Reinvest surplus', policyPercent(firm.parameters.reinvestment_rate)],
      ...(forwardLooking ? [['Required return', policyPercent(firm.parameters.required_return)]] : []),
      ['Capital wear', policyPercent(firm.parameters.depreciation_rate)],
      ['Protected operating float', money(firm.protected_operating_float)],
    ]));
    firmCard.append(firmBody);
    firmCard.append(el('p', 'dividend-note', firm.next_dividend_budget > 0
      ? `Next-period dividend · ${money(firm.next_dividend_budget)}`
      : 'No dividend available for next period.'));
    const allocationBody = el('div', 'statement-body');
    for (const allocation of firm.allocations || []) {
      allocationBody.append(statement(allocation.name, [
        ['Work supplied', `${fmt(allocation.work)} ${cumulative ? 'work-periods' : 'work units'}`],
        ['Wages received', money(allocation.wages_paid)],
        ['Dividends received', money(allocation.dividends_paid)],
        ['Bought from this firm', `${fmt(allocation.sold_x)} X`],
        ['Paid for purchases', money(allocation.sales_received)],
      ]));
    }
    firmCard.append(details(`firm-${firm.entity_id}-households`, 'By household', allocationBody, 'activity'));
    const compared = data.comparison;
    if (compared) {
      const comparisonBody = el('div', 'comparison-body');
      const match = compared.firms?.find(item => item.entity_id === firm.entity_id);
      comparisonBody.append(el('p', 'note', compared.label));
      if (compared.available && match?.available) {
        appendComparisonLegend(comparisonBody, compared);
        appendComparisonMetrics(comparisonBody, match.metrics);
      } else if (compared.available) {
        comparisonBody.append(el('p', 'note', match?.note || 'This firm has no matching identity in the baseline.'));
      }
      comparisonBody.append(el('p', 'note', compared.note));
      firmCard.append(details(`firm-${firm.entity_id}-comparison`, `${firm.name} vs baseline`, comparisonBody, 'activity'));
    }
    return firmCard;


  };
  const accountsBody = el('div', 'firm-account-body');
  const selector = el('div', 'firm-selector');
  selector.setAttribute('role', 'group');
  selector.setAttribute('aria-label', 'Select firm account');
  const selectedBody = el('div', 'selected-firm');
  const selectFirm = firm => {
    selectedFirm = firm;
    for (const button of selector.querySelectorAll('button')) {
      button.setAttribute('aria-pressed', String(button.getAttribute('data-firm') === firm.entity_id));
    }
    selectedBody.replaceChildren(renderFirmCard(firm));
  };
  for (const firm of firms) {
    const button = el('button', '', firm.name);
    button.type = 'button';
    button.setAttribute('data-firm', firm.entity_id);
    button.setAttribute('aria-pressed', String(firm.entity_id === selectedFirm.entity_id));
    button.addEventListener('click', () => {
      selectFirm(firm);
      if (setStateValue) setStateValue('selected_firm', firm.entity_id);
    });
    selector.append(button);
  }
  selectedBody.append(renderFirmCard(selectedFirm));
  accountsBody.append(selector, selectedBody);
  shell.append(details('firm-accounts', 'Firm accounts', accountsBody, 'firm-accounts'));

  shell.append(el('h3', 'section-heading', 'Households'));
  const households = el('div', 'cards');
  report.households.forEach((household, index) => {
    const card = el('article', 'card household-card');
    card.append(partyHeading(household.name, index));
    const weights = household.parameters.weights;
    const priorities = el('div', 'priorities');
    priorities.setAttribute('aria-label', 'Chosen base preference weights');
    for (const [label, weight] of [['Consume', weights.consumption], ['Money', weights.money], ['Leisure', weights.leisure]]) {
      const item = el('span', 'priority');
      item.append(el('small', '', label), el('strong', '', percent(weight)));
      priorities.append(item);
    }
    card.append(priorities);
    card.append(row('Money', `${fmt(household.opening_money)} → ${fmt(household.closing_money)} M`, 'total'));
    card.append(row('Consumed', `${fmt(household.consumed_x)} X`));
    card.append(targetSummary(household));
    card.append(row(cumulative ? 'Average work · leisure' : 'Work · leisure',
      `${fmt(100 * household.average_work, 1)}% · ${fmt(100 * household.average_leisure, 1)}%`));
    const body = el('div', 'statement-body');
    body.append(statement('CASH ACCOUNT', [
      ['Opening money', money(household.opening_money)],
      ['Wages received', `+${money(household.wages_received)}`],
      ['Dividends received', `+${money(household.dividends_received)}`],
      ['Consumption purchases', `−${money(household.purchases_paid)}`],
      ['Closing money', money(household.closing_money), 'total'],
    ]));
    body.append(statement('ASSETS · CLOSING', [
      ['Spendable money', money(household.closing_money)],
      ['Ownership of both firms', money(household.ownership_value_close)],
      ['Assets within this model', money(household.assets_close), 'total'],
    ]));
    body.append(el('p', 'note', 'Ownership is a fixed share of firm equity, not spendable cash or a traded share price.'));
    const scores = household.parameters.scores;
    body.append(el('p', 'note', `Chosen scores · ${fmt(scores.consumption)} consume · ${fmt(scores.money)} money · ${fmt(scores.leisure)} leisure.`));
    body.append(el('p', 'note', `Consumption target · ${fmt(household.parameters.consumption_target)} X each period. The preference scores stay fixed; target gaps add urgency without guaranteeing the target.`));
    if (cumulative) body.append(row('Total work', `${fmt(household.total_work)} work-periods`));
    const byFirm = el('div', 'statement-body');
    for (const allocation of household.firms || []) {
      byFirm.append(statement(allocation.name, [
        ['Work supplied', `${fmt(allocation.work)} ${cumulative ? 'work-periods' : 'work units'}`],
        ['Wages received', money(allocation.wages_received)],
        ['Dividends received', money(allocation.dividends_received)],
        ['Bought from this firm', `${fmt(allocation.consumed_x)} X`],
        ['Paid for purchases', money(allocation.purchases_paid)],
        [`Ownership · ${percent(allocation.ownership)}`, money(allocation.ownership_value_close)],
      ]));
    }
    body.append(details(`household-${household.entity_id}-firms`, 'By firm', byFirm, 'activity'));
    card.append(details(`household-${household.entity_id}`, 'Cash and ownership', body, 'activity'));
    households.append(card);
  });
  shell.append(households);

  const checkValues = Object.values(report.checks || {});
  const checksPassed = checkValues.length > 0 && checkValues.every(Boolean);
  if (!checksPassed) shell.append(el('div', 'failure', 'A check needs attention. Open the evidence below.'));
  const evidenceBody = el('div', 'evidence-body');
  for (const [label, passed] of Object.entries(report.checks || {})) {
    evidenceBody.append(row(label.replaceAll('_', ' '), passed ? 'Verified' : 'Check failed', passed ? 'pass' : 'fail'));
  }
  if (report.transfers?.length) {
    const ledger = el('div', 'ledger');
    const visibleTransfers = report.transfers.slice(-80);
    if (visibleTransfers.length < report.transfers.length) ledger.append(el('p', 'note', 'Showing the latest 80 transfers. The CSV includes every period.'));
    for (const transfer of visibleTransfers) {
      ledger.append(el('p', '', `P${transfer.period} · ${transfer.sender} → ${transfer.receiver} · ${fmt(transfer.quantity, 4)} ${transfer.asset} · ${transfer.kind.replaceAll('_', ' ')}`));
    }
    evidenceBody.append(details('transfers', `Settlement ledger · ${report.transfers.length} transfers`, ledger, 'ledger-details'));
  }
  if (data.diagnostics) {
    const technical = el('div', 'technical');
    const labels = {
      candidate_count: 'Candidates found', candidate_prices: 'Candidate X prices',
      selected_candidate: 'Selected candidate', reference_price: 'Reference X price',
      selection_rule: 'Selection rule', root_search_complete: 'Search coverage',
    };
    for (const [label, value] of Object.entries(data.diagnostics)) {
      let shown = Array.isArray(value) ? value.map(item => fmt(item, 4)).join(', ')
        : typeof value === 'number' ? Number(value.toPrecision(4)).toString() : value;
      if (label === 'selection_rule') shown = value === 'nearest_previous_price'
        ? 'Closest proportional price to the previous period'
        : 'Closest proportional price to the target-free economy';
      if (label === 'root_search_complete') shown = value
        ? 'Analytical target-free solution' : 'Sampled search; additional roots may exist';
      technical.append(el('p', '', `${labels[label] || label.replaceAll('_', ' ')} · ${shown}`));
    }
    technical.append(el('p', 'note', 'Small nonzero values use scientific notation. Rounded rows may not add exactly; calculations and CSV values retain full precision.'));
    evidenceBody.append(details('technical', 'Technical details', technical, 'technical-details'));
  }
  const columns = [...new Set((report.rows || []).flatMap(item => Object.keys(item)))];
  const csvRows = [columns, ...(report.rows || []).map(item => columns.map(column => item[column] ?? ''))];
  const csv = csvRows.map(values => values.map(value => `"${String(value).replaceAll('"', '""')}"`).join(',')).join('\n');
  const download = el('a', 'download', 'Download complete accounts (CSV)');
  download.href = `data:text/csv;charset=utf-8,${encodeURIComponent(csv)}`;
  download.download = `tiny-economy-${report.label.toLowerCase().replaceAll(' ', '-').replace('–', '-')}-accounts.csv`;
  evidenceBody.append(download);
  shell.append(details('evidence', `${checksPassed ? '✓ All checks passed' : '! Check failed'} · Evidence`, evidenceBody, `evidence ${checksPassed ? 'passed' : 'failed'}`));
  shell.append(el('p', 'boundary', 'Targets apply each period; target gaps do not become debt or build up extra urgency. Money and capital carry forward. No borrowing or money creation.'));
  root.append(shell);
}
