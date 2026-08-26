from __future__ import annotations

from dataclasses import dataclass

from econ_agent_sim.model import Agent


@dataclass(frozen=True)
class TatonnementSettings:
    """Numerical settings for two-good Walrasian price discovery."""

    initial_price_x: float = 0.5
    adjustment_speed: float = 1.0
    tolerance: float = 1e-10
    max_iterations: int = 5000

    def __post_init__(self) -> None:
        if self.initial_price_x <= 0:
            raise ValueError("initial_price_x must be strictly positive")
        if not 0.0 < self.adjustment_speed <= 1.0:
            raise ValueError("adjustment_speed must lie in (0, 1]")
        if self.tolerance <= 0:
            raise ValueError("tolerance must be strictly positive")
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")


@dataclass(frozen=True)
class TatonnementStep:
    iteration: int
    price_x: float
    supply_x: float
    demand_x: float
    excess_demand_x: float
    normalized_excess_demand_x: float
    supply_y: float
    demand_y: float
    excess_demand_y: float
    normalized_excess_demand_y: float
    market_error: float
    next_price_x: float | None


def discover_price(
    agents: list[Agent], settings: TatonnementSettings
) -> tuple[tuple[TatonnementStep, ...], dict[str, float]]:
    """Discover the relative price using discrete proportional tatonnement.

    Prices move in the direction of X excess demand:

        p_X(t+1) = p_X(t) * [1 + lambda * z_X(t) / X_bar]

    Both markets must be within the numerical clearing tolerance before the
    search is declared converged. No analytic equilibrium price enters the
    iteration.
    """

    if not agents:
        raise ValueError("tatonnement requires at least one agent")

    total_x = sum(agent.holdings["X"] for agent in agents)
    total_y = sum(agent.holdings["Y"] for agent in agents)
    if total_x <= 0 or total_y <= 0:
        raise ValueError("tatonnement requires positive aggregate supplies of X and Y")

    price_x = settings.initial_price_x
    steps: list[TatonnementStep] = []

    for iteration in range(settings.max_iterations + 1):
        prices = {"X": price_x, "Y": 1.0}
        bundles = [agent.optimal_bundle(prices) for agent in agents]
        demand_x = sum(bundle["X"] for bundle in bundles)
        demand_y = sum(bundle["Y"] for bundle in bundles)
        excess_demand_x = demand_x - total_x
        excess_demand_y = demand_y - total_y
        normalized_x = excess_demand_x / total_x
        normalized_y = excess_demand_y / total_y
        market_error = max(abs(normalized_x), abs(normalized_y))

        if market_error <= settings.tolerance:
            steps.append(
                TatonnementStep(
                    iteration=iteration,
                    price_x=price_x,
                    supply_x=total_x,
                    demand_x=demand_x,
                    excess_demand_x=excess_demand_x,
                    normalized_excess_demand_x=normalized_x,
                    supply_y=total_y,
                    demand_y=demand_y,
                    excess_demand_y=excess_demand_y,
                    normalized_excess_demand_y=normalized_y,
                    market_error=market_error,
                    next_price_x=None,
                )
            )
            return tuple(steps), prices

        next_price_x = price_x * (
            1.0 + settings.adjustment_speed * normalized_x
        )
        if next_price_x <= 0:
            raise AssertionError("tatonnement produced a non-positive price")

        steps.append(
            TatonnementStep(
                iteration=iteration,
                price_x=price_x,
                supply_x=total_x,
                demand_x=demand_x,
                excess_demand_x=excess_demand_x,
                normalized_excess_demand_x=normalized_x,
                supply_y=total_y,
                demand_y=demand_y,
                excess_demand_y=excess_demand_y,
                normalized_excess_demand_y=normalized_y,
                market_error=market_error,
                next_price_x=next_price_x,
            )
        )
        price_x = next_price_x

    raise RuntimeError("tatonnement did not converge within max_iterations")
