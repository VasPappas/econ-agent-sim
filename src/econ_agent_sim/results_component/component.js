// Model data is inserted as text only. This component never changes the run.
export default function render({ data, parentElement }) {
  const root = parentElement.querySelector('.results-root');
  const assets = data.assets || ['X', 'Y', 'Money'];
  const evolving = data.model === 'production_consumption';
  const valuedMoney = data.model === 'money_in_utility' || evolving;
  const fmt = (n, places = 2) => Number(n).toLocaleString('en-US', {
    minimumFractionDigits: places, maximumFractionDigits: places,
  });
  const raw = n => Number(n).toString();
  const diagnostic = n => Number(Number(n).toPrecision(3)).toString();
  const el = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const assetLabel = asset => asset === 'Money' ? 'Money' : asset;
  const agentHeading = (tag, agent) => {
    const index = data.agents.indexOf(agent);
    const heading = el(tag, 'agent-heading');
    heading.append(el('span', `agent-marker tone-${index % 6}`, String(index + 1)), document.createTextNode(agent.name));
    return heading;
  };
  const signed = n => Math.abs(n) < 1e-10 ? fmt(0) : `${n > 0 ? '+' : ''}${fmt(n)}`;
  const priceX = data.prices.X;
  const previousPrice = data.previous_run?.prices.X ?? null;
  const checksPassed = [...Object.values(data.checks), ...Object.values(data.period_checks || {})].every(Boolean);

  const movements = Object.fromEntries(data.agents.map(agent => [
    agent.name,
    Object.fromEntries(assets.map(asset => [asset, { received: 0, sent: 0 }])),
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
  shell.append(el('div', 'topline', `${evolving ? 'Produce · trade · consume' : valuedMoney ? 'One good + money' : 'Money'} · ${data.settings.agent_count} agents`));

  const title = !data.trades.length ? 'No trade needed.'
    : previousPrice === null ? 'Your market result.'
    : Math.abs(priceX - previousPrice) < 1e-6 ? 'The price held steady.'
    : priceX > previousPrice ? 'X became more expensive.' : 'X became less expensive.';
  shell.append(el('h2', '', title));
  shell.append(el('p', 'intro', evolving ? 'See what agents produced, consumed, and carried into the next period.' : 'See the price, then compare what every agent started and finished with.'));

  const receipt = el('div', 'run-receipt');
  receipt.append(el('span', 'eyebrow', data.label), el('p', '', evolving ? 'Production → trade → consumption → carry money forward' : `${data.label} · submitted setup`));
  shell.append(receipt);

  const price = el('div', 'price-panel');
  const priceValues = el('div', 'price-values');
  priceValues.append(el('span', 'eyebrow', valuedMoney ? 'PRICE OF X · IN MONEY' : 'PRICE OF X · Y FIXED AT 1'));
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
  if (!valuedMoney) totals.append(el('p', '', `Y price · ${fmt(data.prices.Y, 4)} · fixed reference`));
  totals.append(
    el('p', '', evolving ? `Produced · ${fmt(data.period_totals.produced.X)} X · Consumed · ${fmt(data.period_totals.consumed.X)} X` : valuedMoney ? `Total goods · ${fmt(data.totals.opening.X)} X` : `Total goods · ${fmt(data.totals.opening.X)} X + ${fmt(data.totals.opening.Y)} Y`),
    el('p', '', `Total money · ${fmt(data.totals.opening.Money)} · ${data.checks.money ? 'conserved' : 'check failed'}`),
  );
  shell.append(totals);

  shell.append(el('h3', '', 'Agent outcomes'));
  shell.append(el('p', 'section-intro', evolving ? 'Goods consumed this period; money before and after trading.' : 'Starting and final balances for the whole submitted run.'));
  const outcomes = el('div', 'outcomes');
  for (const agent of data.agents) {
    const card = el('article', 'outcome-card');
    card.append(agentHeading('h4', agent));
    for (const asset of assets) {
      if (evolving && asset === 'X') {
        const flow = el('div', 'period-flow');
        flow.append(el('p', '', `Produced ${fmt(data.produced[agent.name])} X`),
          el('strong', '', `Consumed ${fmt(data.consumed[agent.name])} X`),
          el('p', 'muted', `Stock: ${fmt(data.period_opening[agent.name].X)} at opening → ${fmt(data.period_closing[agent.name].X)} after consumption`));
        card.append(flow);
        continue;
      }
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
    const agentTrades = data.trades.filter(trade => trade.seller === agent.name || trade.buyer === agent.name);
    if (agentTrades.length) {
      const transactions = el('details', 'agent-transactions');
      transactions.append(el('summary', '', `Show transactions · ${agentTrades.length}`));
      for (const trade of agentTrades) {
        const selling = trade.seller === agent.name;
        const receipt = el('div', 'agent-transaction');
        receipt.append(el('p', '', `${selling ? 'Sold' : 'Bought'} ${fmt(trade.quantity, 4)} ${trade.good} ${selling ? 'to' : 'from'} ${selling ? trade.buyer : trade.seller}`));
        receipt.append(el('p', 'muted', `${selling ? 'Received' : 'Paid'} ${fmt(trade.payment, 4)} Money`));
        transactions.append(receipt);
      }
      card.append(transactions);
    } else {
      card.append(el('p', 'muted', 'No transactions for this agent.'));
    }
    outcomes.append(card);
  }
  shell.append(outcomes);
  if (!data.trades.length) shell.append(el('p', 'no-trade', evolving ? '0 trades · see production and consumption above.' : '0 trades · starting balances unchanged.'));

  if (!checksPassed) shell.append(el('div', 'failure', 'A check needs attention. Open “Verify this run” below.'));
  const accounts = el('details', `accounts ${checksPassed ? 'passed' : 'failed'}`);
  const summary = el('summary', '', `${checksPassed ? '✓ All checks passed' : '! Check failed'} · Verify this run`);
  accounts.append(summary);
  const accountBody = el('div', 'account-body');

  accountBody.append(el('h4', '', evolving ? 'Goods accounted for · money conserved' : 'Conservation'));
  const conservation = el('div', 'conservation');
  for (const asset of assets) {
    const row = el('div', 'conservation-row');
    if (evolving && asset === 'X') {
      const t = data.period_totals;
      row.className = 'period-accounting';
      row.append(el('p', '', `X: ${fmt(t.opening.X)} opening + ${fmt(t.produced.X)} produced − ${fmt(t.consumed.X)} consumed = ${fmt(t.closing.X)} remaining`),
        el('span', data.period_checks.goods ? 'pass' : 'fail', data.period_checks.goods ? 'Accounted for' : 'Check failed'));
      conservation.append(row);
      continue;
    }
    const conserved = data.conservation?.[asset] ?? data.checks[asset === 'Money' ? 'money' : 'accounts'];
    row.append(el('span', '', assetLabel(asset)), el('strong', '', `${fmt(data.totals.opening[asset])} → ${fmt(data.totals.closing[asset])}`), el('span', conserved ? 'pass' : 'fail', conserved ? 'Conserved' : 'Check failed'));
    conservation.append(row);
  }
  accountBody.append(conservation);

  const technical = el('details', 'technical');
  technical.append(el('summary', '', 'Technical details'));
  const technicalBody = el('div', 'technical-body');
  technicalBody.append(
    el('p', '', `Market error · ${diagnostic(data.market_error)}`),
    el('p', '', `Clearing tolerance · ${diagnostic(data.clearing_tolerance)}`),
    el('p', '', `Gross money payments · ${fmt(data.gross_money_payments, 4)}`),
    el('p', '', `Ledger · ${data.trades.length} ${data.trades.length === 1 ? 'trade' : 'trades'} · ${data.trades.length * 2} transfer legs`),
    el('p', 'muted', 'Balances use 2 decimal places; prices and receipts use 4. Calculations and the CSV retain full precision. Rounded amounts may not add up exactly.'),
  );
  technical.append(technicalBody); accountBody.append(technical);

  const csvRows = [evolving ? ['period', 'agent', 'asset', 'opening', 'produced', 'received', 'sent', 'consumed', 'closing'] : ['agent', 'asset', 'start', 'received', 'sent', 'final']];
  for (const agent of data.agents) for (const asset of assets) {
    const flow = movements[agent.name][asset];
    csvRows.push(evolving ? [data.label, agent.name, asset, raw(data.period_opening[agent.name][asset]),
      raw(asset === 'X' ? data.produced[agent.name] : 0), raw(flow.received), raw(flow.sent),
      raw(asset === 'X' ? data.consumed[agent.name] : 0), raw(data.period_closing[agent.name][asset])]
      : [agent.name, asset, raw(agent.opening[asset]), raw(flow.received), raw(flow.sent), raw(agent.closing[asset])]);
  }
  const csv = csvRows.map(row => row.map(value => `"${String(value).replaceAll('"', '""')}"`).join(',')).join('\n');
  const download = el('a', 'download', 'Download full-precision accounts (CSV)');
  download.href = `data:text/csv;charset=utf-8,${encodeURIComponent(csv)}`;
  download.download = `${data.label.toLowerCase().replace(' ', '-')}-accounts.csv`;
  accountBody.append(download);
  accounts.append(accountBody); shell.append(accounts);
  shell.append(el('p', 'boundary', valuedMoney ? data.run_rule : 'Independent experiments. Fresh opening money each time. No borrowing or cash constraint.'));
  root.append(shell);
}
