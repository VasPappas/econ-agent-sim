// All model data is inserted as text, never interpreted as HTML or code.
export default function render({ data, parentElement, setTriggerValue, setStateValue }) {
  const root = parentElement.querySelector('.playground-root');
  const initial = !root.playgroundState;
  const state = root.playgroundState || {
    mode: 'edit', sender: data.agents[0].name, receiver: data.agents[1].name,
    amount: '0.10', tradeIndex: 0, balances: 'closing', pending: false,
    revision: data.revision, selected: data.selected_index,
  };
  let autoReplay = false;
  if (state.revision !== data.revision || state.selected !== data.selected_index) {
    state.pending = false;
    state.mode = data.last_transfer || state.selected !== data.selected_index ? 'result' : 'edit';
    state.tradeIndex = 0;
    if (data.last_transfer) {
      state.sender = data.last_transfer.sender;
      state.receiver = data.last_transfer.receiver;
      const related = data.trades.findIndex(t =>
        [t.seller, t.buyer].includes(state.sender) &&
        [t.seller, t.buyer].includes(state.receiver));
      state.tradeIndex = Math.max(0, related);
      autoReplay = true;
    }
    state.revision = data.revision;
    state.selected = data.selected_index;
  }
  if (initial && data.selected_index > 0) {
    state.mode = 'result';
    autoReplay = Boolean(data.last_transfer);
  }
  if (data.view) state.mode = data.view === 'Experiment' ? 'edit' : 'result';
  if (data.reset_revision != null && state.resetRevision !== data.reset_revision) {
    state.sender = data.agents[0].name;
    state.receiver = data.agents[1].name;
    state.amount = '0.10';
    state.tradeIndex = 0;
    state.resetRevision = data.reset_revision;
  }
  if (initial && Number.isInteger(data.selected_trade)) state.tradeIndex = data.selected_trade;
  state.tradeIndex = Math.max(0, Math.min(state.tradeIndex, data.trades.length - 1));
  if (data.error) state.pending = false;
  const names = data.agents.map(a => a.name);
  if (!names.includes(state.sender)) state.sender = names[0];
  if (!names.includes(state.receiver)) state.receiver = names[1];
  root.playgroundState = state;
  let animations = [];
  let frame;
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
  const navigate = view => {
    if (!data.view) { state.mode = view === 'Experiment' ? 'edit' : 'result'; draw(); return; }
    setTriggerValue('navigation', {
      id: crypto.randomUUID(), revision: data.revision,
      selected_index: data.selected_index, view,
    });
  };
  const rememberTrade = () => setStateValue?.('selection', {
    id: crypto.randomUUID(), revision: data.revision,
    selected_index: data.selected_index, trade_index: state.tradeIndex,
  });
  const ask = tradeIndex => setTriggerValue('question', {
    id: crypto.randomUUID(), revision: data.revision,
    selected_index: data.selected_index, trade_index: tradeIndex,
  });
  function renderCard(name, stocks, side, picker) {
    const card = el('article', `agent-card ${side}`);
    const top = el('div', 'agent-top');
    top.append(el('span', 'avatar', name.replace('Agent ', '')));
    if (picker) {
      const label = el('label', 'agent-label', side === 'from' ? 'FROM' : 'TO');
      const select = el('select', 'agent-select');
      select.setAttribute('aria-label', side === 'from' ? 'Move Y from' : 'Move Y to');
      for (const item of data.agents) {
        const option = el('option', '', item.name);
        option.value = item.name;
        option.selected = item.name === name;
        select.append(option);
      }
      select.onchange = () => {
        state[side === 'from' ? 'sender' : 'receiver'] = select.value;
        draw();
        focus(side === 'from' ? '.from select' : '.to select');
      };
      label.append(select);
      top.append(label);
    } else {
      top.append(el('div', 'agent-name', name));
    }
    card.append(top);
    if (picker) {
      const agent = data.agents.find(a => a.name === name);
      card.append(el('p', 'preference', agent.alpha > .5 ? 'Prefers X'
        : agent.alpha < .5 ? 'Prefers Y' : 'Equal spending shares'));
      card.append(el('p', 'micro', `${fmt(agent.alpha * 100, 0)}% of goods wealth to X`));
    }
    const assets = el('dl', 'asset-list');
    for (const asset of (picker ? ['X', 'Y'] : ['X', 'Y', 'Money'])) {
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
    head.append(el('h2', '', state.mode === 'edit' ? 'A little less here. A little more there.'
      : data.previous_price === null ? 'Your market, in balance.'
      : Math.abs(data.price - data.previous_price) < 1e-6 ? 'The price held steady.'
      : data.price > data.previous_price ? 'X became more expensive.' : 'X became less expensive.'));
    const sub = state.mode === 'edit'
      ? 'Change who starts with Y. See how the whole market responds.'
      : 'See what changed, then follow a trade.';
    shell.append(head, el('p', 'intro', sub));
    if (data.error) {
      const error = el('p', 'error', data.error);
      error.setAttribute('role', 'alert');
      shell.append(error);
    }
    if (state.mode === 'edit') drawEditor(shell);
    else drawResult(shell);
    root.append(shell);
  }
  function drawEditor(shell) {
    const from = data.agents.find(a => a.name === state.sender);
    const to = data.agents.find(a => a.name === state.receiver);
    const pair = el('div', 'agent-pair');
    pair.append(
      renderCard(from.name, { X: from.x, Y: from.y, Money: data.opening_money }, 'from', true),
      renderCard(to.name, { X: to.x, Y: to.y, Money: data.opening_money }, 'to', true),
    );
    shell.append(pair, el('p', 'micro', 'Latest opening endowments. Transfers build on these; closing balances never carry forward.'));
    const form = el('form', 'transfer-form');
    const label = el('label', 'amount-label', 'Y to redistribute');
    const inputId = `amount-${data.revision}`;
    label.htmlFor = inputId;
    const stepper = el('div', 'stepper');
    const input = el('input', 'amount-input');
    input.id = inputId;
    input.type = 'number';
    input.min = '0.01';
    input.max = String(from.y);
    input.step = 'any';
    input.inputMode = 'decimal';
    input.required = true;
    input.value = state.amount;
    const changeAmount = delta => {
      const current = Number(state.amount) || 0;
      state.amount = Math.max(0.01, Math.min(from.y, current + delta)).toFixed(2);
      input.value = state.amount;
      validate();
    };
    const minus = button('−', 'step-button', () => changeAmount(-0.1), 'Decrease Y by 0.10');
    const plus = button('+', 'step-button', () => changeAmount(0.1), 'Increase Y by 0.10');
    stepper.append(minus, input, plus);
    const hint = el('p', 'validation');
    hint.setAttribute('aria-live', 'polite');
    const submit = el('button', 'primary', 'See what changes →');
    submit.type = 'submit';
    const validate = () => {
      const amount = Number(input.value);
      const valid = input.value !== '' && Number.isFinite(amount) && amount >= 0.01 && amount <= from.y;
      hint.textContent = state.sender === state.receiver ? 'Choose two different agents.'
        : from.y < 0.01 ? `${from.name} has no transferable Y left. Choose another sender.`
        : !valid ? `${from.name} has ${fmt(from.y)} Y available. Move between 0.01 and ${fmt(from.y)}.`
        : `${fmt(amount)} Y: ${from.name} → ${to.name}`;
      submit.disabled = !valid || state.sender === state.receiver || state.pending;
      minus.disabled = amount <= 0.01 || state.pending;
      plus.disabled = amount >= from.y || state.pending;
      input.disabled = state.pending;
      if (state.pending) submit.textContent = 'Clearing the market…';
    };
    input.oninput = () => { state.amount = input.value; validate(); };
    form.onsubmit = event => {
      event.preventDefault();
      validate();
      if (submit.disabled) return;
      state.pending = true;
      validate();
      root.querySelectorAll('select').forEach(s => { s.disabled = true; });
      setTriggerValue('action', {
        kind: 'redistribute', id: crypto.randomUUID(), revision: data.revision,
        sender: state.sender, receiver: state.receiver, amount: Number(state.amount),
      });
    };
    form.append(label, stepper, hint, submit);
    shell.append(form);
    if (data.selected_index !== data.latest_index) {
      shell.append(el('p', 'micro', 'This transfer starts from the latest experiment, not the older result selected above.'));
    }
    const footer = el('div', 'editor-footer');
    footer.append(el('span', '', `X price ${fmt(data.price, 4)} M · Y fixed at 1`));
    footer.append(button('See trades ↗', 'text-button', () => {
      navigate('Results');
    }));
    shell.append(footer, el('p', 'boundary', `All ${data.agent_count} agents participate. Money settles trades; it does not limit purchases here.`));

    validate();
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
    if (!(data.changes || []).length) receipt.append(el('p', '', 'Baseline opening endowments'));
    shell.append(receipt, price);
    const constants = el('div', 'constants');
    const total = asset => Object.values(data.opening).reduce((sum, stocks) => sum + stocks[asset], 0);
    constants.append(el('p', '', 'Y price · 1.0000 · fixed reference'),
      el('p', '', `Total goods · ${fmt(total('X'))} X + ${fmt(total('Y'))} Y`),
      el('p', '', `Total money · ${fmt(total('Money'))} · ${data.checks.money ? 'conserved' : 'check failed'}`));
    shell.append(constants);
    const explanation = el('details', 'built-in');
    explanation.append(el('summary', '', 'Why did the price move?'),
      el('p', 'intro', data.explanations?.['Why did X change but not Y?'] || ''),
      el('p', 'micro', 'From the model · no AI usage'),
      button('Ask a follow-up →', 'replay-button', () => ask(null)));
    shell.append(explanation);
    if (data.last_transfer) {
      const t = data.last_transfer;
      shell.append(el('p', 'transfer-receipt', `You moved ${fmt(t.amount)} Y: ${t.sender} → ${t.receiver}.`));
    }
    const checks = el('div', 'checks');
    for (const [key, label] of [['market', 'Market cleared'], ['money', 'Money conserved'], ['accounts', 'Accounts balanced']]) {
      checks.append(el('span', data.checks[key] ? 'check' : 'check failed', `${data.checks[key] ? '✓' : '!'} ${label}`));
    }
    shell.append(checks);
    const trade = data.trades[state.tradeIndex % data.trades.length];
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
      pair.append(renderCard(trade.seller, data[state.balances][trade.seller], 'from', false));
      pair.append(renderCard(trade.buyer, data[state.balances][trade.buyer], 'to', false));
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
      shell.append(el('p', 'intro', 'No goods trades are needed in this experiment.'));
    }
    shell.append(button('Try another transfer →', 'primary try-again', () => {
      navigate('Experiment');
    }));
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
  // Replay is deliberate: the result summary remains the first thing to inspect.
  void autoReplay;
  return () => { stop(); cancelAnimationFrame(frame); };
}
