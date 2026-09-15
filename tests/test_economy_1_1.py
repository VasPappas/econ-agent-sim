"""Input, immutability and preference contracts for the target chapter."""

from dataclasses import FrozenInstanceError, replace
from itertools import pairwise
from math import fsum, isfinite

import pytest

from econ_agent_sim.economy_1_0 import (
    Household as OriginalHousehold,
)
from econ_agent_sim.economy_1_0 import (
    advance_competition_period,
)
from econ_agent_sim.economy_1_1 import (
    Economy11Period,
    Firm,
    Household,
    advance_target_period,
    default_firms,
    default_households,
    household_choice,
    utility,
)


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


def test_zero_target_reproduces_original_settlement_exactly():
    households, firms = setup(0)
    original = tuple(
        OriginalHousehold(
            h.id, h.name, h.money, h.consumption_priority,
            h.money_priority, h.leisure_priority,
        )
        for h in households
    )
    before = after = None
    for _ in range(15):
        before = advance_competition_period(original, firms, before)
        after = advance_target_period(households, firms, after)
        for field in (
            "price", "wage", "work", "leisure", "consumption", "purchases",
            "opening_cash", "closing_cash", "firm_accounts", "transfers", "events",
        ):
            assert getattr(after, field) == getattr(before, field)
        assert all(after.checks.values())


def test_target_preserves_immutable_history_and_requires_restart_for_changes():
    households, firms = setup(1)
    period = advance_target_period(households, firms)
    assert isinstance(period, Economy11Period)
    with pytest.raises(FrozenInstanceError):
        period.households[0].consumption_target = 2
    with pytest.raises(TypeError):
        period.solution["firm_funding"]["firm_a"]["binding"] = False
    with pytest.raises(ValueError, match="Restart"):
        advance_target_period(
            (replace(households[0], consumption_target=2), households[1]),
            firms, period,
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
    satisfied = household_choice(
        Household("h", "H", consumption_target=0.4), 1, 1, 1
    )
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
        replace(f, capital=100, productivity=0.1, depreciation_rate=0.9)
        for f in firms
    )
    period = None
    for _ in range(20):
        period = advance_target_period(households, firms, period)
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
    period = advance_target_period(households, firms)
    reordered = advance_target_period(households[::-1], firms[::-1])
    assert period.transfers == reordered.transfers
    assert period.firm_accounts == reordered.firm_accounts
    assert period.closing_cash == reordered.closing_cash


def test_numerical_range_failure_leaves_accepted_history_intact():
    households, firms = setup(1)
    period = advance_target_period(households, firms)
    old_cash = dict(period.closing_cash)
    with pytest.raises(ValueError, match="precision|range"):
        advance_target_period(
            households,
            (replace(firms[0], productivity=1e-200),
             replace(firms[1], productivity=1e200)),
        )
    assert period.number == 1 and dict(period.closing_cash) == old_cash
