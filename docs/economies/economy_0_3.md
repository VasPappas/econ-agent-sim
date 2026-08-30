# Economy 0.3 — Repeated pure exchange

Economy 0.3 introduces one new mechanism only: **explicit time through repeated exchange periods**.

The economic structure inside each period is unchanged from Economy 0.2:

- ten canonical heterogeneous agents;
- two goods, X and Y;
- Cobb-Douglas utility;
- Walrasian tâtonnement for price discovery;
- no trade while tâtonnement is running;
- deterministic many-agent settlement after convergence;
- an append-only transaction ledger; and
- stock-flow accounting for every agent and good.

There is still no money, production, saving, borrowing, government, banking, or randomness.

## What a period means

Each period is a complete one-shot exchange economy:

`fresh exogenous opening endowments → price discovery → settlement → closing stocks`

The next period then begins with a new exogenous endowment schedule.

Crucially,

`closing stocks in period t` **do not become** `opening stocks in period t + 1`.

That boundary is deliberate. Economy 0.3 introduces a time index without yet introducing intertemporal wealth accumulation, saving, consumption, or inventory carry-over.

## Canonical four-period schedule

Agent identities and Cobb-Douglas preferences remain fixed across all four periods. Aggregate endowments also remain fixed at:

- total X = 10;
- total Y = 10.

The X allocation is held fixed at the Economy 0.2 canonical values. The Y endowment vector is rotated one agent to the right in each successive period.

| Period | Y endowments for Agents 1 → 10 |
| --- | --- |
| 1 | 0.2, 1.8, 0.5, 1.5, 0.8, 1.2, 0.3, 1.7, 0.6, 1.4 |
| 2 | 1.4, 0.2, 1.8, 0.5, 1.5, 0.8, 1.2, 0.3, 1.7, 0.6 |
| 3 | 0.6, 1.4, 0.2, 1.8, 0.5, 1.5, 0.8, 1.2, 0.3, 1.7 |
| 4 | 1.7, 0.6, 1.4, 0.2, 1.8, 0.5, 1.5, 0.8, 1.2, 0.3 |

This changes the distribution of purchasing power and desired trades while keeping aggregate scarcity unchanged.

## Period-by-period analytic benchmark

With Y as the numeraire, each period has the same textbook analytic benchmark used in the earlier exchange economies:

\[
p_{X,t}^* =
\frac{\sum_i \alpha_i y_{i,t}}
{\sum_i (1-\alpha_i)x_{i,t}},
\qquad p_Y = 1.
\]

For the canonical schedule, the benchmark relative prices are approximately:

| Period | Analytic pX |
| ---: | ---: |
| 1 | 1.000000 |
| 2 | 0.690117 |
| 3 | 0.969849 |
| 4 | 0.695142 |

The tâtonnement process does not use these values when updating the trial price. They remain independent regression benchmarks.

## Price discovery inside each period

Every period starts from the configured initial trial price and runs the same normalized Walrasian tâtonnement rule as Economy 0.2.

The initial trial price is a **numerical starting point for the price search**, not a parameter that changes the underlying equilibrium. Changing Initial pX therefore changes the path of trial prices and usually the number of adjustments required to clear the market. For a fixed period population and preferences, the process should still converge to the same equilibrium price.

For example, period 1 has an equilibrium of `pX = 1`. Starting at `pX = 1` clears immediately, while starting below or above 1 requires tâtonnement adjustments before reaching the same equilibrium.

The adjustment-speed parameter `lambda` controls how large each price response is:

\[
p_{X,t+1}=p_{X,t}\left[1+\lambda\frac{z_X(t)}{\bar X}\right].
\]

A smaller `lambda` therefore produces smaller price changes and slower numerical convergence, while leaving the equilibrium unchanged. In the canonical first period with Initial pX = 0.5, `lambda = 1.0` converges in 25 adjustments whereas `lambda = 0.1` requires 355 adjustments under the default tolerance.

No physical transfer occurs during price discovery. Agents repeatedly calculate optimal demands at trial prices, aggregate excess demand is measured, and the relative price changes until both markets clear within tolerance.

Using the same initial trial price every period is intentional. Economy 0.3 does not yet give prices memory from one period to the next.

## Settlement and ledger time stamps

After a period converges, the same deterministic settlement rule from Economy 0.2 matches net sellers to net buyers in population order.

Economy 0.3 adds explicit time labels to the ledger:

- `period` identifies the exchange period;
- `trade_id` equals the period number because each period has one market-clearing settlement event;
- `transaction_id` remains globally unique across the complete multi-period run.

This makes every physical transfer traceable both within a period and across the full simulation horizon.

## Stock-flow accounting

For every agent, good, and period:

\[
\text{closing stock}_{i,g,t}
=
\text{opening stock}_{i,g,t}
+
\text{net ledger flow}_{i,g,t}.
\]

Within every period:

- aggregate X is conserved;
- aggregate Y is conserved;
- aggregate net flow of each good is zero.

Across periods, the model does **not** impose a stock carry-over identity because opening endowments are exogenous resets.

## Configuration rules

An Economy 0.3 scenario may supply an arbitrary non-empty sequence of period populations, subject to four restrictions:

1. agent identities and ordering remain fixed;
2. Cobb-Douglas preference parameters remain fixed;
3. aggregate X remains fixed across periods;
4. aggregate Y remains fixed across periods.

These restrictions isolate the new mechanism to **distribution changing through time**.

## Streamlit interface

The Economy 0.3 page is mobile-first and uses progressive disclosure. The default Overview shows the cross-period equilibrium-price path and a compact status strip. It also displays the selected period's **Start pX**, **Equilibrium pX**, and **Adjustments** so the price-search configuration is visible without opening a detailed table.

The Market view shows the full within-period tâtonnement path from the configured starting price to equilibrium. It displays `lambda` explicitly and uses comparable price and adjustment axes for ordinary runs. This prevents automatic chart scaling from making a 25-adjustment path and a 355-adjustment path look artificially similar.

Agent, accounting, and ledger details remain available through the compact drill-down views and full audit expanders.

For periods after the first, the interface explicitly compares the previous period's closing stocks with the new period's opening endowments so the exogenous reset is visible rather than implicit.

## Version boundary

Economy 0.3 adds **time indexing only**.

It does not yet add:

- carry-over inventories;
- consumption between periods;
- saving or capital accumulation;
- income flows;
- production;
- money;
- credit;
- uncertainty.

Those mechanisms should be introduced separately so their accounting and economic effects remain independently testable.
