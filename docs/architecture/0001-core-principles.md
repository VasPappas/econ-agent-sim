# ADR 0001 — One current economy, independent layers

Status: Accepted; supersedes the original keep-every-economy-runnable policy.

## Decision

Maintain one economic model and one workspace. Retire superseded engines,
pages and tests. Git history is the recovery mechanism. Presets configure the
same model. Isolated analytical and real-growth benchmarks remain verification
tools, not alternative app engines.

## Responsibilities

| Layer | Files | Responsibility |
| --- | --- | --- |
| Settings | domain.py | Six validated inputs and model identity |
| Economics | monetary_growth.py, _monetary_boundaries.py, _monetary_numerics.py | Joint paths, optimality, continuation and funded settlement |
| Application engine | engine.py | Accept a complete immutable 100-period plan or reject it |
| Reporting | reporting.py, comparison.py | Dated accounts, consolidation, comparison and CSV |
| Explanations | explanations.py | Deterministic answers from current accounts |
| Workspace | workspace.py | Draft, accepted run, revealed periods and independent baseline |
| Portable files | experiments.py | Strict versioned validation, replay and atomic restore |
| Presentation | app/streamlit_app.py, workspace_style.py, ui_text.py | Native Streamlit controls, tables, charts and escaped names |
| Benchmarks | textbook_growth.py | Independent real allocation and exact special cases |

Economics imports no Streamlit. UI code does not invent accounts or optimize
decisions. Reports are the authoritative presentation input.

## State and compatibility

A draft is separate from immutable submitted settings. Start publishes only a
fully accepted plan. Advancing reveals cached periods without re-solving or
revising history. Navigation retains the draft; a baseline is independent.
Uploaded experiments replace state only after all validation and replay succeed.

Current files identify schema, model and engine. Stored paths are compared with
deterministic replay within numerical tolerances, not accepted on trust or treated
as cryptographically authenticated. Reject old economics explicitly. Never retain
a second engine merely to load an old file.

## Verification and limits

Keep independent optimality, funded transfers, cash and physical identities,
book-value bridges, exact numerical anchors, continuation sensitivity, strict
file validation, atomic state and real UI interaction checks. Retire tests that
only preserve superseded implementation details.

The app fixes two identical households and two identical firms, revealing at
most 100 periods. Input bounds do not guarantee a supported solution. The
unspent-opening-cash regime, global uniqueness and market adjustment remain
unresolved. Session state is not durable multi-user storage. Add infrastructure
only when actual requirements warrant it.
