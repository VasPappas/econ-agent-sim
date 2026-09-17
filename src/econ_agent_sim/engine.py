"""Funded economic settlement in explicit, isolated period phases.

Only the final immutable snapshot leaves the builder. A rejected candidate
cannot mutate previously accepted history.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields
from math import fsum, nextafter, sqrt

from econ_agent_sim.domain import (
    CAPITAL,
    GOOD,
    LABOR,
    MONEY,
    TOLERANCE,
    EconomyPeriod,
    Event,
    Firm,
    FirmAccount,
    Household,
    HouseholdFirmAllocation,
    Transfer,
    default_firms,
    default_households,
)
from econ_agent_sim.market import (
    SHORTFALL_STRENGTH,
    _spend,
    household_choice,
    solve_market,
    utility,
)
from econ_agent_sim.numerics import require_finite

__all__ = [
    "SHORTFALL_STRENGTH",
    "TOLERANCE",
    "EconomyPeriod",
    "Firm",
    "Household",
    "advance_period",
    "default_firms",
    "default_households",
    "household_choice",
    "utility",
]


def _close(a: float, b: float, scale: float = 0.0) -> bool:
    return abs(a - b) <= TOLERANCE * max(abs(a), abs(b), abs(scale))


def _dividend(profit: float, cash: float, protected: float) -> float:
    return min(max(profit, 0.0), max(cash - protected, 0.0))


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


def advance_period(
    households: tuple[Household, ...],
    firms: tuple[Firm, ...],
    previous: EconomyPeriod | None = None,
) -> EconomyPeriod:
    """Solve and certify one period, publishing nothing unless every phase succeeds."""
    try:
        period = _PeriodBuilder(tuple(households), tuple(firms), previous)
        period._pay_dividends_and_solve()
        period._pay_wages_and_produce()
        period._sell_and_consume()
        period._close_accounts()
        period._certify()
        return period._snapshot()
    except (OverflowError, ZeroDivisionError) as error:
        raise ValueError(
            "This economy exceeded numerical range; no period completed."
        ) from error


class _PeriodBuilder:
    """Mutable, candidate-local working accounts; never stored in run history."""

    def __init__(self, households, firms, previous):
        self.households = households
        self.firms = firms
        self.previous = previous
        if not self.households or len(self.firms) != 2:
            raise ValueError("Provide households and exactly two firms.")
        ids = [item.id for item in (*self.households, *self.firms)]
        if len(ids) != len(set(ids)):
            raise ValueError("Households and firms need globally unique stable IDs.")
        if fsum(h.money for h in self.households) <= 0:
            raise ValueError("Initial aggregate household money must be positive.")
        if self.previous is not None and (
            {h.id: h for h in self.households}
            != {h.id: h for h in self.previous.households}
            or {f.id: f for f in self.firms} != {f.id: f for f in self.previous.firms}
        ):
            raise ValueError("Restart the economy before changing submitted settings.")
        # All arithmetic and residual placement uses stable order, not UI order.
        self.ordered_h = tuple(sorted(self.households, key=lambda item: item.id))
        self.ordered_f = tuple(sorted(self.firms, key=lambda item: item.id))
        self.number = 1 if self.previous is None else self.previous.number + 1
        self.opening = (
            dict(self.previous.closing_cash)
            if self.previous
            else {item.id: item.money for item in (*self.ordered_h, *self.ordered_f)}
        )
        self.capital = {
            f.id: self.previous.firm_accounts[f.id].capital_close
            if self.previous
            else f.capital
            for f in self.ordered_f
        }
        require_finite("Opening stocks", *self.opening.values(), *self.capital.values())
        if min(self.opening.values()) < 0 or min(self.capital.values()) <= 0:
            raise ValueError("Opening cash must be non-negative and capital positive.")
        self.names = {item.id: item.name for item in (*self.ordered_h, *self.ordered_f)}
        self.initial_total = fsum(self.opening.values())
        self.cash_terms = {key: [value] for key, value in self.opening.items()}
        self.cash = dict(self.opening)
        self.transfers = []
        self.events = []
        self.pair_count = 0
        self.minimum_cash = {f.id: self.opening[f.id] for f in self.ordered_f}
        self.funded = True
        self.conserved_each_transfer = True

    def transfer(self, kind, asset, quantity, sender, receiver, pair_id, price=1.0):
        require_finite("Transfer", quantity, price)
        if quantity < 0 or sender == receiver:
            raise ValueError(
                "Transfers require positive quantities and distinct parties."
            )
        if quantity == 0:
            return 0.0
        if asset == MONEY:
            if quantity > self.cash[sender]:
                if not _close(quantity, self.cash[sender]):
                    raise ValueError(
                        "A transfer exceeds the sender's own available money."
                    )
                # Paired delivery is based on the actual funded consideration.
                quantity = self.cash[sender]
            # The displayed running balance is one rounded float, while its
            # accurately summed ledger terms can lie just below that float.
            # Lower the payment by an ulp if needed; never floor a negative
            # closing balance or inject cash into the sender's account.
            requested = quantity
            for _ in range(8):
                if fsum((*self.cash_terms[sender], -quantity)) >= 0:
                    break
                quantity = nextafter(quantity, 0.0)
            if not _close(quantity, requested):
                raise ValueError("The funded payment exceeds numerical precision.")
            self.cash_terms[sender].append(-quantity)
            self.cash_terms[receiver].append(quantity)
            self.cash[sender] = fsum(self.cash_terms[sender])
            self.cash[receiver] = fsum(self.cash_terms[receiver])
            self.funded &= self.cash[sender] >= 0
            if not self.funded:
                raise ValueError(
                    "A funded payment could not be represented without borrowing."
                )
            self.conserved_each_transfer &= _close(
                fsum(self.cash.values()), self.initial_total
            )
            for key, minimum in self.minimum_cash.items():
                self.minimum_cash[key] = min(minimum, self.cash[key])
        self.transfers.append(
            Transfer(
                len(self.transfers) + 1,
                pair_id,
                self.number,
                kind,
                asset,
                quantity,
                self.names[sender],
                self.names[receiver],
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

    def event(self, kind, entity, asset, quantity, value, price, opening_price=None):
        require_finite("Noncash event", quantity, value, price)
        self.events.append(
            Event(
                len(self.events) + 1,
                self.number,
                kind,
                self.names[entity],
                entity,
                asset,
                quantity,
                "capital units" if asset == CAPITAL else "X units",
                price,
                value,
                opening_price,
            )
        )

    def _pay_dividends_and_solve(self):
        self.share = 1 / len(self.ordered_h)
        self.ownership = {
            h.id: {f.id: self.share for f in self.ordered_f} for h in self.ordered_h
        }
        self.allocated_dividends = {}
        self.dividends_paid = {}
        for firm in self.ordered_f:
            profit = (
                self.previous.firm_accounts[firm.id].net_operating_profit
                if self.previous
                else 0.0
            )
            dividend = _dividend(profit, self.opening[firm.id], firm.money)
            split = _split(dividend, {h.id: 1.0 for h in self.ordered_h})
            for h in self.ordered_h:
                self.pair_count += 1
                self.allocated_dividends[h.id, firm.id] = self.transfer(
                    "dividend", MONEY, split[h.id], firm.id, h.id, self.pair_count
                )
            self.dividends_paid[firm.id] = fsum(
                self.allocated_dividends[h.id, firm.id] for h in self.ordered_h
            )
        self.post_dividend = dict(self.cash)
        self.available = {h.id: self.cash[h.id] for h in self.ordered_h}
        self.funding = {f.id: self.cash[f.id] for f in self.ordered_f}
        if min(self.funding.values()) <= 0:
            raise ValueError("Each firm needs positive cash after its own dividends.")
        self.price, self.wage, self.desired_wages, self.desired_bills, self.solution = (
            solve_market(
                self.ordered_h,
                self.ordered_f,
                self.available,
                self.funding,
                self.capital,
                previous_price=self.previous.price if self.previous else None,
            )
        )

    def _pay_wages_and_produce(self):
        self.allocated_wages = {}
        self.allocated_work = {}
        for firm in self.ordered_f:
            split = _split(self.desired_bills[firm.id], self.desired_wages)
            for h in self.ordered_h:
                self.pair_count += 1
                payment = self.transfer(
                    "wage", MONEY, split[h.id], firm.id, h.id, self.pair_count
                )
                self.allocated_wages[h.id, firm.id] = payment
                self.allocated_work[h.id, firm.id] = self.transfer(
                    "labor_delivery",
                    LABOR,
                    payment / self.wage,
                    h.id,
                    firm.id,
                    self.pair_count,
                    self.wage,
                )
        self.wages = {
            h.id: fsum(self.allocated_wages[h.id, f.id] for f in self.ordered_f)
            for h in self.ordered_h
        }
        self.work = {
            h.id: fsum(self.allocated_work[h.id, f.id] for f in self.ordered_f)
            for h in self.ordered_h
        }
        self.leisure = {key: 1 - value for key, value in self.work.items()}
        self.labor = {
            f.id: fsum(self.allocated_work[h.id, f.id] for h in self.ordered_h)
            for f in self.ordered_f
        }
        self.bills = {
            f.id: fsum(self.allocated_wages[h.id, f.id] for h in self.ordered_h)
            for f in self.ordered_f
        }
        self.output = {
            f.id: f.productivity * sqrt(self.capital[f.id]) * sqrt(self.labor[f.id])
            for f in self.ordered_f
        }
        self.values = {
            key: self.price * quantity for key, quantity in self.output.items()
        }
        self.gross = {key: self.values[key] - self.bills[key] for key in self.output}
        self.investment_value = {
            f.id: f.reinvestment_rate * self.gross[f.id] for f in self.ordered_f
        }
        self.investment = {
            key: value / self.price for key, value in self.investment_value.items()
        }
        self.offered = {
            key: self.output[key] - self.investment[key] for key in self.output
        }
        require_finite(
            "Production and investment",
            *self.labor.values(),
            *self.output.values(),
            *self.values.values(),
            *self.gross.values(),
            *self.investment.values(),
            *self.offered.values(),
        )
        if (
            min(
                *self.labor.values(),
                *self.output.values(),
                *self.gross.values(),
                *self.offered.values(),
            )
            <= 0
        ):
            raise ValueError(
                "Firm labor, production and operating surplus must remain positive."
            )
        for firm in self.ordered_f:
            self.event(
                "production",
                firm.id,
                GOOD,
                self.output[firm.id],
                self.values[firm.id],
                self.price,
            )

    def _sell_and_consume(self):
        self.allocated_purchases = {}
        self.allocated_consumption = {}
        for h in self.ordered_h:
            desired_purchase = (
                h.alpha * self.cash[h.id]
                if h.consumption_target == 0
                else _spend(
                    self.cash[h.id],
                    h.weights["consumption"],
                    h.weights["money"],
                    self.price * h.consumption_target,
                )
            )
            split = _split(desired_purchase, self.offered)
            for firm in self.ordered_f:
                self.pair_count += 1
                payment = self.transfer(
                    "goods_payment",
                    MONEY,
                    split[firm.id],
                    h.id,
                    firm.id,
                    self.pair_count,
                )
                self.allocated_purchases[h.id, firm.id] = payment
                self.allocated_consumption[h.id, firm.id] = self.transfer(
                    "goods_delivery",
                    GOOD,
                    payment / self.price,
                    firm.id,
                    h.id,
                    self.pair_count,
                    self.price,
                )
        self.purchases = {
            h.id: fsum(self.allocated_purchases[h.id, f.id] for f in self.ordered_f)
            for h in self.ordered_h
        }
        self.consumption = {
            h.id: fsum(self.allocated_consumption[h.id, f.id] for f in self.ordered_f)
            for h in self.ordered_h
        }
        self.dividends = {
            h.id: fsum(self.allocated_dividends[h.id, f.id] for f in self.ordered_f)
            for h in self.ordered_h
        }
        for h in self.ordered_h:
            self.event(
                "consumption",
                h.id,
                GOOD,
                self.consumption[h.id],
                self.purchases[h.id],
                self.price,
            )

    def _close_accounts(self):
        self.accounts = {}
        for firm in self.ordered_f:
            key = firm.id
            prior = self.previous.firm_accounts[key] if self.previous else None
            sold = fsum(self.allocated_consumption[h.id, key] for h in self.ordered_h)
            received = fsum(self.allocated_purchases[h.id, key] for h in self.ordered_h)
            wear = firm.depreciation_rate * self.capital[key]
            wear_value = self.price * wear
            profit = self.gross[key] - wear_value
            closing_capital = (1 - firm.depreciation_rate) * self.capital[
                key
            ] + self.investment[key]
            opening_price = self.previous.price if self.previous else self.price
            opening_value = opening_price * self.capital[key]
            closing_value = self.price * closing_capital
            gain = (self.price - opening_price) * self.capital[key]
            opening_equity = self.opening[key] + opening_value
            closing_equity = self.cash[key] + closing_value
            retained_open = prior.retained_earnings_close if prior else 0.0
            retained_close = retained_open + profit - self.dividends_paid[key]
            reserve_open = prior.revaluation_reserve_close if prior else 0.0
            reserve_close = reserve_open + gain
            contributed = prior.contributed_equity if prior else opening_equity
            next_dividend = _dividend(profit, self.cash[key], firm.money)
            mrp = 0.5 * self.values[key] / self.labor[key]
            binding = (
                _close(self.bills[key], self.funding[key])
                and mrp > self.wage
                and not _close(mrp, self.wage)
            )
            account = FirmAccount(
                key,
                firm.name,
                self.labor[key],
                self.output[key],
                sold,
                sold / fsum(self.consumption.values()),
                self.output[key] / fsum(self.output.values()),
                self.bills[key],
                received,
                self.values[key],
                self.gross[key],
                profit,
                self.investment[key],
                self.investment_value[key],
                wear,
                wear_value,
                self.capital[key],
                closing_capital,
                opening_price,
                self.price,
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
                self.dividends_paid[key],
                self.funding[key],
                next_dividend,
                self.opening[key],
                self.cash[key],
                binding,
                mrp,
                self.minimum_cash[key],
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
                raise ValueError(
                    "Closing capital has fallen below numerical precision."
                )
            self.accounts[key] = account
            self.event("capital_wear", key, CAPITAL, wear, wear_value, self.price)
            self.event(
                "capital_installation",
                key,
                CAPITAL,
                self.investment[key],
                self.investment_value[key],
                self.price,
            )
            self.event(
                "revaluation",
                key,
                CAPITAL,
                self.capital[key],
                gain,
                self.price,
                opening_price,
            )
        self.allocations = tuple(
            HouseholdFirmAllocation(
                h.id,
                f.id,
                self.share,
                self.allocated_dividends[h.id, f.id],
                self.allocated_wages[h.id, f.id],
                self.allocated_work[h.id, f.id],
                self.allocated_purchases[h.id, f.id],
                self.allocated_consumption[h.id, f.id],
                self.accounts[f.id].equity_open * self.share,
                self.accounts[f.id].equity_close * self.share,
            )
            for h in self.ordered_h
            for f in self.ordered_f
        )

    def _certify(self):
        def summed(field):
            return fsum(getattr(a, field) for a in self.accounts.values())

        household_optimality = []
        for h in self.ordered_h:
            key = h.id
            weights = h.weights
            a, d, g = (weights[name] for name in ("consumption", "money", "leisure"))
            amount, money, free_time = (
                self.consumption[key],
                self.cash[key],
                self.leisure[key],
            )
            marginal_consumption = a / amount
            if amount < h.consumption_target:
                marginal_consumption += SHORTFALL_STRENGTH * (
                    1 / amount - 1 / h.consumption_target
                )
            consumption_benefit = marginal_consumption * money
            consumption_cost = d * self.price
            work_benefit = d * self.wage * free_time
            work_cost = g * money
            household_optimality.append(
                amount > 0
                and money > 0
                and free_time > 0
                and _close(consumption_benefit, consumption_cost)
                and (
                    _close(work_benefit, work_cost)
                    if self.work[key] > 0
                    else work_benefit <= work_cost or _close(work_benefit, work_cost)
                )
            )
        self.checks = {
            "continuity": self.previous is None
            or (
                self.opening == self.previous.closing_cash
                and all(
                    self.capital[f.id]
                    == self.previous.firm_accounts[f.id].capital_close
                    for f in self.ordered_f
                )
            ),
            "payments_funded": self.funded,
            "wages_funded": all(
                self.bills[key] <= self.funding[key] for key in self.bills
            ),
            "no_borrowing": min(self.cash.values()) >= 0
            and min(self.minimum_cash.values()) >= 0,
            "money_conserved": self.conserved_each_transfer
            and _close(fsum(self.cash.values()), self.initial_total),
            "labor_market": _close(fsum(self.work.values()), fsum(self.labor.values())),
            "goods_market": all(
                _close(a.output, a.sales_quantity + a.investment_quantity)
                for a in self.accounts.values()
            ),
            "household_budgets": all(
                _close(
                    self.available[h.id] + self.wages[h.id],
                    self.purchases[h.id] + self.cash[h.id],
                )
                for h in self.ordered_h
            ),
            "household_optimality": all(household_optimality),
            "time_bounds": all(0 <= value < 1 for value in self.work.values()),
            "ledger_accounts": all(
                _close(
                    self.opening[key]
                    + fsum(
                        t.quantity
                        for t in self.transfers
                        if t.asset == MONEY and t.receiver_id == key
                    ),
                    self.cash[key]
                    + fsum(
                        t.quantity
                        for t in self.transfers
                        if t.asset == MONEY and t.sender_id == key
                    ),
                )
                for key in self.cash
            ),
            "paired_transfers": all(
                _close(
                    t.quantity,
                    fsum(
                        u.quantity * u.valuation_price
                        for u in self.transfers
                        if u.pair_id == t.pair_id and u.asset != MONEY
                    ),
                )
                for t in self.transfers
                if t.asset == MONEY and t.kind != "dividend"
            ),
            "dividend_rule": all(
                _close(
                    a.dividends_paid,
                    _dividend(
                        self.previous.firm_accounts[f.id].net_operating_profit
                        if self.previous
                        else 0.0,
                        self.opening[f.id],
                        f.money,
                    ),
                )
                for f in self.ordered_f
                for a in [self.accounts[f.id]]
            ),
            "firm_cash": all(
                _close(
                    a.opening_cash + a.sales_received,
                    a.closing_cash + a.wage_bill + a.dividends_paid,
                )
                for a in self.accounts.values()
            ),
            "firm_optimality": all(
                _close(a.wage_bill, min(0.5 * a.production_value, a.operating_cash))
                for a in self.accounts.values()
            ),
            "production": all(
                _close(
                    self.accounts[f.id].output,
                    f.productivity
                    * sqrt(self.capital[f.id])
                    * sqrt(self.accounts[f.id].work),
                )
                for f in self.ordered_f
            ),
            "investment_policy": all(
                _close(
                    self.accounts[f.id].investment_value,
                    f.reinvestment_rate * self.accounts[f.id].gross_operating_surplus,
                )
                for f in self.ordered_f
            ),
            "capital_units": all(
                _close(
                    a.capital_open + a.investment_quantity,
                    a.capital_close + a.depreciation_quantity,
                )
                for a in self.accounts.values()
            ),
            "capital_value": all(
                _close(
                    a.capital_value_close + a.depreciation_value,
                    a.capital_value_open + a.investment_value + a.holding_gain,
                    a.capital_value_open,
                )
                for a in self.accounts.values()
            ),
            "gross_income": all(
                _close(a.production_value, a.wage_bill + a.gross_operating_surplus)
                for a in self.accounts.values()
            ),
            "net_income": all(
                _close(
                    a.production_value,
                    a.wage_bill + a.net_operating_profit + a.depreciation_value,
                )
                for a in self.accounts.values()
            ),
            "equity_bridge": all(
                _close(
                    a.equity_close + a.dividends_paid,
                    a.equity_open + a.net_operating_profit + a.holding_gain,
                    a.equity_open,
                )
                for a in self.accounts.values()
            ),
            "equity_components": all(
                _close(
                    a.equity_close,
                    a.contributed_equity
                    + a.retained_earnings_close
                    + a.revaluation_reserve_close,
                    a.contributed_equity,
                )
                for a in self.accounts.values()
            ),
            "saving_investment": _close(
                fsum(self.wages.values())
                + fsum(self.dividends.values())
                - fsum(self.purchases.values())
                + summed("net_operating_profit")
                - summed("dividends_paid"),
                summed("investment_value") - summed("depreciation_value"),
                summed("production_value"),
            ),
            "ownership": all(
                _close(fsum(self.ownership[h.id][f.id] for h in self.ordered_h), 1.0)
                for f in self.ordered_f
            ),
        }
        if not all(self.checks.values()):
            failed = ", ".join(key for key, passed in self.checks.items() if not passed)
            raise ValueError(
                f"The economy did not reconcile ({failed}); no period completed."
            )

    def _snapshot(self):
        def summed(field):
            return fsum(getattr(a, field) for a in self.accounts.values())

        self.solution.update(
            {
                "total_labor": fsum(self.work.values()),
                "working_households": sum(value > 0 for value in self.work.values()),
                "resting_households": sum(value == 0 for value in self.work.values()),
                "relative_market_error": abs(
                    summed("output")
                    - fsum(self.consumption.values())
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
                    for key, a in self.accounts.items()
                },
            }
        )
        return EconomyPeriod(
            self.number,
            self.households,
            self.firms,
            self.ownership,
            self.opening,
            self.post_dividend,
            dict(self.cash),
            self.price,
            self.wage,
            self.work,
            self.leisure,
            self.wages,
            self.dividends,
            self.consumption,
            self.purchases,
            self.accounts,
            self.allocations,
            tuple(self.transfers),
            tuple(self.events),
            self.checks,
            self.solution,
        )
