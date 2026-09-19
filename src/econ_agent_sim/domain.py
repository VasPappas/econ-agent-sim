"""The one current model's validated, immutable application settings."""

from dataclasses import asdict, dataclass, fields
from math import isfinite

from .monetary_growth import Parameters

MODEL_ID = "tiny-economy-monetary-1"
ENGINE_VERSION = "tiny-economy-4.0.0"
MAX_PERIODS = 100

# Application limits keep interactive solves bounded. They do not assert that
# every point in this box has an equilibrium in the supported funding regime.
SETTING_BOUNDS = {
    "beta": (.5, .99),
    "depreciation": (.01, 1.),
    "leisure_weight": (.05, 10.),
    "money_weight": (.001, 5.),
    "initial_capital": (.01, 1000.),
    "initial_firm_cash_share": (.01, .99),
}


@dataclass(frozen=True)
class Settings:
    beta: float = .95
    depreciation: float = .1
    leisure_weight: float = 1.
    money_weight: float = .05
    initial_capital: float = 1.
    initial_firm_cash_share: float = .5

    def __post_init__(self):
        for name, (low, high) in SETTING_BOUNDS.items():
            value = getattr(self, name)
            if (type(value) not in (int, float) or not isfinite(value)
                    or not low <= value <= high):
                raise ValueError(f"{name.replace('_', ' ')} must be between {low:g} and {high:g}.")
            object.__setattr__(self, name, float(value))

    def to_parameters(self):
        return Parameters(self.beta, self.depreciation, self.leisure_weight, self.money_weight)

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, value):
        if type(value) is not dict or set(value) != {f.name for f in fields(cls)}:
            raise ValueError("The experiment must contain exactly the six current model settings.")
        return cls(**value)
