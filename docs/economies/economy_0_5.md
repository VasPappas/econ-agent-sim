# Economy 0.5 — Good and Money

An alternative minimal monetary economy: one divisible good X and a fixed stock
of money. Agents explicitly value final money balances, not only consumption.
This money-in-utility assumption is not a theory of money's emergence or a model
of future purchases. There is no production, borrowing, banking or money creation.

Agent i maximizes `x^alpha * m^(1-alpha)` subject to `p*x+m=p*x0+m0`,
with non-negative holdings and `0 < alpha < 1`. Thus desired holdings are
`x*=alpha*(p*x0+m0)/p` and `m*=(1-alpha)*(p*x0+m0)`.
Clearing the good market gives `p=sum(alpha*m0)/sum((1-alpha)*x0)`.
Positive aggregate goods and money are required. A zero-wealth agent stays at zero.
This chapter solves the price directly, without a simulated price-search path.

Each net buyer pays from starting cash and each net seller receives money. One sale
creates exactly two ledger entries: X to the buyer and Money to the seller.
The engine verifies ledger reconciliation, conservation, non-negative final stocks,
and agreement with desired allocations. MonetaryTrade/MonetaryTransaction records
are shared with 0.4, but 0.4's unconstrained monetary settlement is not reused.

The default is two agents with 1 X, 1 Money, and alpha=.5: price 1 and no trade.
Each agent's money, goods and preference can be edited. Runs are independent;
drafts, previous results and reset are isolated from the 0.4 chapter.
Shared Results render only X and Money, and Ask why selects model-specific rules.
The prior two-good chapter remains available with its original economic behavior.
