# Tiny Economy — model and accounting

## Scope and building blocks

A deterministic sequence of static market-clearing periods: households choose
consumption, liquid money and leisure; exactly two price-taking firms hire labor
and produce one homogeneous good X with their own capital. There is one wage w
and one X price p. Households own equal, fixed shares in each firm.

Cobb–Douglas preferences and production are textbook building blocks. Direct
utility from money, soft consumption targets, cash-funded payroll and fixed
investment/dividend rules are additional explicit teaching assumptions. This is
not a calibrated forecasting model, strict Stone–Geary subsistence, strategic
duopoly or a forward-looking growth equilibrium.

## Household choice

Normalize positive priority scores into a+d+g=1. Work is l in [0,1); leisure is
1-l. Each household solves:

```text
max a ln(C) + d ln(M) + g ln(1-l) - phi(C,b)
subject to p C + M = available_cash + w l
C > 0, M > 0, 0 <= l < 1

phi(C,b) = C/b - 1 - ln(C/b)   if 0 < C < b
           0                  if b=0 or C>=b
```

b is its per-period consumption target. Penalty strength is fixed at 1. Below b,
marginal utility of consumption is a/C + 1/C - 1/b; otherwise a/C. The penalty
and its first derivative join continuously at b. Base priorities do not change.
A shortfall is not debt and does not accumulate into subsequent preferences.

Available cash is carried money plus this period's dividends. Money is valued
directly, not through forecasts of future purchases. At an interior optimum,
MU_C=p MU_M and w MU_M=MU_leisure. At zero work the latter becomes an inequality.
All bought X is consumed; there is no household goods storage.

## Firm choice and policies

For each firm independently:

```text
Q = A sqrt(K L)
w L <= post_dividend_cash
I = r (p Q - w L) / p
sold_X = Q - I
next_K = (1-delta) K + I
```

K is opening capital, A productivity, r the reinvestment policy and delta wear.
At fixed prices firms maximize gross production surplus pQ-wL subject to funded
payroll. An unconstrained firm hires until p Q/(2L)=w. Funding can bind sooner.
The policy reinvests a share of gross surplus, not total output or net profit.
Investment retains the firm's own output: no self-sale or cash investment payment.
New capital first produces and depreciates in the next period.

At the start of a period, each firm's dividend is:

```text
min(max(previous_net_profit, 0),
    max(opening_cash - original_operating_float, 0))
```

The first period pays zero. The original float is a dividend protection rule,
not a cash reset or outside injection. Historical retained losses do not veto a
later positive, funded dividend. Household ownership shares remain fixed.

## Clearing and settlement

1. Carry money and capital from the previous immutable snapshot.
2. Pay eligible dividends from each firm's own cash.
3. Solve household choices, labor clearing and goods clearing jointly.
4. Pay funded wages, record production and purchases, consume household X,
   and record depreciation and own-output investment.
5. Reconcile cash, physical flows and financial accounts before accepting the period.

A household's work is allocated in proportion to firms' labor demand. Purchases
are allocated in proportion to each firm's sold X. Labor-service and goods
deliveries pair with reverse money transfers; dividends only transfer money.
There is no cash pooling between firms, borrowing or money creation.

Zero targets use the analytical active-set clearing path. Positive targets use
bounded candidate detection. More than one valid clearing outcome can exist:
period 1 selects the candidate closest in log price to the otherwise identical
target-free reference, later periods the closest to the previous price; lower
price wins numerical ties. See [market_selection.md](market_selection.md) for
reproduction and finite-scan limitations. This is not a simulated adjustment
process, completeness guarantee or stability result.

## Accounting

Output value=pQ=cash sales+pI. Gross operating surplus=pQ-wL.
Net operating profit=pQ-wL-p delta K. Positive cash surplus can coexist with
negative profit when depreciation is large.

Capital uses current replacement cost. Period-1 opening capital uses p1.
In later periods holding gain=(p-p_previous) times opening K. It is separate from
operating profit. Equity is cash plus capital value:

```text
closing_equity - opening_equity
    = net_operating_profit - dividends_paid + holding_gain
```

Households show cash plus claims on both firms. Consolidation eliminates those
claims against firm equity; never double-count them as extra economy assets.
Retained earnings preserve all prior profits and losses.

Cumulative flows add their original-period nominal amounts. They are not
revalued at the final price. Stocks use first opening and selected closing;
prices/wages are selected-period rates. Work/leisure percentages average, while
firm labor and physical production sum. Sales shares use total physical sold X.
Target gaps sum max(target-consumption,0) for each household-period; excess in
one household or period cannot offset another's gap. Coverage caps each
consumption contribution at its own target. A zero target has no coverage rate.

## Supported experiments and limits

The app supports 2–20 households, exactly two firms and up to 100 periods per
portable experiment. Setup scores and policies have finite validated bounds.
Presets turn off investment, depreciation and/or targets as specified; firms,
wages and household optimization remain the same model. They are not substitutes
for historical pure-exchange or one-firm formulations.

There are no banks, debt, interest, government, taxes, shocks, entry, exit,
bankruptcy, strategic price-setting or optimal lifetime investment decisions.
