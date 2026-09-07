"""Regressions for false accounting passes and non-finite model inputs."""

from dataclasses import replace

import pytest

from econ_agent_sim import economy_0_4
from econ_agent_sim.economy_0 import Economy0Config, run_economy_0
from econ_agent_sim.economy_0_2 import Economy02Config, ExchangeAgentConfig
from econ_agent_sim.economy_0_3 import canonical_period_populations, redistribute_y
from econ_agent_sim.economy_0_4 import Economy04Config, run_economy_0_4
from econ_agent_sim.ledger import Ledger
from econ_agent_sim.model import Agent, CobbDouglasPreferences
from econ_agent_sim.numerics import assert_close, balances_match
from econ_agent_sim.price_discovery import TatonnementSettings
from econ_agent_sim.reporting import accounting_rows, stock_flow_rows
from econ_agent_sim.run_workspace import SubmittedRun, default_agents, setup_config


@pytest.mark.parametrize('value', [float('nan'), float('inf'), float('-inf')])
def test_nonfinite_inputs_rejected_at_engine_boundaries(value):
    constructors = [
        lambda: Economy0Config(alice_x=value),
        lambda: ExchangeAgentConfig('A', value, 1, .5),
        lambda: ExchangeAgentConfig('A', 1, value, .5),
        lambda: CobbDouglasPreferences(value),
        lambda: Agent('A', CobbDouglasPreferences(.5), {'X': value}),
        lambda: TatonnementSettings(initial_price_x=value),
        lambda: TatonnementSettings(adjustment_speed=value),
        lambda: TatonnementSettings(tolerance=value),
        lambda: TatonnementSettings(max_iterations=value),
        lambda: Economy04Config(opening_money_per_agent=value),
        lambda: CobbDouglasPreferences(.5).demand(value, {'X': 1, 'Y': 1}),
        lambda: CobbDouglasPreferences(.5).demand(2, {'X': value, 'Y': 1}),
        lambda: CobbDouglasPreferences(.5).demand(2, {'X': 1, 'Y': value}),
        lambda: redistribute_y(canonical_period_populations()[0], sender_name='Agent 1',
                               receiver_name='Agent 2', amount=value),
    ]
    for construct in constructors:
        with pytest.raises(ValueError):
            construct()
    assert not balances_match(value, value)
    with pytest.raises(AssertionError):
        assert_close(value, 0)

    sender = Agent('A', CobbDouglasPreferences(.5), {'X': 1, 'Y': 1})
    receiver = Agent('B', CobbDouglasPreferences(.5), {'X': 1, 'Y': 1})
    ledger = Ledger()
    with pytest.raises(ValueError):
        ledger.transfer(trade_id=1, period=0, good='X', quantity=value,
                        sender=sender, receiver=receiver)
    assert sender.holdings == receiver.holdings == {'X': 1, 'Y': 1}
    assert ledger.transactions == ()


def test_finite_inputs_that_overflow_are_rejected():
    with pytest.raises(ValueError, match='finite'):
        Economy02Config(agents=(ExchangeAgentConfig('A', 1e308, 1, .5),
                                ExchangeAgentConfig('B', 1e308, 1, .5)))
    with pytest.raises(ValueError, match='finite'):
        Economy04Config(opening_money_per_agent=1e308)
    with pytest.raises(ValueError, match='finite'):
        CobbDouglasPreferences(.5).demand(1e308, {'X': 1e-308, 'Y': 1})
    for invalid in (True, 2.5):
        with pytest.raises(ValueError, match='integer'):
            TatonnementSettings(max_iterations=invalid)


def test_reports_detect_changed_closing_balances_and_missing_transfers():
    result = run_economy_0()
    assert all(row['check'] is None for row in accounting_rows(result, 1))
    result.closing_stocks['Alice']['X'] += 1
    rows = stock_flow_rows(result)
    alice_x = next(row for row in rows if (row['agent'], row['good']) == ('Alice', 'X'))
    assert alice_x['closing_stock'] == result.closing_stocks['Alice']['X']
    assert alice_x['check'] == pytest.approx(-1)

    result = run_economy_0()
    missing = replace(result, transactions=result.transactions[1:])
    assert any(not balances_match(row['check'], 0) for row in accounting_rows(missing))


def test_monetary_engine_detects_damaged_payment_leg(monkeypatch):
    monetize = economy_0_4._monetize_transactions

    def damaged(**kwargs):
        trades, transactions = monetize(**kwargs)
        transactions = list(transactions)
        transactions[1] = replace(transactions[1], quantity=transactions[1].quantity + 1)
        return trades, tuple(transactions)

    monkeypatch.setattr(economy_0_4, '_monetize_transactions', damaged)
    with pytest.raises(AssertionError, match='accounting mismatch'):
        run_economy_0_4()


def test_submitted_checks_reconstruct_ledger_even_if_reported_flows_match_bad_balances():
    result = run_economy_0_4()
    period = result.periods[0]
    # Preserve aggregate money and make the recorded flow agree with each bad balance.
    # Only reconstruction from the actual ledger can detect this discrepancy.
    for name, delta in [('Agent 1', 1), ('Agent 2', -1)]:
        period.closing_stocks[name]['Money'] += delta
        period.flows[name]['Money'] += delta
    run = SubmittedRun(result, None, 1, 1)
    assert run.data['checks']['money']
    assert not run.data['checks']['accounts']
    assert any(abs(row['check']) > .9 for row in run.accounting_rows)


def test_baseline_and_historical_multi_period_accounts_still_reconcile():
    baseline = run_economy_0_4(setup_config(default_agents()))
    run = SubmittedRun(baseline, None, 1, 1)
    assert run.data['prices'] == {'X': 1, 'Y': 1}
    assert run.data['trades'] == []
    assert all(run.data['checks'].values())
    historical = run_economy_0_4(Economy04Config(
        period_populations=canonical_period_populations(),
    ))
    for period in historical.periods:
        single = replace(historical, periods=(period,))
        assert all(SubmittedRun(single, None, 1, 1).data['checks'].values())
