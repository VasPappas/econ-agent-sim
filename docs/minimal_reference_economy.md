# Step 1 — A minimal economic reference

Status: implemented verification reference, following the review of release `55dfe72`.
This document specifies the frictionless verification reference. The current
application uses the [constrained monetary model](monetary_boundaries.md)
described in [model.md](model.md), with explicit differences in ownership,
funding and investment constraints.

## Purpose and choice

The reference asks: **how should a household divide its time between work and
leisure, and output between consumption now and productive capital for later?**

Use deterministic neoclassical growth in the Ramsey–Cass–Koopmans family.
QuantEcon's [planning formulation](https://python.quantecon.org/cass_koopmans_1.html)
provides the consumption/capital trade-off; its
[competitive formulation](https://python.quantecon.org/cass_koopmans_2.html)
provides the household budgets and factor markets. Those lectures use fixed
labor. Here we explicitly extend preferences to log leisure and derive the labor
condition below. This extension is part of the specification, not a claim that
the cited implementation already includes it.

The real allocation reference establishes a common objective for saving and
investment. It does not explain money demand, funded payments or price
discovery. The [monetary foundation](monetary_foundation.md) adds the money
preferences, asset budgets and funded payments used by the application.
Price discovery remains outside both models: both assume perfect foresight.

## Minimal environment

- One homogeneous good is used for consumption and capital.
- Identical households have the same preferences, initial capital and one unit
  of available time per period. Population is fixed.
- Production uses capital and labor, with constant productivity and constant
  returns to scale. Producers take factor prices as given.
- Households know the deterministic future environment. There are no shocks,
  growth in technology, taxes or financial frictions in this reference.
- Capital chosen at the end of a period first produces in the following period.
- Consumption, output and capital are expressed per household. Labor is the
  fraction of that household's available time spent working.

Two identical household records and two identical producer records can represent
this symmetric allocation: multiply per-household quantities by two for economy
totals. They do not introduce heterogeneity or strategic competition. No second
app or historical engine is retained. The isolated `textbook_growth.py`
reference remains a verification tool, consistently with ADR 0001.
The application also uses symmetric households and firms; neither construction
is an aggregation result for heterogeneous agents.

## Three structural inputs and one initial condition

| Symbol | Meaning | Illustrative value | Status |
| --- | --- | --- | --- |
| `beta` | Weight placed on next period's utility relative to this period | 0.95 | Preference; `0 < beta < 1` |
| `delta` | Fraction of opening capital worn out each period | 0.10 | Technology; `0 <= delta <= 1` |
| `chi` | Value of leisure relative to consumption | 1.00 | Preference; `chi > 0` |
| `k_0` | Opening capital per household | 1.00 | Initial condition; `k_0 > 0` |

Set productivity `A=1` by choice of the common goods/capital unit. Hold the
production exponent `alpha=0.5` fixed, matching the app's current technology.
Fixing this exponent is an explicit structural assumption, not empirical
calibration. Fixing log utility likewise fixes its curvature; a parameter has
not disappeared merely because it is held constant.

There is no independently imposed saving share or required-return input in this
reference. Saving and the return are outcomes of the same intertemporal problem.
`beta` is a preference, not a paid interest rate. All rates refer to one model
period; no annual or quarterly interpretation is claimed. A calendar frequency
and recalibration are required before interpreting them against data.

## Objective, feasibility and timing

For periods `t=0,1,...`, opening capital `k_t` is inherited. The household chooses
consumption `c_t`, work `l_t` and next capital `k_(t+1)` to maximize:

```text
sum from t=0 to infinity beta^t [log(c_t) + chi log(1-l_t)]

y_t = A k_t^alpha l_t^(1-alpha)
c_t + k_(t+1) = y_t + (1-delta) k_t

c_t > 0, k_(t+1) > 0, 0 < l_t < 1, k_0 given
```

Output is produced with opening capital and current work. Consumption uses
current resources; depreciation applies to opening capital; chosen next capital
carries forward. Gross investment is `i_t = k_(t+1) - (1-delta)k_t`.

The textbook reference permits disinvestment: surviving capital can be converted
back into the common good. Adding `i_t >= 0` would introduce irreversibility and
change the feasible set and optimality conditions. The current application has
that restriction and checks its boundary conditions explicitly; it is not
assumed equivalent to this reference.

For an interior solution, independent checks are:

```text
1/c_t = beta [1-delta + alpha y_(t+1)/k_(t+1)] / c_(t+1)
chi/(1-l_t) = (1-alpha) y_t / (l_t c_t)
lim as t -> infinity beta^t k_(t+1)/c_t = 0
```

The first condition links consumption today and tomorrow. The second balances
the utility of leisure with the consumption that another unit of work buys.
The last condition rules out holding valuable unused wealth forever. Resource
feasibility and first-order conditions alone do not replace that condition.
A finite displayed run is a window on an infinite-horizon decision; it must not
force liquidation at its last displayed period.

## Competitive interpretation and ownership boundary

In the canonical competitive reference, households own capital and rent it to
firms. In units of the common good, the real wage and gross capital rental are:

```text
w_t = (1-alpha) y_t/l_t
v_t = alpha y_t/k_t
c_t + k_(t+1) = w_t l_t + (v_t + 1-delta) k_t
```

Constant returns and competitive factor pricing exhaust output in factor
payments. Firm economic profit after both factor payments is zero. A household
receives labor income and capital rent; depreciation reduces its surviving
capital. The gross return on saving is `1-delta+v_(t+1)`.

The current app has **firms owning capital**, households owning fixed equity
shares, and firms paying funded dividends. Those accounts are not interchangeable
with household-owned capital and rental payments. This reference preserves
that distinction; app dividends must not be relabeled as capital rents.

The [monetary foundation](monetary_foundation.md) now specifies household asset
budgets, owner valuation and investment/liquidity/payout decisions under the
actual ownership arrangement. Its money-in-utility extension has an independent
[interior benchmark](monetary_transitions.md) and the
[constrained implementation](monetary_boundaries.md) used by the application.
The application solves household and firm decisions jointly under those budgets.

## What stays outside this reference

| Mechanism or extension | Treatment here and reason |
| --- | --- |
| Money balances and nominal prices | Absent from the real reference; require an explicit monetary model and asset budget |
| Household and firm heterogeneity | Both the reference and current app use symmetry; heterogeneous ownership requires its own valuation treatment |
| Cash-funded payroll and dividends | Absent here; explicit financing constraints in the monetary model |
| Irreversible investment | Absent here; the current app restricts firms to investing nonnegative amounts of their own output |
| Money services and owner distributions | Require the monetary preferences and corporate ownership budgets specified separately |
| Equilibrium selection across monetary regimes | Global uniqueness and multiplicity remain unresolved; this reference supplies no selection rule |
| Inventories, rationing and adaptive prices | Later market-adjustment design, with a declared event order and trading rules |

The application has no independent investment-share cap, hurdle rate,
consumption target or permanent initial-cash reserve. Saving, investment and
funded distributions follow the joint monetary problem. Exogenous shocks
remain postponed.

## Analytical checks and implementation status

At an interior stationary allocation let `x=k/l`. The reference equations imply:

```text
r_star = 1/beta - 1
x_star = [alpha A / (r_star+delta)]^(1/(1-alpha))
w_star = (1-alpha) A x_star^alpha
c_per_labor = A x_star^alpha - delta x_star
l_star = w_star / [w_star + chi c_per_labor]
k_star = x_star l_star
c_star = c_per_labor l_star
```

For the illustrative inputs above, direct substitution gives:

| Per-household stationary quantity | Value |
| --- | ---: |
| Capital | 4.5765720081 |
| Work fraction | 0.4264705882 |
| Output | 1.3970588235 |
| Consumption | 0.9394016227 |
| Gross investment, equal to replacement | 0.4576572008 |
| Real wage | 1.6379310345 |
| Net return per model period | 0.0526315789 |

These are algebraic verification values, not forecasts for the app or evidence
that its current economy reaches this allocation. Direct numerical substitution
checked the resource, Euler and labor conditions to floating-point precision.
That check does not verify a transition solver or establish convergence.

Already implemented: the isolated fixed-labor, full-depreciation, log-utility
special case in `textbook_growth.py`. Its optimal investment share is
`alpha*beta`; the numerical result at existing defaults remains `0.475`, matching
the separate analytical calculation. Fixed labor must be imposed explicitly in
that comparison; setting `chi=0` in a log-leisure solver is not a silent shortcut.

For the implemented endogenous-labor extension, full depreciation also has an exact
special case, derived from the stated objective and constraints:

```text
k_(t+1) = alpha beta y_t
c_t = (1-alpha beta) y_t
l_t = (1-alpha) / [(1-alpha) + chi (1-alpha beta)]
```

This supplies an additional independent check used by the implemented labor solver.

Now implemented: partial-depreciation transition paths and endogenous labor in
the isolated reference. See [the numerical method and acceptance checks](growth_transition.md).
The [monetary household/firm foundation](monetary_foundation.md) also has an
[interior transition benchmark](monetary_transitions.md) and the
[constrained transition solver](monetary_boundaries.md) used by the application.
Both remain distinct from this frictionless reference.

Before relying on an extended numerical solver, verify resource feasibility,
labor optimality, Euler residuals along transitions, the stationary allocation,
the existing full-depreciation special case, and sensitivity to the numerical
domain and horizon/continuation treatment. Report numerical limitations openly.
The reference is an allocation benchmark; decentralized price discovery and
self-regulation still require a specified adjustment process.

Step 1 delivers this economic specification and its analytical checks. The
monetary foundation and constrained solver supply the application's ownership,
saving, funding and payout structure. Comparisons with the real reference must
remove monetary and investment restrictions explicitly and explain each
mapping; reducing the money preference to zero alone is not a frictionless limit.
