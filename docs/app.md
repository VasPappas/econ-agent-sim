# Streamlit application structure

The Streamlit application is organized as one simulator with permanent economy versions rather than as unrelated demonstrations.

## Home dashboard

`app/streamlit_app.py` is the simulator home page. It does not implement an economy. It explains the progression of mechanisms, compares the permanent versions, and links directly to each runnable economy.

## Permanent economy pages

The completed economies remain separate runnable pages under `app/pages/`:

1. `1_Economy_0_Pure_Exchange.py` — two-agent pure exchange with analytic equilibrium pricing.
2. `2_Economy_0_1_Walrasian_Price_Discovery.py` — the same exchange economy with tâtonnement price discovery.
3. `3_Economy_0_2_Many_Agent_Exchange.py` — many-agent heterogeneous pure exchange.
4. `4_Economy_0_3_Repeated_Exchange.py` — repeated many-agent exchange with user-defined exogenous redistribution across periods.

The economic engine remains independent from these pages. UI changes must not alter equilibrium, settlement, ledger, or accounting logic.

## Economy 0.2 tablet layout

Economy 0.2 is the first page explicitly optimized for inspection on a tablet-sized browser. Its experiment controls live in the main page instead of depending on the Streamlit sidebar. Market dynamics and agent decisions use separate full-width tabs so wide tables are not squeezed beside one another.

The stock-flow checkpoint remains outside those tabs and is displayed at every simulation stage. During tâtonnement it shows zero flows and unchanged opening stocks; after settlement it shows the ledgered flows and closing-stock reconciliation. Settlement results then separate the transfer ledger from the final allocation while keeping both fully inspectable.

A headless Streamlit `AppTest` executes the Economy 0.2 page in CI so UI refactors can catch runtime Streamlit errors in addition to the existing engine tests and Ruff checks.

## Economy 0.3 mobile-first redistribution experiment

Economy 0.3 is phone-first and uses a centered layout with the Streamlit sidebar collapsed. Its default state is intentionally small: one **Baseline** period reproducing the Economy 0.2 canonical endowment distribution.

The user creates time explicitly by adding redistributions. Each action chooses a sender, a receiver, and an amount of Y to move. The next period inherits the latest exogenous endowment schedule with only that redistribution applied. Total Y remains fixed, while X endowments, agent identities, and Cobb-Douglas preferences remain unchanged. The user can add as many redistribution periods as desired, remove the latest one, or reset the experiment to the baseline.

The top-level mobile information hierarchy is deliberately shorter than before:

1. add an optional redistribution;
2. choose `Baseline` or one of the user-created redistribution periods;
3. choose only `Overview`, `Market`, or `Audit`; and
4. reveal detailed tables through explicit expanders when needed.

The selected result is shown in one responsive full-width block instead of several narrow `st.metric` cards. The block shows the exact equilibrium `pX`, the percentage change from the previous step when relevant, and the market/accounting status in text that can wrap naturally on a phone. The selected period itself is not repeated in another card because the period pill already provides that context.

`Overview` is the main teaching surface. It shows the equilibrium-price history only when multiple periods exist, the selected period's equilibrium price and accounting status, the exact agents whose Y endowments changed, and the change in `sum(alpha_i * y_i)`. Its price-history chart uses a clearly disclosed zoomed vertical scale so small redistribution-driven price changes remain visible on a phone without hiding the exact numerical value.

`Market` keeps the full within-period tâtonnement audit. Initial pX remains the numerical starting point, lambda remains the adjustment speed, and the chart uses comparable price and adjustment axes so those parameters do not disappear visually through automatic rescaling. Its search summary also uses a responsive text block rather than a row of narrow metric cards.

`Audit` contains the complete agent decision table, stock-flow accounts, period settlement ledger, exogenous reset comparison, and full multi-period ledger. Nothing needed for traceability is removed; it is simply one level deeper than the primary economic result.

The original four-period rotating-Y schedule is retained in the engine as a legacy deterministic example for reproducibility, but it is no longer the default Streamlit experience.

The guiding rule remains **result first, explanation second, audit detail third**.

The Economy 0.3 headless `AppTest` verifies both the one-period baseline and an injected user-defined redistribution period, then exercises the Market and Audit views.

## Design rule

A new economy should add a new page rather than replacing an older one. The home dashboard should be updated at the same time so the model progression remains understandable from the browser interface.

Successful mobile interaction patterns can be propagated backward to older permanent economy pages as UI-only changes while preserving their model behavior.