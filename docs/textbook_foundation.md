# Textbook foundations and verification references

The current app uses [the monetary specification](monetary_foundation.md) and
[its constrained solver](monetary_boundaries.md). Households and firms plan jointly.
Textbook ingredients are explicit; their combination with prepaid wages, fixed
ownership, irreversible capital and no external finance is a project extension.
The app is not described as an unmodified canonical Ramsey or Sidrauski model.

## Independent real-growth benchmark

`textbook_growth.py` is an isolated verification module. Its fixed-labor,
full-depreciation log-utility problem has the exact investment share `alpha*beta`
(0.475 at the illustrative defaults). Numerical Bellman/value-iteration results
can be checked against that expression; a Bellman residual is not by itself a
global coefficient-error bound, especially as patience approaches one.

The same module implements a partial-depreciation reference with endogenous
labor. See [the real specification](minimal_reference_economy.md) and
[transition method](growth_transition.md). Analytical stationary allocations,
full-depreciation policies, resource constraints, labor and Euler conditions
provide independent checks. This reference allows reversible capital and has
no monetary funding friction. Its rental-capital accounts are not interchangeable
with the app's firm-owned capital and dividend accounts.

## Monetary application

The monetary model adds log real-money services to household preferences and
discounts firm payouts with owners' marginal utility. Four structural inputs
and two starting conditions replace prescribed saving/investment shares and
payout rules. All cash transfers must be funded in the specified event order.

`monetary_growth.py` provides an interior regression reference and the constrained
entry point used by the app. Tests cover exact special cases, stationary paths,
firm supporting bounds, zero investment, zero dividends, funding constraints,
settlement and horizon sensitivity. Unsupported cash retention fails explicitly.
The [current model guide](model.md) explains user-facing accounts and limits.

Perfect foresight, symmetry and market clearing remain assumptions. A verified
equilibrium path does not establish decentralized learning or self-regulation.
There is no claim of empirical calibration or global uniqueness. Shocks remain
postponed while the endogenous mechanisms are developed.

## Reproduce

```bash
python docs/textbook_benchmark.py
python docs/monetary_reference_check.py
python docs/monetary_transition_check.py
pytest -q
```

The reference specifications link the primary teaching sources and give the
actual equations used; tests evaluate those equations independently of the UI.
