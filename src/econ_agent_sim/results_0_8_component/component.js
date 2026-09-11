// Model data is inserted as text only. This component never changes the run.
export default function render({ data, parentElement }) {
  const root = parentElement.querySelector('.results-root');
  const report = data.reporting;
  const fmt = (n, places = 2) => Number(n).toLocaleString('en-US', {
    minimumFractionDigits: places, maximumFractionDigits: places,
  });
  const raw = n => Number(n).toString();
  const nearZero = (n, places = 2) => Math.abs(Number(n)) < 0.5 * 10 ** -places;
  const signed = n => nearZero(n) ? fmt(0) : `${n > 0 ? '+' : ''}${fmt(n)}`;
  const diagnostic = n => Number(Number(n).toPrecision(3)).toString();
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
  const details = (label, body, cls = '') => {
    const section = el('details', cls);
    section.append(el('summary', '', label), body);
    return section;
  };
  const marker = (name, index) => {
    const heading = el('h4', 'party-heading');
    heading.append(el('span', `party-marker tone-${index % 6}`, String(index + 1)),
      document.createTextNode(name));
    return heading;
  };

  root.replaceChildren();
  const shell = el('section', 'results');
  shell.setAttribute('aria-label', 'Firm and wage economy result');
  shell.append(el('div', 'topline', `FIRM · WAGES · CONSUMPTION · ${report.households.length} HOUSEHOLDS`));
  shell.append(el('h2', '', report.scope === 'cumulative' ? 'The economy so far.' : 'Work became wages.'));
  shell.append(el('p', 'intro', report.scope === 'cumulative'
    ? `${report.label} · activity is added; balances run from the first opening to the selected closing.`
    : 'See what households earned and consumed—and how the firm earned current profit and distributed prior profit.'));

  const metrics = el('div', 'headline-metrics');
  for (const [label, value, unit] of [
    ['X PRICE', report.price, 'M / X'],
    ['WAGE', report.wage, 'M / WORK'],
    [report.scope === 'cumulative' ? 'TOTAL OUTPUT' : 'OUTPUT', report.economy.produced_x, 'X'],
  ]) {
    const metric = el('div', 'metric');
    metric.append(el('span', 'eyebrow', label), el('strong', '', fmt(value, 4)), el('small', '', unit));
    metrics.append(metric);
  }
  shell.append(metrics);

  shell.append(el('h3', '', 'Whole economy'));
  const economy = report.economy;
  const economyCard = el('article', 'card economy-card');
  economyCard.append(statement('REAL ACTIVITY', [
    ['Produced X', fmt(economy.produced_x)],
    ['Consumed X', fmt(economy.consumed_x)],
  ]));
  economyCard.append(statement('INCOME', [
    ['Output value', `${fmt(economy.output_value)} M`],
    ['Wages', `${fmt(economy.wages)} M`],
    [report.scope === 'cumulative' ? 'Cumulative profit' : 'Current profit', `${fmt(economy.profit)} M`],
  ], 'income-statement'));
  economyCard.append(row('Total money', `${fmt(economy.opening_money)} → ${fmt(economy.closing_money)} M`,
    nearZero(economy.closing_money - economy.opening_money) ? 'flat' : 'down'));
  shell.append(economyCard);

  shell.append(el('h3', '', 'Households'));
  shell.append(el('p', 'section-intro', 'Balances, earnings and choices. Open activity for the full statement.'));
  const households = el('div', 'cards');
  report.households.forEach((household, index) => {
    const card = el('article', 'card household-card');
    card.append(marker(household.name, index));
    const weights = household.parameters.weights;
    card.append(el('p', 'preference-line', `Priorities · ${fmt(100 * weights.consumption, 0)}% consume · ${fmt(100 * weights.money, 0)}% money · ${fmt(100 * weights.leisure, 0)}% leisure`));
    const quick = el('div', 'quick-stats');
    quick.append(row('Money', `${fmt(household.opening_money)} → ${fmt(household.closing_money)} M`,
      nearZero(household.net_cash_change) ? 'flat' : household.net_cash_change > 0 ? 'up' : 'down'));
    quick.append(row('Consumed', `${fmt(household.consumed_x)} X`));
    quick.append(row('Work · leisure', `${fmt(100 * household.average_work, 1)}% · ${fmt(100 * household.average_leisure, 1)}%`));
    card.append(quick);
    const body = el('div', 'statement-body');
    body.append(statement(report.scope === 'cumulative' ? 'CUMULATIVE ACTIVITY' : 'THIS PERIOD', [
      ['Opening money', `${fmt(household.opening_money)} M`],
      ['Dividends received', `+${fmt(household.dividends_received)} M`, household.dividends_received ? 'up' : 'flat'],
      ['Wages received', `+${fmt(household.wages_received)} M`, household.wages_received ? 'up' : 'flat'],
      ['Purchases', `−${fmt(household.purchases_paid)} M`, household.purchases_paid ? 'down' : 'flat'],
      ['Closing money', `${fmt(household.closing_money)} M`, 'total'],
      ['Net cash change', `${signed(household.net_cash_change)} M`, nearZero(household.net_cash_change) ? 'flat' : household.net_cash_change > 0 ? 'up' : 'down'],
      ...(report.scope === 'cumulative' ? [['Total work', `${fmt(household.total_work)} work-periods`]] : []),
    ]));
    card.append(details(`Activity · ${report.period_count === 1 ? 'this period' : `${report.period_count} periods`}`, body, 'activity'));
    households.append(card);
  });
  shell.append(households);

  shell.append(el('h3', '', 'Firm'));
  const firm = report.firm;
  const firmCard = el('article', 'card firm-card');
  const firmTitle = el('h4', 'party-heading');
  firmTitle.append(el('span', 'firm-marker', 'F'), document.createTextNode(firm.name || 'Firm'));
  firmCard.append(firmTitle, el('p', 'preference-line', `Productivity · ${fmt(firm.parameters.productivity, 2)} X with one full unit of total labor`));
  firmCard.append(el('p', 'production-line', `Produced ${fmt(firm.produced_x)} X · Sold ${fmt(firm.sold_x)} X`));
  firmCard.append(statement('INCOME STATEMENT', [
    ['Sales', `${fmt(firm.sales_received)} M`],
    ['Wages', `−${fmt(firm.wages_paid)} M`, firm.wages_paid ? 'down' : 'flat'],
    [report.scope === 'cumulative' ? 'Cumulative profit' : 'Current profit', `${fmt(firm.profit)} M`, 'total'],
  ], 'income-statement'));
  const cashBody = el('div', 'statement-body');
  cashBody.append(statement(report.scope === 'cumulative' ? 'CUMULATIVE CASH ACCOUNT' : 'CASH ACCOUNT', [
    ['Opening money', `${fmt(firm.opening_money)} M`],
    ['Prior profit distributed', `−${fmt(firm.dividends_paid)} M`, firm.dividends_paid ? 'down' : 'flat'],
    ['Wages paid', `−${fmt(firm.wages_paid)} M`, firm.wages_paid ? 'down' : 'flat'],
    ['Sales received', `+${fmt(firm.sales_received)} M`, firm.sales_received ? 'up' : 'flat'],
    ['Closing money', `${fmt(firm.closing_money)} M`, 'total'],
  ]));
  firmCard.append(details(`Cash account · ${report.period_count === 1 ? 'this period' : `${report.period_count} periods`}`, cashBody, 'activity'));
  firmCard.append(el('p', 'profit-note', `${fmt(firm.profit_awaiting_distribution)} M profit awaits next-period distribution.`));
  shell.append(firmCard);

  const checkValues = Object.values(report.checks || {});
  const checksPassed = checkValues.length > 0 && checkValues.every(Boolean);
  if (!checksPassed) shell.append(el('div', 'failure', 'A check needs attention. Open the evidence below.'));
  const evidenceBody = el('div', 'evidence-body');
  const checks = el('div', 'checks');
  for (const [label, passed] of Object.entries(report.checks || {})) {
    checks.append(row(label.replaceAll('_', ' '), passed ? 'Verified' : 'Check failed', passed ? 'pass' : 'fail'));
  }
  evidenceBody.append(checks);
  if (report.transfers?.length) {
    const ledger = el('div', 'ledger');
    for (const transfer of report.transfers) {
      ledger.append(el('p', '', `P${transfer.period} · ${transfer.sender} → ${transfer.receiver} · ${fmt(transfer.quantity, 4)} ${transfer.asset} · ${transfer.kind.replaceAll('_', ' ')}`));
    }
    evidenceBody.append(details(`Settlement ledger · ${report.transfers.length} ${report.transfers.length === 1 ? 'transfer' : 'transfers'}`, ledger, 'ledger-details'));
  }
  if (data.diagnostics) {
    const technical = el('div', 'technical');
    for (const [label, value] of Object.entries(data.diagnostics)) technical.append(
      el('p', '', `${label.replaceAll('_', ' ')} · ${typeof value === 'number' ? diagnostic(value) : value}`));
    evidenceBody.append(details('Technical details', technical, 'technical-details'));
  }

  const columns = report.rows?.length ? Object.keys(report.rows[0]) : ['period', 'account_type', 'entity'];
  const csvRows = [columns, ...(report.rows || []).map(item => columns.map(column => item[column] ?? ''))];
  const csv = csvRows.map(values => values.map(value => `"${String(value).replaceAll('"', '""')}"`).join(',')).join('\n');
  const download = el('a', 'download', 'Download full-precision accounts (CSV)');
  download.href = `data:text/csv;charset=utf-8,${encodeURIComponent(csv)}`;
  download.download = `${report.label.toLowerCase().replaceAll(' ', '-').replace('–', '-')}-accounts.csv`;
  evidenceBody.append(download);
  shell.append(details(`${checksPassed ? '✓ All checks passed' : '! Check failed'} · Inspect the evidence`, evidenceBody, `evidence ${checksPassed ? 'passed' : 'failed'}`));
  shell.append(el('p', 'boundary', data.run_rule));
  root.append(shell);
}
