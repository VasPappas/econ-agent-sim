"""A reproducible multiple-equilibrium economy and independent certification.

The certificate uses the utility derivatives and physical production identity,
not the market solver's residual or its own success flags.
"""

from dataclasses import replace
from math import fsum, log, sqrt

import pytest

from econ_agent_sim.domain import Firm, Household
from econ_agent_sim.market import market_candidates, solve_market


def multiple_equilibrium_economy():
    """Supported heterogeneous inputs found during the independent audit."""
    households = (
        Household(
            "h0",
            "H0",
            money=23825.05914779393,
            consumption_priority=0.04582221539284675,
            money_priority=2.6778218133203358,
            leisure_priority=0.7162370163924818,
            consumption_target=9.29114042490599,
        ),
        Household(
            "h1",
            "H1",
            money=0,
            consumption_priority=3.0457680976143315,
            money_priority=0.04986743490465014,
            leisure_priority=28.55227622948859,
            consumption_target=0.2343481596156158,
        ),
        Household(
            "h2",
            "H2",
            money=0.17191816680430733,
            consumption_priority=0.0788260129653371,
            money_priority=9.367497022029458,
            leisure_priority=0.02980447201570548,
            consumption_target=0.07441135388634693,
        ),
    )
    firms = (
        Firm(
            "f0",
            "F0",
            money=0.05261931489345532,
            productivity=0.26874722534719536,
            capital=157.25152027086267,
            reinvestment_rate=0.36915685534064807,
            depreciation_rate=0.1,
        ),
        Firm(
            "f1",
            "F1",
            money=323.8094599986422,
            productivity=5.818539701547705,
            capital=10.197288398159515,
            reinvestment_rate=0.648519504552398,
            depreciation_rate=0.1,
        ),
    )
    return households, firms


def market_inputs(households, firms):
    return (
        households,
        firms,
        {h.id: h.money for h in households},
        {f.id: f.money for f in firms},
        {f.id: f.capital for f in firms},
    )


def independently_certify(candidate, households, firms):
    price, wage, wages, bills, _ = candidate
    assert price > 0 and wage > 0
    consumption, work = [], []
    for household in households:
        scores = (
            household.consumption_priority,
            household.money_priority,
            household.leisure_priority,
        )
        a, d, g = (value / fsum(scores) for value in scores)
        labor = wages[household.id] / wage
        assert 0 <= labor < 1
        budget = household.money + wages[household.id]
        low, high = 0.0, budget / price
        target = household.consumption_target
        # Independently find the unique consumption-money optimum conditional
        # on the candidate labor choice, using marginal utilities directly.
        for _ in range(100):
            amount = low + (high - low) / 2
            money = budget - price * amount
            marginal = a / amount
            if 0 < amount < target:
                marginal += 1 / amount - 1 / target
            if marginal > price * d / money:
                low = amount
            else:
                high = amount
        amount = low + (high - low) / 2
        money = budget - price * amount
        marginal = a / amount
        if 0 < amount < target:
            marginal += 1 / amount - 1 / target
        assert marginal == pytest.approx(price * d / money, rel=2e-8)
        assert money > 0
        if labor > 1e-10:
            assert wage * d / money == pytest.approx(g / (1 - labor), rel=2e-8)
        else:
            assert wage * d / money <= g * (1 + 2e-8)
        consumption.append(amount)
        work.append(labor)

    output, investment, employed = [], [], []
    for firm in firms:
        bill = bills[firm.id]
        assert 0 < bill <= firm.money * (1 + 1e-10)
        labor = bill / wage
        produced = firm.productivity * sqrt(firm.capital * labor)
        marginal_revenue = price * produced / (2 * labor)
        if bill < firm.money * (1 - 1e-8):
            assert marginal_revenue == pytest.approx(wage, rel=2e-8)
        else:
            assert marginal_revenue >= wage * (1 - 2e-8)
        output.append(produced)
        investment.append(firm.reinvestment_rate * (price * produced - bill) / price)
        employed.append(labor)
    assert fsum(work) == pytest.approx(fsum(employed), rel=2e-8)
    assert fsum(output) == pytest.approx(fsum(consumption) + fsum(investment), rel=2e-8)


def test_detects_and_independently_certifies_three_valid_equilibria():
    households, firms = multiple_equilibrium_economy()
    candidates = market_candidates(*market_inputs(households, firms))
    assert [candidate[0] for candidate in candidates] == pytest.approx(
        [32.759547175164975, 75.28921916457237, 571.8438592952663],
        rel=2e-8,
    )
    for candidate in candidates:
        independently_certify(candidate, households, firms)
        assert candidate[4]["root_search"] == "finite_log_scan"
        assert candidate[4]["root_search_complete"] is False


def test_first_period_uses_target_free_price_anchor():
    households, firms = multiple_equilibrium_economy()
    candidates = market_candidates(*market_inputs(households, firms))
    without_targets = tuple(replace(h, consumption_target=0) for h in households)
    anchor = solve_market(*market_inputs(without_targets, firms))[0]
    expected = min(candidates, key=lambda item: (abs(log(item[0] / anchor)), item[0]))
    selected = solve_market(*market_inputs(households, firms))
    assert selected[0] == pytest.approx(expected[0], rel=2e-8)
    assert selected[0] == pytest.approx(32.759547175164975, rel=2e-8)
    assert selected[4]["selection_rule"] == "nearest_target_free_price"
    assert selected[4]["reference_price"] == pytest.approx(anchor)
    assert selected[4]["candidate_count"] == 3
    independently_certify(selected, households, firms)


@pytest.mark.parametrize("previous_price", [32.0, 80.0, 600.0])
def test_continuation_uses_nearest_previous_price_in_log_distance(previous_price):
    households, firms = multiple_equilibrium_economy()
    candidates = market_candidates(*market_inputs(households, firms))
    expected = min(
        candidates,
        key=lambda item: (abs(log(item[0] / previous_price)), item[0]),
    )
    selected = solve_market(
        *market_inputs(households, firms),
        previous_price=previous_price,
    )
    assert selected[0] == pytest.approx(expected[0], rel=2e-8)
    assert selected[4]["selection_rule"] == "nearest_previous_price"
    assert selected[4]["reference_price"] == previous_price
    independently_certify(selected, households, firms)


def test_selection_is_invariant_to_input_order_and_currency_units():
    households, firms = multiple_equilibrium_economy()
    expected = solve_market(*market_inputs(households, firms), previous_price=80.0)
    for factor in (1e-6, 1.0, 1e6):
        scaled_households = tuple(
            replace(h, money=h.money * factor) for h in reversed(households)
        )
        scaled_firms = tuple(
            replace(f, money=f.money * factor) for f in reversed(firms)
        )
        selected = solve_market(
            *market_inputs(scaled_households, scaled_firms),
            previous_price=80.0 * factor,
        )
        assert selected[0] / factor == pytest.approx(expected[0], rel=2e-8)
        assert selected[1] / factor == pytest.approx(expected[1], rel=2e-8)
        independently_certify(selected, scaled_households, scaled_firms)


def test_equal_proportional_distance_prefers_lower_price():
    households, firms = multiple_equilibrium_economy()
    candidates = market_candidates(*market_inputs(households, firms))
    midpoint = sqrt(candidates[0][0] * candidates[1][0])
    selected = solve_market(*market_inputs(households, firms), previous_price=midpoint)
    assert selected[0] == candidates[0][0]
    assert selected[4]["selected_candidate"] == 1
