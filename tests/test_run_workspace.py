import json

import pytest

from econ_agent_sim.economy_0_4 import run_economy_0_4
from econ_agent_sim.experiment_chat import context_id
from econ_agent_sim.run_workspace import SubmittedRun, default_agents, setup_config


def test_submitted_data_agrees_with_engine_and_independent_previous_run():
    baseline = run_economy_0_4(setup_config(default_agents()))
    draft = default_agents(3)
    draft[0].update(x=2.0, alpha=.8)
    result = run_economy_0_4(setup_config(draft, money=12))
    run = SubmittedRun(result, baseline, 2, 4)
    context = run.context(0)
    json.dumps(context, allow_nan=False)
    assert context['prices'] == result.periods[0].prices
    assert context['agents'][0]['opening'] == result.periods[0].opening_stocks['Agent 1']
    assert context['agents'][0]['closing'] == result.periods[0].closing_stocks['Agent 1']
    assert context['agents'][0]['alpha'] == .8
    assert context['previous_run']['agents'][0]['alpha'] == .5
    assert len(context['previous_run']['agents']) == 2
    assert context['previous_run']['prices'] == baseline.periods[0].prices
    assert any('Agent 3 added' in c for c in context['setup_changes'])
    assert any('spending share' in c for c in context['setup_changes'])
    assert context['totals']['opening'] == {'X': 4, 'Y': 3, 'Money': 36}
    assert context['selected_trade']['ordinal'] == 1
    assert context['selected_trade']['payment'] == result.trades[0].payment
    assert all(context['checks'].values())
    assert context_id(context) != context_id(run.context())
    draft[0]['x'] = 999
    assert run.context()['agents'][0]['opening']['X'] == 2
    assert 'selected_trade' not in run.data
    assert run.context()['selected_trade'] is None
    assert len(run.accounting_rows) == 9


def test_trade_context_ignores_invalid_indexes():
    run = SubmittedRun(run_economy_0_4(), None, 1, 3)
    assert run.context(-1)["selected_trade"] is None
    assert run.context(True)["selected_trade"] is None
    assert run.context(len(run.period.trades))["selected_trade"] is None


def test_run_rejects_multi_period_results_and_twenty_agents_fit_chat_budget():
    from dataclasses import replace

    result = run_economy_0_4(setup_config(default_agents()))
    with pytest.raises(ValueError, match='exactly one'):
        SubmittedRun(replace(result, periods=result.periods * 2), None, 1, 1)
    from econ_agent_sim.economy_0_2 import canonical_population
    from econ_agent_sim.economy_0_4 import Economy04Config

    large = run_economy_0_4(Economy04Config(period_populations=(canonical_population(20),)))
    context = SubmittedRun(large, large, 2, 2).context(0)
    assert len(json.dumps(context, separators=(',', ':'), allow_nan=False)) <= 35000
