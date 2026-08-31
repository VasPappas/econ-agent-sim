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
    assert 'st.popover("Settings"' not in source
    assert 'settings_panel = st.expander(' in source
    assert '"Settings",' in source
    assert 'key="economy03_settings_open"' in source
    assert 'on_change="rerun"' in source
    assert '"Number of agents"' in source
    assert "min_value=2" in source
    assert "max_value=20" in source
    assert "Agents always come in mirrored pairs" in source
    assert "staged_agent_count = int(st.session_state.economy03_agent_count_input)" in source
    assert "for pair_index in range(staged_agent_count // 2):" in source
    assert "settings below update immediately" in source
    assert '"Adjustment speed (lambda)"' in source
    assert "st.slider(" not in source
    assert "Calibrate the selected agent pairs" in source
    assert "mirrors X and Y" in source
    assert "1 − α" in source
    assert 'key=f"economy03_pair_x_{pair_index}_input"' in source
    assert 'key=f"economy03_pair_y_{pair_index}_input"' in source
    assert 'key=f"economy03_pair_alpha_{pair_index}_input"' in source
    assert 'f"Agent {first_agent} opening X"' in source
    assert 'f"Agent {first_agent} opening Y"' in source
    assert '"Apply and close"' in source
    assert "st.session_state.economy03_settings_open = False" in source
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


def test_economy_0_3_uses_responsive_result_blocks_not_narrow_metric_cards() -> None:
    source = (APP_ROOT / PERMANENT_PAGES[3]).read_text()

    assert 'st.caption("SELECTED RESULT")' in source
    assert "st.metric(" not in source
    assert source.count("with st.container(border=True):") >= 2
    assert "overview_floor = max(0.0, price_low - price_padding)" in source
    assert "overview_ceiling = price_high + price_padding" in source
    assert "zero=False" in source
    assert "The vertical axis is zoomed" in source


def test_economy_0_3_page_avoids_new_helper_imports_for_cloud_hot_reload() -> None:
    source = (APP_ROOT / PERMANENT_PAGES[3]).read_text()

    assert "from econ_agent_sim.economy_0_2 import canonical_population" in source
    assert "templates = canonical_population()" in source
    assert "canonical_population(agent_count)" not in source
    assert (
        "from econ_agent_sim.economy_0_3 import Economy03Config, run_economy_0_3"
        in source
    )
    assert "    baseline_period_populations,\n" not in source
    assert "    redistribute_y,\n" not in source
