# Textbook foundations for investment and saving

Status: the optimal-growth reference remains separate from the app. The
[forward-looking firm policy](forward_investment.md) now implements a conditional
neoclassical user-cost criterion with explicit financing and forecast assumptions.
The previous three-period/runoff investment proposal remains deferred.

The reference now also includes [partial-depreciation transitions with work and
leisure](growth_transition.md), alongside the exact fixed-labor special case
below. This numerical reference implements the [minimal real model](minimal_reference_economy.md);
the [monetary transition implementation](monetary_transitions.md) separately
supports positive distributions and interior investment, not all boundary cases.

## Modeling requirement

Start each new behavioral mechanism from a named model with a source, an
objective, constraints, timing and an equilibrium concept. Reproduce a known
special case before adding project-specific assumptions. Identify those additions
explicitly and test their consequences separately. A familiar production function
or numerical optimization method alone does not make the whole economy a textbook
model.

## Which models address which questions?

| Question | Foundation | Role in Tiny Economy |
| --- | --- | --- |
| How much should a firm invest? | Neoclassical investment; user cost and marginal q | Starting point for the next firm specification; financing and payout assumptions must be explicit. |
| How do consumption and capital accumulation fit together? | Deterministic optimal growth / Ramsey–Cass–Koopmans | A common reference for investment and future household saving. |
| How can we verify the dynamic calculations? | Log utility, Cobb–Douglas production, full-depreciation special case | An isolated benchmark with a closed-form solution and independently checked numerical iteration. |

Carroll's [q-model lecture](https://www.econ2.jhu.edu/people/ccarroll/public/LectureNotes/Investment/qModel/)
derives firm investment from discounted profits, capital accumulation and
adjustment costs under efficient capital markets. It connects the marginal value
of installed capital with the cost of investing. Its financing assumptions cannot
be silently imported into our cash-limited firms.

QuantEcon's [Cass–Koopmans planning problem](https://python.quantecon.org/cass_koopmans_1.html)
describes the consumption/capital allocation problem. Its
[competitive version](https://python.quantecon.org/cass_koopmans_2.html) specifies
households owning capital and renting it to firms. Tiny Economy currently has
firms holding capital and households owning shares, so adopting that particular
decentralization would require a deliberate architectural change.

## Implemented reference problem

The benchmark in `src/econ_agent_sim/textbook_growth.py` uses fixed labor,
constant productivity, one consumption/investment good and an infinite horizon:

```text
maximize sum from t=0 to infinity of beta^t * log(C_t)
subject to:
    Y_t = A * K_t^alpha
    C_t + K_(t+1) = Y_t
    C_t > 0, K_(t+1) > 0
given K_0 > 0, A > 0, 0 < alpha < 1, 0 < beta < 1
```

Capital fully depreciates each period (`delta=1`), so investment equals next
period's capital. This restrictive special case is chosen for verification, not
as a proposed depreciation setting for the app. Labor/leisure choices, money,
borrowing, dividends, adjustment costs and shocks are absent. The discount factor
measures patience; it is not an interest payment on money.

The source is QuantEcon's
[log/Cobb–Douglas example](https://python.quantecon.org/os_stochastic.html#an-example),
which cites Ljungqvist and Sargent, *Recursive Macroeconomic Theory*, section
3.1.2. We take its deterministic special case: constant productivity, no random
draws. That lecture uses available output as the state; our code uses opening
capital, with output `Y=A*K^alpha`.

Our corresponding solution is:

```text
s = alpha * beta
investment = K_next = s * Y
consumption = (1-s) * Y
V(K) = a + b * log(K)
b = alpha / (1-s)
a = [log(1-s) + log(A) + beta*b*(log(s) + log(A))] / (1-beta)
```

The constant investment share here follows from this particular optimization
problem. It does not validate the app's existing fixed-percentage investment
rule, which operates with different objectives and constraints.

## Numerical method and checks

Bellman iteration starts from a zero continuation value and updates the two
coefficients of `a+b*log(K)`. This functional form is preserved exactly by the
Bellman operator for this special case. The implementation uses that property;
it is not a general-purpose solver for other preferences or production functions.
The iteration itself never calls the closed-form solution.

The returned policy is greedy for the final coefficients. Iteration-budget
exhaustion is explicit, and rollout rejects an unconverged numerical solution.
The analytical formula is provided separately as a comparison. Both calculations
use ordinary floating-point arithmetic.

Independent tests check the value against a long discounted-consumption sum;
the optimal choice against feasible alternatives and its first-order condition;
and paths against resource conservation, capital timing, the Euler equation and
the steady state. They also check invalid inputs, mismatched parameters and
iteration-budget failure.

Run the reproducible comparison with:

```bash
python docs/textbook_benchmark.py
pytest -q tests/test_textbook_growth.py
```

The report gives the stopping residual **and** errors against the analytical
coefficients and policy. A small coefficient residual is not a bound on value
error over every positive capital stock. In particular, as `beta` approaches one,
value levels become poorly conditioned and iteration may be very slow. Even a
reported converged result can have appreciable coefficient error. Analytical
evaluation also incurs floating-point rounding. These diagnostics must remain
visible when this reference is used for further numerical work.

## Mapping textbooks to the firm extension

The implemented firm policy uses the standard capital law
`K_next=(1-delta)*K+I` and the textbook desired-capital/user-cost criterion.
Financing, timing and forecasts are specified in the new firm guide. It does not
claim to solve lifetime owner-value maximization with the app's payout constraints.

There is a concrete complication in the current technology. At fixed real wage
`u`, unconstrained hiring with `Q=A*sqrt(K*L)` gives:

```text
L = A^2*K / (4*u^2)
Q - u*L = A^2*K / (4*u)
```

Optimized operating surplus is linear in capital. We cannot claim a finite,
interior desired capital stock merely by attaching a discount factor to that
unconstrained fixed-price problem. The equilibrium price response or an explicitly
motivated constraint/cost must address scale. Quietly replacing that technology
with decreasing returns in capital would change the model.

The following features require explicit treatment in any further integration:

| Existing feature | Required treatment |
| --- | --- |
| Firms own productive capital | Use a capital-owning firm model or justify changing ownership and rental flows. |
| Payroll must be funded before sales | Identify the financing friction and compare it with the unconstrained benchmark. |
| Investment retains the firm's own output | Account for forgone sale revenue and next-period productive capacity. |
| Dividends are capped by profit and protected cash | Reassess the payout constraint; it is not implied by standard firm-value maximization. |
| Households currently value consumption, leisure and money within one period | Specify intertemporal preferences and asset opportunities for the saving milestone. |
| Households have different preferences | Explain how owners value firm payouts; do not identify an arbitrary common firm discount factor with household welfare. |

The earlier three-period forecast and runoff continuation remain documented in
`investment_design.md` for traceability. They are not prerequisites of textbook
investment and are not being implemented as the default foundation.

## Boundary of this change

This reference validates one textbook allocation problem. It does not solve
the two-firm monetary equilibrium or establish household welfare comparisons.
The user-cost policy is a separate extension with its own independent tests and
market integration. Household intertemporal saving still requires an explicit
ownership/valuation specification. Exogenous shocks remain postponed.
