from math import isclose
from pathlib import Path

from streamlit.testing.v1 import AppTest

from econ_agent_sim.economy_0_3 import baseline_period_populations, redistribute_y

APP_ENTRYPOINT = Path(__file__).parents[1] / "app" / "streamlit_app.py"
ECONOMY_03_PAGE = "pages/4_Economy_0_3_Repeated_Exchange.py"


def open_economy_0_3() -> AppTest:
    app = AppTest.from_file(APP_ENTRYPOINT, default_timeout=10).run()
    return app.switch_page(ECONOMY_03_PAGE).run(timeout=10)


def test_economy_0_3_user_redistribution_views_run_without_exceptions() -> None:
    app = open_economy_0_3()

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


def test_economy_0_3_settings_apply_and_close() -> None:
    app = open_economy_0_3()

    app.session_state["economy03_settings_open"] = True
    app.run(timeout=10)
    app.number_input(key="economy03_initial_price_input").set_value(2.0)
    app.number_input(key="economy03_adjustment_speed_input").set_value(0.3)
    apply_button = next(
        button for button in app.button if button.label == "Apply and close"
    )
    apply_button.click().run(timeout=10)

    assert not app.exception
    assert app.session_state["economy03_agent_count"] == 10
    assert app.session_state["economy03_initial_price_x"] == 2.0
    assert app.session_state["economy03_adjustment_speed"] == 0.3
    assert app.session_state["economy03_settings_open"] is False


def test_economy_0_3_agent_count_change_resets_to_paired_baseline() -> None:
    app = open_economy_0_3()

    baseline = baseline_period_populations()[0]
    second = redistribute_y(
        baseline,
        sender_name="Agent 2",
        receiver_name="Agent 1",
        amount=0.5,
    )
    app.session_state["economy03_period_populations"] = (baseline, second)
    app.session_state["economy03_period_picker"] = "Redistribution 1"
    app.session_state["economy03_settings_open"] = True
    app.run(timeout=10)

    app.number_input(key="economy03_agent_count_input").set_value(6)
    apply_button = next(
        button for button in app.button if button.label == "Apply and close"
    )
    apply_button.click().run(timeout=10)

    assert not app.exception
    assert app.session_state["economy03_agent_count"] == 6
    assert app.session_state["economy03_period_picker"] == "Baseline"
    assert app.session_state["economy03_view_picker"] == "Overview"
    assert app.session_state["economy03_settings_open"] is False

    periods = app.session_state["economy03_period_populations"]
    assert len(periods) == 1
    assert len(periods[0]) == 6
    for pair_start in range(0, 6, 2):
        left = periods[0][pair_start]
        right = periods[0][pair_start + 1]
        assert left.x == right.y
        assert left.y == right.x
        assert isclose(left.alpha + right.alpha, 1.0, abs_tol=1e-12)


def test_economy_0_3_pair_alpha_change_resets_and_preserves_mirror() -> None:
    app = open_economy_0_3()

    baseline = baseline_period_populations()[0]
    second = redistribute_y(
        baseline,
        sender_name="Agent 2",
        receiver_name="Agent 1",
        amount=0.2,
    )
    app.session_state["economy03_period_populations"] = (baseline, second)
    app.session_state["economy03_period_picker"] = "Redistribution 1"
    app.session_state["economy03_settings_open"] = True
    app.run(timeout=10)

    app.number_input(key="economy03_pair_alpha_0_input").set_value(0.35)
    apply_button = next(
        button for button in app.button if button.label == "Apply and close"
    )
    apply_button.click().run(timeout=10)

    assert not app.exception
    assert app.session_state["economy03_period_picker"] == "Baseline"
    periods = app.session_state["economy03_period_populations"]
    assert len(periods) == 1
    first, second = periods[0][0], periods[0][1]
    assert isclose(first.alpha, 0.35, abs_tol=1e-12)
    assert isclose(second.alpha, 0.65, abs_tol=1e-12)
    assert isclose(first.alpha + second.alpha, 1.0, abs_tol=1e-12)


def test_economy_0_3_pair_endowment_change_resets_and_preserves_mirror() -> None:
    app = open_economy_0_3()

    baseline = baseline_period_populations()[0]
    second = redistribute_y(
        baseline,
        sender_name="Agent 2",
        receiver_name="Agent 1",
        amount=0.2,
    )
    app.session_state["economy03_period_populations"] = (baseline, second)
    app.session_state["economy03_period_picker"] = "Redistribution 1"
    app.session_state["economy03_settings_open"] = True
    app.run(timeout=10)

    app.number_input(key="economy03_pair_x_0_input").set_value(2.4)
    app.number_input(key="economy03_pair_y_0_input").set_value(0.6)
    apply_button = next(
        button for button in app.button if button.label == "Apply and close"
    )
    apply_button.click().run(timeout=10)

    assert not app.exception
    assert app.session_state["economy03_period_picker"] == "Baseline"
    periods = app.session_state["economy03_period_populations"]
    assert len(periods) == 1
    first, second = periods[0][0], periods[0][1]
    assert isclose(first.x, 2.4, abs_tol=1e-12)
    assert isclose(first.y, 0.6, abs_tol=1e-12)
    assert isclose(second.x, 0.6, abs_tol=1e-12)
    assert isclose(second.y, 2.4, abs_tol=1e-12)
    assert isclose(first.alpha + second.alpha, 1.0, abs_tol=1e-12)

    numerator = sum(agent.alpha * agent.y for agent in periods[0])
    denominator = sum((1.0 - agent.alpha) * agent.x for agent in periods[0])
    assert isclose(numerator, denominator, abs_tol=1e-12)
