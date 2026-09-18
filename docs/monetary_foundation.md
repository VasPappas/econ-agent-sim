# Step 2 — Saving, investment and funded owner payouts

Status: proposed economic specification, following
[Step 1](minimal_reference_economy.md). The running model in `model.md` is
unchanged. This document specifies a joint replacement for its household saving,
conditional investment and prescribed dividend rules; it is not a patch that
removes individual safeguards from the existing solver.

## Decision and textbook basis

Use infinite-horizon household preferences with consumption, leisure and real
money balances. Keep firms owning their capital and households owning fixed
equal shares. Firms choose investment, cash retention and owner distributions
together, using the same valuation of future income as their household owners.

The theoretical ingredients are:

- [Money in utility](https://lhendricks.org/econ720/ih2/miu_sl.pdf): the
  Sidrauski-type approach gives liquid balances a service value in household
  preferences. Our discrete timing and corporate funding constraints are
  explicit extensions of that family.
- [Consumption-based discounting](https://python.quantecon.org/markov_asset.html):
  future income is valued using household marginal utility. We use its
  deterministic, nominal counterpart; shares need not trade for identical owners
  to assign that common marginal value.
- [Dynamic firm valuation](https://www.econ2.jhu.edu/people/ccarroll/public/LectureNotes/Investment/qModel/):
  investment follows from the present value of owner payouts subject to capital
  accumulation. We specify cash constraints instead of importing frictionless
  financing or a fixed interest rate from that model.

This is a specified monetary growth model with financing restrictions. It is not
an unmodified Sidrauski or frictionless Ramsey model. The additional restrictions
are prepaid wages, internally retained output as investment, irreversible capital,
fixed ownership and no external finance. Their consequences must be visible.

## Scope and inputs

Start with two identical households and two identical price-taking firms. Each
household owns half of each firm. There are no share trades, owner capital
injections, loans, interfirm funding, capital resale, inventories or shocks.
Identical preferences, initial household cash and ownership ensure that the
owners agree on discounting along the symmetric equilibrium.

| Input | Role | Illustrative value |
| --- | --- | ---: |
| `beta`, between zero and one | Household patience | 0.95 |
| `delta`, positive and at most one | Capital depreciation per period | 0.10 |
| `chi > 0` | Leisure preference relative to consumption | 1.00 |
| `eta > 0` | Service value of liquid money relative to consumption | 0.05 |
| `k_0 > 0` | Initial capital per firm / per household | Specified for each experiment |
| `s_F`, strictly between zero and one | Firms' share of initial total cash | 0.50 |

These are four preference/technology parameters and two initial conditions.
Each firm initially has `F_0=s_F*Mbar/2`; each household has
`h_0=(1-s_F)*Mbar/2`. Normalize the fixed total money stock `Mbar=1` and common
productivity `A=1`; keep the production exponent `alpha=0.5` fixed. Log utility,
symmetry, payment timing and the financial restrictions are additional disclosed
assumptions. The values are illustrative, with no calendar-frequency calibration.

The first numerical baseline uses positive depreciation. Zero depreciation
requires separate treatment: irreversible capital can support overcapitalized
stationary states, so the interior capital condition below need not identify
every stationary allocation. Heterogeneous owners also require a separate
valuation decision; a common discount factor cannot simply be assumed for them.

## Household budget and saving

Let `p_t` be the money price of X and `W_t` the money wage. Household `i` opens
with cash `h_it`, supplies work `l_it`, consumes `c_it`, and closes with
`h_i,t+1`. Firm `j` pays an opening owner distribution `D_jt`.

```text
maximize sum beta^t [log(c_it) + chi log(1-l_it)
                     + eta log(h_i,t+1 / p_t)]

h_i,t+1 = h_it + W_t l_it + sum_j 0.5 D_jt - p_t c_it
c_it > 0, h_i,t+1 > 0, 0 <= l_it < 1
```

Money services come from balances remaining after purchases, valued at current
goods prices. The household also values those balances for their future uses.
Dividends and wages are available before purchases. Household claims on firms'
book equity are not spendable cash or collateral in this budget.

At an interior choice, define the current marginal value of nominal income as
`lambda_it=1/(p_t*c_it)`. Necessary conditions include:

```text
lambda_it = eta/h_i,t+1 + beta lambda_i,t+1
chi/(1-l_it) = W_t/(p_t c_it)             when l_it > 0
lim as T -> infinity beta^T lambda_iT h_i,T+1 = 0
```

At zero work, the corresponding one-sided labor inequality applies. The money
condition now includes a continuation value; it is no longer the current app's
one-period consumption/money split.

Household cash saving is the change in its money balance. Retained firm earnings
and investment affect its ownership claim and future payouts separately. Fixed
shares do not create a channel for households to lend their cash to firms.

## Owner valuation and the firm's decision

Symmetric households share `lambda_t`. Define:

```text
q_t = beta lambda_(t+1)/lambda_t
    = beta p_t c_t / (p_(t+1) c_(t+1))
Q_(t,s) = beta^(s-t) lambda_s/lambda_t,  Q_(t,t)=1
```

These are shadow discount factors for nominal owner income, not paid interest
rates or observed stock-market prices. Price-taking firms take the equilibrium
price and owner-valuation paths as given. Fixed shares are compatible with this
objective because identical owners attach the same weights to dated payouts.
That agreement does not extend automatically to heterogeneous owners with
restricted asset trading; see the
[shareholder-unanimity literature](https://www.kier.kyoto-u.ac.jp/wp/wp-content/uploads/2025/03/DP1112.pdf).

Firm `j` opens with capital `K_jt` and cash `F_jt`. It chooses labor `L_jt`,
investment `I_jt` and distribution `D_jt` to maximize
`sum from s=t to infinity Q_(t,s) D_js`, subject to:

```text
Y_jt = A K_jt^alpha L_jt^(1-alpha)
D_jt >= 0, L_jt >= 0, 0 <= I_jt <= Y_jt
D_jt + W_t L_jt <= F_jt

K_j,t+1 = (1-delta) K_jt + I_jt
F_j,t+1 = F_jt - D_jt - W_t L_jt + p_t (Y_jt-I_jt)
```

Payroll and distributions must be funded before sales. Investment retains actual
output, forgoing its sale proceeds. Future cash and capital both enter the next
decision. No hypothetical sale or forecast generates cash.

Equivalently, fundamental firm value satisfies
`V_jt(K,F)=max [D+q_t V_j,t+1(K_next,F_next)]`. Define it by actual discounted
distributions with finite value and vanishing discounted continuation value
along the optimum. A Bellman equation alone is not permission to attach an
arbitrary terminal asset value. A finite screen or numerical horizon must not
silently force liquidation at its end.

`D` is an owner distribution, which may include accumulated funds rather than
only current or previous accounting earnings. The previous-profit cap and the
permanent reserve equal to initial cash are replaced by optimization subject to
these budgets. There is no separate hurdle-rate or surplus-investment-fraction
input. Cash needed for future operation is valuable through the continuation
problem, rather than through a preset reserve fraction.

For verification, let `mu_t >= 0` be the multiplier on opening funding and let
`v_F`, `v_K` be derivatives of next period's value. Where derivatives exist:

```text
mu_t [F-D-W_t L] = 0
q_t v_F + mu_t - 1 >= 0
D [q_t v_F + mu_t - 1] = 0

v_K = p_t v_F                       for 0 < I < Y
q_t v_F (p_t Y_L-W_t) = mu_t W_t   for L > 0 and I < Y
```

Boundaries need the full constrained problem, not these interior equalities.
Zero firm cash or zero capital prevents productive recovery without external
finance or capital purchases. Remaining capital may still depreciate, and a
firm with no capital may distribute remaining cash; its entire state need not
stay unchanged. Such choices must be represented when solving the firm's
problem; the old engine's strict-positive-production checks cannot be inherited
as economic assumptions. The initial symmetric baseline requires positive cash
and capital for both firms.

## Equilibrium and funded settlement

A deterministic perfect-foresight equilibrium consists of a complete path of
prices, wages, household choices, firm choices and owner valuations such that
both optimization problems hold, forecasts match that path, and:

```text
sum_i l_it = sum_j L_jt
sum_i c_it + sum_j I_jt = sum_j Y_jt
sum_i h_it + sum_j F_jt = Mbar
```

This is a stronger requirement than solving unrelated one-period equilibria.
It assumes accurate foresight; it does not yet model learning or price discovery.
Neither uniqueness nor convergence from arbitrary initial resources is asserted.
Multiple certified paths must be reported and any selection rule specified;
the old nearest-price convention is not silently carried over.

Plan the path before executing accepted transactions. In each period:

1. Carry opening money and capital; pay each firm's funded owner distributions.
2. Pay wages from the remaining firm cash and deliver the matched labor services.
3. Produce X; retain chosen investment; sell the remaining output to households.
4. Consume household purchases, depreciate opening capital and carry closing states.

The opening firm inequality funds steps 1–2. The household budget with positive
closing cash funds its subsequent purchases. No hidden intraperiod loan is
required. Summing cash budgets gives:

```text
change in total money = p_t [sum_j Y_jt - sum_j I_jt - sum_i c_it] = 0
```

Retain replacement-cost book equity `F+pK` and the existing separation of
operating profit, distributions and holding gains. Fundamental owner value is a
separate valuation concept and generally differs from book equity. Consolidation
must continue eliminating ownership claims against firms, avoiding double counts.

## A verified positive stationary equilibrium

At a symmetric stationary allocation with positive distributions and interior
investment, the equations imply:

```text
q=beta, V_F=1, mu=1-beta
F=D+WL=pc
1=beta(1-delta+Y_K)
W/p=beta Y_L
h=eta p c/(1-beta)
```

The wage is below the marginal product by the factor `beta`. Paying workers
before sales uses funds that owners could otherwise receive immediately, while
the proceeds become available for owner distributions the following period.
That timing has a real economic cost in this model.

Write `x=K/L`, `a=1/beta-1+delta`, and `g=A*x^alpha-delta*x`. Then:

```text
x=(alpha*A/a)^(1/(1-alpha))
b=(1-alpha)*A*x^alpha
w=beta*b
L=w/(w+chi*g), K=x*L, Y=A*K^alpha*L^(1-alpha)
I=delta*K, c=Y-I
F=Mbar*(1-beta)/(2*(1-beta+eta))
h=Mbar*eta/(2*(1-beta+eta))
p=F/c, W=p*w, D=F-W*L
```

At the illustrative parameters above, each matching household/firm has:

| Quantity | Value |
| --- | ---: |
| Firm capital | 4.442472602917 |
| Household work / firm labor | 0.413974455297 |
| Output | 1.356123215627 |
| Gross investment | 0.444247260292 |
| Consumption | 0.911875955336 |
| Household cash | 0.250000000000 |
| Firm opening and closing cash | 0.250000000000 |
| Goods price | 0.274160096598 |
| Money wage | 0.426602564103 |
| Owner distribution per firm / receipts per household | 0.073397435897 |
| Payroll per firm / wages per household | 0.176602564103 |

Firm cash reaches zero after distributions and wages, then returns to `0.25`
through goods sales. Household cash returns to `0.25` after its purchases. This
fixture starts at the displayed capital and cash distribution; it does not
claim that an arbitrary starting point converges there.

There is also a global bound on a firm's deviation at these stationary prices.
Let `S(K,F)=F+pK`. For any feasible one-period firm choice:

```text
D + beta S(K_next,F_next) - S(K,F)
  = -(1-beta)(F-D-WL) + beta*p [Y-aK-bL] <= 0
```

Funding makes the first term nonpositive; the constant-returns production
supporting plane makes the second nonpositive. Summation bounds any feasible
discounted payout stream by initial `S`. The stationary policy achieves equality
and has vanishing discounted terminal `S`, so it attains that upper bound.
Household concavity, its optimality conditions and vanishing discounted terminal
cash likewise support its stationary choice. This establishes the fixture's
optimality, not `V=S` at every possible state.

Reproduce the numerical substitutions and funded cash cycle with:

```bash
python docs/monetary_reference_check.py
```

The checker also uses `eta=1`: stationary real quantities stay the same while
the money split and price level change. That result is specific to this
stationary regime; it is not neutrality of every transition.

## Relation to Step 1 and implementation gates

Reducing `eta` to zero does not recover Step 1. The prepaid-wage effect remains,
and the household cash choice reaches a boundary outside these interior money
conditions. A comparison with the real reference must explicitly remove the
monetary funding restriction, allow reversible capital and frictionless capital
finance, and use a justified ownership mapping. Dropping those restrictions is
a separate benchmark comparison, not an executable cash-settlement shortcut.

Before changing the app:

- Implement and validate the Step 1 partial-depreciation/labor reference using
  its exact special cases and stationary allocation.
- Build the symmetric monetary transition solver against the budgets above,
  checking household optimality, firm complementarity, terminal treatment,
  forecast consistency, and every funded transaction. Use the stationary fixture
  and its bound as independent evidence.
- Establish a supported initial-state domain and investigate multiple paths,
  corners, numerical convergence and continuation sensitivity. A stationary
  example does not resolve those transition questions.
- Integrate the resulting single model only after those checks, with explicit
  saved-file/version handling. Its behavior differs from the present engine.

No transition solver, application behavior or deployment changes are included in
this design step. The next executable milestone is the independently verified
real reference, followed by the monetary transition problem. Market adjustment
and self-regulation remain a later architectural step; shocks remain postponed.
