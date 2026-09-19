# Tiny Economy

An educational monetary economy with households and firms that plan ahead.
[Open Tiny Economy](https://econ-agent-sim.streamlit.app/).

Two identical households choose consumption, work and money balances. Two
identical firms choose investment and dividends using their owners' valuation
of future income. Firms must pay dividends and wages from opening cash, before
selling goods. There is one good, one fixed unit of money, equal fixed ownership,
and no borrowing, inventories or shocks.

The single app has six inputs: patience, depreciation, the value of leisure,
the value of money balances, starting capital and the initial cash split.
Five starting experiments include growth, abundant capital, scarce capital,
tight opening cash and the stationary economy. Firms can choose zero investment
or zero dividends. Unsupported cases that require unused opening cash are
rejected clearly, preserving an existing run.

Start computes a verified 100-period plan with a longer numerical continuation.
Advance reveals that plan; it does not revise earlier choices or liquidate
capital at the display limit. Results include household and firm accounts,
period/cumulative views, trends, baseline comparisons, CSV export and deterministic
explanations. There is no chatbot or API-key requirement.

This uses textbook ingredients with explicit project-specific funding restrictions.
Perfect foresight and market clearing are assumed. It is not evidence of
self-regulating price discovery, empirical realism or global uniqueness.
See the [model](docs/model.md), [monetary specification](docs/monetary_foundation.md),
[constrained numerical method](docs/monetary_boundaries.md) and
[textbook benchmarks](docs/textbook_foundation.md).

## Saving experiments

The workspace lives in the browser session. Download JSON to preserve a draft,
run and optional baseline. Format **6**, model **tiny-economy-monetary-1**, engine
**tiny-economy-4.0.0** files are replayed and checked before restore. Earlier
model files are rejected; they are not reinterpreted under the new economics.
There is no cloud account storage yet.

## Development

```bash
python -m pip install -e ".[dev,app]"
streamlit run app/streamlit_app.py
ruff check .
pytest -q
```

The economic core uses the Python standard library and imports no Streamlit.
CI checks numerical conditions, transaction accounting, reports, file validation,
workspace behavior and actual Streamlit interactions, then starts a real server.
See the [app guide](docs/app.md), [architecture](docs/architecture/0001-core-principles.md)
and [deployment](docs/deployment.md).
