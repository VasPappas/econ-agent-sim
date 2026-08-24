# Econ Agent Sim

An educational, auditable agent-based economic simulator built one economy at a time.

## Design principles

1. **Start from the smallest textbook economy.** Add one mechanism at a time.
2. **Never overwrite a completed economy.** Old scenarios remain runnable and tested.
3. **Trace every transaction.** Transfers live in an append-only ledger.
4. **Make accounting executable.** Stock-flow identities and conservation laws are tests.
5. **Prefer optimization to behavioral tuning.** Economy 0 uses Cobb-Douglas utility maximization.
6. **Keep the economic engine independent of the UI and storage.** No database is needed yet.

## Economy 0

Two agents exchange two goods. Alice begins with one unit of X; Bob begins with one unit of Y. Both have Cobb-Douglas utility `U(X,Y)=X^0.5 Y^0.5`. The Walrasian equilibrium is analytic: with `pY=1`, `pX=1`, and both agents finish with `(0.5 X, 0.5 Y)`.

Read [`docs/economies/economy_0.md`](docs/economies/economy_0.md) before the code if you want the economic explanation first.

## Run

```bash
python -m pip install -e ".[dev]"
pytest
```

For the optional educational UI:

```bash
python -m pip install -e ".[app]"
streamlit run app/streamlit_app.py
```
