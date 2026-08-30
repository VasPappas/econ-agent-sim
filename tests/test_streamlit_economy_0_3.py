from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_ENTRYPOINT = Path(__file__).parents[1] / "app" / "streamlit_app.py"
ECONOMY_03_PAGE = "pages/4_Economy_0_3_Repeated_Exchange.py"


def test_economy_0_3_mobile_views_run_without_streamlit_exceptions() -> None:
    app = AppTest.from_file(APP_ENTRYPOINT, default_timeout=10).run()
    app.switch_page(ECONOMY_03_PAGE).run(timeout=10)

    assert not app.exception
    assert any(item.value == "Overview" for item in app.subheader)

    app.session_state["economy03_period_picker"] = 2
    app.run(timeout=10)
    assert not app.exception

    for view in ("Market", "Agents", "Accounts", "Ledger"):
        app.session_state["economy03_view_picker"] = view
        app.run(timeout=10)
        assert not app.exception
        assert any(item.value == view for item in app.subheader)
