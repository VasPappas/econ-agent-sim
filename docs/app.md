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

The economic engine remains independent from these pages. UI changes must not alter equilibrium, settlement, ledger, or accounting logic.

## Economy 0.2 tablet layout

Economy 0.2 is the first page explicitly optimized for inspection on a tablet-sized browser. Its experiment controls live in the main page instead of depending on the Streamlit sidebar. Market dynamics and agent decisions use separate full-width tabs so wide tables are not squeezed beside one another.

The stock-flow checkpoint remains outside those tabs and is displayed at every simulation stage. During tâtonnement it shows zero flows and unchanged opening stocks; after settlement it shows the ledgered flows and closing-stock reconciliation. Settlement results then separate the transfer ledger from the final allocation while keeping both fully inspectable.

A headless Streamlit `AppTest` executes the Economy 0.2 page in CI so UI refactors can catch runtime Streamlit errors in addition to the existing engine tests and Ruff checks.

## Economy 0.3 mobile-first prototype

Economy 0.3 is the first phone-first interface. It uses a centered layout and starts with the Streamlit sidebar collapsed so the economic content receives the available screen width.

The mobile information hierarchy is deliberately progressive:

1. choose a period with a compact pills control;
2. choose `Overview`, `Market`, `Agents`, `Accounts`, or `Ledger` with a second pills control;
3. show only the selected view below those controls; and
4. place full audit tables behind explicit expanders rather than deleting them.

Experiment parameters have moved into a small `Settings` popover. The default `Overview` therefore contains only the cross-period price path, a horizontally scrollable result strip, market/accounting status, a short explanation of the price movement, and the optional exogenous-reset audit for periods after the first.

The `Market` view contains aggregate supply, the within-period tâtonnement path, the final clearing check, and an expandable iteration table. `Agents` starts with a compact opening-stock/net-demand table and keeps the full optimization table in an expander. `Accounts` summarizes the stock-flow and conservation checks before showing the compact reconciliation. `Ledger` begins with a four-column transfer view and keeps the complete period ledger, final-allocation audit, and multi-period ledger available through expanders.

Horizontal metric strips use Streamlit's no-wrap horizontal container so they remain one compact, touch-scrollable row on narrow screens instead of stacking into a tall column.

The guiding rule is **result first, explanation second, audit detail third**. Nothing required for traceability is removed; detailed material is progressively disclosed when the user asks for it.

The Economy 0.3 headless `AppTest` executes every mobile view in CI, including a later-period run that exercises the exogenous-reset path.

## Design rule

A new economy should add a new page rather than replacing an older one. The home dashboard should be updated at the same time so the model progression remains understandable from the browser interface.

When the Economy 0.3 phone layout has been reviewed on a real device, its successful interaction patterns can be propagated backward to the older permanent economy pages. That propagation should remain a UI-only change and preserve every completed economy's model behavior.
