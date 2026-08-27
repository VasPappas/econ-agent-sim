# Streamlit application structure

The Streamlit application is organized as one simulator with permanent economy versions rather than as unrelated demonstrations.

## Home dashboard

`app/streamlit_app.py` is the simulator home page. It does not implement an economy. It explains the progression of mechanisms, compares the permanent versions, and links directly to each runnable economy.

## Permanent economy pages

The completed economies remain separate runnable pages under `app/pages/`:

1. `1_Economy_0_Pure_Exchange.py` — two-agent pure exchange with analytic equilibrium pricing.
2. `2_Economy_0_1_Walrasian_Price_Discovery.py` — the same exchange economy with tâtonnement price discovery.
3. `3_Economy_0_2_Many_Agent_Exchange.py` — many-agent heterogeneous pure exchange.
4. `4_Economy_0_3_Repeated_Exchange.py` — repeated many-agent exchange with explicit periods and fresh exogenous endowments.

Each page has the same top-level structure: version context, navigation back to the simulator home and adjacent versions, a short summary of what changed, experiment controls, the economic process, and stock-flow accounting.

## Economy 0.2 tablet layout

Economy 0.2 is the first page explicitly optimized for inspection on a tablet-sized browser. Its experiment controls live in the main page instead of depending on the Streamlit sidebar. Market dynamics and agent decisions use separate full-width tabs so wide tables are not squeezed beside one another.

The stock-flow checkpoint remains outside those tabs and is displayed at every simulation stage. During tâtonnement it shows zero flows and unchanged opening stocks; after settlement it shows the ledgered flows and closing-stock reconciliation. Settlement results then separate the transfer ledger from the final allocation while keeping both fully inspectable.

A headless Streamlit `AppTest` executes the Economy 0.2 page in CI so UI refactors can catch runtime Streamlit errors in addition to the existing engine tests and Ruff checks.

## Economy 0.3 period-centered layout

Economy 0.3 keeps the tablet-friendly main-page controls but shifts the visual hierarchy from tâtonnement steps to explicit time periods. The page first shows the full equilibrium-price path across periods, then lets the user choose one period to inspect.

The selected period exposes four full-width views:

- exogenous opening endowments and within-period price discovery;
- agent decisions and net demands;
- the selected-period stock-flow reconciliation; and
- the period ledger plus final allocation.

For periods after the first, the page can show the previous period's closing stocks beside the new period's exogenous opening stocks. This makes the deliberate no-carry-over assumption visible in the interface rather than hiding it in the engine.

The full multi-period ledger is also inspectable, with globally unique transaction IDs and explicit period labels.

## Design rule

A new economy should add a new page rather than replacing an older one. The home dashboard should be updated at the same time so the model progression remains understandable from the browser interface.

The economic engine remains independent from this navigation layer. Reorganizing the Streamlit shell must not alter equilibrium, settlement, ledger, or accounting logic.
