// All model data is inserted as text, never interpreted as HTML or code.
export default function render({ data, parentElement, setTriggerValue, setStateValue }) {
  const root = parentElement.querySelector('.playground-root');
  const initial = !root.playgroundState;
  const state = root.playgroundState || {
    tradeIndex: 0, balances: 'closing',
    revision: data.revision, selected: data.selected_index,
  };
  if (state.revision !== data.revision || state.selected !== data.selected_index) {
    state.tradeIndex = 0;
    state.revision = data.revision;
    state.selected = data.selected_index;
  }
  if (initial && Number.isInteger(data.selected_trade)) state.tradeIndex = data.selected_trade;
  state.tradeIndex = Math.max(0, Math.min(state.tradeIndex, data.trades.length - 1));
  root.playgroundState = state;
  let animations = [];
  const fmt = (n, places = 2) => Number(n).toLocaleString('en-US', {
    minimumFractionDigits: places, maximumFractionDigits: places,
  });
  const el = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const button = (text, cls, fn, label) => {
    const node = el('button', cls, text);
    node.type = 'button';
    if (label) node.setAttribute('aria-label', label);
    node.onclick = fn;
    return node;
  };
  const stop = () => { animations.forEach(a => a.cancel()); animations = []; };
  const focus = selector => root.querySelector(selector)?.focus();
  const rememberTrade = () => setStateValue?.('selection', {
    id: crypto.randomUUID(), revision: data.revision,
    selected_index: data.selected_index, trade_index: state.tradeIndex,
  });
  const ask = tradeIndex => setTriggerValue('question', {
    id: crypto.randomUUID(), revision: data.revision,
    selected_index: data.selected_index, trade_index: tradeIndex,
  });
  function renderCard(name, stocks, side) {
    const card = el('article', `agent-card ${side}`);
    const top = el('div', 'agent-top');
    top.append(el('span', 'avatar', name.replace('Agent ', '')));
    top.append(el('div', 'agent-name', name));
    card.append(top);
    const assets = el('dl', 'asset-list');
    for (const asset of ['X', 'Y', 'Money']) {
      const row = el('div', 'asset-row');
      const title = el('dt', 'asset-label');
      title.append(el('span', `asset-dot ${asset.toLowerCase()}`, asset === 'Money' ? 'M' : asset));
      if (asset === 'Money') title.append(document.createTextNode(' Money'));
      row.append(title, el('dd', '', fmt(stocks[asset])));
      assets.append(row);
    }
    card.append(assets);
    return card;
  }
  function draw() {
    stop();
    root.replaceChildren();
    const shell = el('section', 'playground');
    shell.setAttribute('aria-label', 'Interactive monetary economy');
    const top = el('div', 'topline');
    top.append(el('span', 'eyebrow', `Money · ${data.agent_count} agents`));
    shell.append(top);
    const head = el('div', 'stage-heading');
    head.append(el('h2', '', !data.trades.length ? 'No trade needed.'
      : data.previous_price === null ? 'Your market result.'
      : Math.abs(data.price - data.previous_price) < 1e-6 ? 'The price held steady.'
      : data.price > data.previous_price ? 'X became more expensive.' : 'X became less expensive.'));
    const sub = (data.trades.length ? 'See what changed, then follow a trade.' : 'See the outcome here. Explore the explanation in Ask why.');
    shell.append(head, el('p', 'intro', sub));
    drawResult(shell);
    root.append(shell);
  }
  function drawResult(shell) {
    const price = el('div', 'price-panel');
    const values = el('div', 'price-values');
    values.append(el('span', 'eyebrow', `${data.label.toUpperCase()} · PRICE OF X · Y FIXED AT 1`));
    const number = el('div', 'price-number', `${fmt(data.price, 4)} `);
    number.append(el('span', '', 'M / X'));
    values.append(number);
    price.append(values);
    if (data.previous_price !== null) {
      const change = (data.price / data.previous_price - 1) * 100;
      const delta = el('div', 'price-delta', `${change >= 0 ? '+' : ''}${fmt(change, 2)}%`);
      delta.append(el('small', '', `from ${fmt(data.previous_price, 4)}`));
      price.append(delta);
    }
    const receipt = el('div', 'experiment-receipt');
    receipt.append(el('span', 'eyebrow', data.label));
    for (const c of (data.changes || [])) {
      receipt.append(el('p', '', `${c.name}: ${fmt(c.before)} → ${fmt(c.after)} Y`));
    }
    if (!(data.changes || []).length) receipt.append(el('p', '', data.setup_summary || 'Baseline opening endowments'));
    shell.append(receipt, price);
    const constants = el('div', 'constants');
    const total = asset => Object.values(data.opening).reduce((sum, stocks) => sum + stocks[asset], 0);
    constants.append(el('p', '', 'Y price · 1.0000 · fixed reference'),
      el('p', '', `Total goods · ${fmt(total('X'))} X + ${fmt(total('Y'))} Y`),
      el('p', '', `Total money · ${fmt(total('Money'))} · ${data.checks.money ? 'conserved' : 'check failed'}`));
    shell.append(constants);
    const checks = el('div', 'checks');
    for (const [key, label] of [['market', 'Market cleared'], ['money', 'Money conserved'], ['accounts', 'Accounts balanced']]) {
      checks.append(el('span', data.checks[key] ? 'check' : 'check failed', `${data.checks[key] ? '✓' : '!'} ${label}`));
    }
    shell.append(checks);
    const trade = data.trades[state.tradeIndex];
    if (trade) {
      const tradeHead = el('div', 'trade-heading');
      tradeHead.append(el('span', 'eyebrow', `TRADE ${state.tradeIndex + 1} OF ${data.trades.length}`));
      const next = button('Next trade →', 'text-button', () => {
        state.tradeIndex = Math.min(state.tradeIndex + 1, data.trades.length - 1);
        rememberTrade(); draw(); focus('.next-trade');
      });
      next.classList.add('next-trade');
      const previous = button('←', 'text-button previous-trade', () => {
        state.tradeIndex = Math.max(0, state.tradeIndex - 1);
        rememberTrade(); draw(); focus('.previous-trade');
      }, 'Previous trade');
      previous.disabled = state.tradeIndex === 0;
      next.disabled = state.tradeIndex === data.trades.length - 1;
      const controls = el('div', 'trade-controls');
      controls.append(previous, next);
      tradeHead.append(controls);
      shell.append(tradeHead);
      const stage = el('div', 'flow-stage');
      const people = el('div', 'flow-people');
      const seller = el('div', 'flow-person', trade.seller);
      seller.append(el('small', '', 'SELLER'));
      const buyer = el('div', 'flow-person', trade.buyer);
      buyer.append(el('small', '', 'BUYER'));
      people.append(seller, buyer);
      stage.append(people);
      for (const [kind, label, symbol] of [
        ['goods', `${fmt(trade.quantity, 4)} ${trade.good} →`, trade.good],
        ['payment', `← ${fmt(trade.payment, 4)} Money`, 'M'],
      ]) {
        const lane = el('div', `flow-lane ${kind}`);
        lane.append(el('div', 'lane-label', label));
        const track = el('div', 'track');
        const token = el('span', `token ${kind}`, symbol);
        token.setAttribute('aria-hidden', 'true');
        track.append(token);
        lane.append(track);
        stage.append(lane);
      }
      const replay = button('▶ Replay trade', 'replay-button', () => play());
      stage.append(replay, el('p', 'micro', 'One batch, shown visually. Animation order is not payment timing.'));
      shell.append(stage);
      const tradeHelp = el('details', 'built-in');
      tradeHelp.append(el('summary', '', 'Explain this trade'),
        el('p', 'intro', `${trade.seller} sells ${fmt(trade.quantity, 4)} ${trade.good} to ${trade.buyer}. In return, ${trade.buyer} pays ${fmt(trade.payment, 4)} Money. Unit price: ${fmt(trade.unit_price, 4)}. Closing balances include all trades, not just this one.`),
        el('p', 'micro', 'From the model · no AI usage'));
      shell.append(tradeHelp, button('Ask about this trade', 'replay-button', () => ask(state.tradeIndex)));
      const details = el('details', 'details');
      details.append(el('summary', '', 'Inspect agent balances'));
      const toggle = el('div', 'balance-toggle');
      toggle.setAttribute('role', 'group');
      toggle.setAttribute('aria-label', 'Balance snapshot');
      for (const snapshot of ['opening', 'closing']) {
        const b = button(snapshot === 'opening' ? 'Opening' : 'Closing', '', () => {
          state.balances = snapshot;
          draw();
          root.querySelector('.details').open = true;
          focus(`[data-snapshot="${snapshot}"]`);
        });
        b.dataset.snapshot = snapshot;
        b.setAttribute('aria-pressed', String(state.balances === snapshot));
        toggle.append(b);
      }
      details.append(toggle, el('p', 'micro', 'These are whole-market balances, not the effect of this one trade.'));
      const pair = el('div', 'agent-pair');
      pair.append(renderCard(trade.seller, data[state.balances][trade.seller], 'from'));
      pair.append(renderCard(trade.buyer, data[state.balances][trade.buyer], 'to'));
      details.append(pair);
      const all = el('details', 'all-agents');
      all.append(el('summary', '', `All ${data.agent_count} agents`));
      const list = el('div', 'all-agent-list');
      for (const [name, stocks] of Object.entries(data[state.balances])) {
        const row = el('div', 'all-agent-row');
        row.append(el('strong', '', name), el('span', '', `X ${fmt(stocks.X)} · Y ${fmt(stocks.Y)} · M ${fmt(stocks.Money)}`));
        list.append(row);
      }
      all.append(list); details.append(all); shell.append(details);
    } else {
      shell.append(el('p', 'intro', '0 trades · starting balances unchanged.'));
    }
    shell.append(el('p', 'boundary', 'Independent experiments. Fresh opening money each time. No borrowing or cash constraint.'));
  }
  function play() {
    stop();
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      const b = root.querySelector('.replay-button');
      b.textContent = '✓ Both trade legs shown';
      return;
    }
    root.querySelectorAll('.token').forEach(token => {
      const travel = token.parentElement.clientWidth - token.offsetWidth;
      const reverse = token.classList.contains('payment');
      const a = token.animate([
        { transform: 'translateX(0px)', opacity: 1 },
        { transform: `translateX(${reverse ? -travel : travel}px)`, opacity: 1 },
      ], { duration: 1500, easing: 'cubic-bezier(.4,0,.2,1)', fill: 'forwards' });
      animations.push(a);
    });
  }
  draw();
  return stop;
}
