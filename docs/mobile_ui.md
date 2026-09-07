# Mobile UI evolution

## Current workspace — September 2026

**Edit starting economy** lets users draft X/Y allocations agent by agent, with
live draft totals, then apply them using **Use as baseline**. The full candidate
is validated and solved before replacing the baseline and clearing transfers.
Drafts and baselines are session-local. Reset preserves this custom allocation;
Restore defaults restores the canonical allocation. Changing the agent count
also creates a fresh canonical population; other settings retain quantities.

Experiment now shows an explicit baseline summary with actual configured totals
and an expandable list of every agent's baseline holdings and spending shares.
The next experiment names the opening allocation it builds on. Historical views
are labeled as viewing only. Reset to baseline is visible in every view (disabled
when already at baseline), removes transfers, keeps configured settings, restores
the editor, and returns to Experiment. Restore defaults remains in Settings and
also restores the original population, opening money, and price-search settings.

The home page starts with an exploration action and names the five existing
economies Exchange, Price discovery, Many agents, Redistribution, and Money.
Economy 0.4 uses **Experiment / Results / Ask why**. Results contain the opening
endowment changes, price comparison with the preceding experiment, conservation
checks, and selected trade. Settlement and audit tables are under **Inspect the
evidence**. The earlier economy pages and economic engines are preserved.

Common explanations are generated directly from model values, without API calls.
Only typed follow-up questions use OpenAI. Returning from Ask why restores the
selected trade; bounded conversations are retained separately per context.

Transfers continue to build on the latest opening endowments. Each settlement is
independent and starts with fresh money; closing balances do not carry forward.
Unlike the standalone design preview, the live UI supports arbitrary agent pairs,
amounts, settings, and historical experiments rather than four fixed examples.

The cream/teal styling spans home, controls, results, evidence, and chat. Labels
are enlarged, containers reflow, and navigation remains in normal document flow
to avoid covering browser controls or the phone keyboard. Replay is user-initiated.

The sections below describe earlier implementation stages.

The Streamlit simulator is designed mobile-first. Changes to the phone experience are introduced incrementally so each interaction can be tested before adding the next one.

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
