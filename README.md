# Tiny Economy

One phone-friendly economic laboratory: households choose work, consumption,
money and leisure; two independently funded firms produce, invest and pay dividends.

[Open Tiny Economy](https://econ-agent-sim.streamlit.app/).

## Explore

1. Choose an optional starting preset, or edit the household and firm settings.
2. Run the economy. **Results** shows firms, households and consolidated accounts.
3. Advance one or ten periods. Money and capital carry forward under the submitted settings.
4. Switch between **This period** and **Cumulative**. Historical flows keep their original prices.
5. Use **Ask why** for built-in explanations of the results and model rules.
6. Open **Experiment** to save a baseline, edit a copy, compare, download/reopen or reset.

There is one maintained model, not a catalogue of versioned apps. The four presets
are editable configurations of that model: Everyday economy, Fixed productive
capacity, Capital wears out, and Meeting a consumption target. They simplify
particular mechanisms; they do not recreate every historical exchange model.

## What is explicit

- Household optimization and decreasing-returns-to-labor production use textbook building blocks.
- Direct utility from money, soft consumption targets, cash-funded payroll and fixed
  reinvestment/dividend rules are disclosed modeling choices.
- All payments are funded and traced. Accounts reconcile cash, production, consumption,
  investment, wear, profit and replacement-price holding gains.
- Market clearing need not be unique. Candidate selection follows a documented
  reference/continuation convention, not a simulated price-adjustment process.
- No banks, credit, money creation, government, shocks, entry/exit or lifetime optimization.

See [model and accounting](docs/model.md), [market selection](docs/market_selection.md)
and [architecture](docs/architecture/0001-core-principles.md).

The [audit fixes](docs/hardening_notes.md) improve reliability without changing
economic policies. The next milestone follows a [textbook foundation](docs/textbook_foundation.md),
starting with an isolated optimal-growth reference checked against its known
solution. The [earlier investment proposal](docs/investment_design.md) is deferred.
These reference calculations are not active simulation behavior.

## Save and reopen

The app holds experiments in the current browser session, not a user database.
Download a JSON experiment before leaving to keep your run and baseline.
Current files identify format **4** and engine **tiny-economy-2.0.0**. Opening
replays the exact supported model and checks its accounts before replacing state.
Files from retired models are rejected clearly, never silently reinterpreted.
Earlier implementations remain recoverable from Git history, not in the working tree.

## Develop

Python 3.11 or newer:

```bash
python -m pip install -e ".[dev,app]"
streamlit run app/streamlit_app.py
ruff check .
pytest -q
node --test tests/test*component.cjs
```

The pure engine has no Streamlit or database dependency. Tests cover independent
household/firm optimality, funded ledger replay, accounting, units and scale,
multiple roots, save/reopen integrity, UI state and rendering. CI also starts the
real Streamlit server. See [deployment](docs/deployment.md) and [app guide](docs/app.md).
