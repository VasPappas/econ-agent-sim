# Economy 0.2 — Many-Agent Pure Exchange

## Purpose

Economy 0.2 changes one structural feature: the economy now contains an arbitrary collection of agents rather than exactly Alice and Bob. The canonical experiment uses ten deterministic heterogeneous agents.

Everything else is inherited from Economy 0.1: two goods, Cobb-Douglas optimization, Walrasian tâtonnement, no trade during price discovery, explicit ledger settlement, and stock-flow accounting. There is still no money, production, government, banking, database, randomness, or time dynamics.

## Canonical population

| Agent | Initial X | Initial Y | alpha |
| --- | ---: | ---: | ---: |
| Agent 1 | 1.8 | 0.2 | 0.20 |
| Agent 2 | 0.2 | 1.8 | 0.80 |
| Agent 3 | 1.5 | 0.5 | 0.30 |
| Agent 4 | 0.5 | 1.5 | 0.70 |
| Agent 5 | 1.2 | 0.8 | 0.40 |
| Agent 6 | 0.8 | 1.2 | 0.60 |
| Agent 7 | 1.7 | 0.3 | 0.35 |
| Agent 8 | 0.3 | 1.7 | 0.65 |
| Agent 9 | 1.4 | 0.6 | 0.45 |
| Agent 10 | 0.6 | 1.4 | 0.55 |

The population is deliberately non-random. Adjacent agents are mirrored in endowments and preferences, total X and total Y are both 10, and the analytic benchmark remains `pX = 1` with `pY = 1`.

## Optimization and analytic benchmark

Each agent has Cobb-Douglas utility `U_i(X,Y) = X^alpha_i Y^(1-alpha_i)` and independently chooses the affordable utility-maximizing bundle at each trial price.

For any number of agents, the two-good analytic equilibrium with `pY = 1` is:

`pX* = sum(alpha_i * y_i^0) / sum((1-alpha_i) * x_i^0)`.

As in Economy 0.1, this analytic price is used only as an independent regression benchmark. The tâtonnement algorithm never receives it.

## Price discovery

Economy 0.2 reuses the same normalized proportional rule:

`pX(t+1) = pX(t) * [1 + lambda * zX(t) / total_X]`.

At every iteration all agents optimize, individual demands are aggregated, and the trial price moves in the direction of aggregate X excess demand. Both X and Y markets must be inside the numerical clearing tolerance before settlement begins.

No holdings change during tâtonnement.

## Many-agent settlement

After convergence, each agent has a net target position for each good. Several agents may be buyers and several may be sellers, so Economy 0.2 uses a deterministic clearing convention:

1. list net buyers and sellers in population order;
2. match the first buyer to the first seller;
3. transfer the smaller remaining quantity;
4. record that physical transfer in the append-only ledger;
5. continue until the market is exhausted within numerical tolerance.

This matching rule does not determine prices or preferences; it only converts the already-determined equilibrium allocation into explicit, traceable transfers. All transfers share `trade_id = 1` because they are legs of one market-clearing settlement event, while each transfer has its own `transaction_id`.

## Accounting

For every agent and good:

`closing stock = opening stock + net ledger flows`.

System-wide total X and total Y are conserved, and aggregate net flows are zero. Regression tests also require the ledgered closing allocation to match the desired equilibrium allocation within tight floating-point tolerance.

## Architectural significance

The Economy 0.2 engine loops over a collection of agent specifications for construction, optimization, aggregation, settlement, and accounting. A test uses three agents with completely different names to verify that the new engine does not depend on Alice, Bob, or the canonical ten-agent labels.

The first Streamlit page keeps the canonical population fixed while allowing the initial trial price and tâtonnement adjustment speed to vary. Direct population-table editing can be added later without changing the economic engine.

Economies 0 and 0.1 remain separately runnable and tested.