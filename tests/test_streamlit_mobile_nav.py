from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_ENTRYPOINT = Path(__file__).parents[1] / "app" / "streamlit_app.py"
ECONOMY_03_PAGE = "pages/4_Economy_0_3_Repeated_Exchange.py"
PAGE_SOURCE = Path(__file__).parents[1] / "app" / ECONOMY_03_PAGE


def open_economy_0_3() -> AppTest:
    app = AppTest.from_file(APP_ENTRYPOINT, default_timeout=10).run()
    return app.switch_page(ECONOMY_03_PAGE).run(timeout=10)


def has_expander(app: AppTest, label: str) -> bool:
    return any(item.label == label for item in app.expander)


def has_selected_result(app: AppTest) -> bool:
    return any(item.value == "SELECTED RESULT" for item in app.caption)


def test_economy_0_3_mobile_view_nav_is_scoped_and_phone_safe() -> None:
    source = PAGE_SOURCE.read_text()

    assert '@media (max-width: 768px)' in source
    assert '.st-key-economy03_mobile_nav' in source
    assert 'position: fixed;' in source
    assert 'bottom: calc(5.25rem + env(safe-area-inset-bottom));' in source
    assert 'left: max(1rem, env(safe-area-inset-left));' in source
    assert 'right: max(1rem, env(safe-area-inset-right));' in source
    assert 'padding-bottom: calc(12rem + env(safe-area-inset-bottom));' in source
    assert 'with st.container(key="economy03_mobile_nav"):' in source
    assert 'label_visibility="collapsed"' in source


def test_economy_0_3_view_navigation_still_switches_all_views() -> None:
    app = open_economy_0_3()

    assert not app.exception
    assert any(item.value == "Overview" for item in app.subheader)

    for view in ("Market", "Audit", "Overview"):
        app.session_state["economy03_view_picker"] = view
        app.run(timeout=10)
        assert not app.exception
        assert any(item.value == view for item in app.subheader)


def test_economy_0_3_controls_result_and_boundary_are_overview_only() -> None:
    app = open_economy_0_3()

    assert not app.exception
    assert has_expander(app, "Settings")
    assert has_expander(app, "Add a redistribution")
    assert has_expander(app, "Model boundary")
    assert has_selected_result(app)

    for view in ("Market", "Audit"):
        app.session_state["economy03_view_picker"] = view
        app.run(timeout=10)
        assert not app.exception
        assert not has_expander(app, "Settings")
        assert not has_expander(app, "Add a redistribution")
        assert not has_expander(app, "Model boundary")
        assert not has_selected_result(app)

    app.session_state["economy03_view_picker"] = "Overview"
    app.run(timeout=10)
    assert not app.exception
    assert has_expander(app, "Settings")
    assert has_expander(app, "Add a redistribution")
    assert has_expander(app, "Model boundary")
    assert has_selected_result(app)
