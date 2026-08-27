# Streamlit application structure

The Streamlit application is organized as one simulator with permanent economy versions rather than as unrelated demonstrations.

## Home dashboard

`app/streamlit_app.py` is the simulator home page. It does not implement an economy. It explains the progression of mechanisms, compares the permanent versions, and links directly to each runnable economy.

## Permanent economy pages

The completed economies remain separate runnable pages under `app/pages/`:

1. `1_Economy_0_Pure_Exchange.py` — two-agent pure exchange with analytic equilibrium pricing.
2. `2_Economy_0_1_Walrasian_Price_Discovery.py` — the same exchange economy with tâtonnement price discovery.
3. `3_Economy_0_2_Many_Agent_Exchange.py` — many-agent heterogeneous pure exchange.

Each page has the same top-level structure: version context, navigation back to the simulator home and adjacent versions, a short summary of what changed, experiment controls, the economic process, and stock-flow accounting.

## Economy 0.2 tablet layout

Economy 0.2 is the first page explicitly optimized for inspection on a tablet-sized browser. Its experiment controls live in the main page instead of depending on the Streamlit sidebar. Market dynamics and agent decisions use separate full-width tabs so wide tables are not squeezed beside one another.

The stock-flow checkpoint remains outside those tabs and is displayed at every simulation stage. During tâtonnement it shows zero flows and unchanged opening stocks; after settlement it shows the ledgered flows and closing-stock reconciliation. Settlement results then separate the transfer ledger from the final allocation while keeping both fully inspectable.

A headless Streamlit `AppTest` executes the Economy 0.2 page in CI so UI refactors can catch runtime Streamlit errors in addition to the existing engine tests and Ruff checks.

## Design rule

A new economy should add a new page rather than replacing an older one. The home dashboard should be updated at the same time so the model progression remains understandable from the browser interface.

The economic engine remains independent from this navigation layer. Reorganizing the Streamlit shell must not alter equilibrium, settlement, ledger, or accounting logic.
