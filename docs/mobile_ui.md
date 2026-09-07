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
explorer. Zero-trade runs explain why no exchange is needed. Detailed tables
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

The sections below document earlier implementation stages and their former UI.

## Step 1 — persistent view navigation

Economy 0.3 keeps `Overview`, `Market`, and `Audit` available as the three top-level views. On screens up to 768 px wide, that selector is presented as a fixed bottom navigation bar so the user can switch views without scrolling back to the top of a long page.

The mobile navigation is scoped to the Economy 0.3 view selector through the Streamlit container key `economy03_mobile_nav`. It uses safe-area insets for phones with display cutouts or home indicators. The bar is deliberately raised above the very bottom of the viewport so browser chrome and Streamlit floating controls do not cover `Audit`, and the page reserves extra bottom padding so long content cannot scroll behind the navigation.

On wider screens, the same view selector remains in the normal document flow. No economic model, settings, redistribution behavior, accounting, or ledger logic changes as part of this UI step.

To keep each view focused, the experiment controls and summary belong to `Overview`: `Settings`, `Add a redistribution`, `Selected result`, and `Model boundary` are hidden on `Market` and `Audit`. The remove-last-redistribution action is scoped with the other experiment controls. `Market` is reserved for price discovery and clearing, while `Audit` is reserved for decisions, accounts, and ledgers.

Future phone-oriented improvements such as a more compact header and phone-specific Audit summaries should be evaluated separately rather than bundled into this change.

## Economy 0.4 — component playground

Economy 0.4 now uses a small Components v2 interface on Overview. It is bundled
in `src/econ_agent_sim/playground_component`, uses no remote assets or frontend
build service, and works with the existing Streamlit 1.62.0 pin. The Python
adapter in `playground.py` validates commands and serializes model results;
the economic engine files are unchanged.

The primary interaction is selecting two agents and moving Y between their
latest **opening endowments**. Python validates the command, calculates the
candidate experiment, and commits it only after a successful result. A revision
number rejects stale commands; action identifiers prevent duplicate processing.
The result presents actual prices, accounting checks, and one actual trade with
its reverse money payment. Users can replay or cycle through all recorded trades.

Opening/closing snapshots and all agents are available on demand. Snapshots
represent the whole market, not an intermediate single-trade balance. Animation
is explanatory: payment instructions settle as a batch. No inventory or money
carries between experiments, and no liquidity constraint has been introduced.
The amount editor always targets the latest experiment, even when an older
result is selected. The page explicitly labels this distinction.

Replay and editing controls operate in the browser until submission. Both
transfer legs animate together, and reduced-motion preferences suppress motion.
Native redistribution controls remain in a collapsed expander as a fallback.
Settlement and Audit retain the original tables. Settings are restored from
committed values when widgets remount; clearing redistributions and restoring
defaults are separate actions. Changing views uses cached simulation results.

The Economy 0.4 view selector stays in normal document flow for this first
prototype instead of reserving a large fixed-bottom area. Economy 0.3 is unchanged.

### Verification

- `PYTHONPATH=src python -m unittest discover -s tests -p test_playground.py -v`
  runs the dependency-free validation and model/payload checks.
- `pytest -q` also includes Streamlit integration tests for settings persistence,
  native transfers, distinct reset semantics, and duplicate/stale component events.
- `PYTHONPATH=src python tools/preview_playground.py` starts a local component
  preview at `http://127.0.0.1:8765`, using the real economic engine without
  Streamlit. This is a visual development harness, not a production server.
- Before merging, check the real Streamlit page at 320, 375, and 430 px widths:
  distinct and identical agent selections; a full available-Y transfer; invalid
  amounts; repeated submits; replay/next trade; opening/closing snapshots;
  all-agent inspection; old experiment selection; settings/view round trips;
  keyboard access; and reduced motion. Also check desktop and dark host themes.

The existing structural tests for earlier economies remain unchanged. The
Economy 0.4 structural test now checks the adapter boundary and preservation of
audits, not the discarded layout's exact source strings.
