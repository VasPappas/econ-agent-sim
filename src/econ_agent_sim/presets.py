"""A small set of editable starting points for one supported economic model."""

from dataclasses import dataclass

from econ_agent_sim.engine import default_firms, default_households


@dataclass(frozen=True)
class Preset:
    key: str
    title: str
    description: str


PRESETS = {
    preset.key: preset for preset in (
        Preset(
            "everyday", "Everyday economy",
            "Two equal households and two equal firms. Explore work, consumption, "
            "money and investment with a target of 0.50 X per household.",
        ),
        Preset(
            "fixed_capacity", "Fixed productive capacity",
            "Turn off investment, capital wear and consumption targets. "
            "Explore how preferences and money shape outcomes with unchanged capital.",
        ),
        Preset(
            "capital_wears_out", "Capital wears out",
            "Turn off investment and consumption targets; keep capital wear at 10%. "
            "What happens to production and prices as productive capacity shrinks?",
        ),
        Preset(
            "meeting_a_target", "Meeting a consumption target",
            "Each household aims for 1.00 X per period. Explore how a target gap "
            "changes the trade-off between consumption, money and leisure.",
        ),
        Preset(
            "firms_look_ahead", "Firms look ahead",
            "Both firms compare expected capital returns with required return and wear. "
            "Firm A is less productive: explore why one holds back while the other invests.",
        ),
    )
}


def build_preset(key: str) -> tuple[list[dict], list[dict]]:
    """Return fresh default-sized settings; applying them is an explicit UI action."""
    if key not in PRESETS:
        raise ValueError("Choose a supported starting experiment.")
    households = default_households()
    firms = default_firms()
    if key in {"fixed_capacity", "capital_wears_out"}:
        for household in households:
            household["consumption_target"] = 0.0
        for firm in firms:
            firm["reinvestment_rate"] = 0.0
            firm["depreciation_rate"] = .1 if key == "capital_wears_out" else 0.0
    elif key == "meeting_a_target":
        for household in households:
            household["consumption_target"] = 1.0
    elif key == "firms_look_ahead":
        for firm in firms:
            firm["investment_policy"] = "user_cost"
        firms[0]["productivity"] = .5
    return households, firms
