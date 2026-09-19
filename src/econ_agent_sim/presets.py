"""Tested starting points for the single forward-looking monetary economy."""

from dataclasses import dataclass, replace

from econ_agent_sim.domain import Settings
from econ_agent_sim.monetary_growth import steady_state


@dataclass(frozen=True)
class Preset:
    key: str
    title: str
    description: str


PRESETS = {
    preset.key: preset for preset in (
        Preset(
            "growing", "Growing economy",
            "Start with one unit of capital per firm and an equal split of money "
            "between households and firms. Watch saving and investment change capacity.",
        ),
        Preset(
            "capital_abundant", "Capital abundant",
            "Start with 100 units of capital per firm. Explore why firms can stop "
            "investing while existing capital wears down.",
        ),
        Preset(
            "capital_scarce", "Firms short of capital",
            "Start with 0.1 units of capital per firm. Explore the balance between "
            "consumption today and building productive capacity.",
        ),
        Preset(
            "tight_cash", "Tight opening cash",
            "Firms begin with 4.44 units of capital each and just 5% of all money. "
            "Explore how funding wages can require a pause in dividends.",
        ),
        Preset(
            "stationary", "Stationary economy",
            "Begin at the model's steady state: investment replaces worn capital "
            "and the same choices repeat each period.",
        ),
    )
}


def build_preset(key: str) -> Settings:
    """Return fresh settings; selecting a title alone does not alter a draft."""
    if key not in PRESETS:
        raise ValueError("Choose a supported starting experiment.")
    settings = Settings()
    if key == "capital_abundant":
        return replace(settings, initial_capital=100.)
    if key == "capital_scarce":
        return replace(settings, initial_capital=.1)
    if key == "tight_cash":
        return replace(settings, initial_capital=4.44, initial_firm_cash_share=.05)
    if key == "stationary":
        target = steady_state(settings.to_parameters())
        return replace(
            settings, initial_capital=target.capital,
            initial_firm_cash_share=2 * target.firm_cash,
        )
    return settings
