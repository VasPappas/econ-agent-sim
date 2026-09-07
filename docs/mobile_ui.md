# Mobile UI evolution

## Current workspace — September 2026

Economy 0.4 uses **Set up / Results / Ask why**. It opens with two agents,
each holding 1 X and 1 Y with equal preferences. Nothing is simulated until
**Run**. The initial run clears at equal prices with exactly zero trades.

Set up edits a session-local draft: 2–20 agents (including odd counts), each
agent's X/Y quantities and spending preference, plus opening money. Increasing
population preserves existing agents and adds symmetric agents. Reducing it
removes agents from the end. At least some X and Y must remain in aggregate.

Each Run validates and solves an independent setup, then atomically saves it as
the current result and retains the preceding result for comparison. Failed runs
preserve both results. Draft edits do not alter Results or the assistant's
context. Quantities, preferences, and agent count may differ between runs;
these are independent scenarios, with no carryover of stocks or money.

One **Reset** restores two symmetric agents and opening money of 10 each, clears
current/previous results and conversations, and returns to Set up. API usage
allowances are retained. There is no separate baseline or transfer history.

Results lead with the price and every agent's starting-to-final X, Y, and Money
balances. The replay, animation, and trade navigation have been removed. A single
expandable **Check the accounts** statement contains conservation totals, an
all-agent/single-agent filter, stock-flow arithmetic, trade receipts, technical
residuals, and a full-precision CSV download. Failed checks remain visible before
the statement is opened. Zero-trade runs say that balances are unchanged.

Ask why owns explanation and trade focus. It offers free computed explanations,
the price-adjustment history, and optional typed AI questions grounded in the
submitted result. Collapsed Setup cards summarize each agent's quantities and
preferences.

The home page introduces this flow and retains the earlier runnable chapters.
Economic engines and their invariants are unchanged. The main page uses a
single-period engine call for each run rather than extending the older
redistribution model to accept changing populations and preferences.

Verification: Streamlit integration tests cover explicit Run, exact zero trades,
draft/result separation across views, preferences, added/removed agents, failed
runs, reset, chat grounding, result summaries, and trade focus. Frontend checks
cover outcomes, account statements, receipts, CSV data, and zero-trade results.

## Results component

`SubmittedRun` in `run_workspace.py` is the shared presentation boundary. It holds
one independent engine outcome and the preceding submitted outcome. Results and
Ask why use the same run data, including prices, totals, agents, setup changes,
and trade ordinals. Unsubmitted setup values never enter this data.

Free explanations are generated once through `built_in_explanations(context)`.
Trade explanations and price-search history live in Ask why. The focus selector
there chooses the whole run or one trade; Results emit no browser events. There
is no legacy period selector or parallel baseline adapter in this flow.

The bundled read-only component displays prices, agent outcomes, conservation,
accounts, trade receipts, and technical details. Setup, explanation focus, and
view navigation belong to Streamlit.

The retired redistribution editor, its transfer endpoint and local preview,
and the associated action/navigation callbacks have been removed. The earlier
Redistribution chapter remains runnable with its existing economic behavior.

Run `node tests/test_results_component.cjs` for component outcomes, accounts,
receipts, CSV, and no-trade checks, and `pytest -q` for model and Streamlit
behavior. Use the actual Streamlit page for visual, view-navigation, and keyboard
checks. The former standalone editor preview is no longer maintained.

Earlier UI designs remain available in Git history.

## Accounting and number validation

Completed-run evidence reconstructs net transfers from the ledger and compares
opening stocks plus those transfers with recorded closing balances. Monetary
settlement retains the physical model's final goods balances and settles cash
from trade receipts, independently of the asset ledger used for reconciliation.
A partial replay in earlier chapters shows reconstructed balances with an empty
check until the complete ledger can be compared with the recorded outcome.

`numerics.py` centralizes finite-number validation and absolute accounting
comparisons. The shared accounting tolerance is 1e-8 asset units; Economy 0 keeps
its original, stricter 1e-10 engine tolerance. Market clearing uses normalized
excess demand and the configured tolerance; the settlement threshold and the
legacy ledger's display-only dust threshold retain their separate purposes.
The monetary Results checks use the same accounting tolerance as its engine.
NaN, infinity, overflowing aggregates, and non-integer iteration limits are
rejected within the engine, including calls made without the Streamlit UI.
