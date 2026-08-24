# Economy 0 — Pure Exchange

## Purpose

Economy 0 is the smallest useful baseline: **two agents, two goods, no money, no production, and no time dynamics**. Its job is to make optimization, market clearing, transactions, and stock-flow accounting completely visible.

## Agents and canonical endowments

| Agent | X | Y |
| --- | ---: | ---: |
| Alice | 1 | 0 |
| Bob | 0 | 1 |

Both agents have textbook Cobb-Douglas preferences:

\[
U_i(X,Y)=X^{\alpha_i}Y^{1-\alpha_i}.
\]

The canonical Economy 0 fixes both agents at \(\alpha=0.5\). Given wealth \(w_i\) and prices \(p_X,p_Y\), utility maximization gives:

\[
X_i^*=\alpha_i\frac{w_i}{p_X}, \qquad
Y_i^*=(1-\alpha_i)\frac{w_i}{p_Y}.
\]

## Market clearing

We normalize \(p_Y=1\), because only relative prices matter. For arbitrary Economy 0 endowments and Cobb-Douglas weights, the analytic market-clearing price is:

\[
p_X = \frac{\sum_i \alpha_i y_i^0}{\sum_i(1-\alpha_i)x_i^0}.
\]

In the canonical scenario, \(p_X=1\). Each agent therefore has wealth 1 and demands:

\[
(X^*,Y^*)=(0.5,0.5).
\]

Both markets clear exactly.

## Transactions

In the canonical scenario, the barter trade is stored as two linked physical transfers under one `trade_id`:

1. Alice transfers 0.5 X to Bob.
2. Bob transfers 0.5 Y to Alice.

This is deliberately more explicit than simply replacing the opening allocation with the equilibrium allocation: the ledger tells us exactly how holdings changed.

## Stock-flow accounting

For every agent and every good:

\[
\text{Current stock}=\text{Opening stock}+\text{Cumulative net flow}.
\]

The app displays this identity at every simulation step, including after each individual transfer. At the end, current stock is the closing stock. System-wide, total X and total Y are conserved and aggregate net flow is zero.

## Interactive laboratory

The Streamlit interface is an experiment layer on top of the same economic engine. You can change:

- Alice's initial X and Y endowments
- Bob's initial X and Y endowments
- Alice's Cobb-Douglas \(\alpha\)
- Bob's Cobb-Douglas \(\alpha\)

Then move through the economy one stage at a time:

`Setup → Opening stocks → Optimization → Market clearing → Transactions → Final reconciliation`

The transaction ledger and stock-flow accounting remain visible as the economy progresses. Changing these inputs is for learning and sensitivity experiments; it is **not calibration**.

## Parameters

Economy 0 has only the textbook preference weight \(\alpha\) for each agent plus the chosen initial endowments. The canonical version fixes both preference weights at 0.5 and uses the simple one-good-per-agent endowment above.

## Not yet included

- Money or financial assets
- Production or firms
- Labour
- Saving or capital
- Banks and credit
- Government or central bank
- A database
- Stochastic behaviour
- Time dynamics

These omissions are intentional. Each future economy will add a small, identifiable mechanism while Economy 0 remains runnable.
