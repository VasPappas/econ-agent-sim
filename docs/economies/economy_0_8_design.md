# Economy 0.8 — Firms and Wages

Status: implemented as an independent chapter. Economy 0.7 stays unchanged.

## Purpose and scope

Replace self-employment with households supplying labor to one firm. Keep one
consumption good X, money, endogenous leisure, linked periods, and the existing
three positive relative priority scores. Households consume all purchased X;
neither households nor the firm carry goods between periods.

The firm is a representative price-taking producer, not a strategic monopoly or
monopsony. One displayed firm is an educational aggregation. It takes both the
goods price and wage as given when optimizing. No entry or competition mechanism
is simulated. This assumption must be disclosed in Ask why.

No banking, borrowing, government, investment, inventories, initial goods,
exogenous shocks, or future-planning optimization. Labor is homogeneous: each
household has one unit of time and productivity belongs to the firm. Ownership
is equal and fixed within a simulation; no share-trading market is modeled.

## Timing: funded wages and next-period dividends

Beginning-of-period balances are exactly the previous period's closing balances,
before any dividend transfer. The first period has no prior profit to distribute.

1. Pay the previous period's realized profit to household owners as dividends.
2. Determine a goods price, wage, labor, and purchases that clear both markets.
3. Pay wages from the firm's cash remaining after dividends; no overdrafts.
4. Households supply the agreed labor and the firm produces X.
5. Households pay for and receive X using their now-available money.
6. Households consume X; the firm retains this period's profit until next period.

Equilibrium calculation is simultaneous; these steps specify actual settlement,
not a trial-and-error price animation. Compute and validate the entire candidate
period before appending it to history. Failed solutions leave history unchanged.

If initial firm cash is B, its post-dividend operating cash remains B: closing
firm cash is B plus current profit. This is a derived accounting identity, never
a balance reset or money injection. All dividends require ledger transfers.

Next-period distribution is an explicit simplifying convention, not a universal
textbook rule. Households value current consumption, closing liquid money and
leisure; they do not anticipate future dividends in their choices. Ownership is
a claim to future distributions, not an additional spendable balance today.

## Households

Normalize scores C_i, M_i, G_i into a_i, b_i, g_i, summing to one.
Let alpha_i = a_i/(a_i+b_i). Define h_i as opening household money, d_i as
the dividend received at the start, and z_i = h_i+d_i.

At goods price p>0 and wage w>0, choose consumption c_i, closing money m_i,
and labor l_i to maximize:

`U_i = c_i^a_i * (m_i/p)^b_i * (1-l_i)^g_i`

subject to:

`p*c_i + m_i = z_i + w*l_i`, with `0 <= l_i < 1`.

The solution, including the zero-work corner, is:

`l_i = max(0, (1-g_i) - g_i*z_i/w)`

`c_i = alpha_i*(z_i+w*l_i)/p`

`m_i = (1-alpha_i)*(z_i+w*l_i)`.

The wage is Money per full unit of labor time, not each household's total pay.
Priority weights are not prescribed spending or leisure percentages. Every
household can buy goods even when it supplies no labor if it has cash/dividends.

## Firm

Production is `Q=A*L^theta`, where A>0 and 0<theta<1. Use theta=0.5 initially
as a fixed documented model parameter, and expose A as firm productivity.
This is a decreasing-returns technology. It may be interpreted as a reduced-form
fixed productive capacity, but no priced capital asset or capital cost is added.

The firm maximizes `profit = p*A*L^theta - w*L` subject to `w*L <= B`.

Without a binding cash constraint, `p*A*theta*L^(theta-1) = w`.
With a binding constraint, `w*L = B` and the marginal revenue product can exceed
the wage. Do not label that outcome unconstrained profit maximization.

No fixed costs are modeled, so the constrained optimum has nonnegative profit.
Current dividends are not an expense of current production. Paid dividends are
distributions of prior earnings.

## Market clearing and numerical design

Require `L=sum(l_i)` and `Q=sum(c_i)`.

The system reduces to a scalar wage equation. Define:

`W_i(w)=max(0, (1-g_i)*w - g_i*z_i)`

`W(w)=sum(W_i(w))`

`S(w)=sum(alpha_i*(z_i+W_i(w)))`.

Find the positive wage satisfying:

`W(w) = min(theta*S(w), B)`.

Then recover `l_i=W_i/w`, `L=sum(l_i)`, `Q=A*L^theta`, `p=S/Q`, and
`profit=S-W`. This derives from the firm's first-order condition or cash cap
and goods-market clearing; it is not an arbitrary wage-setting rule.

With positive aggregate post-dividend household cash and B>0, the residual is
negative before any household works and eventually positive. Each active
household's contribution to W-theta*S has positive slope
`(1-theta*alpha_i)*(1-g_i)`. W-B also increases once work starts. A bracketed
scalar solve therefore avoids an unnecessary multidimensional optimizer.

Validation must reject nonfinite values, nonpositive priorities/productivity,
negative balances, no household cash in aggregate, and no firm operating cash.
Individual cashless households are allowed. A zero-funding economy is outside
this version's positive-price equilibrium domain, not silently repaired by a loan.
Validate scale-aware residuals and optimality after solving, including corners.

## Baseline

Two households, each with 1 Money and scores 1:1:1. Each owns 50% of the firm.
Firm initial operating cash is 1 Money, A=2, theta=0.5. Total initial money is 3;
the firm cash is part of the initial endowment, not created during a run.

Derived period-one results (rounded only for display):

| Quantity | Value |
| --- | ---: |
| Wage, Money per labor unit | 1.0000 |
| Work per household | 33.33% |
| Leisure per household | 66.67% |
| Total output and consumption, X | 1.6330 |
| Goods price, Money per X | 0.8165 |
| Total wages, Money | 0.6667 |
| Firm sales, Money | 1.3333 |
| Firm profit, Money | 0.6667 |
| Dividend paid in period one | 0 |
| Closing money per household | 0.6667 |
| Firm closing money | 1.6667 |

In period two the firm distributes 0.6667 from period one, half to each owner.
That restores household post-dividend cash to 1 each and firm operating cash to
1. The same real allocation then repeats in this symmetric baseline. Do not
force the 0.7 no-trade or 50%-work baseline onto a different economic structure.

## Reporting and mobile UI

Keep Set up / Results / Ask why, Reset, period selection and cumulative reporting.
Setup has short household cards (initial Money and three priorities) plus one
firm card (initial operating Money, productivity). Show equal ownership as a
caption. Remove household initial X and household productivity in this chapter.
Explain A as output with one full unit of total labor, not output at every
household's combined maximum effort. Show initial total money including the firm.

Results lead with goods price, wage and total output. Reuse the compact cards:

- Household: opening/closing money; wages received; dividends received; purchases;
  net cash change; consumed X; work/leisure; submitted priority weights.
- Firm income statement: sales minus wages equals profit.
- Firm cash account: opening money minus dividends paid minus wages plus sales
  equals closing money. Show profit awaiting next-period distribution separately.
- Economy: produced/consumed X; output value; wages; current profit; total money.
  Output value equals wages plus current profit, NOT wages plus dividends paid.

Keep supporting receipts and validation collapsed. A flat zero economy-wide cash
change row is unnecessary. Cumulative flows sum actual period transfers; balances
use the first opening and selected closing. Period prices/wages are not summed.
Do not sum production value, wages and profits as three distinct sources of
economy income. Ownership book claims, if displayed later, must be separated
from cash and eliminated against firm equity in consolidated reporting.

## Implementation boundaries and acceptance checks

Add an independent 0.8 engine/page; do not retrofit firms into the 0.7 solver.
Reuse suitable ledger records, formatting, report widgets and chat safety code.
Define explicit household/firm settings, period snapshots and transfer kinds
(`dividend`, `wage`, `goods_payment`, `goods_delivery`). Do not disguise wages
as goods trades or money as production. Keep labor allocation distinct from
stored assets. All settings remain fixed during a linked run until restart.

Acceptance checks before deployment:

- Analytical baseline, including first-period versus later-period dividends.
- Independent household budget/optimality and constrained firm optimality checks.
- Both markets clear; output equals consumption; labor equals household work.
- Nonnegative cash after every settlement phase, not just at period close.
- Dividend payment equals prior profit once and only once; zero in period one.
- Total money conserved across all parties and all phases; period continuity.
- Extreme priorities, zero-work and cashless households, binding firm funding.
- Uniform currency scaling changes p and w proportionally, not real quantities.
- Proportional rescaling of one household's three scores leaves behavior unchanged.
- Period/cumulative reports, CSV and tutor agree on wages, profits and dividends.
- Phone-width layout and actual expanded-card persistence, not label-only tests.

Design arithmetic was checked in a disposable calculation across 1,000 periods
with heterogeneous households and theta between 0.15 and 0.85. It covered 819
cash-constrained firm periods and 6,077 zero-work household cases. These checks
support the equations but are not a production implementation or release test.

## Reference and modeling choices

The unconstrained price-taking hiring condition follows the value-of-marginal-
product treatment in [OpenStax, The Theory of Labor Markets](https://openstax.org/books/principles-economics-3e/pages/14-1-the-theory-of-labor-markets).
The funding cap, delayed dividends, myopic money-in-utility behavior, scalar
reduction and baseline above are this simulation's explicit design choices and
derivations, not claims that the reference specifies this monetary model.
