"""Boundary regressions with independent optimality, ledger and decimal checks."""

from dataclasses import replace
from decimal import Decimal, localcontext
from math import fsum, ulp

import pytest
from test_engine_acceptance import certify_accounts, certify_household_choices

from econ_agent_sim.engine import Firm, Household, _PeriodBuilder, advance_period
from econ_agent_sim.market import _certify_candidate, market_candidates

SCAN_ROUNDING = (
    (
        Household("h0", "H0", money=1e6, consumption_target=.5),
        Household("h1", "H1", money=1e6, consumption_priority=100,
                  money_priority=.01, leisure_priority=100, consumption_target=0),
    ),
    (
        Firm("f0", "F0", money=1e6, productivity=.1, capital=.1,
             reinvestment_rate=0, depreciation_rate=.9),
        Firm("f1", "F1", money=.01, productivity=100, capital=.1,
             reinvestment_rate=0, depreciation_rate=0),
    ),
)

INCOME_CANCELLATION = (
    (
        Household("h0", "H0", money=0, consumption_priority=1,
                  money_priority=.01, leisure_priority=.01, consumption_target=100),
        Household("h1", "H1", money=1e6, consumption_priority=1,
                  money_priority=.01, leisure_priority=.01, consumption_target=.5),
    ),
    (
        Firm("f0", "F0", money=1e6, productivity=100, capital=1e6,
             reinvestment_rate=0, depreciation_rate=0),
        Firm("f1", "F1", money=.01, productivity=.1, capital=1e6,
             reinvestment_rate=.9, depreciation_rate=.9),
    ),
)


@pytest.mark.parametrize("households,firms", [SCAN_ROUNDING, INCOME_CANCELLATION],
                         ids=["intermediate-payroll", "net-income"])
def test_numerical_audit_examples_clear_and_settle(households, firms):
    previous = None
    for _ in range(3):
        current = advance_period(households, firms, previous)
        certify_household_choices(current, check_grid=current.number == 1)
        certify_accounts(current, previous)
        previous = current


def test_income_cancellation_is_bounded_by_the_stored_subtractions():
    period = advance_period(*INCOME_CANCELLATION)
    account = period.firm_accounts["f1"]
    # This is the original audit failure, not merely an ordinary passing account.
    reconstructed = (account.wage_bill + account.net_operating_profit
                     + account.depreciation_value)
    assert abs(account.production_value - reconstructed) > (
        1e-9 * account.production_value
    )
    with localcontext() as context:
        context.prec = 80
        decimal = Decimal.from_float
        residual = (decimal(account.production_value) - decimal(account.wage_bill)
                    - decimal(account.net_operating_profit)
                    - decimal(account.depreciation_value))
        rounding = (decimal(ulp(account.gross_operating_surplus))
                    + decimal(ulp(account.net_operating_profit))) / 2
        assert abs(residual) <= rounding


def test_income_certificate_rejects_more_than_rounding_error(monkeypatch):
    close_accounts = _PeriodBuilder._close_accounts

    def corrupt_profit(builder):
        close_accounts(builder)
        account = builder.accounts["f1"]
        # Much smaller than 1e-9 of depreciation, but hundreds of float steps:
        # using depreciation as the relative tolerance scale would hide it.
        builder.accounts["f1"] = replace(
            account, net_operating_profit=account.net_operating_profit + 1e-6
        )

    monkeypatch.setattr(_PeriodBuilder, "_close_accounts", corrupt_profit)
    with pytest.raises(ValueError, match="net_income"):
        advance_period(*INCOME_CANCELLATION)


def test_scan_rounding_does_not_relax_final_payroll_clearing():
    households, firms = SCAN_ROUNDING
    available = {h.id: h.money for h in households}
    funding = {f.id: f.money for f in firms}
    capital = {f.id: f.capital for f in firms}
    price, wage, wages, bills, _ = market_candidates(
        households, firms, available, funding, capital
    )[0]
    wages = dict(wages)
    wages["h0"] += 1e-6 * fsum(bills.values())
    with pytest.raises(ValueError, match="candidate market exceeded"):
        _certify_candidate(
            households, firms, available, funding, capital, price, wage, wages, bills
        )
