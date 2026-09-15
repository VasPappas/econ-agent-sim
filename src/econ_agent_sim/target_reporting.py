"""Original-price accounts with household consumption-target coverage.

Coverage is measured separately for every household and period. Extra
consumption cannot erase a previous shortfall or another household's shortfall.
The target changes preferences; it is not a guaranteed minimum entitlement.
"""

from collections.abc import Sequence
from math import fsum

from econ_agent_sim.competition_reporting import competition_report
from econ_agent_sim.economy_1_0 import TOLERANCE, Economy10Period
from econ_agent_sim.economy_1_1 import Economy11Period


def _coverage(consumption, target):
    consumed = tuple(consumption)
    needed = target * len(consumed)
    met = fsum(min(value, target) for value in consumed)
    shortfall = fsum(max(target - value, 0.0) for value in consumed)
    below = sum(
        target - value > TOLERANCE * max(target, abs(value))
        for value in consumed
    )
    return {
        "needed_x": needed,
        "needs_met_x": met,
        "shortfall_x": shortfall,
        "target_coverage": met / needed if needed else None,
        "below_target_periods": below,
    }


def target_report(
    periods: Economy11Period | Sequence[Economy11Period], cumulative: bool = False
) -> dict:
    """Extend the common firm and household accounts with soft-target metrics."""
    history = (periods,) if isinstance(periods, Economy10Period) else tuple(periods)
    if not history or not all(isinstance(period, Economy11Period) for period in history):
        raise ValueError("Use completed Economy 1.1 periods for this report.")
    # The shared reporting contract checks linked periods, fixed settings and
    # ownership, and retains each monetary flow's original transaction price.
    report = competition_report(history, cumulative)
    selected = history if cumulative else history[-1:]
    specifications = {household.id: household for household in selected[-1].households}
    for household in report["households"]:
        identity = household["entity_id"]
        target = specifications[identity].consumption_target
        household["parameters"]["consumption_target"] = target
        household.update(_coverage(
            (period.consumption[identity] for period in selected), target
        ))

    households = report["households"]
    economy = report["economy"]
    for field in ("needed_x", "needs_met_x", "shortfall_x"):
        economy[field] = fsum(household[field] for household in households)
    economy["target_coverage"] = (
        economy["needs_met_x"] / economy["needed_x"]
        if economy["needed_x"] else None
    )
    economy["household_periods_below_target"] = sum(
        household["below_target_periods"] for household in households
    )
    economy["households_below_target"] = sum(
        household["below_target_periods"] > 0 for household in households
    )

    for row in report["rows"]:
        if row.get("record_type") == "account" and row.get("account_type") == "household":
            target = specifications[row["entity_id"]].consumption_target
            row["consumption_target"] = target
            row.update(_coverage((row["consumed_x"],), target))

    report["model"] = "consumption_target"
    report["policies"]["consumption_target"] = (
        "Below the consumption target, each extra unit of X becomes more valuable. "
        "Households still trade off consumption, money and leisure; the target "
        "does not guarantee consumption or create goods, cash or transfers. "
        "A zero target turns off the extra incentive."
    )
    report["policies"]["target_coverage"] = (
        "Target coverage counts consumption up to each household's target in each "
        "period. Shortfalls sum separately across households and periods; extra "
        "consumption cannot cancel them. Zero-target coverage is not applicable. "
        "Below-target period counts ignore numerical rounding dust."
    )
    return report
