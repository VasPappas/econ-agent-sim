// All report values are inserted as text. Only disclosure state is local to this view.
export default function render({ data, parentElement }) {
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
  const percent = value => `${fmt(100 * value, 0)}%`;
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
  const firm = report.firm;

  root.replaceChildren();
  const shell = el('section', 'results');
  shell.setAttribute('aria-label', 'Investment and growth results');
  shell.append(el('div', 'topline', `${report.label} · ${report.households.length} HOUSEHOLDS + ONE FIRM`));
  const change = firm.capital_close - firm.capital_open;
  const maintained = Math.abs(change) <= 1e-9 * Math.max(firm.capital_open, firm.capital_close);
  shell.append(el('h2', '', maintained ? 'Capital held steady.' : change > 0 ? 'Capital grew.' : 'Capital declined.'));
  shell.append(el('p', 'intro', maintained
    ? firm.investment_quantity === 0 && firm.depreciation_quantity === 0
      ? 'There was no new investment or capital wear.'
      : 'New capital replaced the units that wore out.'
    : change > 0 ? 'Investment added more capital than wear removed.' : 'Wear removed more capital than investment added.'));
  if (cumulative) shell.append(el('p', 'scope-note', 'Activity adds across these periods. Balances show the first opening and selected closing.'));

  const metrics = el('div', 'headline-metrics');
  for (const [label, value, unit] of [
    ['X PRICE', report.price, 'M / X'],
    ['WAGE', report.wage, 'M / WORK'],
    [cumulative ? 'TOTAL OUTPUT' : 'OUTPUT', economy.produced_x, 'X'],
  ]) {
    const metric = el('div', 'metric');
    metric.append(el('span', 'eyebrow', label), el('strong', '', fmt(value, 4)), el('small', '', unit));
    metrics.append(metric);
  }
  shell.append(metrics);
  if (cumulative) shell.append(el('p', 'scope-note', `Price and wage are for Period ${report.through_period}.`));

  const economyCard = el('article', 'card economy-card');
  economyCard.append(el('h3', 'card-heading', 'Whole economy'));
  const production = el('div', 'production-allocation');
  production.append(el('div', 'statement-heading', 'WHERE THE OUTPUT WENT'));
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
  economyCard.append(row('Capital units', `${fmt(economy.capital_open)} → ${fmt(economy.capital_close)}`, 'total'));
  economyCard.append(row('Total money', money(economy.closing_money)));
  economyCard.append(statement('INCOME · MONEY VALUE', [
    ['Wages earned', money(economy.wages)],
    ['Firm net profit', money(economy.net_operating_profit)],
    ['Net economy income', money(economy.net_income), 'total'],
  ]));
  const economyBody = el('div', 'statement-body');
  economyBody.append(statement('FROM OUTPUT TO NET INCOME', [
    ['Output value', money(economy.production_value)],
    ['Less capital wear', `−${money(economy.depreciation_value)}`],
    ['Net economy income', money(economy.net_income), 'total'],
  ]));
  economyBody.append(el('p', 'note', 'Dividends move income between the firm and its owners; they are not added to economy income again.'));
  economyBody.append(el('p', 'note', 'Amounts are rounded for display. Totals use full precision, so rounded rows may not add exactly.'));
  economyBody.append(statement('RESOURCES', [
    ['Money at opening', money(economy.opening_money)],
    ['Money at closing', money(economy.closing_money)],
    ['Produced', `${fmt(economy.produced_x)} X`],
    ['Consumed', `${fmt(economy.consumed_x)} X`],
    ['Installed as capital', `${fmt(economy.investment_quantity)} X`],
  ]));
  economyBody.append(el('p', 'note', 'Ownership claims are excluded here so the same firm assets are not counted twice.'));
  economyCard.append(details('economy', 'Income and resource details', economyBody, 'activity'));
  shell.append(economyCard);

  const firmCard = el('article', 'card firm-card');
  firmCard.append(partyHeading(firm.name || 'Firm', null));
  firmCard.append(el('p', 'parameters', `${percent(firm.parameters.reinvestment_rate)} reinvest surplus · ${percent(firm.parameters.depreciation_rate)} capital wear`));
  firmCard.append(statement('PRODUCTION · X', [
    ['Produced', fmt(firm.produced_x)],
    ['Sold to households', fmt(firm.sold_x)],
    ['Added to capital', fmt(firm.investment_quantity)],
  ], 'production-statement'));
  const capitalBridge = el('div', 'capital-bridge');
  capitalBridge.append(row('Capital units', `${fmt(firm.capital_open)} → ${fmt(firm.capital_close)}`, 'total'));
  capitalBridge.append(el('p', 'note', `Added ${fmt(firm.investment_quantity)} · Wear ${fmt(firm.depreciation_quantity)}. Closing capital works next period.`));
  firmCard.append(capitalBridge);
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
    ['Reinvest surplus', percent(firm.parameters.reinvestment_rate)],
    ['Capital wear', percent(firm.parameters.depreciation_rate)],
    ['Protected operating float', money(firm.protected_operating_float)],
  ]));
  firmCard.append(details('firm-accounts', 'Cash and balance sheet', firmBody, 'activity'));
  firmCard.append(el('p', 'dividend-note', firm.next_dividend_budget > 0
    ? `Next-period dividend · ${money(firm.next_dividend_budget)}`
    : 'No dividend available for next period.'));
  shell.append(firmCard);

  shell.append(el('h3', 'section-heading', 'Households'));
  const households = el('div', 'cards');
  report.households.forEach((household, index) => {
    const card = el('article', 'card household-card');
    card.append(partyHeading(household.name, index));
    const weights = household.parameters.weights;
    const priorities = el('div', 'priorities');
    priorities.setAttribute('aria-label', 'Chosen preference weights');
    for (const [label, weight] of [['Consume', weights.consumption], ['Money', weights.money], ['Leisure', weights.leisure]]) {
      const item = el('span', 'priority');
      item.append(el('small', '', label), el('strong', '', percent(weight)));
      priorities.append(item);
    }
    card.append(priorities);
    card.append(row('Money', `${fmt(household.opening_money)} → ${fmt(household.closing_money)} M`, 'total'));
    card.append(row('Consumed', `${fmt(household.consumed_x)} X`));
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
      [`Firm ownership · ${percent(household.ownership)}`, money(household.ownership_value_close)],
      ['Assets within this model', money(household.assets_close), 'total'],
    ]));
    body.append(el('p', 'note', 'Ownership is a fixed share of firm equity, not spendable cash or a traded share price.'));
    const scores = household.parameters.scores;
    body.append(el('p', 'note', `Chosen scores · ${fmt(scores.consumption)} consume · ${fmt(scores.money)} money · ${fmt(scores.leisure)} leisure.`));
    if (cumulative) body.append(row('Total work', `${fmt(household.total_work)} work-periods`));
    card.append(details(`household-${index}`, 'Cash and ownership', body, 'activity'));
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
    for (const [label, value] of Object.entries(data.diagnostics)) {
      technical.append(el('p', '', `${label.replaceAll('_', ' ')} · ${typeof value === 'number' ? Number(value.toPrecision(4)).toString() : value}`));
    }
    technical.append(el('p', 'note', 'Small nonzero values use scientific notation. Rounded rows may not add exactly; calculations and CSV values retain full precision.'));
    evidenceBody.append(details('technical', 'Technical details', technical, 'technical-details'));
  }
  const columns = [...new Set((report.rows || []).flatMap(item => Object.keys(item)))];
  const csvRows = [columns, ...(report.rows || []).map(item => columns.map(column => item[column] ?? ''))];
  const csv = csvRows.map(values => values.map(value => `"${String(value).replaceAll('"', '""')}"`).join(',')).join('\n');
  const download = el('a', 'download', 'Download complete accounts (CSV)');
  download.href = `data:text/csv;charset=utf-8,${encodeURIComponent(csv)}`;
  download.download = `economy-09-${report.label.toLowerCase().replaceAll(' ', '-').replace('–', '-')}-accounts.csv`;
  evidenceBody.append(download);
  shell.append(details('evidence', `${checksPassed ? '✓ All checks passed' : '! Check failed'} · Evidence`, evidenceBody, `evidence ${checksPassed ? 'passed' : 'failed'}`));
  shell.append(el('p', 'boundary', 'Money and capital carry forward. Households consume their purchases; new capital produces from the next period. No borrowing or money creation.'));
  root.append(shell);
}
