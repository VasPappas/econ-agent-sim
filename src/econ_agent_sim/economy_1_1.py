"""Two firms with a smooth, optional household consumption target.

The target adds a fixed log-gap shortfall penalty to normalized log utility.
It is a preference, never a purchase guarantee or a source of money or goods.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from math import fsum, isfinite, log, nextafter, sqrt

from econ_agent_sim.economy_1_0 import (
    CAPITAL,
    GOOD,
    LABOR,
    MONEY,
    TOLERANCE,
    Economy10Event,
    Economy10Period,
    Economy10Transfer,
    Firm,
    FirmAccount,
    HouseholdFirmAllocation,
    _close,
    _dividend,
    _split,
)
from econ_agent_sim.economy_1_0 import (
    Household as BaseHousehold,
)
from econ_agent_sim.economy_1_0 import (
    _solve_market as _solve_cobb_douglas_market,
)
from econ_agent_sim.economy_1_0 import default_firms as _default_firms
from econ_agent_sim.numerics import require_finite

SHORTFALL_STRENGTH = 1.0


@dataclass(frozen=True)
class Household(BaseHousehold):
    consumption_target: float = 0.5

    def __post_init__(self) -> None:
        super().__post_init__()
        require_finite("Consumption target", self.consumption_target)
        if self.consumption_target < 0:
            raise ValueError("The consumption target must be non-negative.")


@dataclass(frozen=True)
class Economy11Period(Economy10Period):
    """The same immutable accounts, with target-aware household settings."""


def default_households(count: int = 2) -> list[dict]:
    if type(count) is not int or count < 1:
        raise ValueError("Use at least one household.")
    return [
        asdict(Household(f"household_{i + 1}", f"Household {i + 1}"))
        for i in range(count)
    ]


def default_firms() -> list[dict]:
    return _default_firms()


def utility(household: Household, consumption: float, money: float, leisure: float):
    """Normalized log utility; target urgency depends on this period only."""
    if min(consumption, money, leisure) <= 0 or leisure > 1:
        return float("-inf")
    require_finite("Household bundle", consumption, money, leisure)
    weights = household.weights
    value = (
        weights["consumption"] * log(consumption)
        + weights["money"] * log(money)
        + weights["leisure"] * log(leisure)
    )
    target = household.consumption_target
    if 0 < consumption < target:
        ratio = consumption / target
        value -= SHORTFALL_STRENGTH * (
            ratio - 1 - (log(consumption) - log(target))
        )
    return value


def _spend(total, consumption_weight, other_weight, target_cost):
    """Exact expenditure optimum, with a stable smaller quadratic root."""
    ordinary = consumption_weight / (consumption_weight + other_weight) * total
    if target_cost <= 0 or ordinary >= target_cost:
        return ordinary
    adjusted = consumption_weight + SHORTFALL_STRENGTH
    ratio = SHORTFALL_STRENGTH * (total / target_cost)
    scale = max(adjusted, other_weight, ratio)
    aa, ss, rr = adjusted / scale, other_weight / scale, ratio / scale
    # (A+s+r)^2-4Ar = (r-A)^2 + 2s(r+A) + s^2.
    discriminant = (rr - aa) ** 2 + 2 * ss * (rr + aa) + ss * ss
    fraction = 2 * aa / (aa + ss + rr + sqrt(discriminant))
    amount = fraction * total
    require_finite("Target-aware consumption expenditure", amount)
    return amount


def _choice(weights, target, available, price, wage):
    a, d, g = weights
    total = available + wage
    target_cost = price * target
    require_finite("Household purchasing power", total, target_cost)
    spending = _spend(total, a, d + g, target_cost)
    other = total - spending
    desired_wages = wage - g / (d + g) * other
    if desired_wages <= 0:
        spending = _spend(available, a, d, target_cost)
        return spending, available - spending, 1.0, 0.0
    leisure = g / (d + g) * other / wage
    return spending, d / (d + g) * other, leisure, desired_wages


def household_choice(
    household: Household, available_cash: float, price: float, wage: float
) -> dict[str, float]:
    """Choose consumption, closing money and leisure at given market prices."""
    require_finite("Household market inputs", available_cash, price, wage)
    if available_cash < 0 or min(price, wage) <= 0:
        raise ValueError("Cash must be non-negative and market prices positive.")
    weights = household.weights
    spending, money, leisure, wages = _choice(
        (weights["consumption"], weights["money"], weights["leisure"]),
        household.consumption_target,
        available_cash,
        price,
        wage,
    )
    return {
        "consumption": spending / price,
        "purchases": spending,
        "money": money,
        "leisure": leisure,
        "work": wages / wage,
        "wages": wages,
    }


def _solve_market(households, firms, available, funding, capital):
    """Bracket a continuous outer goods residual; never assume monotonicity.

    At each firm-payroll parameter, the inner household payroll residual is
    strictly increasing in the wage. Its upper bound is the Cobb-Douglas wage.
    Target urgency only increases labor supply at those fixed prices. The outer
    residual is negative at zero payroll and positive at sufficiently large
    production values because household expenditure is bounded by funded cash.
    Every returned market is separately certified after funded settlement.
    """
    if all(h.consumption_target == 0 for h in households):
        price, wage, wages, bills, solution = _solve_cobb_douglas_market(
            households, firms, available, funding, capital
        )
        solution["preference_model"] = "log_gap_target"
        solution["shortfall_strength"] = SHORTFALL_STRENGTH
        return price, wage, wages, bills, solution
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
    records = []
    for household in households:
        weights = household.weights
        records.append(
            (
                household.id,
                weights["consumption"],
                weights["money"],
                weights["leisure"],
                household.consumption_target,
                cash[household.id],
            )
        )
    thresholds = sorted(
        (g * z / (1 - g), key, g, z) for key, _, _, g, _, z in records
    )

    def ordinary_wage(payroll):
        active = []
        wage = 0.0
        for threshold, key, g, z in thresholds:
            if active and wage <= threshold:
                break
            active.append((key, g, z))
            wage = (payroll + fsum(g * z for _, g, z in active)) / fsum(
                1 - g for _, g, _ in active
            )
        return wage

    evaluations = 0
    inner_iterations = 0

    def evaluate(psi):
        nonlocal evaluations, inner_iterations
        evaluations += 1
        unconstrained = {key: value * psi for key, value in relative.items()}
        payroll = {key: min(value, caps[key]) for key, value in unconstrained.items()}
        total_payroll = fsum(payroll.values())
        values = {
            key: 2 * sqrt(unconstrained[key]) * sqrt(payroll[key]) for key in payroll
        }
        sales = fsum(
            (1 - f.reinvestment_rate) * values[f.id]
            + f.reinvestment_rate * payroll[f.id]
            for f in firms
        )

        def household_payroll(wage):
            price = 2 * sqrt(psi) * sqrt(wage) / largest
            choices = {
                key: _choice((a, d, g), target, z, price, wage)
                for key, a, d, g, target, z in records
            }
            residual = fsum(choice[3] for choice in choices.values()) - total_payroll
            return residual, price, choices

        low = total_payroll / len(records)
        high = ordinary_wage(total_payroll)
        if min(low, high) <= 0 or not isfinite(high):
            raise ValueError("The positive wage is below numerical precision.")
        # Roundoff can put the analytic upper bound one ulp below its root.
        while household_payroll(high)[0] < 0:
            high *= 2
            inner_iterations += 1
            if not isfinite(high) or inner_iterations > 200000:
                raise ValueError("The wage equilibrium exceeds numerical range.")
        for _ in range(100):
            middle = low + (high - low) / 2
            if middle in (low, high):
                break
            residual = household_payroll(middle)[0]
            inner_iterations += 1
            if residual > 0:
                high = middle
            else:
                low = middle
            if abs(residual) <= 2e-14 * total_payroll:
                low = high = middle
                break
        wage = min((low, high), key=lambda value: abs(household_payroll(value)[0]))
        labor_residual, price, choices = household_payroll(wage)
        spending = fsum(choice[0] for choice in choices.values())
        require_finite("Market residual", sales, spending, wage, price, labor_residual)
        if abs(labor_residual) > 1e-11 * total_payroll:
            raise ValueError("The household wage solution exceeds numerical precision.")
        wages = {key: choice[3] for key, choice in choices.items()}
        return sales - spending, wage, price, wages, payroll

    low, high, iterations = 0.0, 1.0, 0
    while evaluate(high)[0] <= 0:
        high *= 2
        iterations += 1
        if not isfinite(high) or iterations > 1024:
            raise ValueError("The positive market equilibrium exceeds numerical range.")
    best = None
    for _ in range(180):
        middle = low + (high - low) / 2
        if middle in (low, high):
            break
        candidate = evaluate(middle)
        iterations += 1
        if best is None or abs(candidate[0]) < abs(best[0]):
            best = candidate
        if candidate[0] > 0:
            high = middle
        else:
            low = middle
        if abs(candidate[0]) <= 2e-14:
            break
    if best is None:
        raise ValueError("The goods equilibrium exceeds numerical precision.")
    residual, normalized_wage, normalized_price, normalized_wages, normalized_bills = best
    wage, price = normalized_wage * scale, normalized_price * scale
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
            "method": "bracketed_target_goods_and_labor",
            "preference_model": "log_gap_target",
            "shortfall_strength": SHORTFALL_STRENGTH,
            "iterations": iterations,
            "market_evaluations": evaluations,
            "labor_iterations": inner_iterations,
            "normalized_residual": residual,
            "tolerance": TOLERANCE,
        },
    )


def advance_target_period(
    households: tuple[Household, ...],
    firms: tuple[Firm, ...],
    previous: Economy11Period | None = None,
) -> Economy11Period:
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
        desired_purchase = (
            h.alpha * cash[h.id]
            if h.consumption_target == 0
            else _spend(
                cash[h.id],
                h.weights["consumption"],
                h.weights["money"],
                price * h.consumption_target,
            )
        )
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
        weights = h.weights
        a, d, g = (weights[name] for name in ("consumption", "money", "leisure"))
        amount, money, free_time = consumption[key], cash[key], leisure[key]
        marginal_consumption = a / amount
        if amount < h.consumption_target:
            marginal_consumption += SHORTFALL_STRENGTH * (
                1 / amount - 1 / h.consumption_target
            )
        consumption_benefit = marginal_consumption * money
        consumption_cost = d * price
        work_benefit = d * wage * free_time
        work_cost = g * money
        household_optimality.append(
            amount > 0
            and money > 0
            and free_time > 0
            and _close(consumption_benefit, consumption_cost)
            and (
                _close(work_benefit, work_cost)
                if work[key] > 0
                else work_benefit <= work_cost or _close(work_benefit, work_cost)
            )
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
            f"Economy 1.1 did not reconcile ({failed}); no period completed."
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
    return Economy11Period(
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
