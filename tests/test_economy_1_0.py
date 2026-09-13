"""Input, snapshot and numeric failure contracts for the competition engine."""

from dataclasses import FrozenInstanceError, replace
from math import fsum

import pytest

from econ_agent_sim.economy_1_0 import (
    Firm,
    Household,
    advance_competition_period,
    default_firms,
    default_households,
)


def setup():
    return (
        tuple(Household(**row) for row in default_households()),
        tuple(Firm(**row) for row in default_firms()),
    )


def test_snapshots_are_recursively_frozen_and_survive_new_draft():
    households, firms = setup()
    period = advance_competition_period(households, firms)
    with pytest.raises(FrozenInstanceError):
        period.firm_accounts["firm_a"].capital_close = 9
    with pytest.raises(TypeError):
        period.ownership["household_1"]["firm_a"] = 0
    with pytest.raises(TypeError):
        period.solution["firm_funding"]["firm_a"]["binding"] = True
    with pytest.raises(TypeError):
        period.closing_cash["firm_a"] = 100
    draft = [replace(firms[0], productivity=3), firms[1]]
    assert period.firms[0].productivity == 2
    with pytest.raises(ValueError, match="Restart"):
        advance_competition_period(households, draft, period)
    assert period.number == 1


def test_stable_identity_is_independent_of_names():
    households, firms = setup()
    households = tuple(replace(h, name="Same display name") for h in households)
    firms = tuple(replace(f, name="Same display name") for f in firms)
    period = advance_competition_period(households, firms)
    assert set(period.closing_cash) == {h.id for h in households} | {
        f.id for f in firms
    }
    assert len(period.firm_accounts) == 2
    assert all(t.sender_id != t.receiver_id for t in period.transfers)
    with pytest.raises(ValueError, match="unique"):
        advance_competition_period(
            households, (replace(firms[0], id=households[0].id), firms[1])
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"productivity": float("nan")},
        {"money": 0},
        {"capital": -1},
        {"theta": 0.4},
        {"reinvestment_rate": 1},
        {"depreciation_rate": 1},
    ],
)
def test_invalid_firm_settings_fail_before_advance(changes):
    with pytest.raises(ValueError):
        Firm("firm_a", "Firm A", **changes)


def test_household_priorities_must_be_positive_and_representable():
    with pytest.raises(ValueError):
        Household("h", "H", consumption_priority=0)
    with pytest.raises(ValueError):
        Household("h", "H", consumption_priority=1e-300, money_priority=1e300)
    households, firms = setup()
    with pytest.raises(ValueError, match="aggregate"):
        advance_competition_period(
            tuple(replace(h, money=0) for h in households), firms
        )


def test_unsupported_numeric_capacity_fails_without_changing_history():
    households, firms = setup()
    period = advance_competition_period(households, firms)
    old_cash = dict(period.closing_cash)
    extremes = (
        replace(firms[0], productivity=1e-200),
        replace(firms[1], productivity=1e200),
    )
    with pytest.raises(ValueError, match="precision|range"):
        advance_competition_period(households, extremes)
    assert period.number == 1 and dict(period.closing_cash) == old_cash


def test_twenty_households_have_bounded_paired_evidence_and_funded_payments():
    households = tuple(Household(**row) for row in default_households(20))
    _, firms = setup()
    first = advance_competition_period(households, firms)
    second = advance_competition_period(households, firms, first)
    assert len(second.transfers) <= 200
    assert all(second.checks.values())
    assert all(account.minimum_cash >= 0 for account in second.firm_accounts.values())


def test_binding_last_payment_stays_funded_at_full_ledger_precision():
    households = tuple(
        Household(
            f"h{i}",
            f"H{i}",
            money=0.1,
            consumption_priority=1 + i / 3,
            money_priority=0.2 + i / 7,
            leisure_priority=1 + i / 5,
        )
        for i in range(2)
    )
    firms = tuple(
        Firm(f"f{i}", f"F{i}", money=0.03, productivity=2 + i, reinvestment_rate=0.2)
        for i in range(2)
    )
    period = advance_competition_period(households, firms)
    terms = {key: [amount] for key, amount in period.opening_cash.items()}
    for transfer in period.transfers:
        if transfer.asset != "Money":
            continue
        terms[transfer.sender_id].append(-transfer.quantity)
        terms[transfer.receiver_id].append(transfer.quantity)
        assert fsum(terms[transfer.sender_id]) >= 0
    assert {key: fsum(values) for key, values in terms.items()} == period.closing_cash
