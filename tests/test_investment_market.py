"""Independent market certificates for conditional user-cost investment.

The user-cost policy can have several equilibria even with zero household
targets. At a flat capital objective, clearing chooses an actual optimal member
of the investment interval, not an interpolation between nonoptimal actions.
"""

from dataclasses import replace
from math import fsum, sqrt

import pytest

from econ_agent_sim.domain import Firm, Household
from econ_agent_sim.market import market_candidates, solve_market


def settings(*, required_return=.05, target=0, rate=.4, wear=.1):
    households = tuple(
        Household(f"h{i}", f"H{i}", consumption_target=target) for i in range(2)
    )
    firms = tuple(
        Firm(
            f"f{i}", f"F{i}", investment_policy="user_cost",
            required_return=required_return, reinvestment_rate=rate,
            depreciation_rate=wear,
        )
        for i in range(2)
    )
    return households, firms


def inputs(households, firms):
    return (
        households, firms, {h.id: h.money for h in households},
        {f.id: f.money for f in firms}, {f.id: f.capital for f in firms},
    )


def independently_certify(candidate, households, firms):
    price, wage, wages, bills, diagnostics = candidate
    investment = diagnostics["investment_values"]
    sales = []
    for firm in firms:
        bill = bills[firm.id]
        labor = bill / wage
        output = firm.productivity * sqrt(firm.capital * labor)
        surplus = price * output - bill
        value = investment[firm.id]
        budget = firm.reinvestment_rate * surplus
        assert bill <= firm.money * (1 + 1e-9)
        assert bill == pytest.approx(min(price * output / 2, firm.money), rel=1e-9)
        assert value >= 0
        assert value <= budget + 1e-9 * max(budget, value)
        if firm.investment_policy == "percentage":
            assert value == pytest.approx(budget, rel=1e-9)
        else:
            # Reconstruct the derivative of the concave forecast objective.
            capital_next = (1 - firm.depreciation_rate) * firm.capital + value / price
            real_wage = wage / price
            real_funding = firm.money / price
            gamma = firm.productivity**2 / (4 * real_wage)
            cash_limited_derivative = .5 * firm.productivity * sqrt(
                real_funding / (real_wage * capital_next)
            )
            derivative = min(gamma, cash_limited_derivative)
            cost = firm.required_return + firm.depreciation_rate
            if budget == 0:
                assert value == 0
            elif value <= 1e-8 * budget:
                assert derivative <= cost * (1 + 1e-8)
            elif value >= (1 - 1e-8) * budget:
                assert derivative >= cost * (1 - 1e-8)
            else:
                assert derivative == pytest.approx(cost, rel=1e-8)
        sales.append(price * output - value)
    spending = []
    for household in households:
        assert household.consumption_target == 0
        gamma = household.leisure_priority / fsum(household.scores.values())
        expected_wages = max(0, (1 - gamma) * wage - gamma * household.money)
        assert wages[household.id] == pytest.approx(expected_wages, abs=1e-9 * wage)
        spending.append(household.alpha * (household.money + wages[household.id]))
    assert fsum(sales) == pytest.approx(fsum(spending), rel=1e-9)
    assert fsum(wages.values()) == pytest.approx(fsum(bills.values()), rel=1e-9)


@pytest.mark.parametrize("target", (0, .5, 10))
def test_low_user_cost_reaches_budget_and_matches_fixed_percentage_market(target):
    households, firms = settings(target=target)
    benchmark_firms = tuple(replace(f, investment_policy="percentage") for f in firms)
    reference = solve_market(*inputs(households, benchmark_firms))
    selected = solve_market(*inputs(households, firms))
    assert selected[0] == pytest.approx(reference[0], rel=1e-9)
    assert selected[1] == pytest.approx(reference[1], rel=1e-9)
    assert "investment_values" not in reference[4]
    assert selected[4]["root_search_complete"] is False
    assert selected[4]["selection_rule"] == "nearest_percentage_benchmark_price"
    for firm in firms:
        output = firm.productivity * sqrt(firm.capital * selected[3][firm.id] / selected[1])
        expected = firm.reinvestment_rate * (selected[0] * output - selected[3][firm.id])
        assert selected[4]["investment_values"][firm.id] == pytest.approx(expected)


def test_high_user_cost_can_choose_no_investment_with_a_positive_budget():
    households, firms = settings(required_return=1)
    reference_firms = tuple(
        replace(f, investment_policy="percentage", reinvestment_rate=0) for f in firms
    )
    reference = solve_market(*inputs(households, reference_firms))
    selected = solve_market(*inputs(households, firms))
    assert selected[0] == pytest.approx(reference[0], rel=1e-9)
    assert selected[1] == pytest.approx(reference[1], rel=1e-9)
    assert all(value == 0 for value in selected[4]["investment_values"].values())
    independently_certify(selected, households, firms)


def test_zero_targets_can_have_three_equilibria_including_an_interior_tie():
    households, firms = settings(required_return=.75)
    candidates = market_candidates(*inputs(households, firms))
    assert len(candidates) == 3
    for candidate in candidates:
        independently_certify(candidate, households, firms)
        assert candidate[4]["root_search_complete"] is False
    price, wage, _, bills, diagnostics = candidates[1]
    cost = .85
    # Symmetry gives B/(.5+.75B)=cost^2 at the indifferent real wage.
    total_payroll = .5 * cost**2 / (1 - .75 * cost**2)
    expected_wage = .5 + .75 * total_payroll
    expected_investment_value = (1.5 * total_payroll - 1) / 2
    assert wage == pytest.approx(expected_wage, rel=2e-11)
    assert price == pytest.approx(cost * expected_wage, rel=2e-11)
    assert fsum(bills.values()) == pytest.approx(total_payroll, rel=2e-11)
    assert diagnostics["indifferent_firms"] == ("f0", "f1")
    assert diagnostics["investment_values"] == pytest.approx(
        {"f0": expected_investment_value, "f1": expected_investment_value}, rel=2e-11,
    )
    selected = solve_market(*inputs(households, firms), previous_price=price)
    assert selected[4]["selected_candidate"] == 2
    assert selected[4]["selection_rule"] == "nearest_previous_price"


def test_mixed_policies_clear_and_keep_the_percentage_firms_own_rule():
    households, firms = settings(required_return=1)
    firms = (firms[0], replace(firms[1], investment_policy="percentage"))
    selected = solve_market(*inputs(households, firms))
    assert selected[4]["investment_values"]["f0"] == 0
    assert selected[4]["investment_values"]["f1"] > 0
    independently_certify(selected, households, firms)


def test_simultaneous_indifference_uses_proportional_available_capacity():
    households, firms = settings(required_return=.75)
    firms = (replace(firms[0], reinvestment_rate=.2), firms[1])
    candidates = market_candidates(*inputs(households, firms))
    tied = [item for item in candidates if item[4]["indifferent_firms"]]
    assert len(tied) == 1
    independently_certify(tied[0], households, firms)
    investment = tied[0][4]["investment_values"]
    assert investment["f1"] == pytest.approx(2 * investment["f0"], rel=1e-9)


@pytest.mark.parametrize("factor", (1e-6, 1e6))
def test_indifferent_selection_is_invariant_to_money_units_and_input_order(factor):
    households, firms = settings(required_return=.75)
    reference = market_candidates(*inputs(households, firms))[1]
    scaled_households = tuple(replace(h, money=h.money * factor) for h in reversed(households))
    scaled_firms = tuple(replace(f, money=f.money * factor) for f in reversed(firms))
    selected = solve_market(
        *inputs(scaled_households, scaled_firms), previous_price=reference[0] * factor,
    )
    assert selected[0] / factor == pytest.approx(reference[0], rel=1e-9)
    assert selected[1] / factor == pytest.approx(reference[1], rel=1e-9)
    for key, value in reference[4]["investment_values"].items():
        assert selected[4]["investment_values"][key] / factor == pytest.approx(value, rel=1e-9)
    independently_certify(selected, scaled_households, scaled_firms)


@pytest.mark.parametrize("rate,wear,required_return", ((0, .1, .05), (.4, 0, 0)))
def test_zero_budget_and_zero_user_cost_are_well_defined(rate, wear, required_return):
    households, firms = settings(rate=rate, wear=wear, required_return=required_return)
    selected = solve_market(*inputs(households, firms))
    independently_certify(selected, households, firms)
