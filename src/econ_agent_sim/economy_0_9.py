"""A funded firm, own-account investment, and linked economic accounts.

Money settles actual wages, dividends and purchases. New capital is physical
output retained by the firm; it is neither a self-sale nor a cash payment.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, fields
from functools import cached_property
from math import fsum, isfinite, nextafter
from types import MappingProxyType

from econ_agent_sim.numerics import require_finite

MONEY = "Money"
GOOD = "X"
CAPITAL = "Capital"
FIRM_NAME = "Firm"
TOLERANCE = 1e-9


@dataclass(frozen=True)
class Household:
    name: str
    money: float = 1.0
    consumption_priority: float = 1.0
    money_priority: float = 1.0
    leisure_priority: float = 1.0

    def __post_init__(self) -> None:
        require_finite("Household settings", self.money, *self.scores.values())
        if not self.name.strip():
            raise ValueError("Use a household name.")
        if self.money < 0:
            raise ValueError("Household money must be non-negative.")
        if min(self.scores.values()) <= 0:
            raise ValueError("Household priorities must be positive.")
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
        normalized = {name: value / scale for name, value in self.scores.items()}
        total = fsum(normalized.values())
        return {name: value / total for name, value in normalized.items()}

    @property
    def alpha(self) -> float:
        scale = max(self.consumption_priority, self.money_priority)
        consumption = self.consumption_priority / scale
        return consumption / (consumption + self.money_priority / scale)


@dataclass(frozen=True)
class Firm:
    name: str = FIRM_NAME
    money: float = 1.0
    productivity: float = 2.0
    theta: float = 0.5
    capital: float = 1.0
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
        if not self.name.strip():
            raise ValueError("Use a firm name.")
        if min(self.money, self.productivity, self.capital) <= 0:
            raise ValueError(
                "Firm operating money, productivity and capital must be positive."
            )
        if not 0 < self.theta < 1:
            raise ValueError("The labor exponent must lie between zero and one.")
        if not 0 <= self.reinvestment_rate < 1:
            raise ValueError("Reinvestment must be at least zero and below 100%.")
        if not 0 <= self.depreciation_rate < 1:
            raise ValueError("Capital wear must be at least zero and below 100%.")


def default_households(count: int = 2) -> list[dict]:
    if type(count) is not int or count < 1:
        raise ValueError("Use at least one household.")
    return [asdict(Household(f"Household {index + 1}")) for index in range(count)]


def default_firm() -> dict:
    return asdict(Firm())


@dataclass(frozen=True)
class Economy09Transfer:
    transaction_id: int
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
class Economy09Event:
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
class Economy09Period:
    number: int
    households: tuple[Household, ...]
    firm: Firm
    ownership: Mapping[str, float]
    opening_cash: Mapping[str, float]
    post_dividend_cash: Mapping[str, float]
    price: float
    wage: float
    work: Mapping[str, float]
    leisure: Mapping[str, float]
    wages: Mapping[str, float]
    dividends: Mapping[str, float]
    consumption: Mapping[str, float]
    purchases: Mapping[str, float]
    output: float
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
    closing_cash: Mapping[str, float]
    transfers: tuple[Economy09Transfer, ...]
    events: tuple[Economy09Event, ...]
    checks: Mapping[str, bool]
    solution: Mapping

    def __post_init__(self) -> None:
        # A submitted snapshot must not change when a setup draft is edited.
        for field in fields(self):
            value = getattr(self, field.name)
            if isinstance(value, dict):
                object.__setattr__(self, field.name, MappingProxyType(dict(value)))

    @property
    def prices(self) -> dict[str, float]:
        return {GOOD: self.price, MONEY: 1.0, "Labor": self.wage}

    @property
    def produced(self) -> dict[str, float]:
        return {self.firm.name: self.output}

    @property
    def consumed(self) -> Mapping[str, float]:
        return self.consumption


def _close(a: float, b: float, scale: float = 0.0) -> bool:
    """Relative reconciliation, including explicit scales for net quantities."""
    return abs(a - b) <= TOLERANCE * max(abs(a), abs(b), abs(scale))


def _dividend(net_profit: float, firm_cash: float, protected_float: float) -> float:
    return min(max(net_profit, 0.0), max(firm_cash - protected_float, 0.0))


def _solve_wage(
    households: tuple[Household, ...],
    available_cash: dict[str, float],
    operating_cash: float,
    kappa: float,
) -> tuple[float, dict[str, float], int]:
    """Bracket the monotone wage equation in household-cash-normalized units."""
    scale = fsum(available_cash.values())
    if scale <= 0 or not isfinite(scale):
        raise ValueError(
            "Households need positive finite aggregate cash after dividends."
        )
    normalized = {name: cash / scale for name, cash in available_cash.items()}
    funding = operating_cash / scale
    weights = {household.name: household.weights for household in households}

    def bills(wage: float, cash: dict[str, float]) -> dict[str, float]:
        return {
            household.name: max(
                0.0,
                (1 - weights[household.name]["leisure"]) * wage
                - weights[household.name]["leisure"] * cash[household.name],
            )
            for household in households
        }

    def residual(wage: float) -> float:
        payments = bills(wage, normalized)
        sales = fsum(
            household.alpha * (normalized[household.name] + payments[household.name])
            for household in households
        )
        return fsum(payments.values()) - min(kappa * sales, funding)

    low, high, iterations = 0.0, 1.0, 0
    while residual(high) <= 0:
        high *= 2
        iterations += 1
        if not isfinite(high) or iterations > 1024:
            raise ValueError("A positive equilibrium wage could not be bracketed.")
    for _ in range(160):
        midpoint = (low + high) / 2
        if midpoint in (low, high):
            break
        if residual(midpoint) > 0:
            high = midpoint
        else:
            low = midpoint
        iterations += 1
    wage = low * scale
    wages = bills(wage, available_cash)
    # Use the feasible side of the root. Conversion back to currency units can
    # round a binding payroll up by an ulp; lower the wage, never add cash.
    for _ in range(8):
        if fsum(wages.values()) <= operating_cash:
            break
        wage = nextafter(wage, 0.0)
        wages = bills(wage, available_cash)
    require_finite("Equilibrium wage and wage bills", wage, *wages.values())
    if wage <= 0:
        raise ValueError("The equilibrium wage is below numerical precision.")
    return wage, wages, iterations


def advance_investment_period(
    households: tuple[Household, ...],
    firm: Firm,
    previous: Economy09Period | None = None,
) -> Economy09Period:
    """Compute, settle and validate a period before returning its frozen snapshot."""
    try:
        return _advance_investment_period(households, firm, previous)
    except (OverflowError, ZeroDivisionError) as error:
        raise ValueError(
            "This economy exceeded numerical range; no period completed."
        ) from error


def _advance_investment_period(
    households: tuple[Household, ...],
    firm: Firm,
    previous: Economy09Period | None,
) -> Economy09Period:
    households = tuple(households)
    if not households:
        raise ValueError("Provide at least one household.")
    names = tuple(household.name for household in households)
    if len(set(names)) != len(names) or firm.name in names:
        raise ValueError("Households and the firm need unique names.")
    if fsum(household.money for household in households) <= 0:
        raise ValueError("Initial aggregate household money must be positive.")
    if previous is not None and (
        households != previous.households or firm != previous.firm
    ):
        raise ValueError(
            "Restart the economy before changing household or firm settings."
        )
    number = 1 if previous is None else previous.number + 1
    opening_cash = (
        dict(previous.closing_cash)
        if previous
        else {
            **{household.name: household.money for household in households},
            firm.name: firm.money,
        }
    )
    capital_open = firm.capital if previous is None else previous.capital_close
    require_finite("Opening balances", capital_open, *opening_cash.values())
    if capital_open <= 0 or min(opening_cash.values()) < 0:
        raise ValueError("Opening capital must be positive and cash non-negative.")
    ownership = {name: 1 / len(households) for name in names}
    dividends_paid = _dividend(
        previous.net_operating_profit if previous else 0.0,
        opening_cash[firm.name],
        firm.money,
    )
    dividends = {name: dividends_paid * ownership[name] for name in names}
    dividends_paid = fsum(dividends.values())
    operating_cash = opening_cash[firm.name] - dividends_paid
    if operating_cash <= 0:
        raise ValueError("The firm needs positive cash after dividends.")
    post_dividend_cash = {
        **{name: opening_cash[name] + dividends[name] for name in names},
        firm.name: operating_cash,
    }
    available_cash = {name: post_dividend_cash[name] for name in names}
    rate = firm.reinvestment_rate
    kappa = firm.theta / (1 - rate * (1 - firm.theta))
    wage, wages, iterations = _solve_wage(
        households,
        available_cash,
        operating_cash,
        kappa,
    )
    wage_bill = fsum(wages.values())
    work = {name: wages[name] / wage for name in names}
    leisure = {name: 1 - work[name] for name in names}
    total_labor = fsum(work.values())
    output = (
        firm.productivity * capital_open ** (1 - firm.theta) * total_labor**firm.theta
    )
    require_finite("Labor and output", total_labor, output)
    if total_labor <= 0 or output <= 0:
        raise ValueError("Labor or production has fallen below numerical precision.")
    purchases = {
        household.name: household.alpha
        * (available_cash[household.name] + wages[household.name])
        for household in households
    }
    sales_received = fsum(purchases.values())
    production_value = (sales_received - rate * wage_bill) / (1 - rate)
    price = production_value / output
    gross_operating_surplus = production_value - wage_bill
    investment_value = rate * gross_operating_surplus
    investment_quantity = investment_value / price
    consumption = {name: purchases[name] / price for name in names}
    depreciation_quantity = firm.depreciation_rate * capital_open
    depreciation_value = price * depreciation_quantity
    net_operating_profit = gross_operating_surplus - depreciation_value
    capital_close = (1 - firm.depreciation_rate) * capital_open + investment_quantity
    capital_price_open = previous.price if previous else price
    capital_value_open = capital_price_open * capital_open
    capital_value_close = price * capital_close
    holding_gain = (price - capital_price_open) * capital_open
    require_finite(
        "Goods, prices and capital accounts",
        price,
        production_value,
        gross_operating_surplus,
        investment_quantity,
        investment_value,
        depreciation_quantity,
        depreciation_value,
        net_operating_profit,
        capital_close,
        capital_value_open,
        capital_value_close,
        holding_gain,
        *purchases.values(),
        *consumption.values(),
    )
    if price <= 0 or capital_close <= 0 or gross_operating_surplus < 0:
        raise ValueError(
            "A positive price, capital and operating surplus are required."
        )

    party_ids = {name: f"household_{index + 1}" for index, name in enumerate(names)}
    party_ids[firm.name] = "firm"
    transfers: list[Economy09Transfer] = []
    events: list[Economy09Event] = []
    closing_cash = dict(opening_cash)
    opening_total = fsum(opening_cash.values())
    money_conserved_each_transfer = True
    payments_funded = True
    minimum_firm_cash = opening_cash[firm.name]

    def transfer(
        kind: str, asset: str, quantity: float, sender: str, receiver: str
    ) -> None:
        nonlocal money_conserved_each_transfer, payments_funded, minimum_firm_cash
        if quantity == 0:
            return
        require_finite("Transfer quantity", quantity)
        if quantity < 0 or sender == receiver:
            raise ValueError(
                "A transfer needs a positive quantity and distinct parties."
            )
        transfers.append(
            Economy09Transfer(
                len(transfers) + 1,
                number,
                kind,
                asset,
                quantity,
                sender,
                receiver,
                party_ids[sender],
                party_ids[receiver],
                "Money" if asset == MONEY else "X units",
                1.0 if asset == MONEY else price,
            )
        )
        if asset == MONEY:
            payments_funded &= closing_cash[sender] >= quantity or _close(
                closing_cash[sender], quantity
            )
            closing_cash[sender] -= quantity
            closing_cash[receiver] += quantity
            money_conserved_each_transfer &= _close(
                fsum(closing_cash.values()),
                opening_total,
            )
            minimum_firm_cash = min(minimum_firm_cash, closing_cash[firm.name])

    def event(
        kind: str,
        entity: str,
        asset: str,
        quantity: float,
        value: float,
        opening_price: float | None = None,
    ) -> None:
        events.append(
            Economy09Event(
                len(events) + 1,
                number,
                kind,
                entity,
                party_ids[entity],
                asset,
                quantity,
                "capital units" if asset == CAPITAL else "X units",
                price,
                value,
                opening_price,
            )
        )

    for name in names:
        transfer("dividend", MONEY, dividends[name], firm.name, name)
    for name in names:
        transfer("wage", MONEY, wages[name], firm.name, name)
    event("production", firm.name, GOOD, output, production_value)
    for name in names:
        transfer("goods_payment", MONEY, purchases[name], name, firm.name)
        transfer("goods_delivery", GOOD, consumption[name], firm.name, name)
    for name in names:
        event("consumption", name, GOOD, consumption[name], purchases[name])
    event("capital_wear", firm.name, CAPITAL, depreciation_quantity, depreciation_value)
    event(
        "capital_installation",
        firm.name,
        CAPITAL,
        investment_quantity,
        investment_value,
    )
    event(
        "revaluation",
        firm.name,
        CAPITAL,
        capital_open,
        holding_gain,
        capital_price_open,
    )

    equity_open = opening_cash[firm.name] + capital_value_open
    equity_close = closing_cash[firm.name] + capital_value_close
    retained_earnings_open = previous.retained_earnings_close if previous else 0.0
    retained_earnings_close = (
        retained_earnings_open + net_operating_profit - dividends_paid
    )
    revaluation_reserve_open = previous.revaluation_reserve_close if previous else 0.0
    revaluation_reserve_close = revaluation_reserve_open + holding_gain
    contributed_equity = previous.contributed_equity if previous else equity_open
    next_dividend_budget = _dividend(
        net_operating_profit, closing_cash[firm.name], firm.money
    )
    require_finite(
        "Closing money and equity",
        *closing_cash.values(),
        equity_open,
        equity_close,
        retained_earnings_close,
        revaluation_reserve_close,
        next_dividend_budget,
    )
    marginal_revenue_product = firm.theta * production_value / total_labor
    funding_binding = (
        _close(wage_bill, operating_cash)
        and firm.theta * production_value > wage_bill
        and not _close(firm.theta * production_value, wage_bill)
    )
    household_optimality = []
    for household in households:
        name = household.name
        g = household.weights["leisure"]
        resources = available_cash[name] + wages[name]
        if resources <= 0 or leisure[name] <= 0:
            household_optimality.append(False)
            continue
        benefit = (1 - g) * wage * leisure[name]
        cost = g * resources
        household_optimality.append(
            _close(benefit, cost)
            if work[name] > 0
            else benefit <= cost or _close(benefit, cost)
        )
    ledger_accounts = all(
        _close(
            opening_cash[name]
            + fsum(
                item.quantity
                for item in transfers
                if item.asset == MONEY and item.receiver == name
            ),
            closing_cash[name]
            + fsum(
                item.quantity
                for item in transfers
                if item.asset == MONEY and item.sender == name
            ),
        )
        for name in closing_cash
    )
    consumed = fsum(consumption.values())
    household_saving = wage_bill + dividends_paid - sales_received
    checks = {
        "continuity": previous is None
        or (
            opening_cash == previous.closing_cash
            and capital_open == previous.capital_close
        ),
        "dividend_rule": _close(
            dividends_paid,
            _dividend(
                previous.net_operating_profit if previous else 0.0,
                opening_cash[firm.name],
                firm.money,
            ),
        ),
        "payments_funded": payments_funded,
        "wages_funded": wage_bill <= operating_cash
        or _close(wage_bill, operating_cash),
        "no_borrowing": min(closing_cash.values()) >= 0,
        "money_conserved": money_conserved_each_transfer,
        "goods_market": _close(output, consumed + investment_quantity),
        "capital_units": _close(
            capital_open + investment_quantity, capital_close + depreciation_quantity
        ),
        "household_budgets": all(
            _close(
                available_cash[name] + wages[name],
                purchases[name] + closing_cash[name],
            )
            for name in names
        ),
        "household_optimality": all(household_optimality),
        "ledger_accounts": ledger_accounts
        and _close(
            fsum(item.quantity for item in transfers if item.kind == "goods_delivery"),
            consumed,
        ),
        "firm_cash": _close(
            opening_cash[firm.name] + sales_received,
            closing_cash[firm.name] + wage_bill + dividends_paid,
        ),
        "investment_policy": _close(investment_value, rate * gross_operating_surplus),
        "gross_income": _close(production_value, wage_bill + gross_operating_surplus),
        "net_income": _close(
            production_value, wage_bill + net_operating_profit + depreciation_value
        ),
        "firm_optimality": _close(
            wage_bill, min(firm.theta * production_value, operating_cash)
        ),
        "capital_value": _close(
            capital_value_close + depreciation_value,
            capital_value_open + investment_value + holding_gain,
            capital_value_open,
        ),
        "equity_bridge": _close(
            equity_close + dividends_paid,
            equity_open + net_operating_profit + holding_gain,
            equity_open,
        ),
        "equity_components": _close(
            equity_close,
            contributed_equity + retained_earnings_close + revaluation_reserve_close,
            contributed_equity,
        ),
        "saving_investment": _close(
            household_saving + net_operating_profit - dividends_paid,
            investment_value - depreciation_value,
            production_value,
        ),
        "time_bounds": all(0 <= labor < 1 for labor in work.values()),
    }
    if not all(checks.values()):
        failed = ", ".join(name for name, passed in checks.items() if not passed)
        raise ValueError(
            f"Economy 0.9 did not reconcile ({failed}); no period completed."
        )
    solution = {
        "method": "household_cash_normalized_scalar",
        "iterations": iterations,
        "total_labor": total_labor,
        "working_households": sum(labor > 0 for labor in work.values()),
        "resting_households": sum(labor == 0 for labor in work.values()),
        "operating_cash": operating_cash,
        "protected_operating_float": firm.money,
        "minimum_firm_cash": minimum_firm_cash,
        "funding_binding": funding_binding,
        "marginal_revenue_product": marginal_revenue_product,
        "investment_output_share": investment_quantity / output,
        "kappa": kappa,
        "relative_market_error": abs(output - consumed - investment_quantity) / output,
        "tolerance": TOLERANCE,
    }
    return Economy09Period(
        number=number,
        households=households,
        firm=firm,
        ownership=ownership,
        opening_cash=opening_cash,
        post_dividend_cash=post_dividend_cash,
        price=price,
        wage=wage,
        work=work,
        leisure=leisure,
        wages=wages,
        dividends=dividends,
        consumption=consumption,
        purchases=purchases,
        output=output,
        wage_bill=wage_bill,
        sales_received=sales_received,
        production_value=production_value,
        gross_operating_surplus=gross_operating_surplus,
        net_operating_profit=net_operating_profit,
        investment_quantity=investment_quantity,
        investment_value=investment_value,
        depreciation_quantity=depreciation_quantity,
        depreciation_value=depreciation_value,
        capital_open=capital_open,
        capital_close=capital_close,
        capital_price_open=capital_price_open,
        capital_price_close=price,
        capital_value_open=capital_value_open,
        capital_value_close=capital_value_close,
        holding_gain=holding_gain,
        equity_open=equity_open,
        equity_close=equity_close,
        retained_earnings_open=retained_earnings_open,
        retained_earnings_close=retained_earnings_close,
        revaluation_reserve_open=revaluation_reserve_open,
        revaluation_reserve_close=revaluation_reserve_close,
        contributed_equity=contributed_equity,
        dividends_paid=dividends_paid,
        operating_cash=operating_cash,
        next_dividend_budget=next_dividend_budget,
        closing_cash=closing_cash,
        transfers=tuple(transfers),
        events=tuple(events),
        checks=checks,
        solution=solution,
    )


def investment_report(
    periods: tuple[Economy09Period, ...], cumulative: bool = False
) -> dict:
    """Canonical UI/tutor/evidence contract; flows retain each period's own price."""
    if not periods:
        raise ValueError("A report needs at least one completed period.")
    selected = tuple(periods) if cumulative else tuple(periods[-1:])
    first, last = selected[0], selected[-1]
    for index, period in enumerate(selected):
        if period.households != last.households or period.firm != last.firm:
            raise ValueError("A cumulative report needs unchanged settings.")
        if index and (
            period.number != selected[index - 1].number + 1
            or period.opening_cash != selected[index - 1].closing_cash
            or period.capital_open != selected[index - 1].capital_close
        ):
            raise ValueError("A cumulative report needs consecutive linked periods.")

    def flow(field: str) -> float:
        return fsum(getattr(period, field) for period in selected)

    def household_flow(field: str, name: str) -> float:
        return fsum(getattr(period, field)[name] for period in selected)

    household_reports = []
    for index, household in enumerate(last.households):
        name = household.name
        total_work = household_flow("work", name)
        ownership = last.ownership[name]
        household_reports.append(
            {
                "name": name,
                "entity_id": f"household_{index + 1}",
                "opening_money": first.opening_cash[name],
                "closing_money": last.closing_cash[name],
                "wages_received": household_flow("wages", name),
                "dividends_received": household_flow("dividends", name),
                "purchases_paid": household_flow("purchases", name),
                "net_cash_change": last.closing_cash[name] - first.opening_cash[name],
                "consumed_x": household_flow("consumption", name),
                "consumed": household_flow("consumption", name),
                "total_work": total_work,
                "average_work": total_work / len(selected),
                "average_leisure": 1 - total_work / len(selected),
                "ownership": ownership,
                "ownership_value_open": ownership * first.equity_open,
                "ownership_value_close": ownership * last.equity_close,
                "assets_open": first.opening_cash[name] + ownership * first.equity_open,
                "assets_close": last.closing_cash[name] + ownership * last.equity_close,
                "parameters": {
                    "scores": household.scores,
                    "weights": household.weights,
                    "alpha": household.alpha,
                },
            }
        )
    firm_report = {
        "name": last.firm.name,
        "entity_id": "firm",
        "productivity": last.firm.productivity,
        "theta": last.firm.theta,
        "produced_x": flow("output"),
        "sold_x": fsum(entry["consumed_x"] for entry in household_reports),
        "opening_money": first.opening_cash[last.firm.name],
        "closing_money": last.closing_cash[last.firm.name],
        "sales_received": flow("sales_received"),
        "wages_paid": flow("wage_bill"),
        "dividends_paid": flow("dividends_paid"),
        "net_cash_change": last.closing_cash[last.firm.name]
        - first.opening_cash[last.firm.name],
        "capital_open": first.capital_open,
        "capital_close": last.capital_close,
        "capital_value_open": first.capital_value_open,
        "capital_value_close": last.capital_value_close,
        "capital_price_open": first.capital_price_open,
        "capital_price_close": last.capital_price_close,
        "equity_open": first.equity_open,
        "equity_close": last.equity_close,
        "retained_earnings_open": first.retained_earnings_open,
        "retained_earnings_close": last.retained_earnings_close,
        "revaluation_reserve_open": first.revaluation_reserve_open,
        "revaluation_reserve_close": last.revaluation_reserve_close,
        "contributed_equity": last.contributed_equity,
        "protected_operating_float": last.firm.money,
        "operating_cash": last.operating_cash,
        "next_dividend_budget": last.next_dividend_budget,
        "parameters": asdict(last.firm),
    }
    for field in (
        "production_value",
        "gross_operating_surplus",
        "net_operating_profit",
        "investment_quantity",
        "investment_value",
        "depreciation_quantity",
        "depreciation_value",
        "holding_gain",
    ):
        firm_report[field] = flow(field)
    firm_report["cash_operating_surplus"] = (
        firm_report["sales_received"] - firm_report["wages_paid"]
    )
    firm_report["investment_output_share"] = (
        firm_report["investment_quantity"] / firm_report["produced_x"]
    )
    economy = {
        "opening_money": fsum(first.opening_cash.values()),
        "closing_money": fsum(last.closing_cash.values()),
        "produced_x": firm_report["produced_x"],
        "consumed_x": firm_report["sold_x"],
        "capital_open": first.capital_open,
        "capital_close": last.capital_close,
        "capital_value_open": first.capital_value_open,
        "capital_value_close": last.capital_value_close,
        "production_value": firm_report["production_value"],
        "output_value": firm_report["production_value"],
        "investment_quantity": firm_report["investment_quantity"],
        "investment_value": firm_report["investment_value"],
        "depreciation_quantity": firm_report["depreciation_quantity"],
        "depreciation_value": firm_report["depreciation_value"],
        "holding_gain": firm_report["holding_gain"],
        "wages": firm_report["wages_paid"],
        "gross_operating_surplus": firm_report["gross_operating_surplus"],
        "net_operating_profit": firm_report["net_operating_profit"],
        "net_income": firm_report["wages_paid"] + firm_report["net_operating_profit"],
        "dividends": firm_report["dividends_paid"],
        "household_cash_saving": fsum(
            entry["net_cash_change"] for entry in household_reports
        ),
        "firm_net_saving": firm_report["net_operating_profit"]
        - firm_report["dividends_paid"],
        "average_work": fsum(entry["average_work"] for entry in household_reports)
        / len(household_reports),
        "average_leisure": fsum(entry["average_leisure"] for entry in household_reports)
        / len(household_reports),
    }
    economy["assets_open"] = economy["opening_money"] + first.capital_value_open
    economy["assets_close"] = economy["closing_money"] + last.capital_value_close
    checks = {
        "periods": all(all(period.checks.values()) for period in selected),
        "money": _close(economy["opening_money"], economy["closing_money"]),
        "goods": _close(
            economy["produced_x"],
            economy["consumed_x"] + economy["investment_quantity"],
        ),
        "capital": _close(
            economy["capital_open"] + economy["investment_quantity"],
            economy["capital_close"] + economy["depreciation_quantity"],
        ),
        "income": _close(
            economy["production_value"],
            economy["net_income"] + economy["depreciation_value"],
        ),
        "capital_value": _close(
            first.capital_value_open
            + firm_report["investment_value"]
            + firm_report["holding_gain"],
            last.capital_value_close + firm_report["depreciation_value"],
            first.capital_value_open,
        ),
        "equity": _close(
            first.equity_open
            + firm_report["net_operating_profit"]
            + firm_report["holding_gain"],
            last.equity_close + firm_report["dividends_paid"],
            first.equity_open,
        ),
        "saving": _close(
            economy["household_cash_saving"] + economy["firm_net_saving"],
            economy["investment_value"] - economy["depreciation_value"],
            economy["production_value"],
        ),
    }
    transfer_rows = [asdict(item) for period in selected for item in period.transfers]
    event_rows = [asdict(item) for period in selected for item in period.events]
    rows = _account_rows(selected)
    rows.extend({"record_type": "transfer", **entry} for entry in transfer_rows)
    rows.extend({"record_type": "event", **entry} for entry in event_rows)
    return {
        "model": "investment_growth",
        "scope": "cumulative" if cumulative else "period",
        "label": f"Periods {first.number}\N{EN DASH}{last.number}"
        if len(selected) > 1
        else f"Period {last.number}",
        "period_count": len(selected),
        "through_period": last.number,
        "price": last.price,
        "wage": last.wage,
        "real_wage": last.wage / last.price,
        "price_wage_period": last.number,
        "households": household_reports,
        "firm": firm_report,
        "economy": economy,
        "checks": checks,
        "transfers": transfer_rows,
        "events": event_rows,
        "rows": rows,
        "policies": {
            "investment": "A fixed share of output value minus wages, before capital wear, becomes capital next period.",
            "dividend": "Previous-period positive net operating profit, limited to cash above the initial operating float; past retained losses are not a payout gate.",
            "valuation": "Capital at current X replacement price; initial capital uses the first solved price. Holding gains are separate from operating profit.",
            "ownership": "Equal fixed shares in firm equity; ownership value is not spendable cash and is eliminated in consolidated assets.",
            "cumulative": "Flows sum at each period's own price; stocks use the first opening and selected closing. Price and wage describe the selected period.",
        },
    }


def _account_rows(periods: tuple[Economy09Period, ...]) -> list[dict]:
    """Full-precision account snapshots alongside explicit-unit evidence rows."""
    rows = []
    for period in periods:
        common = {
            "record_type": "account",
            "period": period.number,
            "price": period.price,
            "wage": period.wage,
            "money_unit": MONEY,
            "goods_unit": "X units",
            "capital_unit": "capital units",
            "labor_unit": "work periods",
        }
        for index, household in enumerate(period.households):
            name = household.name
            share = period.ownership[name]
            rows.append(
                {
                    **common,
                    "account_type": "household",
                    "entity": name,
                    "entity_id": f"household_{index + 1}",
                    "opening_money": period.opening_cash[name],
                    "dividends_received": period.dividends[name],
                    "wages_received": period.wages[name],
                    "purchases_paid": period.purchases[name],
                    "closing_money": period.closing_cash[name],
                    "consumed_x": period.consumption[name],
                    "work_fraction": period.work[name],
                    "leisure_fraction": period.leisure[name],
                    "ownership": share,
                    "ownership_value_open": share * period.equity_open,
                    "ownership_value_close": share * period.equity_close,
                    **{
                        f"{key}_priority": value
                        for key, value in household.scores.items()
                    },
                    **{
                        f"{key}_weight": value
                        for key, value in household.weights.items()
                    },
                }
            )
        firm_row = {
            **common,
            "account_type": "firm",
            "entity": period.firm.name,
            "entity_id": "firm",
            "opening_money": period.opening_cash[period.firm.name],
            "closing_money": period.closing_cash[period.firm.name],
            "produced_x": period.output,
            "sold_x": fsum(period.consumption.values()),
            "wages_paid": period.wage_bill,
            "protected_operating_float": period.firm.money,
            "productivity": period.firm.productivity,
            "theta": period.firm.theta,
            "reinvestment_rate": period.firm.reinvestment_rate,
            "depreciation_rate": period.firm.depreciation_rate,
        }
        for field in (
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
            "capital_price_open",
            "capital_price_close",
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
            firm_row[field] = getattr(period, field)
        rows.append(firm_row)
    return rows


@dataclass(frozen=True)
class Economy09Run:
    current: Economy09Period
    previous: Economy09Period | None
    revision: int

    @property
    def period(self) -> Economy09Period:
        return self.current

    @cached_property
    def data(self) -> dict:
        current, previous = self.current, self.previous
        report = investment_report((current,))
        return {
            "model": "investment_growth",
            "label": f"Period {current.number}",
            "number": current.number,
            "revision": self.revision,
            "settings": {
                "household_count": len(current.households),
                "households": [asdict(h) for h in current.households],
                "firm": asdict(current.firm),
                "ownership": dict(current.ownership),
            },
            "price": current.price,
            "wage": current.wage,
            "prices": current.prices,
            "output": current.output,
            "produced": current.produced,
            "consumed": dict(current.consumption),
            "work": dict(current.work),
            "effort": dict(current.work),
            "leisure_time": dict(current.leisure),
            "wages": dict(current.wages),
            "dividends": dict(current.dividends),
            "purchases": dict(current.purchases),
            "net_operating_profit": current.net_operating_profit,
            "firm": report["firm"],
            "households": report["households"],
            "agents": report["households"],
            "economy": report["economy"],
            "period_opening": dict(current.opening_cash),
            "period_closing": dict(current.closing_cash),
            "totals": {
                "opening": {
                    MONEY: report["economy"]["opening_money"],
                    CAPITAL: current.capital_open,
                },
                "closing": {
                    MONEY: report["economy"]["closing_money"],
                    CAPITAL: current.capital_close,
                },
            },
            "report": report,
            "reporting": report,
            "transfers": report["transfers"],
            "events": report["events"],
            "trades": [],
            "checks": dict(current.checks),
            "solution": dict(current.solution),
            "diagnostics": dict(current.solution),
            "previous_period": previous.number if previous else None,
            "previous_run": {
                "number": previous.number,
                "prices": previous.prices,
                "wage": previous.wage,
                "net_operating_profit": previous.net_operating_profit,
            }
            if previous
            else None,
            "price_x_change_percent": 100 * (current.price / previous.price - 1)
            if previous
            else None,
            "run_rule": "Linked periods. Cash-limited prior net-profit dividends, funded wages, production using opening capital, household consumption, capital wear and own-account investment. Money is conserved; new capital works next period.",
        }

    def context(self, transfer_index=None) -> dict:
        transfers = self.data["transfers"]
        selected = (
            transfers[transfer_index]
            if type(transfer_index) is int and 0 <= transfer_index < len(transfers)
            else None
        )
        return {**self.data, "selected_transfer": selected}
