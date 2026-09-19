# Symmetric monetary transitions: the first supported regime

This executable reference implements the model specified in
[the monetary foundation](monetary_foundation.md) in one deliberately limited
regime: every firm has a positive owner distribution and strictly interior
investment in every period. It does not change the application engine or solve
all possible constrained monetary equilibria.

There are two identical households and two identical capital-owning firms. Each
household owns half of each firm. Production is `Y=K^alpha L^(1-alpha)` with
`alpha=0.5`; productivity and total money are normalized to one. Preferences are
`log(c)+chi log(1-l)+eta log(h_next/p)`, discounted by `beta`. The structural
inputs remain `beta`, positive depreciation `delta`, `chi` and `eta`; initial
conditions are capital per firm and firms' share of total money. No extra
investment propensity, interest rate, payout rule or liquidity target is added.

The theoretical ingredients are textbook, but their combination and payment
timing are this project's explicit extension. The
[Cass–Koopmans growth model](https://python.quantecon.org/cass_koopmans_1.html)
provides capital accumulation and intertemporal consumption choice;
[money-in-utility notes](https://lhendricks.org/econ720/ih2/miu_sl.pdf) explain
liquidity services; and
[consumption-based valuation](https://python.quantecon.org/markov_asset.html)
provides owners' discounting of future payments. None of these sources alone
implies the prepaid-wage and no-external-finance restrictions used here.

## 1. The regime and its consequences

Use per-household/per-firm quantities, which coincide under symmetry. Write
`e_t=p_t*c_t` for nominal consumption spending. The supported regime requires:

```text
D_t > 0,  L_t > 0,  0 < I_t < Y_t,  0 < l_t < 1.
```

Where the firm's value function is differentiable, a positive distribution
implies that the marginal value of opening firm cash is one. With
`q_t=beta*lambda_(t+1)/lambda_t` and household marginal income value
`lambda_t=1/e_t`, the household money condition gives

```text
q_t = 1 - eta*e_t/h_(t+1) < 1.
```

The firm's funding multiplier is therefore `mu_t=1-q_t>0`. Opening cash is fully
used for distributions and wages:

```text
F_t = D_t + W_t*L_t.
F_(t+1) = p_t*(Y_t-I_t) = e_t.
h_(t+1) = 1/2 - e_t.
```

These are implications of the specified optimum and market clearing in this
regime, not additional rules imposing a cash target or dividend fraction.
The global bound below verifies firm optimality without relying solely on
differentiability or local first-order conditions.

## 2. Money spending is determined, not guessed

Substitution in the household money Euler equation gives

```text
1/e_t = eta/(1/2-e_t) + beta/e_(t+1),

e_(t+1) = beta*e_t*(1/2-e_t) / [1/2-(1+eta)*e_t].
```

Positive future spending requires `0<e_t<1/[2*(1+eta)]`. The unique positive
fixed point is

```text
e_star = (1-beta) / [2*(1-beta+eta)].
```

There are two reasons not to choose another initial value:

- Above `e_star`, the spending map has a growth factor greater than one, which
  rises with spending. Iteration eventually violates the admissible upper bound.
- Below `e_star`, spending decreases and household cash stays above
  `1/2-e_0`. Iterating the money Euler equation yields
  `beta^N*lambda_N = lambda_0 - sum_(j=0)^(N-1) beta^j*eta/h_(j+1)`.
  The right side is bounded below by
  `1/e_0-eta/[(1-beta)*(1/2-e_0)]>0`. Discounted marginal-value-weighted
  household cash therefore cannot vanish, violating the household
  transversality condition.

Thus an infinite feasible equilibrium satisfying that condition in this regime
has `e_t=e_star`, constant `lambda_t=1/e_star`, and `q_t=beta`. From period one
onwards, firm cash equals `e_star` and household cash equals `1/2-e_star`.
Initial cash may differ: the first funded distribution and purchases adjust it.

## 3. Solve the real allocation with the correct labor wedge

Let `MPK_t=alpha*Y_t/K_t`, `MPL_t=(1-alpha)*Y_t/L_t`, and
`R_t=1-delta+MPK_t`. Firm labor choice and household labor choice imply

```text
W_t/p_t = beta*MPL_t,
chi*c_t/(1-l_t) = beta*MPL_t.
```

For interior investment, the firm's capital condition is
`p_(t-1)=beta*p_t*R_t` for `t>=1`. Since `p_t=e_star/c_t`, it becomes

```text
c_t/c_(t-1) = beta*(1-delta+MPK_t),
c_t + K_(t+1) = Y_t + (1-delta)*K_t.
```

The resource equation, consumption Euler equation and labor equation are
exactly those of the existing real transition solver with auxiliary leisure
weight `chi_effective=chi/beta`. This permits reuse of its numerical method.

This is an **auxiliary numerical representation**, not a claim that the
monetary equilibrium maximizes a planner's welfare function with that weight.
Actual household preferences still use `chi` and `eta`; firms still own
capital, and households still hold fixed shares. In particular, replacing
money balances by an aggregate price identity inside household utility and then
optimizing that substituted expression would wrongly make a price-taking
household internalize the effect of its decisions on the equilibrium price.

The real solver allows reversible capital. Its candidate can be used here only
if the entire monetary path satisfies irreversible investment and funded
positive distributions. Rejected choices must not be clipped into feasibility.

## 4. Recover prices, distributions and settlement

For each accepted real allocation, recover

```text
p_t = e_star/c_t,
W_t = p_t*beta*MPL_t,
I_t = K_(t+1)-(1-delta)*K_t,
D_t = F_t-W_t*L_t.
```

Initially `F_0=s_F/2` and `h_0=(1-s_F)/2`; later `F_t=e_star` and
`h_t=1/2-e_star`. The initial distribution must pass its own funding screen.
For later periods, positive distributions and investment equivalently require

```text
beta*(1-alpha) < c_t/Y_t < 1.
```

The initial additional requirement is
`s_F/2 > beta*e_star*(1-alpha)*Y_0/c_0`. The upper investment bound follows
from strictly positive consumption, but is still checked explicitly.

Settlement executes the specified ordering, not just the net budget identity:

1. Pay distributions from opening firm cash.
2. Pay wages from the remaining firm cash; match the delivered labor.
3. Produce, retain investment, and sell consumption output to households.
4. Carry remaining cash and updated capital into the next period.

Firm cash is zero immediately after payroll and is replenished by sales.
Household cash stays nonnegative during funded purchases. Two copies of the
per-entity settlement conserve the normalized money stock at each stage.
No sales forecast is used as opening cash, and there is no intraperiod loan.

Within this regime, `eta` changes the money split and price level, not the real
allocation conditional on acceptance. The initial cash split affects the first
distribution and its feasibility. These are conditional results of symmetry,
log preferences and this active-constraint regime, not general neutrality
claims for the model's unresolved corner regimes.

## 5. A global firm deviation bound

Define a dated capital valuation coefficient and an affine upper bound:

```text
a_t = beta*p_t*(1-delta+MPK_t),
S_t(K,F) = F+a_t*K.
```

The capital Euler equation implies `a_t=p_(t-1)` for `t>=1`, or equivalently
`a_(t+1)=p_t`. At date zero, use the displayed formula for `a_0`: there is no
observed historical price that can be silently substituted for it.

For any feasible one-period firm deviation `(D,L,I)` from arbitrary
nonnegative opening state `(K,F)`, evaluated at the candidate price path,

```text
D + beta*S_(t+1)(K_next,F_next) - S_t(K,F)
  = -(1-beta)*(F-D-W_t*L)
    + beta*p_t*[Y(K,L)-MPK_t*K-MPL_t*L]
  <= 0.
```

Opening funding makes the first term nonpositive. Concavity and constant
returns of the production function make the second nonpositive: its tangent
plane at the candidate capital/labor ratio is a global supporting plane.
Investment cancels algebraically. Therefore the inequality also covers
deviations at zero investment, full-output investment, zero distributions,
zero work, and zero productive capital, whenever those choices are feasible.

Discounting and summing gives

```text
sum_(t=0)^T beta^t*D_t + beta^(T+1)*S_(T+1) <= S_0.
```

Since the terminal bound is nonnegative, no feasible payout stream exceeds
`S_0`. The candidate binds funding and uses the supporting-plane production
ratio, so it attains equality each period. Convergence to positive stationary
capital, consumption and prices implies
`beta^(T+1)*S_(T+1)->0`; hence the candidate attains the upper bound on actual
discounted distributions. This establishes global optimality along the
candidate path, not merely local stationarity. It does not assert that the
firm value equals `S_t` at every off-path state.

`S_t` is a fundamental-value bound, not replacement-cost book equity
`F+p_t*K`. The two capital price coefficients generally differ on transitions.

## 6. Household sufficiency and terminal conditions

Given the candidate prices, wages and dividends, household utility is concave
and the budget set is convex. For any feasible alternative with the same
opening household cash, concavity and the candidate's labor and money
conditions bound its period utility gain by

```text
utility_alt_t - utility_t
  <= lambda_t*(h_alt_t-h_t)
     - beta*lambda_(t+1)*(h_alt_(t+1)-h_(t+1)).
```

The discounted sum telescopes. Alternative terminal cash is nonnegative, and
the candidate's constant marginal income value and bounded cash give
`beta^T*lambda_T*h_(T+1)->0`. Thus no feasible household deviation improves
its discounted utility. This argument treats firm payouts and prices as given,
as required for a price-taking household with fixed ownership.

For firms, the terminal condition concerns their discounted continuation value,
not household cash. The convergent real reference and its positive stationary
tail supply the limiting condition used in the firm bound above. Neither
agent is instructed to liquidate assets at the end of the displayed run.

## 7. Numerical acceptance, failure and scope

The implementation exposes `Parameters`, `steady_state`, `solve_transition`,
`settle_period`, and `firm_deviation_gap`. The transition routine uses the real
solver's horizon, iteration and tolerance controls. Its result reports whether
it converged and provides an explicit status when it does not; unsuccessful
solutions do not provide a history to execute as an accepted equilibrium.

```python
from econ_agent_sim.monetary_growth import Parameters, solve_transition

parameters = Parameters(
    beta=0.95, depreciation=0.10, leisure_weight=1.0, money_weight=0.05,
)
result = solve_transition(
    parameters, initial_capital=1.0, periods=40,
    initial_firm_cash_share=0.50,
)
if not result.converged:
    raise RuntimeError(f"{result.status}; period={result.failure_period}")
for period in result.periods:
    print(period.number, period.consumption, period.investment, period.distribution)
```

The default controls are `horizon=64`, `max_horizon=2048`,
`max_iterations=80`, `tolerance=1e-10`, and
`continuation_tolerance=1e-8`. They are numerical controls, not extra economic
parameters. `residuals` reports named economic diagnostics;
`max_equation_residual`, `prefix_difference`, `terminal_gap`, `horizon`, and
`comparison_horizon` expose the acceptance evidence. `failure_period` uses
one-based numbering when a particular period violates the supported regime.

The numerical construction solves toward the auxiliary model's stationary
allocation, repeats with a longer horizon, and compares the requested prefix.
See [the real transition method](growth_transition.md) for the boundary-value
algorithm and its continuation checks. The monetary audit must cover the
**full computational path**, not only the periods requested for display, and
check the stationary continuation as well. Relevant checks include:

- Strict investment and distribution regime conditions, including initial
  distribution funding.
- Household and firm cash budgets, capital accumulation and goods/labor/money
  clearing.
- Household money and labor conditions, firm labor/capital conditions and
  funding complementarity.
- The chronological settlement cycle and nonnegative intermediate cash.
- Horizon agreement, approach to the stationary continuation, and the
  coefficient relationships used by the firm deviation bound.

These are finite-precision residual and continuation checks. They are not a
rigorous global bound on the error between a finite numerical path and an
infinite-horizon equilibrium. The exact optimality proofs above apply when
their equations and limiting conditions hold exactly; their numerical
implementation reports an approximation within disclosed tolerances.

An investment or distribution boundary means **this solver's regime is not
supported for that candidate**. It does not establish nonexistence of a
monetary equilibrium. A different solution may involve zero distributions,
binding investment constraints, extra cash retention or different transition
prices; those active-constraint cases need a separate constrained solver.
Numerical budget or convergence failures likewise must not be interpreted as
economic nonexistence.

The regime screen runs on each equation-converged finite-horizon candidate,
before requiring agreement with a longer horizon. Near a constraint boundary,
that candidate can be rejected even if a longer starting horizon would produce
an admissible path. Such rejection is not a proof that the exact infinite path
leaves this regime. The statuses `unsupported_nonpositive_distribution` and
`unsupported_investment_boundary` describe the candidate that failed the
screen, not a complete classification of all equilibria for those inputs.

Within the everywhere-interior, positive-distribution regime, the money
argument fixes spending, and the strictly concave auxiliary growth problem
fixes the real allocation, when its infinite-horizon optimum meets the regime
requirements. This supplies at most one allocation in that regime for given
inputs. It does not rule out equilibria in other regimes or establish global
uniqueness for the entire monetary economy.

Finally, perfect foresight remains an assumption. This is not a model of
decentralized price discovery, learning or observed market self-regulation.
Heterogeneity, finance, inventories and shocks are not introduced by this
milestone. Application integration remains a separate step after verification.

## Reproduce the checks

```bash
pytest -q tests/test_monetary_growth.py
python docs/monetary_transition_check.py
```

The tests independently reconstruct household and firm conditions, the
stationary fixture, the exact full-depreciation policy and the supporting-plane
inequality. Settlement tests cover all four agents, invalid closing balances
and unfunded transfers. A failure beyond the displayed period must reject the
whole candidate, and changing the displayed length must not change accepted
early choices.

The report includes accepted transitions from initial capital 1 and 10 under
default parameters, the stationary case, a changed money preference and explicit
failures. Capital 20 requires negative investment in the auxiliary candidate;
capital 0.5 with a 95% initial firm cash share reaches a later payout boundary;
a 5% initial firm share cannot fund the stationary allocation's opening payroll.
These are reproducible examples, not a complete characterization of the
supported initial-state domain. An insufficient horizon is reported separately
from an unsupported economic regime.
