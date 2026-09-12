# Economy 0.9.1 — Portable experiments

This release extends the Investment and growth workspace with saved experiments
and baseline comparisons. It keeps the Economy 0.9 economic rules and ledger.

## User workflow

1. Run an economy for as many periods as needed, then keep it as a baseline.
2. Edit a copy of its starting setup, change a setting, and start a new simulation.
3. Compare the two experiments at the same period, using either that period alone
   or cumulative results from the first period.
4. Download the experiment file to keep the current simulation, unsubmitted setup
   edits, report selection, and optional baseline. Open it later to continue.

The compact Experiments disclosure holds file and baseline actions. Comparison
appears in Results when a baseline exists. Reset restores the default active
setup and clears its simulation; the separately kept baseline remains available.
Opening an experiment file replaces the active experiment and baseline with that
file's contents only after the whole file passes validation.

## File contract

The portable JSON format records an explicit format version and engine version.
Each experiment has a name, full-precision draft settings, separately frozen run
settings, completed period count, verification fingerprints for its snapshots,
and the selected period and report scope. A file can also contain one baseline.

Opening a file runs the same deterministic engine from the saved starting settings
and verifies every completed snapshot before accepting the restored history.
The restored accounts must reproduce the saved fingerprints exactly. Unsupported
versions and mismatches are rejected rather than silently revaluing or changing
historical results. Future engine releases must retain a compatible loader or
provide an explicit migration; compatibility is not assumed from the filename.

Fingerprints detect altered or incompatible histories; they are not a signature
or proof of authorship. JSON is data only. No pickle, object imports, or arbitrary
code execution are used. Parsing, household counts, period counts, names, numeric
domains and file size are bounded. Imports are atomic: failure leaves the active
setup, history and baseline unchanged.

Saved files contain simulation data only. API keys, chat conversations and request
allowance records are excluded. No database or user account is introduced. A
baseline kept in the current session still needs a download to survive session
loss. The existing full-precision CSV remains available as accounting evidence;
the JSON file is the reopenable experiment.

## Comparison contract

The six headline comparisons are total household consumption, closing physical
capital, average household work, the price of X, the wage's purchasing power
(X per work unit), and net firm operating profit. Changes are current minus
baseline, with work changes in percentage points. Higher or lower values are
not automatically labeled better or worse.

Both runs must contain the explicitly selected period. If one run is shorter,
the interface identifies their shared horizon instead of comparing unlike dates
or silently extending the saved baseline.

Period and cumulative values come from the canonical accounting report:

- Consumption and net profit cover the selected report range.
- Monetary flows sum at their original period prices, independently in each run.
- Capital is the selected period's closing stock, never a sum of capital stocks.
- Work is the average across households and the selected periods.
- Price and wage purchasing power are the selected period's rates in either mode.

Changed starting parameters are shown with the comparison. Household priorities
are compared as normalized weights because multiplying all three scores by the
same amount leaves preferences unchanged. A comparison may change more than one
parameter; it is not presented as a causal estimate for a single setting.

## Implementation boundaries

`investment_experiments.py` owns the portable format and pure restoration logic.
`investment_comparison.py` derives comparisons from frozen period snapshots.
The Streamlit page and experiment view own session updates and file controls;
the existing results component renders comparisons. The economic solver and
canonical report remain independent of Streamlit and file persistence.

## Verification

Acceptance checks cover exact account/evidence restoration with a separate edited
draft, deterministic continuation, invalid and incompatible uploads, unchanged
baselines through edits and resets, and matched-horizon comparisons including
cumulative original-price flows and closing stocks. Local integration validation:
266 Python tests, all three JavaScript component suites, and Ruff pass.

The available cloud browser does not support phone viewport emulation. Responsive
layout is checked in code; live inspection uses the available desktop viewport.

Live verification passed for an eleven-period baseline and edited copy, cumulative
comparisons, historical period selection, changed settings, and the built-in
comparison question. A file generated outside the hosted session reopened with
exact verified accounts, its separate 60% draft, a completed 20% run, baseline,
selected Period 2 and cumulative scope. Continuing produced Period 4 using the
submitted 20% policy; the three-period baseline remained fixed, and comparison
correctly reported the unmatched horizon. GitHub CI passed for the release.

The browser's download event was not received when the Download control was
activated. Its security policy blocked inspection of Chrome's downloads page, so
actual browser download completion is unverified. Serialization and restoration,
including their Streamlit callbacks, pass automated tests. A phone download check
remains outstanding alongside phone viewport inspection.
