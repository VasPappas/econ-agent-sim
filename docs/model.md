# The current Tiny Economy model

Model `tiny-economy-monetary-1`; engine `tiny-economy-4.0.0`.
The app runs one symmetric, deterministic monetary growth model. Its full
specification and numerical acceptance rules are in
[monetary_foundation.md](monetary_foundation.md) and
[monetary_boundaries.md](monetary_boundaries.md).

## People, firms and inputs

There are two identical households and two identical price-taking firms.
Each household owns half of each firm. Firms own productive capital. One good X
serves consumption and investment; productivity and total money are normalized
to one, and the capital exponent is fixed at 0.5. No population, interest-rate,
investment-propensity or dividend-percentage control is required.

| Input | Default | App range | Meaning |
| --- | ---: | ---: | --- |
| `beta` | 0.95 | 0.50–0.99 | Weight on next period's utility |
| `depreciation` | 0.10 | 0.01–1 | Capital wear per period |
| `leisure_weight` | 1 | 0.05–10 | Leisure relative to consumption |
| `money_weight` | 0.05 | 0.001–5 | Service value of real closing money |
| `initial_capital` | 1 | 0.01–1000 | Capital per firm |
| `initial_firm_cash_share` | 0.50 | 0.01–0.99 | Firms' fraction of the fixed money stock |

These are four structural parameters and two starting conditions. Ranges are
interactive input limits, not a claim that every combination is solvable.
Percentages in the UI are converted to fractions in the model and saved files.
One period has no assigned calendar frequency; defaults are illustrative.

## Joint forward-looking choices

A household maximizes the discounted sum of
`log(c) + leisure_weight*log(1-l) + money_weight*log(h_next/p)`.
Its money budget is `h_next = h + W*l + dividends - p*c`.
Work, spending and cash saving are chosen together. Ownership value is not
spendable money, and households cannot lend to firms or trade their shares.

A firm produces `Y=sqrt(K*L)`, retains `I` units as investment, and carries
`K_next=(1-depreciation)*K+I` into the next period. Investment and dividends are
nonnegative. It maximizes owner distributions using the same marginal-utility
valuation of future money as its identical household owners. It faces
`D+W*L <= F` before sales, and closes with `F_next=F-D-W*L+p*(Y-I)`.
There is no prescribed investment share, payout ratio, protected original-cash
reserve or separate user-cost interest rate.

The implemented regime allows zero investment and zero dividends while verifying
that opening funding binds optimally. Cases where positive unused opening cash
would be optimal are rejected as unsupported. That message does not mean no
equilibrium exists. Other numerical failures are also reported without a partial run.

## Timing and settlement

1. Firms enter with cash and capital, then pay funded dividends.
2. Firms pay wages from remaining opening cash; households supply work.
3. Firms produce; households purchase consumption goods; retained output becomes investment.
4. Opening capital depreciates and new capital becomes available next period.

Every monetary transfer has a funded payer and recipient. Retaining output and
wearing out capital are physical events, not cash payments. Total money remains
one; total output equals consumption plus investment. There are no loans,
money creation, inventories, capital resale, external finance or shocks.

## Accounts and values

Per-firm book equity is cash plus capital at the goods replacement price. This
is not the solver's shadow value or a traded equity price. Period 1 opening
capital uses period 1's price. Thereafter, opening capital is carried at the
previous period's price and revalued separately:

```text
Operating profit = p*Y - W*L - depreciation*p*K
Holding gain = (p - previous_p)*K
Closing equity = opening equity + operating profit - dividends + holding gain
```

Cumulative flows keep their original dates and prices. Opening/closing stocks
are not summed; work and leisure fractions are averaged. Household ownership
claims equal firm equity and are eliminated in economy consolidation. Total
book assets are total money plus capital replacement value, without double counting.

## Numerical and economic limits

Start solves all 100 displayable periods with a checked continuation extending
beyond them. It verifies equations, complementary inequalities, funded settlement,
longer-horizon agreement and approach to the stationary continuation. Advance
only reveals the immutable accepted plan. No ending liquidation is imposed at
period 100. These are numerical acceptance checks, not an exact infinite-horizon
error bound or a global uniqueness proof.

Perfect foresight, symmetry, log preferences and market clearing are assumptions.
Two firms do not introduce strategic competition. The model does not explain
learning, uncertain expectations, decentralized price discovery, rationing or
self-regulation. Inventories, financial intermediation, heterogeneity and shocks
remain future design decisions; exogenous shocks stay postponed.
