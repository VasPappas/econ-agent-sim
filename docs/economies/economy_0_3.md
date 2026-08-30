# Economy 0.3 — Repeated pure exchange through redistribution

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

`exogenous opening endowments → price discovery → settlement → closing stocks`

The next period begins from another exogenous endowment schedule. Closing stocks from period `t` do **not** become opening stocks in period `t + 1`.

That boundary is deliberate. Economy 0.3 introduces a time index without yet introducing intertemporal wealth accumulation, saving, consumption, or inventory carry-over.

## Baseline first, then user-defined redistribution

The default Economy 0.3 experiment now contains only one period: **Baseline**. It reproduces the canonical Economy 0.2 population exactly.

The user decides whether time should continue. A new period is created by choosing:

- one agent to give up Y;
- one different agent to receive Y; and
- the amount of Y to move.

The transfer defines the next period's **exogenous opening endowments**. It is not a market transaction and therefore does not appear in the settlement ledger.

Every user-created period preserves:

- the same agent identities and ordering;
- the same Cobb-Douglas preference parameters;
- every agent's X endowment;
- aggregate X = 10; and
- aggregate Y = 10.

Only the distribution of Y changes. The user may add as many redistribution periods as desired, remove the latest one, or reset the experiment to Baseline.

## Why redistribution can change the equilibrium price

With Y as the numeraire, every period has the same textbook analytic benchmark:

\[
p_{X,t}^* =
\frac{\sum_i \alpha_i y_{i,t}}
{\sum_i (1-\alpha_i)x_i},
\qquad p_Y = 1.
\]

Because X endowments and preferences remain fixed, the denominator does not change across user-created periods. What changes is:

\[
\sum_i \alpha_i y_{i,t}.
\]

This is the Y endowment weighted by each agent's preference for X. Moving Y toward agents with higher `alpha` tends to raise the demand pressure for X and therefore raises the equilibrium relative price of X. Moving Y toward lower-alpha agents tends to do the opposite.

The Streamlit Overview displays this weighted quantity alongside the equilibrium-price change so the causal mechanism is visible directly.

## Price discovery inside each period

Every period starts from the configured initial trial price and runs the same normalized Walrasian tâtonnement rule as Economy 0.2.

The initial trial price is a **numerical starting point for the price search**, not a parameter that changes the underlying equilibrium. Changing Initial pX therefore changes the path of trial prices and usually the number of adjustments required to clear the market.

The adjustment-speed parameter `lambda` controls the size of each price response to excess demand. Smaller lambda means smaller price moves and therefore more tâtonnement adjustments, while the equilibrium for a fixed period remains unchanged.

No physical transfer occurs during price discovery. Agents repeatedly calculate optimal demands at trial prices, aggregate excess demand is measured, and the relative price changes until both markets clear within tolerance.

Using the same Initial pX and lambda in every period is intentional. Economy 0.3 does not yet give prices memory from one period to the next.

## Settlement and ledger time stamps

After a period converges, the same deterministic settlement rule from Economy 0.2 matches net sellers to net buyers in population order.

Economy 0.3 adds explicit time labels to the ledger:

- `period` identifies the exchange period;
- `trade_id` equals the period number because each period has one market-clearing settlement event; and
- `transaction_id` remains globally unique across the complete multi-period experiment.

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
- aggregate Y is conserved; and
- aggregate net flow of each good is zero.

Across periods, the model does **not** impose a stock carry-over identity because each opening endowment schedule is exogenous.

## Configuration rules

An Economy 0.3 scenario may supply an arbitrary non-empty sequence of period populations, subject to four restrictions:

1. agent identities and ordering remain fixed;
2. Cobb-Douglas preference parameters remain fixed;
3. aggregate X remains fixed across periods; and
4. aggregate Y remains fixed across periods.

The app uses a narrower interaction rule on top of that general engine: each new period moves Y between two existing agents while holding all X endowments fixed.

## Legacy four-period example

The original Economy 0.3 implementation used a deterministic four-period schedule created by rotating the baseline Y vector across agents. That schedule remains available through `canonical_period_populations()` so the completed historical example remains reproducible and testable.

It is no longer the default app experience because the arbitrary rotation made the price path harder to interpret. The current default instead lets the user create the redistribution that causes each new period.

## Streamlit interface

The Economy 0.3 page is mobile-first and deliberately compact.

The primary flow is:

`Baseline → Add a redistribution → Compare`

The top-level views are only:

- `Overview` — equilibrium change, changed Y endowments, weighted X-demand pressure, and accounting status;
- `Market` — the full within-period tâtonnement path and final clearing check; and
- `Audit` — agent decisions, stock-flow accounts, settlement ledger, exogenous reset, and the complete multi-period ledger.

The interface follows the rule **result first, explanation second, audit detail third**.

## Version boundary

Economy 0.3 adds **time indexing through user-chosen exogenous redistribution only**.

It does not yet add:

- carry-over inventories;
- consumption between periods;
- saving or capital accumulation;
- income flows;
- production;
- money;
- credit; or
- uncertainty.

Those mechanisms should be introduced separately so their accounting and economic effects remain independently testable.
