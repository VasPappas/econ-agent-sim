from pathlib import Path

from streamlit.testing.v1 import AppTest

from econ_agent_sim.economy_0_3 import baseline_period_populations, redistribute_y

APP_ENTRYPOINT = Path(__file__).parents[1] / "app" / "streamlit_app.py"
ECONOMY_03_PAGE = "pages/4_Economy_0_3_Repeated_Exchange.py"


def test_economy_0_3_user_redistribution_views_run_without_exceptions() -> None:
    app = AppTest.from_file(APP_ENTRYPOINT, default_timeout=10).run()
    app.switch_page(ECONOMY_03_PAGE).run(timeout=10)

    assert not app.exception
    assert any(item.value == "Overview" for item in app.subheader)
    assert any(item.value == "Redistribution experiment" for item in app.title)

    baseline = baseline_period_populations()[0]
    second = redistribute_y(
        baseline,
        sender_name="Agent 2",
        receiver_name="Agent 1",
        amount=0.5,
    )
    app.session_state["economy03_period_populations"] = (baseline, second)
    app.session_state["economy03_period_picker"] = "Redistribution 1"
    app.run(timeout=10)

    assert not app.exception
    assert any(item.value == "Overview" for item in app.subheader)

    for view in ("Market", "Audit"):
        app.session_state["economy03_view_picker"] = view
        app.run(timeout=10)
        assert not app.exception
        assert any(item.value == view for item in app.subheader)
