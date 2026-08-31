# Economy 0.3 — Repeated pure exchange through redistribution

Economy 0.3 introduces one new mechanism only: **explicit time through repeated exchange periods**.

The economic structure inside each period is unchanged from Economy 0.2:

- a user-selected balanced population of heterogeneous agents;
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

## Balanced agent pairs

The Streamlit experiment lets the user choose any **even** number of agents from 2 through 20.

For this teaching baseline, agents always come in mirrored pairs. Within each pair:

- one agent's X endowment is the other's Y endowment;
- one agent's Y endowment is the other's X endowment; and
- their Cobb-Douglas preference weights add to 1.

Settings expose one preference parameter for every pair: the first agent's `alpha`, or preference weight for X. The partner automatically receives `1 - alpha`. For example, choosing `alpha = 0.35` for Agent 1 makes Agent 2's alpha `0.65`.

Because endowments and preferences are mirrored together, each complete pair contributes equal aggregate X and Y and remains balanced around the benchmark relative price `pX = 1`, even when the pair's alpha is changed. The historical ten-agent Economy 0.2 population is exactly the default 10-agent case. For populations above ten, the same five deterministic endowment-pair types repeat with new agent names.

This pairing is an **experimental design convention**, not a mathematical restriction of pure exchange. The underlying Economy 0.2 engine still accepts arbitrary populations, including odd numbers. Economy 0.3 deliberately offers only complete pairs so changing population size or a mirrored pair's preference does not accidentally introduce a new baseline price effect.

Changing either the number of agents or any pair alpha resets the interactive experiment to Baseline because those choices redefine the population to which later redistributions apply.

## Baseline first, then user-defined redistribution

The default Economy 0.3 experiment contains only one period: **Baseline**. The default population has ten agents, while Settings can select another even paired population and can change the mirrored pair preferences.

The user decides whether time should continue. A new period is created by choosing:

- one agent to give up Y;
- one different agent to receive Y; and
- the amount of Y to move.

The transfer defines the next period's **exogenous opening endowments**. It is not a market transaction and therefore does not appear in the settlement ledger.

Every user-created period preserves:

- the same agent identities and ordering;
- the same Cobb-Douglas preference parameters;
- every agent's X endowment;
- aggregate X equal to the selected number of agents; and
- aggregate Y equal to the selected number of agents.

Only the distribution of Y changes. The user may add as many redistribution periods as desired, remove the latest one, or reset the experiment to Baseline.

## Why redistribution can change the equilibrium price

With Y as the numeraire, every period has the same textbook analytic benchmark:

\[
p_{X,t}^* =
\frac{\sum_i \alpha_i y_{i,t}}
{\sum_i (1-\alpha_i)x_i},
\qquad p_Y = 1.
\]

Because X endowments and preferences remain fixed within an experiment, the denominator does not change across user-created periods. What changes is:

\[
\sum_i \alpha_i y_{i,t}.
\]

This is the Y endowment weighted by each agent's preference for X. Moving Y toward agents with higher `alpha` tends to raise the demand pressure for X and therefore raises the equilibrium relative price of X. Moving Y toward lower-alpha agents tends to do the opposite.

The Streamlit Overview displays this weighted quantity alongside the equilibrium-price change so the causal mechanism is visible directly.

## Price discovery inside each period

Every period starts from the configured initial trial price and runs the same normalized Walrasian tâtonnement rule as Economy 0.2.

The initial trial price is a **numerical starting point for the price search**, not a parameter that changes the underlying equilibrium. Changing Initial pX therefore changes the path of trial prices and usually the number of adjustments required to clear the market.

The adjustment-speed parameter `lambda` controls the size of each price response to excess demand. Smaller lambda means smaller price moves and therefore more tâtonnement adjustments, while the equilibrium for a fixed period remains unchanged.

Pair alpha is different from Initial pX and lambda: alpha changes agents' preferences and therefore changes their desired bundles. The mirrored-pair construction keeps the unredistributed Baseline at `pX = 1`, but after Y is redistributed the chosen alphas determine how strongly the new distribution affects demand pressure and equilibrium price.

No physical transfer occurs during price discovery. Agents repeatedly calculate optimal demands at trial prices, aggregate excess demand is measured, and the relative price changes until both markets clear within tolerance.

Using the same Initial pX and lambda in every period is intentional. Economy 0.3 does not yet give prices memory from one period to the next.

## Settlement and ledger time stamps

After a period converges, the same deterministic settlement rule from Economy 0.2 matches net sellers to net buyers in population order.

Settlement uses the declared numerical tolerance as an economic cutoff. Residual desired transfers smaller than that tolerance are treated as numerical round-off rather than as meaningful physical transactions, so the ledger does not contain rows such as `0.0000000002 X`. The resulting closing allocation still matches the theoretical target within the model's stated tolerance, while stock-flow accounting remains exact for every transfer that is actually recorded.

Economy 0.3 keeps three identifiers internally:

- `period` identifies the exchange period;
- `transaction_id` identifies one actual physical transfer and remains globally unique across the complete experiment; and
- `trade_id` groups the transfers belonging to one settlement event. In Economy 0.3 there is exactly one settlement event per period, so `trade_id` currently equals `period`.

Because `trade_id` carries no extra information for the user in Economy 0.3, the normal Streamlit ledger hides it and shows only `transaction_id`, `period`, `good`, `quantity`, `sender`, and `receiver`. The internal field is retained for later economies where one period may contain multiple separate settlement events.

This makes every economically meaningful physical transfer traceable without exposing redundant implementation detail.

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

The app uses a narrower interaction rule on top of that general engine: the Baseline is constructed from complete mirrored pairs, Settings may redefine those pair preferences before the experiment begins, and each new period moves Y between two existing agents while holding all X endowments and alphas fixed.

## Legacy four-period example

The original Economy 0.3 implementation used a deterministic four-period schedule created by rotating the baseline Y vector across the canonical ten agents. That schedule remains available through `canonical_period_populations()` so the completed historical example remains reproducible and testable.

It is no longer the default app experience because the arbitrary rotation made the price path harder to interpret. The current default instead lets the user create the redistribution that causes each new period.

## Streamlit interface

The Economy 0.3 page is mobile-first and deliberately compact.

The primary flow is:

`Choose paired population → Baseline → Add a redistribution → Compare`

The top-level views are only:

- `Overview` — equilibrium change, changed Y endowments, weighted X-demand pressure, and accounting status;
- `Market` — the full within-period tâtonnement path and final clearing check; and
- `Audit` — agent decisions, stock-flow accounts, settlement ledger, exogenous reset, and the complete multi-period ledger.

Settings use a full-width inline expander directly in the page. All numeric choices use the same number-input pattern with `− / +` controls: Number of agents changes by two, Initial pX changes by 0.1, lambda changes by 0.1, and each pair alpha changes by 0.05. For every visible pair, the user chooses the first agent's alpha and the partner automatically uses `1 - alpha`.

Submitting **Apply and close** applies the settings and closes the panel. Changing agent count or any pair alpha resets redistribution history to Baseline; changing only Initial pX or lambda preserves the existing redistribution history because those two settings change only the numerical price-search path.

The selected result is shown in one full-width responsive block rather than several narrow metric cards. It displays the number of agents, exact equilibrium `pX`, percentage change from the previous step when relevant, and market/accounting status.

When multiple redistributions exist, the Overview price-history chart uses a disclosed zoomed vertical axis so small relative-price changes remain visible. The exact numerical `pX` remains visible above the chart, so the zoom improves readability without replacing the quantitative result.

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
