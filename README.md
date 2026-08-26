# Econ Agent Sim

An educational, auditable agent-based economic simulator built one economy at a time.

## Design principles

1. **Start from the smallest textbook economy.** Add one mechanism at a time.
2. **Never overwrite a completed economy.** Old scenarios remain runnable and tested.
3. **Trace every transaction.** Transfers live in an append-only ledger.
4. **Make accounting executable.** Stock-flow identities and conservation laws are tests.
5. **Prefer optimization to behavioral tuning.** Agents use textbook optimization wherever possible.
6. **Keep the economic engine independent of the UI and storage.** No database is needed yet.
7. **Browser-first development.** GitHub Codespaces is the standard development environment; no local installation is required.

## Economy 0 — Pure exchange

Two agents exchange two goods. Alice begins with one unit of X; Bob begins with one unit of Y. Both have Cobb-Douglas utility `U(X,Y)=X^0.5 Y^0.5`. The Walrasian equilibrium is analytic: with `pY=1`, `pX=1`, and both agents finish with `(0.5 X, 0.5 Y)`.

Read [`docs/economies/economy_0.md`](docs/economies/economy_0.md).

## Economy 0.1 — Walrasian price discovery

Economy 0.1 keeps Economy 0 intact and adds one standard textbook mechanism: Walrasian tâtonnement. The model starts from a trial relative price, agents optimize, excess demand is measured, and the trial price adjusts until the market clears. No trade occurs during the price-search phase; barter settlement happens only after convergence.

The analytic Economy 0 price remains visible as a regression benchmark but is not used by the tâtonnement update.

Read [`docs/economies/economy_0_1.md`](docs/economies/economy_0_1.md).

## Economy 0.2 — Many-agent pure exchange

Economy 0.2 generalizes the exchange economy from two named agents to an arbitrary population. The canonical laboratory uses ten deterministic heterogeneous agents. Each agent optimizes independently, demands are aggregated, the same Walrasian tâtonnement process discovers the clearing price, and a deterministic clearing procedure matches net sellers to net buyers through the append-only ledger.

The canonical population is deliberately non-random and has an analytic benchmark of `pX=1`, keeping the new many-agent mechanism reproducible and independently testable.

Read [`docs/economies/economy_0_2.md`](docs/economies/economy_0_2.md).

## Run in GitHub Codespaces

1. In GitHub, select the branch you want to inspect. For work in progress, use its feature branch; for completed economies, use `main`.
2. Click **Code** → **Codespaces** → **Create codespace**.
3. Wait for setup to finish. Python, Streamlit, pytest, and Ruff are installed automatically.
4. In the Codespaces terminal, run:

```bash
streamlit run app/streamlit_app.py
```

GitHub will forward port `8501` and open the Streamlit app in your browser. Streamlit's page navigation lets you move between permanent economy versions.

To run the same quality checks used by CI:

```bash
ruff check .
pytest -q
```

GitHub Actions runs these checks automatically for pull requests.
