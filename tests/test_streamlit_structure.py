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


def test_economy_0_3_is_mobile_first_user_driven_redistribution() -> None:
    source = (APP_ROOT / PERMANENT_PAGES[3]).read_text()

    assert 'layout="centered"' in source
    assert 'initial_sidebar_state="collapsed"' in source
    assert "st.sidebar" not in source
    assert 'st.title("Redistribution experiment")' in source
    assert 'st.popover("Settings"' in source
    assert 'with st.expander("Add a redistribution"' in source
    assert '"Move Y from"' in source
    assert '"Move Y to"' in source
    assert '"Add as next period"' in source
    assert '"Remove last redistribution"' in source
    assert "baseline_period_populations" in source
    assert "redistribute_y(" in source
    assert source.count("st.pills(") == 2
    assert 'options=("Overview", "Market", "Audit")' in source
    assert "horizontal=True, wrap=False" in source
    assert 'if view == "Overview"' in source
    assert 'elif view == "Market"' in source
    assert 'st.subheader("Audit")' in source
    assert 'with st.expander("Agent decisions")' in source
    assert 'with st.expander("Stock-flow accounts")' in source
    assert 'with st.expander("Period settlement ledger")' in source
    assert 'with st.expander("Full multi-period ledger")' in source
    assert "comparison_iterations = max(400, adjustments) * 1.05" in source
    assert "alt.Scale(domain=[0.0, comparison_iterations])" in source
    assert "alt.Scale(domain=[0.0, comparison_ceiling])" in source
    assert 'with st.expander("Model boundary")' in source


def test_economy_0_3_page_avoids_new_helper_imports_for_cloud_hot_reload() -> None:
    source = (APP_ROOT / PERMANENT_PAGES[3]).read_text()

    assert "from econ_agent_sim.economy_0_2 import canonical_population" in source
    assert (
        "from econ_agent_sim.economy_0_3 import Economy03Config, run_economy_0_3"
        in source
    )
    assert "    baseline_period_populations,\n" not in source
    assert "    redistribute_y,\n" not in source
