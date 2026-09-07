// Model data is inserted as text only. This component never changes the run.
export default function render({ data, parentElement }) {
  const root = parentElement.querySelector('.results-root');
  const fmt = (n, places = 2) => Number(n).toLocaleString('en-US', {
    minimumFractionDigits: places, maximumFractionDigits: places,
  });
  const raw = n => Number(n).toString();
  const el = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const assetLabel = asset => asset === 'Money' ? 'Money' : asset;
  const signed = n => Math.abs(n) < 1e-10 ? fmt(0) : `${n > 0 ? '+' : ''}${fmt(n)}`;
  const priceX = data.prices.X;
  const previousPrice = data.previous_run?.prices.X ?? null;
  const checksPassed = Object.values(data.checks).every(Boolean);

  const movements = Object.fromEntries(data.agents.map(agent => [
    agent.name,
    Object.fromEntries(['X', 'Y', 'Money'].map(asset => [asset, { received: 0, sent: 0 }])),
  ]));
  for (const trade of data.trades) {
    movements[trade.seller][trade.good].sent += trade.quantity;
    movements[trade.buyer][trade.good].received += trade.quantity;
    movements[trade.buyer].Money.sent += trade.payment;
    movements[trade.seller].Money.received += trade.payment;
  }

  root.replaceChildren();
  const shell = el('section', 'results');
  shell.setAttribute('aria-label', 'Monetary economy result');
  shell.append(el('div', 'topline', `Money · ${data.settings.agent_count} agents`));

  const title = !data.trades.length ? 'No trade needed.'
    : previousPrice === null ? 'Your market result.'
    : Math.abs(priceX - previousPrice) < 1e-6 ? 'The price held steady.'
    : priceX > previousPrice ? 'X became more expensive.' : 'X became less expensive.';
  shell.append(el('h2', '', title));
  shell.append(el('p', 'intro', 'See the price, then compare what every agent started and finished with.'));

  const receipt = el('div', 'run-receipt');
  receipt.append(el('span', 'eyebrow', data.label), el('p', '', `${data.label} · submitted setup`));
  shell.append(receipt);

  const price = el('div', 'price-panel');
  const priceValues = el('div', 'price-values');
  priceValues.append(el('span', 'eyebrow', 'PRICE OF X · Y FIXED AT 1'));
  const number = el('div', 'price-number', `${fmt(priceX, 4)} `);
  number.append(el('span', '', 'M / X'));
  priceValues.append(number);
  price.append(priceValues);
  if (previousPrice !== null) {
    const change = data.price_x_change_percent;
    const delta = el('div', 'price-delta', `${change >= 0 ? '+' : ''}${fmt(change, 2)}%`);
    delta.append(el('small', '', `from ${fmt(previousPrice, 4)}`));
    price.append(delta);
  }
  shell.append(price);

  const totals = el('div', 'totals');
  totals.append(
    el('p', '', `Y price · ${fmt(data.prices.Y, 4)} · fixed reference`),
    el('p', '', `Total goods · ${fmt(data.totals.opening.X)} X + ${fmt(data.totals.opening.Y)} Y`),
    el('p', '', `Total money · ${fmt(data.totals.opening.Money)} · ${data.checks.money ? 'conserved' : 'check failed'}`),
  );
  shell.append(totals);

  shell.append(el('h3', '', 'Agent outcomes'));
  shell.append(el('p', 'section-intro', 'Starting and final balances for the whole submitted run.'));
  const outcomes = el('div', 'outcomes');
  for (const agent of data.agents) {
    const card = el('article', 'outcome-card');
    card.append(el('h4', '', agent.name));
    for (const asset of ['X', 'Y', 'Money']) {
      const start = agent.opening[asset];
      const finish = agent.closing[asset];
      const row = el('div', 'outcome-row');
      const label = el('span', 'asset-label');
      label.append(el('span', `asset-dot ${asset.toLowerCase()}`, asset === 'Money' ? 'M' : asset));
      label.append(document.createTextNode(assetLabel(asset)));
      row.append(label, el('span', 'start-finish', `${fmt(start)} → ${fmt(finish)}`));
      const change = finish - start;
      row.append(el('span', `change ${Math.abs(change) < 1e-10 ? 'flat' : change > 0 ? 'up' : 'down'}`, signed(change)));
      card.append(row);
    }
    outcomes.append(card);
  }
  shell.append(outcomes);
  if (!data.trades.length) shell.append(el('p', 'no-trade', '0 trades · starting balances unchanged.'));

  if (!checksPassed) shell.append(el('div', 'failure', 'An account check needs attention. Open the account statement below.'));
  const accounts = el('details', `accounts ${checksPassed ? 'passed' : 'failed'}`);
  const summary = el('summary', '', `${checksPassed ? '✓ All checks passed' : '! Check failed'} · Check the accounts`);
  accounts.append(summary);
  const accountBody = el('div', 'account-body');

  accountBody.append(el('h4', '', 'Conservation'));
  const conservation = el('div', 'conservation');
  for (const asset of ['X', 'Y', 'Money']) {
    const row = el('div', 'conservation-row');
    row.append(el('span', '', assetLabel(asset)), el('strong', '', `${fmt(data.totals.opening[asset])} → ${fmt(data.totals.closing[asset])}`), el('span', data.checks[asset === 'Money' ? 'money' : 'accounts'] ? 'pass' : 'fail', data.checks[asset === 'Money' ? 'money' : 'accounts'] ? 'Conserved' : 'Check failed'));
    conservation.append(row);
  }
  accountBody.append(conservation);

  accountBody.append(el('h4', '', 'Agent account'));
  const select = el('select', 'agent-select');
  select.setAttribute('aria-label', 'Choose an agent account');
  const allOption = el('option', '', 'All agents');
  allOption.value = '';
  select.append(allOption);
  for (const agent of data.agents) {
    const option = el('option', '', agent.name);
    option.value = agent.name;
    select.append(option);
  }
  accountBody.append(select);
  const accountCard = el('div', 'account-card');
  accountBody.append(accountCard);
  const accountTable = agent => {
    const table = el('div', 'account-table');
    table.append(el('h5', '', agent.name));
    const header = el('div', 'account-row account-header');
    for (const label of ['Asset', 'Start', 'Received', 'Sent', 'Final']) header.append(el('span', '', label));
    table.append(header);
    for (const asset of ['X', 'Y', 'Money']) {
      const flow = movements[agent.name][asset];
      const row = el('div', 'account-row');
      for (const value of [assetLabel(asset), fmt(agent.opening[asset]), fmt(flow.received), fmt(flow.sent), fmt(agent.closing[asset])]) row.append(el('span', '', value));
      table.append(row);
    }
    return table;
  };
  const drawAccount = name => {
    accountCard.replaceChildren();
    const agents = name ? data.agents.filter(item => item.name === name) : data.agents;
    for (const agent of agents) accountCard.append(accountTable(agent));
  };
  select.onchange = () => drawAccount(select.value);
  drawAccount('');

  accountBody.append(el('h4', '', 'Trade receipts'));
  if (!data.trades.length) {
    accountBody.append(el('p', 'muted', 'No transactions were needed.'));
  } else {
    const receipts = el('div', 'receipts');
    for (const trade of data.trades) {
      const item = el('details', 'trade-receipt');
      item.append(el('summary', '', `${trade.seller} → ${trade.buyer} · ${fmt(trade.quantity, 4)} ${trade.good} for ${fmt(trade.payment, 4)} Money`));
      const legs = el('div', 'ledger-legs');
      legs.append(el('p', '', `${trade.good}: ${trade.seller} → ${trade.buyer} · ${raw(trade.quantity)}`));
      legs.append(el('p', '', `Money: ${trade.buyer} → ${trade.seller} · ${raw(trade.payment)}`));
      item.append(legs); receipts.append(item);
    }
    accountBody.append(receipts);
  }

  const technical = el('details', 'technical');
  technical.append(el('summary', '', 'Technical details'));
  const technicalBody = el('div', 'technical-body');
  technicalBody.append(
    el('p', '', `Market error · ${raw(data.market_error)}`),
    el('p', '', `Clearing tolerance · ${raw(data.clearing_tolerance)}`),
    el('p', '', `Gross money payments · ${raw(data.gross_money_payments)}`),
    el('p', '', `Ledger · ${data.trades.length} trades · ${data.trades.length * 2} transfer legs`),
  );
  technical.append(technicalBody); accountBody.append(technical);

  const csvRows = [['agent', 'asset', 'start', 'received', 'sent', 'final']];
  for (const agent of data.agents) for (const asset of ['X', 'Y', 'Money']) {
    const flow = movements[agent.name][asset];
    csvRows.push([agent.name, asset, raw(agent.opening[asset]), raw(flow.received), raw(flow.sent), raw(agent.closing[asset])]);
  }
  const csv = csvRows.map(row => row.map(value => `"${String(value).replaceAll('"', '""')}"`).join(',')).join('\n');
  const download = el('a', 'download', 'Download full-precision accounts (CSV)');
  download.href = `data:text/csv;charset=utf-8,${encodeURIComponent(csv)}`;
  download.download = `${data.label.toLowerCase().replace(' ', '-')}-accounts.csv`;
  accountBody.append(download);
  accounts.append(accountBody); shell.append(accounts);
  shell.append(el('p', 'boundary', 'Independent experiments. Fresh opening money each time. No borrowing or cash constraint.'));
  root.append(shell);
}
