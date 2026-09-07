from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from econ_agent_sim.numerics import require_finite


@dataclass(frozen=True)
class CobbDouglasPreferences:
    """Two-good Cobb-Douglas preferences: U(x, y) = x^alpha y^(1-alpha)."""

    alpha: float

    def __post_init__(self) -> None:
        if not 0.0 < self.alpha < 1.0:
            raise ValueError("alpha must lie strictly between 0 and 1")

    def demand(self, wealth: float, prices: Mapping[str, float]) -> dict[str, float]:
        px = prices["X"]
        py = prices["Y"]
        require_finite("prices and wealth", px, py, wealth)
        if px <= 0 or py <= 0:
            raise ValueError("prices must be strictly positive")
        if wealth < 0:
            raise ValueError("wealth cannot be negative")
        bundle = {
            "X": self.alpha * wealth / px,
            "Y": (1.0 - self.alpha) * wealth / py,
        }
        require_finite("demand", *bundle.values())
        return bundle


@dataclass
class Agent:
    name: str
    preferences: CobbDouglasPreferences
    holdings: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for good in ("X", "Y"):
            self.holdings.setdefault(good, 0.0)
        require_finite("holdings", *self.holdings.values())
        if any(quantity < 0 for quantity in self.holdings.values()):
            raise ValueError("holdings cannot be negative")

    def snapshot(self) -> Mapping[str, float]:
        return MappingProxyType(dict(self.holdings))

    def wealth(self, prices: Mapping[str, float]) -> float:
        return sum(prices[good] * quantity for good, quantity in self.holdings.items())

    def optimal_bundle(self, prices: Mapping[str, float]) -> dict[str, float]:
        return self.preferences.demand(self.wealth(prices), prices)
