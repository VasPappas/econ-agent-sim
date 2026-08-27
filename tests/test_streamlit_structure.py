from pathlib import Path


APP_ROOT = Path("app")
PERMANENT_PAGES = (
    "pages/1_Economy_0_Pure_Exchange.py",
    "pages/2_Economy_0_1_Walrasian_Price_Discovery.py",
    "pages/3_Economy_0_2_Many_Agent_Exchange.py",
)


def test_home_dashboard_and_permanent_economy_pages_exist() -> None:
    assert (APP_ROOT / "streamlit_app.py").is_file()
    for relative_path in PERMANENT_PAGES:
        assert (APP_ROOT / relative_path).is_file()


def test_home_dashboard_links_to_every_permanent_economy() -> None:
    home_source = (APP_ROOT / "streamlit_app.py").read_text()
    for relative_path in PERMANENT_PAGES:
        assert relative_path in home_source
