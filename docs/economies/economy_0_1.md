# Economy 0.1 — Walrasian Price Discovery

## What this version adds

Economy 0.1 keeps the pure-exchange economy from Economy 0 and adds exactly one mechanism: **Walrasian tâtonnement**, a standard textbook price-adjustment process.

Everything else is unchanged:

- two agents: Alice and Bob
- two goods: X and Y
- Cobb-Douglas utility maximization
- fixed initial endowments
- no money
- no production
- no government, banking, or stochastic behavior
- trade is recorded in the same append-only ledger
- stock-flow identities must reconcile exactly

Economy 0 remains separately runnable.

## Why add tâtonnement?

Economy 0 computes the market-clearing relative price analytically. That is useful because it gives us a trusted textbook benchmark, but it does not show how a market might search for that price.

Economy 0.1 therefore starts from a **trial price** rather than the known equilibrium price.

At each iteration:

1. a trial price for X is announced;
2. each agent calculates wealth at that trial price;
3. each agent chooses the Cobb-Douglas utility-maximizing bundle;
4. aggregate demand for X is compared with the fixed supply of X;
5. the price rises if there is excess demand and falls if there is excess supply;
6. the process repeats until excess demand is numerically negligible.

No trade takes place during this search. Settlement occurs only after the price-discovery process has converged.

## Textbook rule

Let

\[
z_X(p_t)=D_X(p_t)-\bar X
\]

be excess demand for X at trial price \(p_t\), where \(\bar X\) is total available X.

The core Walrasian tâtonnement principle is:

\[
\Delta p_X \propto z_X.
\]

A price rises when its market has excess demand and falls when its market has excess supply.

For the discrete simulator we use the normalized proportional form:

\[
p_{t+1}
=
p_t\left(1+\lambda\frac{z_X(p_t)}{\bar X}\right),
\qquad 0<\lambda\le1.
\]

The normalization by total X makes the adjustment-speed parameter \(\lambda\) dimensionless. It is a numerical scale convention; it does not change the equilibrium price. With positive Cobb-Douglas demands and \(0<\lambda\le1\), trial prices remain positive.

The default Economy 0.1 experiment uses:

- initial trial price \(p_X=0.5\)
- numeraire price \(p_Y=1\)
- adjustment speed \(\lambda=1\)

The adjustment speed is an experiment parameter, not a calibrated economic parameter.

## Benchmark versus discovery

Economy 0 already gives the analytic market-clearing benchmark:

\[
p_X^*
=
\frac{\sum_i \alpha_i y_i^0}
{\sum_i(1-\alpha_i)x_i^0}.
\]

Economy 0.1 displays this benchmark so we can verify the numerical price-discovery process. **The tâtonnement algorithm does not use this benchmark to update prices.** It sees only the current trial price and excess demand.

For the canonical Economy 0 endowments and preferences, the benchmark remains:

\[
p_X^*=1,\qquad p_Y=1.
\]

Tâtonnement should converge to the same relative price and therefore to the same final allocation as Economy 0.

## Trading and accounting

During tâtonnement, holdings do not change. Agents only submit desired bundles at announced trial prices.

After convergence, the barter settlement is recorded using explicit ledger entries. For the canonical case this is still:

1. Alice transfers approximately 0.5 X to Bob.
2. Bob transfers approximately 0.5 Y to Alice.

The word “approximately” refers only to floating-point numerical tolerance. The regression tests require the discovered solution to agree with the analytic benchmark to tight numerical precision.

For every agent and good:

\[
\text{Closing stock}
=
\text{Opening stock}
+
\text{Net transaction flows}.
\]

Total X and total Y remain conserved.

## Interactive laboratory

The Streamlit page for Economy 0.1 lets you change:

- Alice and Bob's endowments
- Alice and Bob's Cobb-Douglas preference weights
- the initial trial price for X
- the tâtonnement adjustment speed

You can then inspect the price search iteration by iteration, including:

- trial price
- supply
- aggregate demand
- excess demand
- direction of the next price movement
- the full price path
- the analytic Economy 0 benchmark for comparison
- final transaction settlement and stock-flow accounting

## Interpretation caveat

Walrasian tâtonnement is a **theoretical benchmark**, not a claim that real-world markets literally operate through a single auctioneer who forbids trade until equilibrium is found. Its purpose here is pedagogical: it introduces a standard general-equilibrium price-adjustment mechanism while changing only one feature of Economy 0.

## Not yet included

Economy 0.1 still has no:

- money
- production
- firms or labour
- saving or capital
- banks or credit
- government or central bank
- database
- stochastic behavior
- repeated economic periods

Those mechanisms belong to later economies.
