"""Household choice and common goods/labor market clearing."""

from __future__ import annotations

from itertools import pairwise
from math import ceil, exp, fsum, isfinite, log, sqrt

from econ_agent_sim.domain import TOLERANCE, Household
from econ_agent_sim.numerics import require_finite

SHORTFALL_STRENGTH = 1.0


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
        value -= SHORTFALL_STRENGTH * (ratio - 1 - (log(consumption) - log(target)))
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


def _solve_cobb_douglas_market(households, firms, available, funding, capital):
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
            "payroll_parameter": psi,
            "iterations": iterations,
            "normalized_residual": residual,
            "tolerance": TOLERANCE,
        },
    )


def market_candidates(households, firms, available, funding, capital):
    """Return certified equilibria found by a deterministic, finite root search.

    Each tuple contains price, wage, household payroll, firm payroll and
    diagnostics. Results are sorted by price. Firm-only bounds cover every
    possible root, but a finite grid cannot guarantee discovery of a tangency
    or arbitrarily close root pair. That limitation is part of the diagnostics.
    """
    households = tuple(sorted(households, key=lambda item: item.id))
    firms = tuple(sorted(firms, key=lambda item: item.id))
    reference = _solve_cobb_douglas_market(
        households, firms, available, funding, capital
    )
    if all(h.consumption_target == 0 for h in households):
        price, wage, wages, bills, solution = reference
        _certify_candidate(
            households, firms, available, funding, capital, price, wage, wages, bills
        )
        solution.update(
            {
                "preference_model": "log_gap_target",
                "shortfall_strength": SHORTFALL_STRENGTH,
                "candidate_prices": (price,),
                "candidate_count": 1,
                "candidate_index": 1,
                "reference_price": price,
                "root_search": "analytic_unique",
                "root_search_complete": True,
            }
        )
        return ((price, wage, wages, bills, solution),)
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
    thresholds = sorted((g * z / (1 - g), key, g, z) for key, _, _, g, _, z in records)

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

    def firm_totals(psi):
        payroll = {
            key: min(weight * psi, caps[key]) for key, weight in relative.items()
        }
        production_value = {
            key: 2 * sqrt(relative[key] * psi) * sqrt(payroll[key]) for key in relative
        }
        sales = fsum(
            (1 - f.reinvestment_rate) * production_value[f.id]
            + f.reinvestment_rate * payroll[f.id]
            for f in firms
        )
        # Sum the difference directly: subtracting two large aggregate values
        # would discard the small positive margin when reinvestment is near 1.
        sales_less_payroll = fsum(
            (1 - f.reinvestment_rate) * (production_value[f.id] - payroll[f.id])
            for f in firms
        )
        return sales, sales_less_payroll

    # No household can spend less than its target-free optimum from opening
    # cash, or more than opening cash plus wages. These firm-only bounds
    # exclude roots outside the scan without assuming a monotone goods residual.
    spending_floor = fsum(h.alpha * cash[h.id] for h in households)
    low = high = 1.0
    for _ in range(1100):
        if firm_totals(low)[0] < spending_floor:
            break
        low /= 2
        if low == 0:
            raise ValueError("The lower market bound exceeds numerical precision.")
    else:
        raise ValueError("The lower market bound exceeds numerical range.")
    for _ in range(1100):
        if firm_totals(high)[1] > 1:
            break
        high *= 2
        if not isfinite(high):
            raise ValueError("The upper market bound exceeds numerical range.")
    else:
        raise ValueError("The upper market bound exceeds numerical range.")

    log_low, log_high = log(low), log(high)
    # At least 128 intervals; never wider than a 25% change in payroll scale.
    # Include every firm funding kink and the target-free solution explicitly.
    intervals = max(128, ceil((log_high - log_low) / log(1.25)))
    if intervals > 8192:
        raise ValueError("The market search range exceeds numerical precision.")
    points = {
        low,
        high,
        reference[4]["payroll_parameter"],
        *(
            exp(log_low + (log_high - log_low) * i / intervals)
            for i in range(1, intervals)
        ),
    }
    points.update(
        caps[key] / relative[key]
        for key in relative
        if low < caps[key] / relative[key] < high
    )
    samples = [(psi, evaluate(psi)) for psi in sorted(points) if low <= psi <= high]
    roots = []
    iterations = 0

    def keep(psi, candidate):
        if not any(abs(log(psi) - log(found[0])) < 1e-9 for found in roots):
            roots.append((psi, candidate))

    for psi, candidate in samples:
        if candidate[0] == 0:
            keep(psi, candidate)
    for (left, left_value), (right, right_value) in pairwise(samples):
        if left_value[0] == 0 or right_value[0] == 0:
            continue
        if (left_value[0] > 0) == (right_value[0] > 0):
            continue
        best_psi, best = min(
            ((left, left_value), (right, right_value)),
            key=lambda pair: abs(pair[1][0]),
        )
        for _ in range(180):
            middle = left + (right - left) / 2
            if middle in (left, right):
                break
            candidate = evaluate(middle)
            iterations += 1
            if abs(candidate[0]) < abs(best[0]):
                best_psi, best = middle, candidate
            if (candidate[0] > 0) == (left_value[0] > 0):
                left, left_value = middle, candidate
            else:
                right, right_value = middle, candidate
            if abs(candidate[0]) <= 2e-14 * firm_totals(middle)[0]:
                break
        keep(best_psi, best)
    if not roots:
        raise ValueError(
            "No market equilibrium was resolved within numerical precision."
        )

    results = []
    for psi, candidate in roots:
        (
            residual,
            normalized_wage,
            normalized_price,
            normalized_wages,
            normalized_bills,
        ) = candidate
        wage, price = normalized_wage * scale, normalized_price * scale
        wages = {key: value * scale for key, value in normalized_wages.items()}
        bills = {
            key: min(value * scale, funding[key])
            for key, value in normalized_bills.items()
        }
        require_finite(
            "Market prices and payroll", wage, price, *wages.values(), *bills.values()
        )
        if min(price, wage, *bills.values()) <= 0:
            raise ValueError(
                "The equilibrium price, wage or firm payroll is below numerical precision."
            )
        _certify_candidate(
            households, firms, available, funding, capital, price, wage, wages, bills
        )
        results.append(
            (
                price,
                wage,
                wages,
                bills,
                {
                    "method": "scanned_target_goods_and_labor",
                    "preference_model": "log_gap_target",
                    "shortfall_strength": SHORTFALL_STRENGTH,
                    "iterations": iterations,
                    "market_evaluations": evaluations,
                    "labor_iterations": inner_iterations,
                    "normalized_residual": residual,
                    "tolerance": TOLERANCE,
                    "payroll_parameter": psi,
                    "reference_price": reference[0],
                    "root_search": "finite_log_scan",
                    "root_search_complete": False,
                    "scan_intervals": intervals,
                    "search_lower_bound": low,
                    "search_upper_bound": high,
                },
            )
        )
    results.sort(key=lambda result: result[0])
    candidate_prices = tuple(result[0] for result in results)
    for index, result in enumerate(results, 1):
        result[4].update(
            {
                "candidate_prices": candidate_prices,
                "candidate_count": len(results),
                "candidate_index": index,
            }
        )
    return tuple(results)


def _certify_candidate(
    households, firms, available, funding, capital, price, wage, wages, bills
):
    """Check unnormalized household budgets and firm KKT before selecting a root."""
    choices = {
        h.id: household_choice(h, available[h.id], price, wage) for h in households
    }
    output = {
        f.id: f.productivity * sqrt(capital[f.id]) * sqrt(bills[f.id] / wage)
        for f in firms
    }
    sales = fsum(
        (1 - f.reinvestment_rate) * price * output[f.id]
        + f.reinvestment_rate * bills[f.id]
        for f in firms
    )
    spending = fsum(choice["purchases"] for choice in choices.values())
    require_finite(
        "Candidate market quantities",
        sales,
        spending,
        *output.values(),
        *wages.values(),
        *bills.values(),
    )

    def close(a, b, scale=0.0):
        return abs(a - b) <= TOLERANCE * max(abs(a), abs(b), abs(scale))

    if not (
        close(sales, spending)
        and close(fsum(wages.values()), fsum(bills.values()))
        # At an exact no-work corner, algebraically equivalent payroll formulas
        # can differ by an ulp. Compare each wage using the unit-time wage scale;
        # aggregate payroll clearing above retains its strict relative check.
        and all(close(wages[h.id], choices[h.id]["wages"], wage) for h in households)
        and all(
            close(bills[f.id], min(0.5 * price * output[f.id], funding[f.id]))
            for f in firms
        )
    ):
        raise ValueError("A candidate market exceeded numerical precision.")


def solve_market(
    households, firms, available, funding, capital, *, previous_price=None
):
    """Select the detected root nearest the previous or target-free price in log space.

    This deterministic continuation convention is not a stability theorem.
    The lower price wins a numerical tie. Target-free markets retain the exact
    analytical household-payroll optimization.
    """
    if previous_price is not None:
        require_finite("Previous market price", previous_price)
        if previous_price <= 0:
            raise ValueError("The previous market price must be positive.")
    candidates = market_candidates(households, firms, available, funding, capital)
    reference_price = (
        previous_price
        if previous_price is not None
        else candidates[0][4]["reference_price"]
    )
    distances = [
        abs(log(candidate[0]) - log(reference_price)) for candidate in candidates
    ]
    minimum = min(distances)
    index = next(
        i for i, distance in enumerate(distances) if distance <= minimum + 1e-12
    )
    price, wage, wages, bills, diagnostics = candidates[index]
    diagnostics = dict(diagnostics)
    diagnostics.update(
        {
            "selected_candidate": index + 1,
            "selection_rule": "nearest_previous_price"
            if previous_price is not None
            else "nearest_target_free_price",
            "reference_price": reference_price,
        }
    )
    return price, wage, wages, bills, diagnostics
