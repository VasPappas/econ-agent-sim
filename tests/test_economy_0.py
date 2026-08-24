from math import isclose

from econ_agent_sim.economy_0 import run_economy_0


def test_equilibrium_prices_are_one_to_one() -> None:
    result = run_economy_0()
    assert result.prices == {"X": 1.0, "Y": 1.0}


def test_agents_reach_textbook_equilibrium_allocation() -> None:
    result = run_economy_0()
    assert result.closing_stocks == {
        "Alice": {"X": 0.5, "Y": 0.5},
        "Bob": {"X": 0.5, "Y": 0.5},
    }


def test_every_transfer_is_recorded() -> None:
    result = run_economy_0()
    assert len(result.transactions) == 2
    assert {(t.good, t.quantity, t.sender, t.receiver) for t in result.transactions} == {
        ("X", 0.5, "Alice", "Bob"),
        ("Y", 0.5, "Bob", "Alice"),
    }
    assert {t.trade_id for t in result.transactions} == {1}


def test_stock_flow_identity_holds_for_every_agent_and_good() -> None:
    result = run_economy_0()
    for agent, opening in result.opening_stocks.items():
        for good, opening_quantity in opening.items():
            assert isclose(
                opening_quantity + result.flows[agent][good],
                result.closing_stocks[agent][good],
                abs_tol=1e-12,
            )


def test_goods_are_conserved_system_wide() -> None:
    result = run_economy_0()
    for good in ("X", "Y"):
        opening_total = sum(v[good] for v in result.opening_stocks.values())
        closing_total = sum(v[good] for v in result.closing_stocks.values())
        net_flow = sum(v[good] for v in result.flows.values())
        assert isclose(opening_total, closing_total, abs_tol=1e-12)
        assert isclose(net_flow, 0.0, abs_tol=1e-12)
