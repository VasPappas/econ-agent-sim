# Numerical growth transitions

The isolated reference in `src/econ_agent_sim/textbook_growth.py` now solves
partial depreciation with endogenous work and leisure. It implements the real
allocation problem specified in [Step 1](minimal_reference_economy.md). It is a
verification tool for the project; the current monetary app is unchanged.

The named foundation is the
[Cass–Koopmans allocation problem](https://python.quantecon.org/cass_koopmans_1.html),
with the explicitly stated log-leisure extension. This implementation uses a
boundary-value method rather than the cited lecture's shooting implementation.
The separate [monetary specification](monetary_foundation.md) now has a
[first-regime transition solver](monetary_transitions.md). Its constrained
monetary equilibrium is not interchangeable with this frictionless reference.

## Use

```python
from econ_agent_sim.textbook_growth import TransitionParameters, solve_transition

parameters = TransitionParameters(
    beta=0.95, depreciation=0.10, leisure_weight=1.0,
)
result = solve_transition(parameters, initial_capital=1.0, periods=40)
if not result.converged:
    raise RuntimeError(result.status)
for period in result.periods:
    print(period.number, period.consumption, period.labor, period.next_capital)
```

The three main inputs are patience, depreciation and leisure preference, with
initial capital separate. Productivity and the production exponent remain
available for reference checks; defaults are `A=1`, `alpha=0.5`.
Gross investment can be negative because this reference permits consuming
surviving capital. The cash-funded app's irreversible investment is a different
constraint.

The older `Parameters`, `solve_growth`, `exact_solution` and `rollout` APIs remain
the fixed-labor/full-depreciation reference. They explicitly reject
`TransitionParameters` to prevent silently ignoring depreciation or leisure.
`steady_state(TransitionParameters(...))` returns the analytical stationary
capital, labor, output, consumption, replacement investment and real wage.

## Numerical method

1. For a trial horizon `H`, fix inherited capital `K_0` and distant capital
   `K_H=K_star`, the analytical stationary capital. Positive consumption and
   interior labor are required in every period.
2. At each pair `(K_t,K_(t+1))`, solve the static work/leisure choice.
   With `alpha=0.5` this is a quadratic in `sqrt(labor)`;
   other exponents use a sign bracket around the unique interior root.
3. Solve all interior capital Euler conditions jointly. The Hessian of the
   labor-optimized period utility is obtained by eliminating labor from the
   joint Hessian. Neighboring periods create a tridiagonal Newton system.
4. Update positive capital in logarithms. Backtracking preserves feasibility
   and decreases the residual using fixed row scales within each line search.
5. Double the horizon and solve again. Compare the requested prefix, economic
   residuals and tail proximity to the stationary allocation before accepting.

A fixed saving rule at stationary labor initializes the solve; it is not the
partial-depreciation policy. In the full-depreciation special case that starting
guess coincides with the exact policy, which must still pass the independently
reconstructed optimality and continuation checks.

The default starting horizon is `max(64, periods+16)`, followed by doubling up
to 2048 periods. The default Newton budget is 80 updates per attempted horizon.
These are numerical controls, not household planning horizons or economic
parameters. The displayed run never imposes capital liquidation at its end.
The solver uses only the Python standard library.

## What acceptance establishes

A successful result requires two solved horizons, with:

- Interior Euler, labor and resource residuals meeting `tolerance` (default
  `1e-10`). Diagnostics are relative, including for small positive quantities.
- The displayed capital, next capital, consumption, labor and leisure agreeing
  across the two horizons within `continuation_tolerance` (default `1e-8`).
- Final-period capital, consumption, labor and leisure close to their stationary
  values, and the Euler condition linking that period to a stationary next
  period within `continuation_tolerance`.

`horizon` reports the accepted longer horizon; `comparison_horizon` reports its
shorter comparison. `max_euler_residual` includes the terminal Euler condition,
so it can exceed the stricter interior `tolerance` on a successful result.
`terminal_gap` is the maximum of the relative tail distances and terminal Euler
error. `prefix_difference` records the largest relative difference in the
displayed choices. Other residual diagnostics cover the complete solved horizon,
not only the displayed prefix.

These checks provide evidence that the displayed transition is insensitive to
the tested continuation horizon. They are not a rigorous global
infinite-horizon error bound. Fixing distant capital is an approximation whose
effect must be checked; first-order conditions alone do not establish the
transversality condition for an arbitrary infinite extension.

Invalid inputs raise `ValueError`. Exhausted numerical budgets, a failed line
search, or an unrepresentable calculation return `converged=False`, a status and
an empty period tuple. No partially solved history is released as usable output.
Some failure diagnostics can be `None`. The standalone analytical `steady_state`
helper raises `ArithmeticError` if its allocation is outside floating-point
range; the transition solver catches that and returns a failed result.

Extreme patience, parameter ratios or initial capital can require more than the
declared budget or exceed numerical precision. Algebraically admissible inputs
are not a promise that this solver will certify a path. No monetary or
self-regulation claim follows from a successful real-reference calculation.

## Independent checks

`tests/test_growth_transition.py` reconstructs the resource constraint, household
labor condition, capital Euler condition and competitive factor payments. It
compares full-depreciation paths with the analytical saving and labor policies,
partial-depreciation stationary allocations with independent formulas, and
transitions from above and below the stationary stock. It also checks genuine
disinvestment, independence from the displayed length and starting horizon, and
explicit numerical-budget failure.

Run the checks and the reproducible report with:

```bash
pytest -q tests/test_textbook_growth.py tests/test_growth_transition.py
python docs/textbook_benchmark.py
```

The report retains the original affine-log benchmark diagnostics and adds
partial-depreciation transitions, the exact labor-choice special case and an
intentionally insufficient horizon budget. It does not run or alter Streamlit.
