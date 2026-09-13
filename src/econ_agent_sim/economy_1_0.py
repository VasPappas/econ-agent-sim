"""Two separately funded price-taking firms and immutable economic accounts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, fields
from math import fsum, isfinite, nextafter, sqrt
from types import MappingProxyType

from econ_agent_sim.numerics import require_finite

MONEY = "Money"
GOOD = "X"
CAPITAL = "Capital"
LABOR = "Labor"
TOLERANCE = 1e-9


def _freeze(value):
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


class _FrozenMappings:
    def __post_init__(self) -> None:
        for field in fields(self):
            object.__setattr__(self, field.name, _freeze(getattr(self, field.name)))


@dataclass(frozen=True)
class Household:
    id: str
    name: str
    money: float = 1.0
    consumption_priority: float = 1.0
    money_priority: float = 1.0
    leisure_priority: float = 1.0

    def __post_init__(self) -> None:
        require_finite("Household settings", self.money, *self.scores.values())
        if not self.id.strip() or not self.name.strip():
            raise ValueError("Use a household ID and name.")
        if self.money < 0 or min(self.scores.values()) <= 0:
            raise ValueError(
                "Household money must be non-negative and priorities positive."
            )
        if (
            min(self.weights.values()) <= 0
            or max(self.weights.values()) >= 1
            or not 0 < self.alpha < 1
        ):
            raise ValueError("The relative priorities exceed numerical precision.")

    @property
    def scores(self) -> dict[str, float]:
        return {
            "consumption": self.consumption_priority,
            "money": self.money_priority,
            "leisure": self.leisure_priority,
        }

    @property
    def weights(self) -> dict[str, float]:
        scale = max(self.scores.values())
        normalized = {key: value / scale for key, value in self.scores.items()}
        total = fsum(normalized.values())
        return {key: value / total for key, value in normalized.items()}

    @property
    def alpha(self) -> float:
        scale = max(self.consumption_priority, self.money_priority)
        consumption = self.consumption_priority / scale
        return consumption / (consumption + self.money_priority / scale)


@dataclass(frozen=True)
class Firm:
    id: str
    name: str
    money: float = 0.5
    productivity: float = 2.0
    theta: float = 0.5
    capital: float = 0.5
    reinvestment_rate: float = 0.4
    depreciation_rate: float = 0.1

    def __post_init__(self) -> None:
        require_finite(
            "Firm settings",
            self.money,
            self.productivity,
            self.theta,
            self.capital,
            self.reinvestment_rate,
            self.depreciation_rate,
        )
        if not self.id.strip() or not self.name.strip():
            raise ValueError("Use a firm ID and name.")
        if min(self.money, self.productivity, self.capital) <= 0:
            raise ValueError("Firm money, productivity and capital must be positive.")
        if self.theta != 0.5:
            raise ValueError("Economy 1.0 uses a fixed labor exponent of 0.5.")
        if not 0 <= self.reinvestment_rate < 1 or not 0 <= self.depreciation_rate < 1:
            raise ValueError(
                "Reinvestment and capital wear must lie from zero to below 100%."
            )


def default_households(count: int = 2) -> list[dict]:
    if type(count) is not int or count < 1:
        raise ValueError("Use at least one household.")
    return [
        asdict(Household(f"household_{i + 1}", f"Household {i + 1}"))
        for i in range(count)
    ]


def default_firms() -> list[dict]:
    return [asdict(Firm("firm_a", "Firm A")), asdict(Firm("firm_b", "Firm B"))]


@dataclass(frozen=True)
class Economy10Transfer:
    transaction_id: int
    pair_id: int
    period: int
    kind: str
    asset: str
    quantity: float
    sender: str
    receiver: str
    sender_id: str
    receiver_id: str
    unit: str
    valuation_price: float


@dataclass(frozen=True)
class Economy10Event:
    event_id: int
    period: int
    kind: str
    entity: str
    entity_id: str
    asset: str
    quantity: float
    unit: str
    valuation_price: float
    value: float
    opening_valuation_price: float | None = None


@dataclass(frozen=True)
class HouseholdFirmAllocation:
    household_id: str
    firm_id: str
    ownership_share: float
    dividends: float
    wages: float
    work: float
    purchases: float
    consumption: float
    ownership_value_open: float
    ownership_value_close: float


@dataclass(frozen=True)
class FirmAccount:
    id: str
    name: str
    work: float
    output: float
    sales_quantity: float
    sales_share: float
    production_share: float
    wage_bill: float
    sales_received: float
    production_value: float
    gross_operating_surplus: float
    net_operating_profit: float
    investment_quantity: float
    investment_value: float
    depreciation_quantity: float
    depreciation_value: float
    capital_open: float
    capital_close: float
    capital_price_open: float
    capital_price_close: float
    capital_value_open: float
    capital_value_close: float
    holding_gain: float
    equity_open: float
    equity_close: float
    retained_earnings_open: float
    retained_earnings_close: float
    revaluation_reserve_open: float
    revaluation_reserve_close: float
    contributed_equity: float
    dividends_paid: float
    operating_cash: float
    next_dividend_budget: float
    opening_cash: float
    closing_cash: float
    funding_binding: bool
    marginal_revenue_product: float
    minimum_cash: float


@dataclass(frozen=True)
class Economy10Period(_FrozenMappings):
    number: int
    households: tuple[Household, ...]
    firms: tuple[Firm, ...]
    ownership: Mapping[str, Mapping[str, float]]
    opening_cash: Mapping[str, float]
    post_dividend_cash: Mapping[str, float]
    closing_cash: Mapping[str, float]
    price: float
    wage: float
    work: Mapping[str, float]
    leisure: Mapping[str, float]
    wages: Mapping[str, float]
    dividends: Mapping[str, float]
    consumption: Mapping[str, float]
    purchases: Mapping[str, float]
    firm_accounts: Mapping[str, FirmAccount]
    allocations: tuple[HouseholdFirmAllocation, ...]
    transfers: tuple[Economy10Transfer, ...]
    events: tuple[Economy10Event, ...]
    checks: Mapping[str, bool]
    solution: Mapping

    @property
    def prices(self) -> dict[str, float]:
        return {GOOD: self.price, MONEY: 1.0, LABOR: self.wage}

    @property
    def produced(self) -> dict[str, float]:
        return {key: account.output for key, account in self.firm_accounts.items()}

    @property
    def consumed(self) -> Mapping[str, float]:
        return self.consumption

    def _sum(self, name: str) -> float:
        return fsum(getattr(account, name) for account in self.firm_accounts.values())


# Aggregate properties intentionally have the same economic meaning as the
# preceding chapter. Firm identity always lives in the plural account mapping.
for _field in (
    "output",
    "wage_bill",
    "sales_received",
    "production_value",
    "gross_operating_surplus",
    "net_operating_profit",
    "investment_quantity",
    "investment_value",
    "depreciation_quantity",
    "depreciation_value",
    "capital_open",
    "capital_close",
    "capital_value_open",
    "capital_value_close",
    "holding_gain",
    "equity_open",
    "equity_close",
    "retained_earnings_open",
    "retained_earnings_close",
    "revaluation_reserve_open",
    "revaluation_reserve_close",
    "contributed_equity",
    "dividends_paid",
    "operating_cash",
    "next_dividend_budget",
):
    setattr(
        Economy10Period, _field, property(lambda self, name=_field: self._sum(name))
    )


def _close(a: float, b: float, scale: float = 0.0) -> bool:
    return abs(a - b) <= TOLERANCE * max(abs(a), abs(b), abs(scale))


def _dividend(profit: float, cash: float, protected: float) -> float:
    return min(max(profit, 0.0), max(cash - protected, 0.0))


def _solve_market(households, firms, available, funding, capital):
    """Monotone goods residual with exact active-prefix payroll inversion.

    Money is normalized by available household cash; production capacity is
    normalized before squaring. Every solution is subsequently certified using
    the original unnormalized household, production and funding equations.
    """
    scale = fsum(available.values())
    if not isfinite(scale) or scale <= 0:
        raise ValueError("Households need positive finite cash after dividends.")
    cash = {h.id: available[h.id] / scale for h in households}
    caps = {f.id: funding[f.id] / scale for f in firms}
    capacity = {f.id: f.productivity * sqrt(capital[f.id]) for f in firms}
    require_finite(
        "Normalized firm funding and capacity", *caps.values(), *capacity.values()
    )
    largest = max(capacity.values())
    relative = {key: (value / largest) ** 2 for key, value in capacity.items()}
    if min(caps.values()) <= 0 or min(relative.values()) <= 0:
        raise ValueError(
            "Relative firm funding or production capacity is below numerical precision."
        )
    gamma = {h.id: h.weights["leisure"] for h in households}
    thresholds = sorted(
        (gamma[h.id] * cash[h.id] / (1 - gamma[h.id]), h.id) for h in households
    )

    def household_payroll(total):
        active = []
        wage = 0.0
        for threshold, key in thresholds:
            if active and wage <= threshold:
                break
            active.append(key)
            wage = (total + fsum(gamma[k] * cash[k] for k in active)) / fsum(
                1 - gamma[k] for k in active
            )
        wages = {
            h.id: max(0.0, (1 - gamma[h.id]) * wage - gamma[h.id] * cash[h.id])
            for h in households
        }
        return wage, wages

    def evaluate(psi):
        unconstrained = {key: value * psi for key, value in relative.items()}
        payroll = {key: min(value, caps[key]) for key, value in unconstrained.items()}
        # sqrt(x)*sqrt(y) avoids the avoidable overflowing product x*y.
        values = {
            key: 2 * sqrt(unconstrained[key]) * sqrt(payroll[key]) for key in payroll
        }
        wage, wages = household_payroll(fsum(payroll.values()))
        sales = fsum(
            (1 - f.reinvestment_rate) * values[f.id]
            + f.reinvestment_rate * payroll[f.id]
            for f in firms
        )
        spending = fsum(h.alpha * (cash[h.id] + wages[h.id]) for h in households)
        require_finite("Market residual", sales, spending, wage)
        return sales - spending, wage, wages, payroll

    low, high, iterations = 0.0, 1.0, 0
    while evaluate(high)[0] <= 0:
        high *= 2
        iterations += 1
        if not isfinite(high) or iterations > 1024:
            raise ValueError("The positive market equilibrium exceeds numerical range.")
    for _ in range(180):
        middle = low + (high - low) / 2
        if middle in (low, high):
            break
        if evaluate(middle)[0] > 0:
            high = middle
        else:
            low = middle
        iterations += 1
    candidates = [
        (abs(evaluate(value)[0]), value) for value in (low, high) if value > 0
    ]
    _, psi = min(candidates)
    residual, normalized_wage, normalized_wages, normalized_bills = evaluate(psi)
    wage = normalized_wage * scale
    price = (2 * sqrt(psi) * sqrt(normalized_wage) / largest) * scale
    wages = {key: value * scale for key, value in normalized_wages.items()}
    bills = {
        key: min(value * scale, funding[key]) for key, value in normalized_bills.items()
    }
    require_finite(
        "Market prices and payroll", wage, price, *wages.values(), *bills.values()
    )
    if min(price, wage, *bills.values()) <= 0:
        raise ValueError(
            "The equilibrium price, wage or firm payroll is below numerical precision."
        )
    return (
        price,
        wage,
        wages,
        bills,
        {
            "method": "cash_and_capacity_normalized_scalar",
            "iterations": iterations,
            "normalized_residual": residual,
            "tolerance": TOLERANCE,
        },
    )


def _split(amount: float, weights: Mapping[str, float]) -> dict[str, float]:
    """Allocate a funded total proportionally, with a bounded final residual.

    Stable IDs make the final rounding recipient independent of display order.
    The largest weight receives the residual to avoid erasing tiny participants.
    """
    if amount == 0:
        return {key: 0.0 for key in weights}
    total = fsum(weights.values())
    if total <= 0:
        raise ValueError("A positive allocation requires positive weights.")
    last = max(weights, key=lambda key: (weights[key], key))
    allocation = {
        key: amount * (weights[key] / total) for key in sorted(weights) if key != last
    }
    allocation[last] = amount - fsum(allocation.values())
    if allocation[last] < 0 or not _close(
        allocation[last], amount * (weights[last] / total), amount
    ):
        raise ValueError("The proportional allocation exceeds numerical precision.")
    for _ in range(4):
        if fsum(allocation.values()) <= amount:
            break
        allocation[last] = nextafter(allocation[last], 0.0)
    if fsum(allocation.values()) > amount:
        raise ValueError("The funded allocation could not be reconciled.")
    return allocation


def advance_competition_period(
    households: tuple[Household, ...],
    firms: tuple[Firm, ...],
    previous: Economy10Period | None = None,
) -> Economy10Period:
    """Solve and settle one candidate without mutating accepted history."""
    try:
        return _advance_period(tuple(households), tuple(firms), previous)
    except (OverflowError, ZeroDivisionError) as error:
        raise ValueError(
            "This economy exceeded numerical range; no period completed."
        ) from error


def _advance_period(households, firms, previous):
    if not households or len(firms) != 2:
        raise ValueError("Provide households and exactly two firms.")
    ids = [item.id for item in (*households, *firms)]
    if len(ids) != len(set(ids)):
        raise ValueError("Households and firms need globally unique stable IDs.")
    if fsum(h.money for h in households) <= 0:
        raise ValueError("Initial aggregate household money must be positive.")
    if previous is not None and (
        {h.id: h for h in households} != {h.id: h for h in previous.households}
        or {f.id: f for f in firms} != {f.id: f for f in previous.firms}
    ):
        raise ValueError("Restart the economy before changing submitted settings.")
    # All arithmetic and residual placement uses stable order, not UI order.
    ordered_h = tuple(sorted(households, key=lambda item: item.id))
    ordered_f = tuple(sorted(firms, key=lambda item: item.id))
    number = 1 if previous is None else previous.number + 1
    opening = (
        dict(previous.closing_cash)
        if previous
        else {item.id: item.money for item in (*ordered_h, *ordered_f)}
    )
    capital = {
        f.id: previous.firm_accounts[f.id].capital_close if previous else f.capital
        for f in ordered_f
    }
    require_finite("Opening stocks", *opening.values(), *capital.values())
    if min(opening.values()) < 0 or min(capital.values()) <= 0:
        raise ValueError("Opening cash must be non-negative and capital positive.")
    names = {item.id: item.name for item in (*ordered_h, *ordered_f)}
    initial_total = fsum(opening.values())
    cash_terms = {key: [value] for key, value in opening.items()}
    cash = dict(opening)
    transfers = []
    events = []
    pair_count = 0
    minimum_cash = {f.id: opening[f.id] for f in ordered_f}
    funded = True
    conserved_each_transfer = True

    def transfer(kind, asset, quantity, sender, receiver, pair_id, price=1.0):
        nonlocal funded, conserved_each_transfer
        require_finite("Transfer", quantity, price)
        if quantity < 0 or sender == receiver:
            raise ValueError(
                "Transfers require positive quantities and distinct parties."
            )
        if quantity == 0:
            return 0.0
        if asset == MONEY:
            if quantity > cash[sender]:
                if not _close(quantity, cash[sender]):
                    raise ValueError(
                        "A transfer exceeds the sender's own available money."
                    )
                # Paired delivery is based on the actual funded consideration.
                quantity = cash[sender]
            # The displayed running balance is one rounded float, while its
            # accurately summed ledger terms can lie just below that float.
            # Lower the payment by an ulp if needed; never floor a negative
            # closing balance or inject cash into the sender's account.
            requested = quantity
            for _ in range(8):
                if fsum((*cash_terms[sender], -quantity)) >= 0:
                    break
                quantity = nextafter(quantity, 0.0)
            if not _close(quantity, requested):
                raise ValueError("The funded payment exceeds numerical precision.")
            cash_terms[sender].append(-quantity)
            cash_terms[receiver].append(quantity)
            cash[sender] = fsum(cash_terms[sender])
            cash[receiver] = fsum(cash_terms[receiver])
            funded &= cash[sender] >= 0
            if not funded:
                raise ValueError(
                    "A funded payment could not be represented without borrowing."
                )
            conserved_each_transfer &= _close(fsum(cash.values()), initial_total)
            for key, minimum in minimum_cash.items():
                minimum_cash[key] = min(minimum, cash[key])
        transfers.append(
            Economy10Transfer(
                len(transfers) + 1,
                pair_id,
                number,
                kind,
                asset,
                quantity,
                names[sender],
                names[receiver],
                sender,
                receiver,
                "Money"
                if asset == MONEY
                else "work units"
                if asset == LABOR
                else "X units",
                price,
            )
        )
        return quantity

    def event(kind, entity, asset, quantity, value, price, opening_price=None):
        require_finite("Noncash event", quantity, value, price)
        events.append(
            Economy10Event(
                len(events) + 1,
                number,
                kind,
                names[entity],
                entity,
                asset,
                quantity,
                "capital units" if asset == CAPITAL else "X units",
                price,
                value,
                opening_price,
            )
        )

    share = 1 / len(ordered_h)
    ownership = {h.id: {f.id: share for f in ordered_f} for h in ordered_h}
    allocated_dividends = {}
    dividends_paid = {}
    for firm in ordered_f:
        profit = (
            previous.firm_accounts[firm.id].net_operating_profit if previous else 0.0
        )
        dividend = _dividend(profit, opening[firm.id], firm.money)
        split = _split(dividend, {h.id: 1.0 for h in ordered_h})
        for h in ordered_h:
            pair_count += 1
            allocated_dividends[h.id, firm.id] = transfer(
                "dividend", MONEY, split[h.id], firm.id, h.id, pair_count
            )
        dividends_paid[firm.id] = fsum(
            allocated_dividends[h.id, firm.id] for h in ordered_h
        )
    post_dividend = dict(cash)
    available = {h.id: cash[h.id] for h in ordered_h}
    funding = {f.id: cash[f.id] for f in ordered_f}
    if min(funding.values()) <= 0:
        raise ValueError("Each firm needs positive cash after its own dividends.")
    price, wage, desired_wages, desired_bills, solution = _solve_market(
        ordered_h, ordered_f, available, funding, capital
    )
    allocated_wages = {}
    allocated_work = {}
    for firm in ordered_f:
        split = _split(desired_bills[firm.id], desired_wages)
        for h in ordered_h:
            pair_count += 1
            payment = transfer("wage", MONEY, split[h.id], firm.id, h.id, pair_count)
            allocated_wages[h.id, firm.id] = payment
            allocated_work[h.id, firm.id] = transfer(
                "labor_delivery", LABOR, payment / wage, h.id, firm.id, pair_count, wage
            )
    wages = {
        h.id: fsum(allocated_wages[h.id, f.id] for f in ordered_f) for h in ordered_h
    }
    work = {
        h.id: fsum(allocated_work[h.id, f.id] for f in ordered_f) for h in ordered_h
    }
    leisure = {key: 1 - value for key, value in work.items()}
    labor = {
        f.id: fsum(allocated_work[h.id, f.id] for h in ordered_h) for f in ordered_f
    }
    bills = {
        f.id: fsum(allocated_wages[h.id, f.id] for h in ordered_h) for f in ordered_f
    }
    output = {
        f.id: f.productivity * sqrt(capital[f.id]) * sqrt(labor[f.id])
        for f in ordered_f
    }
    values = {key: price * quantity for key, quantity in output.items()}
    gross = {key: values[key] - bills[key] for key in output}
    investment_value = {f.id: f.reinvestment_rate * gross[f.id] for f in ordered_f}
    investment = {key: value / price for key, value in investment_value.items()}
    offered = {key: output[key] - investment[key] for key in output}
    require_finite(
        "Production and investment",
        *labor.values(),
        *output.values(),
        *values.values(),
        *gross.values(),
        *investment.values(),
        *offered.values(),
    )
    if min(*labor.values(), *output.values(), *gross.values(), *offered.values()) <= 0:
        raise ValueError(
            "Firm labor, production and operating surplus must remain positive."
        )
    for firm in ordered_f:
        event("production", firm.id, GOOD, output[firm.id], values[firm.id], price)
    allocated_purchases = {}
    allocated_consumption = {}
    for h in ordered_h:
        desired_purchase = h.alpha * cash[h.id]
        split = _split(desired_purchase, offered)
        for firm in ordered_f:
            pair_count += 1
            payment = transfer(
                "goods_payment", MONEY, split[firm.id], h.id, firm.id, pair_count
            )
            allocated_purchases[h.id, firm.id] = payment
            allocated_consumption[h.id, firm.id] = transfer(
                "goods_delivery",
                GOOD,
                payment / price,
                firm.id,
                h.id,
                pair_count,
                price,
            )
    purchases = {
        h.id: fsum(allocated_purchases[h.id, f.id] for f in ordered_f)
        for h in ordered_h
    }
    consumption = {
        h.id: fsum(allocated_consumption[h.id, f.id] for f in ordered_f)
        for h in ordered_h
    }
    dividends = {
        h.id: fsum(allocated_dividends[h.id, f.id] for f in ordered_f)
        for h in ordered_h
    }
    for h in ordered_h:
        event("consumption", h.id, GOOD, consumption[h.id], purchases[h.id], price)
    accounts = {}
    for firm in ordered_f:
        key = firm.id
        prior = previous.firm_accounts[key] if previous else None
        sold = fsum(allocated_consumption[h.id, key] for h in ordered_h)
        received = fsum(allocated_purchases[h.id, key] for h in ordered_h)
        wear = firm.depreciation_rate * capital[key]
        wear_value = price * wear
        profit = gross[key] - wear_value
        closing_capital = (1 - firm.depreciation_rate) * capital[key] + investment[key]
        opening_price = previous.price if previous else price
        opening_value = opening_price * capital[key]
        closing_value = price * closing_capital
        gain = (price - opening_price) * capital[key]
        opening_equity = opening[key] + opening_value
        closing_equity = cash[key] + closing_value
        retained_open = prior.retained_earnings_close if prior else 0.0
        retained_close = retained_open + profit - dividends_paid[key]
        reserve_open = prior.revaluation_reserve_close if prior else 0.0
        reserve_close = reserve_open + gain
        contributed = prior.contributed_equity if prior else opening_equity
        next_dividend = _dividend(profit, cash[key], firm.money)
        mrp = 0.5 * values[key] / labor[key]
        binding = (
            _close(bills[key], funding[key]) and mrp > wage and not _close(mrp, wage)
        )
        account = FirmAccount(
            key,
            firm.name,
            labor[key],
            output[key],
            sold,
            sold / fsum(consumption.values()),
            output[key] / fsum(output.values()),
            bills[key],
            received,
            values[key],
            gross[key],
            profit,
            investment[key],
            investment_value[key],
            wear,
            wear_value,
            capital[key],
            closing_capital,
            opening_price,
            price,
            opening_value,
            closing_value,
            gain,
            opening_equity,
            closing_equity,
            retained_open,
            retained_close,
            reserve_open,
            reserve_close,
            contributed,
            dividends_paid[key],
            funding[key],
            next_dividend,
            opening[key],
            cash[key],
            binding,
            mrp,
            minimum_cash[key],
        )
        require_finite(
            "Firm closing accounts",
            *(
                getattr(account, f.name)
                for f in fields(account)
                if f.name not in {"id", "name", "funding_binding"}
            ),
        )
        if closing_capital <= 0:
            raise ValueError("Closing capital has fallen below numerical precision.")
        accounts[key] = account
        event("capital_wear", key, CAPITAL, wear, wear_value, price)
        event(
            "capital_installation",
            key,
            CAPITAL,
            investment[key],
            investment_value[key],
            price,
        )
        event("revaluation", key, CAPITAL, capital[key], gain, price, opening_price)
    allocations = tuple(
        HouseholdFirmAllocation(
            h.id,
            f.id,
            share,
            allocated_dividends[h.id, f.id],
            allocated_wages[h.id, f.id],
            allocated_work[h.id, f.id],
            allocated_purchases[h.id, f.id],
            allocated_consumption[h.id, f.id],
            accounts[f.id].equity_open * share,
            accounts[f.id].equity_close * share,
        )
        for h in ordered_h
        for f in ordered_f
    )

    def summed(field):
        return fsum(getattr(a, field) for a in accounts.values())

    household_optimality = []
    for h in ordered_h:
        key = h.id
        g = h.weights["leisure"]
        resources = available[key] + wages[key]
        benefit = (1 - g) * wage * leisure[key]
        cost = g * resources
        household_optimality.append(
            resources > 0
            and leisure[key] > 0
            and (
                _close(benefit, cost)
                if work[key] > 0
                else benefit <= cost or _close(benefit, cost)
            )
            and _close(purchases[key], h.alpha * resources)
            and _close(cash[key], (1 - h.alpha) * resources)
        )
    checks = {
        "continuity": previous is None
        or (
            opening == previous.closing_cash
            and all(
                capital[f.id] == previous.firm_accounts[f.id].capital_close
                for f in ordered_f
            )
        ),
        "payments_funded": funded,
        "wages_funded": all(bills[key] <= funding[key] for key in bills),
        "no_borrowing": min(cash.values()) >= 0 and min(minimum_cash.values()) >= 0,
        "money_conserved": conserved_each_transfer
        and _close(fsum(cash.values()), initial_total),
        "labor_market": _close(fsum(work.values()), fsum(labor.values())),
        "goods_market": all(
            _close(a.output, a.sales_quantity + a.investment_quantity)
            for a in accounts.values()
        ),
        "household_budgets": all(
            _close(available[h.id] + wages[h.id], purchases[h.id] + cash[h.id])
            for h in ordered_h
        ),
        "household_optimality": all(household_optimality),
        "time_bounds": all(0 <= value < 1 for value in work.values()),
        "ledger_accounts": all(
            _close(
                opening[key]
                + fsum(
                    t.quantity
                    for t in transfers
                    if t.asset == MONEY and t.receiver_id == key
                ),
                cash[key]
                + fsum(
                    t.quantity
                    for t in transfers
                    if t.asset == MONEY and t.sender_id == key
                ),
            )
            for key in cash
        ),
        "paired_transfers": all(
            _close(
                t.quantity,
                fsum(
                    u.quantity * u.valuation_price
                    for u in transfers
                    if u.pair_id == t.pair_id and u.asset != MONEY
                ),
            )
            for t in transfers
            if t.asset == MONEY and t.kind != "dividend"
        ),
        "dividend_rule": all(
            _close(
                a.dividends_paid,
                _dividend(
                    previous.firm_accounts[f.id].net_operating_profit
                    if previous
                    else 0.0,
                    opening[f.id],
                    f.money,
                ),
            )
            for f in ordered_f
            for a in [accounts[f.id]]
        ),
        "firm_cash": all(
            _close(
                a.opening_cash + a.sales_received,
                a.closing_cash + a.wage_bill + a.dividends_paid,
            )
            for a in accounts.values()
        ),
        "firm_optimality": all(
            _close(a.wage_bill, min(0.5 * a.production_value, a.operating_cash))
            for a in accounts.values()
        ),
        "production": all(
            _close(
                accounts[f.id].output,
                f.productivity * sqrt(capital[f.id]) * sqrt(accounts[f.id].work),
            )
            for f in ordered_f
        ),
        "investment_policy": all(
            _close(
                accounts[f.id].investment_value,
                f.reinvestment_rate * accounts[f.id].gross_operating_surplus,
            )
            for f in ordered_f
        ),
        "capital_units": all(
            _close(
                a.capital_open + a.investment_quantity,
                a.capital_close + a.depreciation_quantity,
            )
            for a in accounts.values()
        ),
        "capital_value": all(
            _close(
                a.capital_value_close + a.depreciation_value,
                a.capital_value_open + a.investment_value + a.holding_gain,
                a.capital_value_open,
            )
            for a in accounts.values()
        ),
        "gross_income": all(
            _close(a.production_value, a.wage_bill + a.gross_operating_surplus)
            for a in accounts.values()
        ),
        "net_income": all(
            _close(
                a.production_value,
                a.wage_bill + a.net_operating_profit + a.depreciation_value,
            )
            for a in accounts.values()
        ),
        "equity_bridge": all(
            _close(
                a.equity_close + a.dividends_paid,
                a.equity_open + a.net_operating_profit + a.holding_gain,
                a.equity_open,
            )
            for a in accounts.values()
        ),
        "equity_components": all(
            _close(
                a.equity_close,
                a.contributed_equity
                + a.retained_earnings_close
                + a.revaluation_reserve_close,
                a.contributed_equity,
            )
            for a in accounts.values()
        ),
        "saving_investment": _close(
            fsum(wages.values())
            + fsum(dividends.values())
            - fsum(purchases.values())
            + summed("net_operating_profit")
            - summed("dividends_paid"),
            summed("investment_value") - summed("depreciation_value"),
            summed("production_value"),
        ),
        "ownership": all(
            _close(fsum(ownership[h.id][f.id] for h in ordered_h), 1.0)
            for f in ordered_f
        ),
    }
    if not all(checks.values()):
        failed = ", ".join(key for key, passed in checks.items() if not passed)
        raise ValueError(
            f"Economy 1.0 did not reconcile ({failed}); no period completed."
        )
    solution.update(
        {
            "total_labor": fsum(work.values()),
            "working_households": sum(value > 0 for value in work.values()),
            "resting_households": sum(value == 0 for value in work.values()),
            "relative_market_error": abs(
                summed("output")
                - fsum(consumption.values())
                - summed("investment_quantity")
            )
            / summed("output"),
            "firm_funding": {
                key: {
                    "binding": a.funding_binding,
                    "operating_cash": a.operating_cash,
                    "minimum_cash": a.minimum_cash,
                    "marginal_revenue_product": a.marginal_revenue_product,
                }
                for key, a in accounts.items()
            },
        }
    )
    return Economy10Period(
        number,
        households,
        firms,
        ownership,
        opening,
        post_dividend,
        dict(cash),
        price,
        wage,
        work,
        leisure,
        wages,
        dividends,
        consumption,
        purchases,
        accounts,
        allocations,
        tuple(transfers),
        tuple(events),
        checks,
        solution,
    )
