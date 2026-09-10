# Economy 0.7 — Work and Leisure

Self-employed agents choose work, consumption and money holdings at a competitive
price. There are no firms, wages, borrowing, uncertainty or forward-looking plans.
Money is valued directly for its current purchasing power by assumption.

## Preferences and the time budget

Each agent has one unit of time, split between work `l` and leisure `1-l`.
Productivity `A>0` turns work into `q=A*l` units of X. All post-trade X is consumed
within the period. Only money carries forward; initial X is available in period 1.

For consumption preference `alpha` and leisure preference `g`, both strictly
between zero and one, utility is

`U = c^((1-g)*alpha) * (m/p)^((1-g)*(1-alpha)) * (1-l)^g`.

The three weights sum to one. `alpha` splits the non-leisure weight between
consumption and money; it is not consumption's share of all three priorities.
`g` is a preference weight, not the fraction of time the agent must spend resting.
Money balances are divided by the current goods price, so utility values real
balances. This does not introduce expectations of future prices or future utility.

At a price the agent takes as given, the constraints are
`p*c + m = m0 + p*(x0 + A*l)`, `0 <= l < 1`, with nonnegative holdings.
Let `e=x0+m0/p`. The optimal choices are

`l = max(0, (1-g) - g*e/A)`

`c = alpha*(e+A*l)`

`m/p = (1-alpha)*(e+A*l)`.

A sufficiently wealthy agent chooses zero work. Positive productivity ensures
even an agent starting with no goods or money can produce, consume and sell goods
to acquire a positive cash balance. The economy as a whole requires positive
money. Degenerate endpoint preferences and zero productivity are excluded.

## Joint market and work solution

Write `s=1/p`. Aggregate excess goods demand is
`F(s)=sum(alpha*m0*s - (1-alpha)*(x0+A*l(s)))`.
Work is continuous and piecewise linear in `s`. When an agent works,
`x0+A*l=(1-g)*(x0+A)-g*m0*s`; otherwise it is simply `x0`.
Thus `F` is continuous, piecewise linear and strictly increasing with positive
aggregate money. At zero purchasing power, supply is positive and `F(0)<0`;
for sufficiently large `s`, cash-financed demand dominates and `F(s)>0`.
There is a unique finite positive clearing price.

The engine solves each linear segment analytically, starting with agents who
would work at `s=0`. If the candidate root would imply negative work, those agents
are set to zero work and the root is recalculated. The root can only increase,
so an excluded worker cannot re-enter; at most N+1 solves are needed. This is not
a simulated price-adjustment process or a series of trades at different prices.

The chosen production is settled through Economy 0.6's market and ledger. Its
independently calculated price must match the joint solution. Work optimality is
also checked at the actual settlement price: marginal benefit equals marginal
leisure cost for workers, and is no greater than cost for zero-work agents.
Budget feasibility and strict concavity of log utility make these conditions
sufficient for the agent's optimum at the given price.

## Baseline and interpretation

Two identical agents start with zero X, one Money, productivity 2, `alpha=1/2`
and `g=1/3`. Each chooses work 1/2 and leisure 1/2, produces and consumes one X,
retains one Money, and trades nothing at price 1. This repeats across periods.
The exact leisure weight is 1/3; rounding its label does not change the model.

Higher leisure preference reduces work at a fixed price. Higher productivity
raises work weakly at a fixed price in this particular specification, while also
raising output; general-equilibrium price changes can alter that comparison.
Greater opening wealth reduces work. These are model implications, not universal
claims about labor supply. Saving remains a within-period demand for money.

## Accounting and result contract

The period identity is `opening X + produced + received - sent - consumed = 0`.
Money satisfies `opening Money + received - sent = closing Money`, with exactly
those closing balances used to open the next period. Goods are conserved during
trade; production adds them and consumption removes them. All transfer receipts
carry the correct period number. Changing agent specifications requires restart.

`WorkPeriod` extends `ProductionPeriod` with `effort`, `leisure_time`, `work_checks`
and `solution`. Original `WorkAgent` specifications are retained across periods.
`WorkRun(current, previous, revision)` uses the shared market and period data
contract with model `work_leisure`, plus those four fields. Market closing X is
consumption, never end-of-period stored inventory. The ordinary period checks
retain production/consumption accounting; work checks separately report feasible
time, optimal work and agreement of the joint price with settlement.
