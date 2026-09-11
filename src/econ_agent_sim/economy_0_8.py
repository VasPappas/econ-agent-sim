"""Competitive households, a funded firm, wages and delayed dividends.

Economy 0.8 is intentionally independent of the earlier exchange engines.  It
has one consumption good, homogeneous labor and one representative price-taking
firm.  Every monetary movement is recorded as an explicit transfer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import cached_property
from math import fsum, isclose

from econ_agent_sim.numerics import require_finite

MONEY = "Money"
GOOD = "X"
FIRM_NAME = "Firm"
TOLERANCE = 1e-9


@dataclass(frozen=True)
class Household:
    """Fixed household settings for a linked Economy 0.8 run."""

    name: str
    money: float = 1.0
    consumption_priority: float = 1.0
    money_priority: float = 1.0
    leisure_priority: float = 1.0

    def __post_init__(self) -> None:
        require_finite(
            "Household money and priorities",
            self.money,
            self.consumption_priority,
            self.money_priority,
            self.leisure_priority,
        )
        if not self.name.strip():
            raise ValueError("Use a household name.")
        if self.money < 0:
            raise ValueError("Household money must be non-negative.")
        if min(
            self.consumption_priority,
            self.money_priority,
            self.leisure_priority,
        ) <= 0:
            raise ValueError("Household priorities must be positive.")

    @property
    def weights(self) -> dict[str, float]:
        total = fsum(
            (
                self.consumption_priority,
                self.money_priority,
                self.leisure_priority,
            )
        )
        return {
            "consumption": self.consumption_priority / total,
            "money": self.money_priority / total,
            "leisure": self.leisure_priority / total,
        }

    @property
    def alpha(self) -> float:
        return self.consumption_priority / (
            self.consumption_priority + self.money_priority
        )


@dataclass(frozen=True)
class Firm:
    """Fixed representative-firm settings for a linked run."""

    name: str = FIRM_NAME
    money: float = 1.0
    productivity: float = 2.0
    theta: float = 0.5

    def __post_init__(self) -> None:
        require_finite("Firm settings", self.money, self.productivity, self.theta)
        if not self.name.strip():
            raise ValueError("Use a firm name.")
        if self.money <= 0:
            raise ValueError("Firm operating money must be positive.")
        if self.productivity <= 0:
            raise ValueError("Firm productivity must be positive.")
        if not 0 < self.theta < 1:
            raise ValueError("The production exponent must lie between zero and one.")


def default_households(count: int = 2) -> list[dict]:
    if count < 1:
        raise ValueError("Use at least one household.")
    return [asdict(Household(f"Household {index + 1}")) for index in range(count)]


def default_firm() -> dict:
    return asdict(Firm())


@dataclass(frozen=True)
class Economy08Transfer:
    """One physical leg in the append-only period settlement record."""

    transaction_id: int
    period: int
    kind: str
    asset: str
    quantity: float
    sender: str
    receiver: str


@dataclass(frozen=True)
class Economy08Period:
    number: int
    households: tuple[Household, ...]
    firm: Firm
    ownership: dict[str, float]
    opening_cash: dict[str, float]
    post_dividend_cash: dict[str, float]
    price: float
    wage: float
    work: dict[str, float]
    leisure: dict[str, float]
    wages: dict[str, float]
    dividends: dict[str, float]
    consumption: dict[str, float]
    purchases: dict[str, float]
    output: float
    revenue: float
    wage_bill: float
    profit: float
    closing_cash: dict[str, float]
    transfers: tuple[Economy08Transfer, ...]
    checks: dict[str, bool]
    solution: dict

    @property
    def prices(self) -> dict[str, float]:
        return {GOOD: self.price, MONEY: 1.0, "Labor": self.wage}

    @property
    def produced(self) -> dict[str, float]:
        return {self.firm.name: self.output}

    @property
    def consumed(self) -> dict[str, float]:
        return self.consumption


def _validate_population(households: tuple[Household, ...], firm: Firm) -> None:
    if not households:
        raise ValueError("Provide at least one household.")
    names = tuple(household.name for household in households)
    if len(set(names)) != len(names) or firm.name in names:
        raise ValueError("Households and the firm need unique names.")


def _wage_bills(
    wage: float,
    households: tuple[Household, ...],
    available_cash: dict[str, float],
) -> dict[str, float]:
    bills = {}
    for household in households:
        leisure_weight = household.weights["leisure"]
        bills[household.name] = max(
            0.0,
            (1 - leisure_weight) * wage
            - leisure_weight * available_cash[household.name],
        )
    return bills


def _wage_residual(
    wage: float,
    households: tuple[Household, ...],
    available_cash: dict[str, float],
    operating_cash: float,
    theta: float,
) -> float:
    bills = _wage_bills(wage, households, available_cash)
    total_wages = fsum(bills.values())
    spending = fsum(
        household.alpha * (available_cash[household.name] + bills[household.name])
        for household in households
    )
    return total_wages - min(theta * spending, operating_cash)


def _solve_wage(
    households: tuple[Household, ...],
    available_cash: dict[str, float],
    operating_cash: float,
    theta: float,
) -> tuple[float, dict[str, float], int]:
    """Solve the monotone piecewise-linear wage equation by bracketing."""

    cash_scale = fsum(available_cash.values()) + operating_cash
    low = 0.0
    high = max(1.0, cash_scale)
    iterations = 0
    while _wage_residual(high, households, available_cash, operating_cash, theta) <= 0:
        high *= 2
        iterations += 1
        require_finite("Wage bracket", high)
        if iterations > 1024:
            raise ValueError("A positive equilibrium wage could not be bracketed.")

    # A fixed iteration count gives ample accuracy even over large currency
    # scales and makes the solver deterministic.
    for _ in range(160):
        midpoint = (low + high) / 2
        if _wage_residual(
            midpoint, households, available_cash, operating_cash, theta
        ) > 0:
            high = midpoint
        else:
            low = midpoint
    wage = (low + high) / 2
    bills = _wage_bills(wage, households, available_cash)
    require_finite("Equilibrium wage and wage bills", wage, *bills.values())
    if wage <= 0:
        raise ValueError("The equilibrium wage must be positive.")
    return wage, bills, iterations + 160


def _append_transfer(
    transfers: list[Economy08Transfer],
    *,
    period: int,
    kind: str,
    asset: str,
    quantity: float,
    sender: str,
    receiver: str,
) -> None:
    require_finite("Transfer quantity", quantity)
    if quantity < 0:
        raise ValueError("Transfer quantities cannot be negative.")
    if quantity == 0:
        return
    transfers.append(
        Economy08Transfer(
            len(transfers) + 1,
            period,
            kind,
            asset,
            quantity,
            sender,
            receiver,
        )
    )


def _close(a: float, b: float) -> bool:
    return isclose(a, b, rel_tol=TOLERANCE, abs_tol=1e-10)


def advance_firm_period(
    households: tuple[Household, ...],
    firm: Firm,
    previous: Economy08Period | None = None,
) -> Economy08Period:
    """Solve and settle one linked period without borrowing or money creation."""

    _validate_population(households, firm)
    if previous is not None and (
        households != previous.households or firm != previous.firm
    ):
        raise ValueError("Restart the economy before changing household or firm settings.")

    number = 1 if previous is None else previous.number + 1
    opening_cash = (
        {name: float(value) for name, value in previous.closing_cash.items()}
        if previous is not None
        else {
            **{household.name: household.money for household in households},
            firm.name: firm.money,
        }
    )
    require_finite("Opening cash", *opening_cash.values())
    if any(value < 0 for value in opening_cash.values()):
        raise ValueError("Opening cash balances cannot be negative.")

    ownership = {household.name: 1 / len(households) for household in households}
    prior_profit = 0.0 if previous is None else previous.profit
    dividends = {
        household.name: prior_profit * ownership[household.name]
        for household in households
    }
    transfers: list[Economy08Transfer] = []
    for household in households:
        _append_transfer(
            transfers,
            period=number,
            kind="dividend",
            asset=MONEY,
            quantity=dividends[household.name],
            sender=firm.name,
            receiver=household.name,
        )

    operating_cash = opening_cash[firm.name] - fsum(dividends.values())
    post_dividend_cash = {
        household.name: opening_cash[household.name] + dividends[household.name]
        for household in households
    }
    post_dividend_cash[firm.name] = operating_cash
    require_finite("Cash after dividends", *post_dividend_cash.values())
    if operating_cash <= 0 or any(value < 0 for value in post_dividend_cash.values()):
        raise ValueError("Dividend settlement left insufficient operating cash.")
    available_cash = {
        household.name: post_dividend_cash[household.name]
        for household in households
    }
    if fsum(available_cash.values()) <= 0:
        raise ValueError("Households need positive aggregate cash after dividends.")

    wage, wages, iterations = _solve_wage(
        households, available_cash, operating_cash, firm.theta
    )
    wage_bill = fsum(wages.values())
    work = {name: payment / wage for name, payment in wages.items()}
    leisure = {name: 1 - labor for name, labor in work.items()}
    total_labor = fsum(work.values())
    output = firm.productivity * total_labor**firm.theta
    require_finite("Labor and output", total_labor, output)
    if total_labor <= 0 or output <= 0:
        raise ValueError("The economy needs positive labor and output.")

    purchases = {
        household.name: household.alpha
        * (available_cash[household.name] + wages[household.name])
        for household in households
    }
    revenue = fsum(purchases.values())
    price = revenue / output
    consumption = {
        household.name: purchases[household.name] / price
        for household in households
    }
    profit = revenue - wage_bill
    require_finite(
        "Prices, spending and profit",
        price,
        revenue,
        profit,
        *purchases.values(),
        *consumption.values(),
    )

    cash_after_wages = dict(post_dividend_cash)
    for household in households:
        payment = wages[household.name]
        cash_after_wages[firm.name] -= payment
        cash_after_wages[household.name] += payment
        _append_transfer(
            transfers,
            period=number,
            kind="wage",
            asset=MONEY,
            quantity=payment,
            sender=firm.name,
            receiver=household.name,
        )
    closing_cash = dict(cash_after_wages)
    for household in households:
        name = household.name
        payment = purchases[name]
        closing_cash[name] -= payment
        closing_cash[firm.name] += payment
        _append_transfer(
            transfers,
            period=number,
            kind="goods_payment",
            asset=MONEY,
            quantity=payment,
            sender=name,
            receiver=firm.name,
        )
        _append_transfer(
            transfers,
            period=number,
            kind="goods_delivery",
            asset=GOOD,
            quantity=consumption[name],
            sender=firm.name,
            receiver=name,
        )

    cash_scale = max(1.0, fsum(opening_cash.values()))
    phase_tolerance = 1e-10 * cash_scale
    funding_binding = _close(wage_bill, operating_cash) and (
        firm.theta * revenue > wage_bill + phase_tolerance
    )
    marginal_revenue_product = firm.theta * revenue / total_labor
    household_optimality = []
    for household in households:
        name = household.name
        weights = household.weights
        resources = available_cash[name] + wages[name]
        marginal_at_choice = (
            (1 - weights["leisure"]) * wage / resources
            - weights["leisure"] / leisure[name]
        )
        household_optimality.append(
            abs(marginal_at_choice) <= 1e-8 * max(1.0, wage / resources)
            if work[name] > 1e-10
            else marginal_at_choice <= 1e-10 * max(1.0, wage / resources)
        )

    parties = (*[household.name for household in households], firm.name)
    money_received = {
        name: fsum(
            transfer.quantity
            for transfer in transfers
            if transfer.asset == MONEY and transfer.receiver == name
        )
        for name in parties
    }
    money_sent = {
        name: fsum(
            transfer.quantity
            for transfer in transfers
            if transfer.asset == MONEY and transfer.sender == name
        )
        for name in parties
    }
    ledger_money_accounts = all(
        _close(
            opening_cash[name] + money_received[name],
            closing_cash[name] + money_sent[name],
        )
        for name in parties
    )
    goods_sent = fsum(
        transfer.quantity
        for transfer in transfers
        if transfer.kind == "goods_delivery" and transfer.sender == firm.name
    )
    ledger_goods_accounts = _close(goods_sent, output) and all(
        _close(
            fsum(
                transfer.quantity
                for transfer in transfers
                if transfer.kind == "goods_delivery"
                and transfer.receiver == household.name
            ),
            consumption[household.name],
        )
        for household in households
    )
    kind_assets = {
        "dividend": MONEY,
        "wage": MONEY,
        "goods_payment": MONEY,
        "goods_delivery": GOOD,
    }

    checks = {
        "continuity": previous is None or opening_cash == previous.closing_cash,
        "dividend_rule": _close(fsum(dividends.values()), prior_profit),
        "dividend_funded": min(post_dividend_cash.values()) >= -phase_tolerance,
        "wages_funded": cash_after_wages[firm.name] >= -phase_tolerance,
        "purchases_funded": all(
            closing_cash[household.name] >= -phase_tolerance
            for household in households
        ),
        "no_borrowing": min(closing_cash.values()) >= -phase_tolerance,
        "money_conserved": _close(
            fsum(opening_cash.values()), fsum(closing_cash.values())
        ),
        "goods_market": _close(output, fsum(consumption.values())),
        "labor_market": _close(total_labor, fsum(work.values())),
        "household_budgets": all(
            _close(
                available_cash[household.name] + wages[household.name],
                purchases[household.name] + closing_cash[household.name],
            )
            for household in households
        ),
        "household_optimality": all(household_optimality),
        "ledger_accounts": ledger_money_accounts and ledger_goods_accounts,
        "transfer_kinds": all(
            kind_assets.get(transfer.kind) == transfer.asset
            for transfer in transfers
        ),
        "firm_cash": _close(
            opening_cash[firm.name]
            - fsum(dividends.values())
            - wage_bill
            + revenue,
            closing_cash[firm.name],
        ),
        "firm_profit": _close(revenue, wage_bill + profit),
        "firm_optimality": (
            marginal_revenue_product + phase_tolerance >= wage
            if funding_binding
            else _close(marginal_revenue_product, wage)
        ),
        "operating_cash": _close(operating_cash, firm.money),
        "time_bounds": all(0 <= labor < 1 for labor in work.values()),
    }
    if not all(checks.values()):
        failed = ", ".join(name for name, passed in checks.items() if not passed)
        raise ValueError(f"Economy 0.8 did not reconcile ({failed}); no period completed.")

    # Clamp only settlement-scale negative zero.  The checks above reject any
    # economically material overdraft before this presentation cleanup.
    closing_cash = {
        name: 0.0 if -phase_tolerance <= value < 0 else value
        for name, value in closing_cash.items()
    }
    solution = {
        "method": "bracketed_scalar",
        "iterations": iterations,
        "total_labor": total_labor,
        "working_households": sum(labor > 0 for labor in work.values()),
        "resting_households": sum(labor == 0 for labor in work.values()),
        "operating_cash": operating_cash,
        "funding_binding": funding_binding,
        "marginal_revenue_product": marginal_revenue_product,
    }
    return Economy08Period(
        number,
        households,
        firm,
        ownership,
        opening_cash,
        post_dividend_cash,
        price,
        wage,
        work,
        leisure,
        wages,
        dividends,
        consumption,
        purchases,
        output,
        revenue,
        wage_bill,
        profit,
        closing_cash,
        tuple(transfers),
        checks,
        solution,
    )


def firm_report(periods: tuple[Economy08Period, ...], cumulative: bool = False) -> dict:
    """Return mobile-ready statements and CSV rows for the selected scope."""

    if not periods:
        raise ValueError("A report needs at least one completed period.")
    selected = periods if cumulative else periods[-1:]
    first, last = selected[0], selected[-1]
    if any(
        period.households != last.households or period.firm != last.firm
        for period in selected
    ):
        raise ValueError("A cumulative report needs unchanged settings.")

    def total(mapping_name: str, household_name: str) -> float:
        return fsum(
            getattr(period, mapping_name)[household_name] for period in selected
        )

    households_report = []
    rows = []
    for household in last.households:
        name = household.name
        wages_received = total("wages", name)
        dividends_received = total("dividends", name)
        purchases_paid = total("purchases", name)
        consumed_x = total("consumption", name)
        total_work = total("work", name)
        entry = {
            "name": name,
            "opening_money": first.opening_cash[name],
            "closing_money": last.closing_cash[name],
            "wages_received": wages_received,
            "dividends_received": dividends_received,
            "purchases_paid": purchases_paid,
            "net_cash_change": last.closing_cash[name] - first.opening_cash[name],
            "consumed_x": consumed_x,
            "consumed": consumed_x,
            "total_work": total_work,
            "average_work": total_work / len(selected),
            "average_leisure": 1 - total_work / len(selected),
            "ownership": last.ownership[name],
            "parameters": {
                "scores": {
                    "consumption": household.consumption_priority,
                    "money": household.money_priority,
                    "leisure": household.leisure_priority,
                },
                "weights": household.weights,
                "alpha": household.alpha,
            },
        }
        households_report.append(entry)

    for period in selected:
        for household in period.households:
            name = household.name
            rows.append(
                {
                    "period": period.number,
                    "account_type": "household",
                    "entity": name,
                    "opening_money": period.opening_cash[name],
                    "dividends_received": period.dividends[name],
                    "wages_received": period.wages[name],
                    "purchases_paid": period.purchases[name],
                    "sales_received": 0.0,
                    "dividends_paid": 0.0,
                    "wages_paid": 0.0,
                    "closing_money": period.closing_cash[name],
                    "produced_x": 0.0,
                    "consumed_x": period.consumption[name],
                    "work_fraction": period.work[name],
                    "leisure_fraction": period.leisure[name],
                    "consumption_priority": household.consumption_priority,
                    "money_priority": household.money_priority,
                    "leisure_priority": household.leisure_priority,
                    "consumption_weight": household.weights["consumption"],
                    "money_weight": household.weights["money"],
                    "leisure_weight": household.weights["leisure"],
                    "ownership": period.ownership[name],
                    "current_profit": 0.0,
                    "price": period.price,
                    "wage": period.wage,
                }
            )
        rows.append(
            {
                "period": period.number,
                "account_type": "firm",
                "entity": period.firm.name,
                "opening_money": period.opening_cash[period.firm.name],
                "dividends_received": 0.0,
                "wages_received": 0.0,
                "purchases_paid": 0.0,
                "sales_received": period.revenue,
                "dividends_paid": fsum(period.dividends.values()),
                "wages_paid": period.wage_bill,
                "closing_money": period.closing_cash[period.firm.name],
                "produced_x": period.output,
                "consumed_x": 0.0,
                "work_fraction": 0.0,
                "leisure_fraction": 0.0,
                "consumption_priority": 0.0,
                "money_priority": 0.0,
                "leisure_priority": 0.0,
                "consumption_weight": 0.0,
                "money_weight": 0.0,
                "leisure_weight": 0.0,
                "ownership": 1.0,
                "current_profit": period.profit,
                "price": period.price,
                "wage": period.wage,
            }
        )

    dividends_paid = fsum(value for period in selected for value in period.dividends.values())
    wages_paid = fsum(period.wage_bill for period in selected)
    sales_received = fsum(period.revenue for period in selected)
    profits = fsum(period.profit for period in selected)
    produced = fsum(period.output for period in selected)
    consumed = fsum(value for period in selected for value in period.consumption.values())
    opening_total = fsum(first.opening_cash.values())
    closing_total = fsum(last.closing_cash.values())
    scope = "cumulative" if cumulative else "period"
    return {
        "scope": scope,
        "label": (
            f"Periods {first.number}\N{EN DASH}{last.number}"
            if cumulative and len(selected) > 1
            else f"Period {last.number}"
        ),
        "period_count": len(selected),
        "through_period": last.number,
        "price": last.price,
        "wage": last.wage,
        "households": households_report,
        "firm": {
            "name": last.firm.name,
            "productivity": last.firm.productivity,
            "theta": last.firm.theta,
            "opening_money": first.opening_cash[last.firm.name],
            "closing_money": last.closing_cash[last.firm.name],
            "sales_received": sales_received,
            "sales": sales_received,
            "wages_paid": wages_paid,
            "profit": profits,
            "current_profit": profits,
            "dividends_paid": dividends_paid,
            "net_cash_change": (
                last.closing_cash[last.firm.name] - first.opening_cash[last.firm.name]
            ),
            "profit_awaiting_distribution": last.profit,
            "parameters": {
                "productivity": last.firm.productivity,
                "theta": last.firm.theta,
            },
        },
        "economy": {
            "opening_money": opening_total,
            "closing_money": closing_total,
            "produced_x": produced,
            "produced": produced,
            "consumed_x": consumed,
            "consumed": consumed,
            "output_value": sales_received,
            "wages": wages_paid,
            "profit": profits,
            "current_profit": profits,
            "dividends": dividends_paid,
            "average_work": fsum(
                entry["total_work"] for entry in households_report
            )
            / (len(selected) * len(last.households)),
            "average_leisure": 1
            - fsum(entry["total_work"] for entry in households_report)
            / (len(selected) * len(last.households)),
        },
        "checks": {
            "periods": all(all(period.checks.values()) for period in selected),
            "goods": _close(produced, consumed),
            "money": _close(opening_total, closing_total),
            "income": _close(sales_received, wages_paid + profits),
        },
        "transfers": [
            asdict(transfer) for period in selected for transfer in period.transfers
        ],
        "rows": rows,
    }


@dataclass(frozen=True)
class Economy08Run:
    current: Economy08Period
    previous: Economy08Period | None
    revision: int

    @property
    def period(self) -> Economy08Period:
        return self.current

    @cached_property
    def data(self) -> dict:
        report = firm_report((self.current,))
        current = self.current
        previous = self.previous
        opening_total = fsum(current.opening_cash.values())
        closing_total = fsum(current.closing_cash.values())
        return {
            "model": "firms_wages",
            "label": f"Period {current.number}",
            "number": current.number,
            "revision": self.revision,
            "settings": {
                "household_count": len(current.households),
                "households": [asdict(household) for household in current.households],
                "firm": asdict(current.firm),
                "ownership": current.ownership,
            },
            "price": current.price,
            "wage": current.wage,
            "prices": current.prices,
            "output": current.output,
            "produced": {current.firm.name: current.output},
            "consumed": current.consumption,
            "effort": current.work,
            "work": current.work,
            "leisure_time": current.leisure,
            "wages": current.wages,
            "dividends": current.dividends,
            "purchases": current.purchases,
            "profit": current.profit,
            "firm": report["firm"],
            "households": report["households"],
            "agents": report["households"],
            "period_opening": current.opening_cash,
            "period_closing": current.closing_cash,
            "totals": {
                "opening": {MONEY: opening_total},
                "closing": {MONEY: closing_total},
            },
            "report": report,
            "reporting": report,
            "transfers": report["transfers"],
            "trades": [],
            "checks": current.checks,
            "solution": current.solution,
            "diagnostics": current.solution,
            "previous_period": previous.number if previous else None,
            "previous_run": (
                {
                    "number": previous.number,
                    "prices": previous.prices,
                    "wage": previous.wage,
                    "profit": previous.profit,
                }
                if previous
                else None
            ),
            "price_x_change_percent": (
                100 * (current.price / previous.price - 1) if previous else None
            ),
            "run_rule": (
                "Linked periods. The firm pays prior profit as dividends, hires funded "
                "labor, produces and sells X, then retains current profit for next period."
            ),
        }

    def context(self, transfer_index=None) -> dict:
        transfers = self.data["transfers"]
        selected = (
            transfers[transfer_index]
            if type(transfer_index) is int and 0 <= transfer_index < len(transfers)
            else None
        )
        return {**self.data, "selected_transfer": selected}
