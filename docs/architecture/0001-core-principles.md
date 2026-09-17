# ADR 0001 — One current economy, independent layers

Status: Accepted; supersedes the original keep-every-economy-runnable policy.

## Decision

Maintain one economic model and one workspace. Delete retired version pages,
engines, presentation layers and tests that exist only to preserve those retired
implementations. Git history is the recovery mechanism; do not maintain an archive
directory or imports from historical engines. Presets are configurations, not forks.

## Responsibilities

| Layer | Files | Responsibility |
| --- | --- | --- |
| Domain | domain.py | Validated settings and immutable period records |
| Choice and clearing | market.py, numerics.py | Household optimization, wage/price candidates and documented selection |
| Settlement | engine.py | Six explicit phases; funded transfers; physical and accounting certification |
| Reporting | reporting.py, comparison.py | One canonical period/cumulative report, comparison and full-precision CSV |
| Explanation | explanations.py, experiment_chat.py | Deterministic answers and bounded read-only AI requests |
| Workspace | workspace.py | Framework-independent draft, submitted history and baseline transitions |
| Portable files | experiments.py | Versioned validation, deterministic replay and atomic restore |
| Presentation | app/streamlit_app.py, experiment_view.py, chat_view.py, results_component, workspace_style.py | Streamlit controls and compact results rendering |

Economic modules do not import Streamlit. UI code does not re-solve or invent
accounts. Reports are the authoritative presentation input. A prospective
database or other frontend should consume the same engine and report records.

## State and atomicity

A draft is distinct from immutable submitted settings and completed periods.
Navigation never resets the draft. Continuing periods always uses submitted
settings, not unsimulated edits. Presets only change the draft when explicitly
applied. A multi-period advance and uploaded-file restore publish state only after
all calculations and validations succeed. A saved baseline remains independent.

Every money movement is a funded ledger transfer. Production, consumption,
depreciation and investment have explicit physical events; they are not invented
cash transfers. Immutable snapshots prevent later UI actions from altering history.

## Compatibility and recovery

Current portable files specify schema, model and engine identities. A fingerprint
detects replay changes but is not a security signature. Reject incompatible files
before changing the workspace. Bump engine identity when solving or accounting
changes saved results. Never keep a second engine merely to load old files.

## Tests worth keeping

Retain independent economic optimality and ledger reconstruction, accounting
identities, deterministic numerical anchors, unit/order invariance, root-selection
regressions, strict file validation and atomicity, a released file fixture,
mobile rendering contracts and behavioral navigation tests. Do not retain tests
solely for dead chapters, duplicate wrappers or textual implementation details.

## Limits

Session state is not durable multi-user storage. Current file/UI limits are 20
households and 100 periods. A finite equilibrium scan is neither a uniqueness nor
a dynamic-stability proof. See ../market_selection.md. Future scaling should be
measured; do not introduce databases, background jobs or service layers before
there is an actual product requirement.
