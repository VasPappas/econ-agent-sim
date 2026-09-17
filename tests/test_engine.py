"""Current economy: funded settlement, immutable history and household choice."""

from dataclasses import FrozenInstanceError, replace
from itertools import pairwise
from math import fsum, isfinite, sqrt

import pytest

from econ_agent_sim.engine import (
    EconomyPeriod,
    Firm,
    Household,
    advance_period,
    default_firms,
    default_households,
    household_choice,
    utility,
)
from econ_agent_sim.market import market_candidates


def setup(target=0.5, count=2):
    return (
        tuple(
            replace(Household(**row), consumption_target=target)
            for row in default_households(count)
        ),
        tuple(Firm(**row) for row in default_firms()),
    )


@pytest.mark.parametrize("target", [-0.1, float("nan"), float("inf")])
def test_target_rejects_invalid_input_before_any_period(target):
    with pytest.raises(ValueError, match="target|finite"):
        Household("h", "H", consumption_target=target)


def test_default_settings_have_a_fixed_optional_target():
    rows = default_households(3)
    assert [row["consumption_target"] for row in rows] == [0.5] * 3
    assert Household("h", "H", consumption_target=0).consumption_target == 0
    with pytest.raises(ValueError):
        default_households(0)


def test_zero_target_uses_ordinary_shares_and_preserves_accounting_over_time():
    households, firms = setup(0)
    period = None
    for number in range(1, 16):
        period = advance_period(households, firms, period)
        assert period.number == number
        assert period.solution["root_search"] == "analytic_unique"
        assert period.solution["candidate_count"] == 1
        assert all(period.checks.values())
        assert fsum(period.closing_cash.values()) == pytest.approx(3)
        for household in households:
            key = household.id
            resources = period.post_dividend_cash[key] + period.wages[key]
            assert period.purchases[key] == pytest.approx(household.alpha * resources)
            assert period.closing_cash[key] == pytest.approx(
                (1 - household.alpha) * resources
            )
        if number == 1:
            # Frozen economic anchor from the released analytical model.
            assert period.price == 1.036523113726489
            assert period.wage == 1.1818181818181817
            assert period.consumption["household_1"] == 0.7016464154456235


def test_target_preserves_immutable_history_and_requires_restart_for_changes():
    households, firms = setup(1)
    period = advance_period(households, firms)
    assert isinstance(period, EconomyPeriod)
    with pytest.raises(FrozenInstanceError):
        period.households[0].consumption_target = 2
    with pytest.raises(TypeError):
        period.solution["firm_funding"]["firm_a"]["binding"] = False
    with pytest.raises(ValueError, match="Restart"):
        advance_period(
            (replace(households[0], consumption_target=2), households[1]),
            firms,
            period,
        )
    assert period.number == 1
    assert period.households[0].consumption_target == 1


def test_raising_an_unmet_target_increases_consumption_and_work_at_fixed_prices():
    household = Household("h", "H", consumption_target=0)
    choices = [
        household_choice(replace(household, consumption_target=b), 1, 1, 1)
        for b in (0, 1, 2, 10)
    ]
    assert all(
        later["consumption"] > earlier["consumption"]
        and later["work"] > earlier["work"]
        for earlier, later in pairwise(choices)
    )
    for choice in choices:
        assert choice["money"] > 0
        assert 0 < choice["leisure"] <= 1
        assert choice["purchases"] + choice["money"] == pytest.approx(
            1 + choice["wages"]
        )


def test_targets_already_met_leave_the_optimal_bundle_unchanged():
    plain = household_choice(Household("h", "H", consumption_target=0), 1, 1, 1)
    satisfied = household_choice(Household("h", "H", consumption_target=0.4), 1, 1, 1)
    assert satisfied == plain


def test_resting_household_still_optimizes_consumption_and_money():
    household = Household("h", "H", consumption_target=100)
    choice = household_choice(household, 20, 1, 0.01)
    assert choice["work"] == choice["wages"] == 0
    assert choice["leisure"] == 1
    chosen = utility(household, choice["consumption"], choice["money"], 1)
    for change in (-0.01, 0.01):
        assert chosen > utility(
            household,
            choice["consumption"] + change,
            choice["money"] - change,
            1,
        )


def test_log_gap_is_smooth_at_target_and_finite_for_very_small_ratios():
    household = Household("h", "H", consumption_target=0.5)
    ordinary = replace(household, consumption_target=0)
    target = household.consumption_target
    assert utility(household, target, 1, 0.5) == utility(ordinary, target, 1, 0.5)
    epsilon = 1e-6
    below = (
        utility(household, target, 1, 0.5)
        - utility(household, target - epsilon, 1, 0.5)
    ) / epsilon
    above = (
        utility(household, target + epsilon, 1, 0.5)
        - utility(household, target, 1, 0.5)
    ) / epsilon
    assert below == pytest.approx(above, abs=5e-6)
    assert isfinite(
        utility(replace(household, consumption_target=1e200), 1e-200, 1, 0.5)
    )


def test_shortfall_never_creates_money_or_unproduced_consumption():
    households, firms = setup(10)
    firms = tuple(
        replace(f, capital=100, productivity=0.1, depreciation_rate=0.9) for f in firms
    )
    period = None
    for _ in range(20):
        period = advance_period(households, firms, period)
        assert all(period.checks.values())
        assert fsum(period.closing_cash.values()) == pytest.approx(3)
        assert fsum(period.consumption.values()) == pytest.approx(
            period.output - period.investment_quantity
        )
        for household in households:
            assert 0 < period.consumption[household.id] < 10
            assert period.closing_cash[household.id] > 0
            assert period.leisure[household.id] > 0


def test_reordering_keeps_every_funded_transfer_and_account_identical():
    households, firms = setup(1, 3)
    households = tuple(
        replace(h, money=0.1 + i, consumption_target=0.5 + i)
        for i, h in enumerate(households)
    )
    firms = (replace(firms[0], productivity=3), firms[1])
    period = advance_period(households, firms)
    reordered = advance_period(households[::-1], firms[::-1])
    assert period.transfers == reordered.transfers
    assert period.firm_accounts == reordered.firm_accounts
    assert period.closing_cash == reordered.closing_cash


def test_numerical_range_failure_leaves_accepted_history_intact():
    households, firms = setup(1)
    period = advance_period(households, firms)
    old_cash = dict(period.closing_cash)
    with pytest.raises(ValueError, match="precision|range"):
        advance_period(
            households,
            (
                replace(firms[0], productivity=1e-200),
                replace(firms[1], productivity=1e200),
            ),
        )
    assert period.number == 1 and dict(period.closing_cash) == old_cash


def test_immutable_period_recursively_owns_all_nested_records():
    households, firms = setup(1)
    period = advance_period(households, firms)
    with pytest.raises(TypeError):
        period.ownership[households[0].id][firms[0].id] = 0
    with pytest.raises(FrozenInstanceError):
        period.firm_accounts[firms[0].id].capital_close = 0
    with pytest.raises(TypeError):
        period.solution["candidate_prices"][0] = 0
    with pytest.raises(TypeError):
        period.checks["money_conserved"] = False


def test_public_zero_target_candidate_rejects_unresolved_labor_at_extreme_precision():
    households, firms = setup(0)
    households = tuple(replace(h, consumption_priority=1e-100) for h in households)
    # These finite, positive priorities are representable as settings, but the
    # solver's finite scalar resolution cannot certify their tiny labor market.
    # Direct callers must receive the same rejection as funded settlement.
    with pytest.raises(ValueError, match="precision"):
        market_candidates(
            households,
            firms,
            {h.id: h.money for h in households},
            {f.id: f.money for f in firms},
            {f.id: f.capital for f in firms},
        )


def test_zero_target_exact_no_work_corner_survives_candidate_certification():
    households, firms = setup(0)
    households = (households[0], replace(households[1], money=0))
    firms = tuple(replace(f, reinvestment_rate=0) for f in firms)
    period = advance_period(households, firms)
    assert period.price == pytest.approx(sqrt(1 / 6))
    assert period.wage == pytest.approx(0.5)
    assert period.work[households[0].id] == pytest.approx(0, abs=1e-15)
    assert period.work[households[1].id] == pytest.approx(2 / 3)
    assert all(period.checks.values())
