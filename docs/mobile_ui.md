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

Results show prices, submitted setup changes, accounting checks, and a trade
explorer. Zero-trade runs show unchanged starting balances; Ask why explains the outcome. Detailed tables
remain under **Inspect the evidence**. Ask why offers free computed explanations
and optional typed AI questions grounded in submitted results.

The home page introduces this flow and retains the earlier runnable chapters.
Economic engines and their invariants are unchanged. The main page uses a
single-period engine call for each run rather than extending the older
redistribution model to accept changing populations and preferences.

Verification: Streamlit integration tests cover explicit Run, exact zero trades,
draft/result separation across views, preferences, added/removed agents, failed
runs, reset, chat grounding, and stale component events. Frontend checks cover
selection, remounts, and component events.

## Results component

`SubmittedRun` in `run_workspace.py` is the shared presentation boundary. It holds
one independent engine outcome and the preceding submitted outcome. Results and
Ask why use the same run data, including prices, totals, agents, setup changes,
and trade ordinals. Evidence receives that same submitted run for its detailed
ledger and price-search records. Unsubmitted setup values never enter this data.

Free explanations are generated once through `built_in_explanations(context)`.
Trade explanations live in Ask why, reached through the selected trade's button.
Browser events identify the submitted revision and trade index; there is no
legacy period selector or parallel baseline adapter in this flow.

The bundled component displays submitted outcomes: prices, checks, trades,
replay, and opening/closing balances. It emits only trade-selection state and
questions about a selected trade. Setup and view navigation belong to Streamlit.

The retired redistribution editor, its transfer endpoint and local preview,
and the associated action/navigation callbacks have been removed. The earlier
Redistribution chapter remains runnable with its existing economic behavior.

Run `node tests/test_playground_component.cjs` for component selection, remount,
and no-trade checks, and `pytest -q` for model and Streamlit behavior. Use the
actual Streamlit page for visual checks, replay, view navigation, and keyboard
interaction. The former standalone editor preview is no longer maintained.

Earlier UI designs remain available in Git history.
