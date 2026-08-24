# Economy 0 — Pure Exchange

## Purpose

Economy 0 is the smallest useful baseline: **two agents, two goods, no money, no production, and no time dynamics**. Its job is to make optimization, market clearing, transactions, and stock-flow accounting completely visible.

## Agents and endowments

| Agent | X | Y |
| --- | ---: | ---: |
| Alice | 1 | 0 |
| Bob | 0 | 1 |

Both agents have textbook Cobb-Douglas preferences:

\[
U(X,Y)=X^{0.5}Y^{0.5}.
\]

Given wealth \(w\) and prices \(p_X,p_Y\), utility maximization gives:

\[
X^*=0.5\frac{w}{p_X}, \qquad Y^*=0.5\frac{w}{p_Y}.
\]

## Market clearing

We normalize \(p_Y=1\). The analytic Walrasian equilibrium is \(p_X=1\). Each agent therefore has wealth 1 and demands:

\[
(X^*,Y^*)=(0.5,0.5).
\]

Both markets clear exactly.

## Transactions

The barter trade is stored as two linked physical transfers under one `trade_id`:

1. Alice transfers 0.5 X to Bob.
2. Bob transfers 0.5 Y to Alice.

This is deliberately more explicit than simply replacing the opening allocation with the equilibrium allocation: the ledger tells us exactly how holdings changed.

## Stock-flow accounting

For every agent and every good:

\[
\text{Closing stock}=\text{Opening stock}+\text{Net flow}.
\]

System-wide, total X and total Y are conserved and aggregate net flow is zero. The simulator checks these identities in the model and regression tests.

## Parameters

There is one preference parameter per Cobb-Douglas agent, `alpha`. Economy 0 fixes both at the symmetric textbook value `0.5`; there is nothing to calibrate.

## Not yet included

- Money or financial assets
- Production or firms
- Labour
- Saving or capital
- Banks and credit
- Government or central bank
- A database
- Stochastic behaviour

These omissions are intentional. Each future economy will add a small, identifiable mechanism while Economy 0 remains runnable.
