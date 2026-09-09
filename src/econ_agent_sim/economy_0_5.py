"""One good and valued money balances, with simultaneous competitive clearing."""

from dataclasses import asdict, dataclass
from functools import cached_property
from math import fsum, isclose

from econ_agent_sim.economy_0_4 import MonetaryTrade, MonetaryTransaction
from econ_agent_sim.numerics import require_finite

ASSETS = ("X", "Money")
TOLERANCE = 1e-9


@dataclass(frozen=True)
class MoneyAgent:
    name: str
    x: float = 1.0
    money: float = 1.0
    alpha: float = .5

    def __post_init__(self):
        require_finite("Starting balances and preferences", self.x, self.money, self.alpha)
        if not self.name.strip() or self.x < 0 or self.money < 0:
            raise ValueError("Use a name and non-negative starting balances.")
        if not 0 < self.alpha < 1:
            raise ValueError("Preference for the good must lie strictly between 0 and 1.")


def default_money_agents(count=2):
    return [asdict(MoneyAgent(f"Agent {i + 1}")) for i in range(count)]


def matches(a, b):
    # Both amounts are in the same asset units; allow accumulated roundoff.
    return isclose(a, b, rel_tol=TOLERANCE, abs_tol=1e-10)


@dataclass(frozen=True)
class MoneyResult:
    population: tuple[MoneyAgent, ...]
    prices: dict
    opening_stocks: dict
    desired_bundles: dict
    closing_stocks: dict
    trades: tuple[MonetaryTrade, ...]
    transactions: tuple[MonetaryTransaction, ...]


def run_money_economy(population: tuple[MoneyAgent, ...]) -> MoneyResult:
    if not population or len({a.name for a in population}) != len(population):
        raise ValueError("Provide agents with unique names.")
    total_x, total_m = fsum(a.x for a in population), fsum(a.money for a in population)
    require_finite("Aggregate balances", total_x, total_m)
    if total_x <= 0 or total_m <= 0:
        raise ValueError("The economy needs a positive total of both X and Money.")
    # x*=alpha*(p*x0+m0)/p; market clearing gives this analytic price.
    denominator = fsum((1 - a.alpha) * a.x for a in population)
    numerator = fsum(a.alpha * a.money for a in population)
    if denominator <= 0 or numerator <= 0:
        raise ValueError("Starting balances are too small for a finite interior price.")
    price = numerator / denominator
    require_finite("Price", price)
    if price <= 0:
        raise ValueError("Price must be positive.")
    opening = {a.name: {"X": a.x, "Money": a.money} for a in population}
    desired = {}
    for a in population:
        wealth = price * a.x + a.money
        require_finite("Wealth", wealth)
        desired[a.name] = {"X": a.alpha * wealth / price, "Money": (1 - a.alpha) * wealth}
        require_finite("Desired balances", *desired[a.name].values())
    closing = {name: dict(stocks) for name, stocks in opening.items()}
    # Large economies must not discard a small agent's meaningful demand.
    epsilon = min(1e-12 * total_x, 1e-12)
    buyers, sellers = [], []
    for a in population:
        net = desired[a.name]["X"] - a.x
        if net > epsilon:
            buyers.append([a.name, net])
        elif net < -epsilon:
            sellers.append([a.name, -net])
    trades, ledger = [], []
    i = j = 0
    while i < len(buyers) and j < len(sellers):
        buyer, wanted = buyers[i]
        seller, offered = sellers[j]
        quantity = min(wanted, offered, closing[seller]["X"], closing[buyer]["Money"] / price)
        payment = quantity * price
        if quantity <= 0 or payment > closing[buyer]["Money"]:
            raise ValueError("Could not settle within available goods and money.")
        trade_id = len(trades) + 1
        trades.append(MonetaryTrade(trade_id, 1, "X", quantity, price, seller, buyer, payment))
        ledger.extend((
            MonetaryTransaction(len(ledger) + 1, trade_id, 1, "X", quantity, seller, buyer),
            MonetaryTransaction(len(ledger) + 2, trade_id, 1, "Money", payment, buyer, seller),
        ))
        closing[seller]["X"] -= quantity
        closing[buyer]["X"] += quantity
        closing[buyer]["Money"] -= payment
        closing[seller]["Money"] += payment
        buyers[i][1] -= quantity
        sellers[j][1] -= quantity
        if buyers[i][1] <= epsilon:
            i += 1
        if sellers[j][1] <= epsilon:
            j += 1
    result = MoneyResult(population, {"X": price, "Money": 1.0}, opening, desired,
                         closing, tuple(trades), tuple(ledger))
    # Reconstruct ledger independently of mutable settlement balances.
    for row in account_rows(result):
        assert matches(row["opening"] + row["net flow"], row["closing"]), "Ledger mismatch"
        assert matches(row["closing"], desired[row["agent"]][row["asset"]]), "Unsettled demand"
        assert row["closing"] >= 0, "Borrowing is not allowed"
        require_finite("Final balance", row["closing"])
    for asset in ASSETS:
        assert matches(fsum(s[asset] for s in opening.values()),
                       fsum(s[asset] for s in closing.values())), "Conservation failed"
    return result


def account_rows(result):
    flows = {name: {asset: {"received": 0.0, "sent": 0.0} for asset in ASSETS}
             for name in result.opening_stocks}
    for t in result.transactions:
        flows[t.sender][t.asset]["sent"] += t.quantity
        flows[t.receiver][t.asset]["received"] += t.quantity
    rows = []
    for name, opening in result.opening_stocks.items():
        for asset in ASSETS:
            flow = flows[name][asset]
            net = flow["received"] - flow["sent"]
            close = result.closing_stocks[name][asset]
            rows.append({"agent": name, "asset": asset, "opening": opening[asset],
                         **flow, "net flow": net, "closing": close,
                         "check": opening[asset] + net - close})
    return rows


@dataclass(frozen=True)
class MoneyRun:
    result: MoneyResult
    previous: MoneyResult | None
    number: int
    revision: int

    @property
    def period(self):
        return self.result

    @cached_property
    def data(self):
        r, prior = self.result, self.previous
        totals = {key: {asset: fsum(s[asset] for s in stocks.values()) for asset in ASSETS}
                  for key, stocks in (("opening", r.opening_stocks), ("closing", r.closing_stocks))}
        rows = account_rows(r)
        conservation = {a: matches(totals["opening"][a], totals["closing"][a]) for a in ASSETS}
        market_error = abs(fsum(s["X"] for s in r.desired_bundles.values()) - totals["opening"]["X"]) / totals["opening"]["X"]
        return {
            "model": "money_in_utility", "assets": list(ASSETS),
            "label": f"Run {self.number}", "revision": self.revision,
            "settings": {"agent_count": len(r.population)}, "prices": r.prices,
            "previous_run": ({"number": self.number - 1, "prices": prior.prices,
                              "agents": [asdict(a) for a in prior.population]} if prior else None),
            "price_x_change_percent": 100 * (r.prices["X"] / prior.prices["X"] - 1) if prior else None,
            "setup_changes": (["Same setup as the previous run." if r.population == prior.population
                               else "Starting quantities, money or preferences changed; compare the submitted agents."]
                              if prior else ["First run · no previous result to compare."]),
            "agents": [{"name": a.name, "alpha": a.alpha, "opening": r.opening_stocks[a.name],
                        "closing": r.closing_stocks[a.name], "desired": r.desired_bundles[a.name]}
                       for a in r.population],
            "trades": [dict(ordinal=i + 1, **asdict(t)) for i, t in enumerate(r.trades)],
            "totals": totals, "conservation": conservation,
            "market_error": market_error, "clearing_tolerance": TOLERANCE,
            "gross_money_payments": fsum(t.payment for t in r.trades),
            "checks": {"market": market_error <= TOLERANCE, "money": conservation["Money"],
                       "goods": conservation["X"],
                       "accounts": all(matches(row["opening"] + row["net flow"], row["closing"]) for row in rows),
                       "no_borrowing": all(s[a] >= 0 for s in r.closing_stocks.values() for a in ASSETS)},
            "run_rule": "Independent experiments. Starting goods and money are conserved. No borrowing, production or money creation.",
        }

    def context(self, trade_index=None):
        trades = self.data["trades"]
        selected = trades[trade_index] if type(trade_index) is int and 0 <= trade_index < len(trades) else None
        return {**self.data, "selected_trade": selected}
