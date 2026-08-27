from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_ENTRYPOINT = Path(__file__).parents[1] / "app" / "streamlit_app.py"
ECONOMY_02_PAGE = "pages/3_Economy_0_2_Many_Agent_Exchange.py"


def test_economy_0_2_page_runs_without_streamlit_exceptions() -> None:
    app = AppTest.from_file(APP_ENTRYPOINT, default_timeout=10).run()
    app.switch_page(ECONOMY_02_PAGE).run(timeout=10)

    assert not app.exception
    assert any(item.value == "Experiment controls" for item in app.subheader)
    assert any(item.value == "Stock-flow checkpoint" for item in app.subheader)
