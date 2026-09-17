# Forward-looking investment: the neoclassical user-cost rule

Each firm can use **Percentage policy** or **Forward-looking · user cost**.
The first remains the released benchmark. The second chooses investment by
comparing the forecast marginal operating return on capital with its user cost.
Households keep their existing within-period choices; this release does not
claim a unified lifetime-saving or perfect-foresight equilibrium.

## Textbook foundation and explicit extensions

The foundation is the neoclassical desired-capital/user-cost condition. With
an unchanged expected capital-good price and no tax or adjustment cost, its
benchmark condition is `marginal operating return = required return + depreciation`.
Carroll's [investment lecture](https://www.econ2.jhu.edu/people/ccarroll/public/LectureNotes/Investment/qModel/)
derives this capital-cost condition and its relation to marginal q.

Our implementation applies that criterion to a firm that finances payroll from
its own cash. It forecasts current prices, wage and payroll funds unchanged,
and recomputes its decision each period. These are conditional forecasts, not
knowledge of the future clearing price or wage.

Additional Tiny Economy rules remain explicit: firms own capital; new capital
comes from retaining their own output; investment is irreversible and fits a
precommitted fraction of current gross surplus; and existing profit-capped
dividends and the protected operating float remain. The budget fraction is a
financing commitment, not an optimized payout rate. It is below 100%, so some
surplus remains cash. The required return is an assumed real opportunity cost
per simulation period, not paid interest or a return derived from households.

The policy optimizes the stated conditional user-cost criterion. It does not
maximize lifetime dividends under all the simulation's financial constraints.
There is no capital liquidation transaction or arbitrary finite-horizon runoff.

## Decision and timing

At candidate goods price `p` and wage `w`, let `K`, `A`, `delta` be opening
capital, productivity and wear. `M` is cash after the opening dividend, `theta`
the maximum surplus fraction invested, and `r` the required return.

```text
u = w/p, b = M/p                  forecast real wage and payroll funds
L = min(A^2*K/(4*u^2), b/u)       current funded hiring
Q = A*sqrt(K*L)
S = Q-u*L                        current real gross surplus
0 <= I <= theta*S
K_next = (1-delta)*K + I
```

The firm chooses next capital `k` to maximize:

```text
J(k) = g(k) - (r+delta)*k
g(k) = max over 0 <= u*future_L <= b of [A*sqrt(k*future_L) - u*future_L]
(1-delta)*K <= k <= (1-delta)*K + theta*S
```

Current surplus-maximizing hiring is consistent with this rule: a higher surplus
raises current earnings and expands the feasible investment set. Hiring beyond
its funded surplus optimum improves neither. Forecast payroll funds are held
fixed when evaluating that set, rather than equated to current closing cash.

Writing `gamma=A^2/(4*u)` and `c=r+delta`:

```text
g(k)  = gamma*k                   when k <= b/gamma
        2*sqrt(gamma*b*k) - b     otherwise
g'(k) = min(gamma, sqrt(gamma*b/k))
```

This concave forecast function incorporates payroll funding. Unconstrained
optimized operating surplus is linear in capital; diminishing marginal returns
arise here when forecast payroll capacity binds. The underlying constant-returns
production technology has not changed.

If `gamma<c`, investment is zero. If `gamma>c>0`, desired capital is
`gamma*b/c^2`, clipped to the feasible interval. If `c=0`, invest the allowed
budget. At `gamma=c`, all feasible capital up to `b/gamma` has the same score;
the solver keeps that complete optimal interval.

## Clearing, accounting and numerical limits

The common markets include chosen investment. At a flat optimum, goods clearing
selects within the optimal interval. If both firms are indifferent, additional
retention is allocated in proportion to interval capacities, with stable IDs for
roundoff. The selection and indifferent firms appear in numerical evidence.

Every completed period independently checks the budget and concave first-order
conditions: marginal return cannot exceed cost at a zero-investment optimum,
cannot be below cost at a budget ceiling, and equals cost in the interior, within
the declared tolerance. Payroll, goods settlement and all existing accounting
certificates must also pass. Forecasts never create transactions or realized income.

Multiple outcomes can occur even with zero consumption targets. The initial
reference is the percentage-policy economy with the same budget fractions and
zero targets; later periods use the previous price. The closest detected price
in log distance is selected. The finite root scan does not claim completeness
or economic stability. See [market selection](market_selection.md).

## Exploring decisions

**Firm accounts → Why this investment?** shows investment, its budget, replacement
needs, expected marginal return before wear and user cost including wear. It
explains zero investment, a budget ceiling, an interior target or indifference.
A zero budget can prevent investment even when returns are attractive.
Cumulative accounts sum realized flows; the investment explanation is explicitly
for the selected final period and never sums forecasts.

Try **Firms look ahead**: both firms have a 5% required return, 10% wear and 40%
maximum surplus budget. Firm A has productivity 0.5 and Firm B 2.0. In period 1,
A invests zero and B about 0.3121 X. This is an illustration, not a calibration.

With otherwise default symmetric firms, these first-period cases also illustrate
the selected policy (returns are per model period, not annual estimates):

| Required return | Investment per firm, X | Outcome |
| --- | ---: | --- |
| 5% | 0.175412 | Budget ceiling |
| 75% | 0.151182 | Interior target |
| 90% | 0 | Returns below user cost |

The 75% case has three certified equilibrium candidates; the displayed result
uses the stated selection rule. Raising required return reduces desired
investment at fixed prices. Full-economy comparisons also change prices and may
switch equilibrium, so that is not a universal aggregate comparative-static claim.

Changing policy, return or budget edits the draft and requires a new simulation.
Completed results stay fixed. New downloads use format 5 / engine 3.0.0; released
format-4 / engine-2.0.0 percentage files migrate only after exact replay validation.
Their original percentage behavior is preserved. Corrupt or incompatible files
are rejected before replacing the workspace.

Independent tests reconstruct forecast labor and investment objectives, compare
feasible alternatives, verify ties and corners, and check mixed/all-forward
multi-period settlement and unit invariance. The separate
[optimal-growth reference](textbook_foundation.md) remains a reference for its
own named textbook allocation problem. Household lifetime saving, credit and
shocks remain outside this release.
