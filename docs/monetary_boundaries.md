# Monetary transitions with investment and distribution boundaries

The application's solver extends the [positive-distribution monetary regime](monetary_transitions.md)
to dates with zero investment or zero owner distributions. It implements a
specified subset of the [monetary foundation](monetary_foundation.md), not a
general equilibrium solver for every possible cash-retention regime. The
application engine calls `solve_constrained_transition` and accepts only
verified paths. The earlier interior solver remains an independent benchmark.

## Using the solver directly

```python
from econ_agent_sim.monetary_growth import Parameters, solve_constrained_transition

result = solve_constrained_transition(
    Parameters(), initial_capital=0.1, periods=40,
    initial_firm_cash_share=0.5,
)
if result.converged:
    periods = result.periods
else:
    print(result.status)  # Failed results contain no usable period history.
```

At the default structural parameters, initial capital `0.1` and firm cash
share `0.5` produce zero-distribution dates; capital `100` with the same cash
share produces zero-investment dates. Capital `4.44` and cash share `0.05`
produce a first date with both zero investment and zero distributions. These
are numerical regression examples, not a classification of all admissible
initial conditions. The original `solve_transition` remains the strictly
interior benchmark.

The application exposes four structural inputs and two initial conditions,
with fixed symmetry and total money. It solves 100 displayable periods once
before starting an experiment, then reveals that verified path through its
period controls. Unsupported regimes or failed numerical checks do not replace
an existing run. Parameter bounds limit the interactive inputs; they do not
guarantee that every allowed combination is solvable in this regime.

Numerical defaults remain `horizon=64`, `max_horizon=2048`,
`max_iterations=80`, `tolerance=1e-10`, and
`continuation_tolerance=1e-8`. At each horizon the iteration budget applies
separately to the auxiliary initialization and the constrained solve;
`iterations` counts both. Four-variable neighboring time blocks allow a
dependency-free Newton solve with colored finite differences and a damped
line search. Matrix pivots are chosen within each block, not across dates;
a singular local block can cause `numerical_failure` even if the complete
linear system would be invertible using broader pivoting. This is a solver
limitation, not evidence of economic nonexistence.

## Supported regime

Two identical households and two identical firms retain the foundation's
preferences, production, ownership, payment timing and four structural inputs.
Capital, consumption, prices and household closing cash are positive, and
labor is strictly between zero and one. Investment and distributions may be
zero. Positive consumption under symmetry implies investment is below output.

The solver looks for paths on which opening firm funding binds:

```text
F_t = D_t + W_t L_t,
F_(t+1) = p_t c_t = e_t.
```

This is a searched active-constraint regime, not an additional economic rule
requiring firms to exhaust cash. Its funding multiplier is independently
checked for the correct nonnegative sign. A candidate with a negative funding
multiplier is not an equilibrium and must be rejected, not repaired by clipping
that multiplier or its distributions.

The household money equation and transversality argument in the earlier
regime continue to apply under binding funding, even when distributions are
zero. Thus

```text
e_t = e_star = (1-beta) / [2*(1-beta+eta)],
q_t = beta,
p_t = e_star/c_t,
h_(t+1) = 1/2-e_star,
F_(t+1) = e_star.
```

The household labor condition gives `W_t=e_star*chi/(1-L_t)`.
Consequently nonnegative distributions require

```text
L_0 <= F_0 / (F_0 + chi*e_star),
L_t <= 1/(1+chi)                       for t >= 1.
```

Equality corresponds to zero distributions. These caps are consequences of
the household condition, settlement and the searched funding regime. Adding
them to the earlier real planner is not sufficient: a binding distribution
constraint also changes the shadow value of firm cash and the capital
conditions.

## Cash and capital values

Let `b_t` be the marginal supporting value of opening firm cash, and `a_t`
the corresponding value per unit of opening capital, in units of current
owner distributions. Write `MPK_t=alpha*Y_t/K_t` and
`MPL_t=(1-alpha)*Y_t/L_t`. For a general nominal discount factor `q_t`,
the sufficient conditions used below are

```text
b_t >= 1,
mu_t = b_t - q_t*b_(t+1) >= 0,
g_t = q_t*[p_t*b_(t+1) - a_(t+1)] >= 0,

a_t = q_t*[(1-delta)*a_(t+1) + p_t*b_(t+1)*MPK_t],
b_t*W_t = q_t*b_(t+1)*p_t*MPL_t,

D_t*(b_t-1) = 0,
[F_t-D_t-W_t*L_t]*mu_t = 0,
I_t*g_t = 0.
```

The implementation specializes these equations to `q_t=beta` and binding
funding. A positive distribution sets `b_t=1`. At zero distributions, cash
may be more valuable inside the firm, so `b_t` need not equal one. Positive
investment sets `a_(t+1)=p_t*b_(t+1)`; at zero investment, the capital value
may lie below the cash opportunity cost. The capital recursion still applies
at zero investment. Replacing it by an isolated consumption Euler inequality
would incorrectly omit the continuation value of surviving capital.

The funding sign is a substantive additional check. In particular, `q_t<1`
does not imply `mu_t>=0` when cash values vary. On a zero-distribution date,
the labor equation implies

```text
q_t*b_(t+1)/b_t = (F_t/e_star)*(c_t/Y_t)/(1-alpha).
```

Hence nonnegative `mu_t` requires
`(F_t/e_star)*(c_t/Y_t)<=1-alpha`. After date zero, `F_t=e_star`, so
zero distributions require `I_t>=alpha*Y_t`. In this binding-funding regime,
zero distributions and zero investment therefore cannot occur simultaneously
after date zero. This restriction is not a claim about unsupported regimes
with positive unspent opening cash.

## A global bound against firm deviations

Define `S_t(K,F)=a_t*K+b_t*F`. Under the conditions above, for any feasible
one-period deviation from any nonnegative opening capital and cash,

```text
D + q_t*S_(t+1)(K_next,F_next) - S_t(K,F)
  = -(b_t-1)*D
    - mu_t*(F-D-W_t*L)
    - g_t*I
    + q_t*b_(t+1)*p_t*[Y(K,L)-MPK_t*K-MPL_t*L]
  <= 0.
```

The first three terms are nonpositive by feasibility and the multiplier
signs. The last term is nonpositive because the candidate production ratio
provides a global supporting plane for concave, constant-returns production.
The bound covers feasible deviations with zero investment, all output
invested, zero distributions, positive unspent opening cash, zero labor, or
zero productive capital. The candidate itself attains equality through
complementarity and its production ratio.

Let `Q_(0,t)` be the product of the dated nominal discount factors. Summing
the bound yields

```text
sum_(t=0)^T Q_(0,t)*D_t
  + Q_(0,T+1)*S_(T+1)(K_(T+1),F_(T+1)) <= S_0(K_0,F_0).
```

All terminal values are nonnegative, so no feasible payout stream exceeds
the opening bound. If the candidate has vanishing discounted continuation
value, its payouts attain the bound, proving global firm optimality. In the
supported regime, convergence to the positive stationary state with bounded
`a_t,b_t` suffices because `Q_(0,t)=beta^t`.

This is a conditional statement about a complete infinite path. It does not
prove that an arbitrary finite numerical path has such an extension, nor
that the affine bound equals the firm's value at all off-path states. These
valuation coefficients also do not replace replacement-cost book equity.

## Numerical boundary and acceptance

The finite boundary problem uses unknowns `K_(t+1),L_t,b_t,a_t` at each
date. Resources give consumption; the household condition gives wages and
binding funding gives distributions. The four dated equations are the labor
condition, the capital-value recursion and the two complementarity equations

```text
min(I_t/Y_t, 1-a_(t+1)/(p_t*b_(t+1))) = 0,
min(D_t/F_t, b_t-1) = 0.
```

These minima encode both the inequalities and their complementary products;
merely checking the products would permit incorrectly signed solutions.
Economic residual checks reconstruct the conditions independently of the
numerical residual vector, including the funding multiplier omitted from the
four equations because the solver searches the binding regime.

Opening capital is given. At the computational end, cash and capital
supporting values are set to their stationary values, `b_H=1` and
`a_H=a_star`, while ending capital is free. This approximates continuation
near the stationary state; it does not force liquidation or declare that the
stationary gradient is an exact continuation value at an arbitrary state.

Acceptance additionally requires proximity of the ending state and choices
to the stationary allocation, agreement of the requested prefix across two
planning horizons, correct inequality and complementarity signs, and funded,
money-conserving settlement. These are numerical accuracy and continuation
checks, not an exact proof of infinite-horizon convergence, existence or
uniqueness. Failure to find a certified path must not be described as proof
that no equilibrium exists.

Numerically computed investment within the equation tolerance times output
of zero is represented as exactly zero. Distributions within that tolerance
times opening firm cash of zero are represented by the exact active labor
cap and zero distributions; wages, production and consumption are then
reconstructed consistently. These adjustments are limited to residual-sized
quantities, not material constraint violations. All economic equations,
inequalities and settlement checks are rerun on the reported choices, so a
rounding adjustment cannot bypass acceptance. Horizon comparisons scale
investment by output, distributions by opening cash and funding multipliers
by cash value, rather than divide by quantities that may legitimately vanish.

The household concavity argument remains applicable at the recovered prices,
wages and dividends. Its money and labor conditions are checked separately
from firm conditions. A complete path converging to the stated positive
stationary allocation satisfies the household cash transversality condition;
finite horizon agreement supplies evidence for that continuation rather than
an independent exact proof of it.

## Remaining limits

The solver does not yet search regimes with positive unspent opening firm
cash, asymmetric agents, borrowing, owner cash injections, zero productive
initial states, shocks or adaptive expectations. Perfect foresight and
stationary-tail continuation remain explicit assumptions. The earlier
interior solver remains available as an independent regression benchmark.
The Streamlit application uses the constrained solver with these same limits;
integration does not establish global existence or uniqueness or implement a
decentralized price-adjustment process.

Run `pytest -q tests/test_monetary_boundaries.py tests/test_monetary_numerics.py`
and `python docs/monetary_transition_check.py` to reproduce the checks. The
report retains the old interior examples alongside constrained results. For
capital `0.1` and initial firm cash share `0.99`, the constrained candidate
has a negative funding multiplier and is explicitly rejected as
`unsupported_cash_retention`; more opening cash must not silently force an
economically unjustified spending pattern.
