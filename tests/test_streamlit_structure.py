from pathlib import Path

APP_ROOT = Path("app")
PERMANENT_PAGES = (
    "pages/1_Economy_0_Pure_Exchange.py",
    "pages/2_Economy_0_1_Walrasian_Price_Discovery.py",
    "pages/3_Economy_0_2_Many_Agent_Exchange.py",
    "pages/4_Economy_0_3_Repeated_Exchange.py",
)


def test_home_dashboard_and_permanent_economy_pages_exist() -> None:
    assert (APP_ROOT / "streamlit_app.py").is_file()
    for relative_path in PERMANENT_PAGES:
        assert (APP_ROOT / relative_path).is_file()


def test_home_dashboard_links_to_every_permanent_economy() -> None:
    home_source = (APP_ROOT / "streamlit_app.py").read_text()
    for relative_path in PERMANENT_PAGES:
        assert relative_path in home_source


def test_economy_0_2_keeps_tablet_controls_and_accounting_in_main_page() -> None:
    source = (APP_ROOT / PERMANENT_PAGES[2]).read_text()

    assert "st.sidebar" not in source
    assert 'st.subheader("Experiment controls")' in source
    assert 'st.subheader("Stock-flow checkpoint")' in source
    assert 'st.tabs(["Market process", "Agent decisions"])' in source


def test_economy_0_3_keeps_period_centered_tablet_layout() -> None:
    source = (APP_ROOT / PERMANENT_PAGES[3]).read_text()

    assert "st.sidebar" not in source
    assert 'st.subheader("Experiment controls")' in source
    assert 'st.subheader("Across-period view")' in source
    assert '"Endowments & price"' in source
    assert '"Accounting"' in source
    assert '"Full multi-period ledger"' in source
    assert "Closing stocks from one period are not" in source
