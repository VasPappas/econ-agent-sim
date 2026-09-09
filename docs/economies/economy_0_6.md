# Economy 0.6 — Production and Consumption

A linked sequence of one-good monetary markets. Agent settings are fixed for a
simulation; changing them requires a restart. This chapter preserves Economy 0.5
as an independent, static experiment.

## A period

1. Open with the previous period's closing balances (or initial balances in period 1).
2. Add each agent's fixed production of X to their inventory.
3. Clear and settle the X market using the Economy 0.5 engine.
4. Consume **all** X each agent holds after trade.
5. Carry money into the next period. No X remains in storage.

Production is an exogenous flow, with no inputs, labor cost, wage, employer or work
decision. Agents are not choosing effort. Consumption is the market allocation,
not a fixed physical requirement: an agent with no resources can consume zero.

## Decisions and prices

Each agent makes a myopic, within-period choice between consumption `c` and
end-of-period money `m`, maximizing `c^alpha * m^(1-alpha)`, with `0 < alpha < 1`.
Money is directly valued by assumption. This does not model forward-looking saving
or explain the emergence of money. There is no borrowing or money creation.

Let `q_i` be opening X plus current production and `m_i` opening money. Wealth is
`w_i=p*q_i+m_i`. Desired consumption is `alpha_i*w_i/p`; desired closing money is
`(1-alpha_i)*w_i`. The clearing price is
`p=sum(alpha_i*m_i)/sum((1-alpha_i)*q_i)`.

All post-trade X becomes consumption, so the static engine's goods demand is
exactly consumption demand here. A net buyer can fund the purchase from opening
cash; net sellers receive money. Trade itself conserves both assets. Production
adds goods, and consumption removes them. No aggregate supply means there is no
finite interior market to solve: advancing reports this and preserves history.

## Baseline and dynamics

Two agents each start with zero X, one Money, production of one X per period and
equal preference for consumption and money. Every period has price 1, no trade,
one X consumed per agent and one Money carried forward. Initial X defaults to zero
so the first period does not accidentally receive two periods' supply.

Different production or preferences can generate trade and redistribution. Trade
need not continue forever: a steady state with no trade is valid. With common
alpha and constant total output Q, periods after initial inventory is consumed
have constant price `alpha*M/((1-alpha)*Q)`; individual cash balances can still
change. Unequal preferences can also produce changing prices. A zero-production
agent may spend down their finite cash; the model guarantees no minimum consumption.

## Accounting and UI contract

For each agent and for the whole economy, the checked identity is
`opening X + produced + received - sent - consumed = closing X`.
Money satisfies `opening Money + received - sent = closing Money`. Closing money
equals the next period's opening money. Transfers are independently reconstructed
from the actual ledger; market allocations, non-negative holdings and conservation
also retain the checks from Economy 0.5.

`ProductionPeriod` records opening balances, production, a complete `MoneyResult`
for the market stage, consumption, closing balances and period checks.
`ProductionRun.data` retains the shared market-stage `agents`, `totals`, `checks`
and receipts, and adds `period_opening`, `produced`, `consumed`, `period_closing`,
`period_totals` and `period_checks`. Market-stage final X must be labeled as
post-trade X or consumption, never as end-of-period inventory. Period totals use
asset maps at opening, produced, consumed and closing; production and consumption
of Money are zero. Trade receipts are identified within their period.
