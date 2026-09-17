"""Immutable settings and economic records for Tiny Economy."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, fields
from math import fsum
from types import MappingProxyType

from econ_agent_sim.numerics import require_finite

MONEY = "Money"
GOOD = "X"
CAPITAL = "Capital"
LABOR = "Labor"
TOLERANCE = 1e-9


def _freeze(value):
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


class _FrozenMappings:
    def __post_init__(self) -> None:
        for field in fields(self):
            object.__setattr__(self, field.name, _freeze(getattr(self, field.name)))


@dataclass(frozen=True)
class Household:
    id: str
    name: str
    money: float = 1.0
    consumption_priority: float = 1.0
    money_priority: float = 1.0
    leisure_priority: float = 1.0
    consumption_target: float = 0.5

    def __post_init__(self) -> None:
        require_finite("Household settings", self.money, *self.scores.values())
        require_finite("Consumption target", self.consumption_target)
        if self.consumption_target < 0:
            raise ValueError("The consumption target must be non-negative.")
        if not self.id.strip() or not self.name.strip():
            raise ValueError("Use a household ID and name.")
        if self.money < 0 or min(self.scores.values()) <= 0:
            raise ValueError(
                "Household money must be non-negative and priorities positive."
            )
        if (
            min(self.weights.values()) <= 0
            or max(self.weights.values()) >= 1
            or not 0 < self.alpha < 1
        ):
            raise ValueError("The relative priorities exceed numerical precision.")

    @property
    def scores(self) -> dict[str, float]:
        return {
            "consumption": self.consumption_priority,
            "money": self.money_priority,
            "leisure": self.leisure_priority,
        }

    @property
    def weights(self) -> dict[str, float]:
        scale = max(self.scores.values())
        normalized = {key: value / scale for key, value in self.scores.items()}
        total = fsum(normalized.values())
        return {key: value / total for key, value in normalized.items()}

    @property
    def alpha(self) -> float:
        scale = max(self.consumption_priority, self.money_priority)
        consumption = self.consumption_priority / scale
        return consumption / (consumption + self.money_priority / scale)


@dataclass(frozen=True)
class Firm:
    id: str
    name: str
    money: float = 0.5
    productivity: float = 2.0
    theta: float = 0.5
    capital: float = 0.5
    reinvestment_rate: float = 0.4
    depreciation_rate: float = 0.1

    def __post_init__(self) -> None:
        require_finite(
            "Firm settings",
            self.money,
            self.productivity,
            self.theta,
            self.capital,
            self.reinvestment_rate,
            self.depreciation_rate,
        )
        if not self.id.strip() or not self.name.strip():
            raise ValueError("Use a firm ID and name.")
        if min(self.money, self.productivity, self.capital) <= 0:
            raise ValueError("Firm money, productivity and capital must be positive.")
        if self.theta != 0.5:
            raise ValueError("The current model uses a fixed labor exponent of 0.5.")
        if not 0 <= self.reinvestment_rate < 1 or not 0 <= self.depreciation_rate < 1:
            raise ValueError(
                "Reinvestment and capital wear must lie from zero to below 100%."
            )


def default_households(count: int = 2) -> list[dict]:
    if type(count) is not int or count < 1:
        raise ValueError("Use at least one household.")
    return [
        asdict(Household(f"household_{i + 1}", f"Household {i + 1}"))
        for i in range(count)
    ]


def default_firms() -> list[dict]:
    return [asdict(Firm("firm_a", "Firm A")), asdict(Firm("firm_b", "Firm B"))]


@dataclass(frozen=True)
class Transfer:
    transaction_id: int
    pair_id: int
    period: int
    kind: str
    asset: str
    quantity: float
    sender: str
    receiver: str
    sender_id: str
    receiver_id: str
    unit: str
    valuation_price: float


@dataclass(frozen=True)
class Event:
    event_id: int
    period: int
    kind: str
    entity: str
    entity_id: str
    asset: str
    quantity: float
    unit: str
    valuation_price: float
    value: float
    opening_valuation_price: float | None = None


@dataclass(frozen=True)
class HouseholdFirmAllocation:
    household_id: str
    firm_id: str
    ownership_share: float
    dividends: float
    wages: float
    work: float
    purchases: float
    consumption: float
    ownership_value_open: float
    ownership_value_close: float


@dataclass(frozen=True)
class FirmAccount:
    id: str
    name: str
    work: float
    output: float
    sales_quantity: float
    sales_share: float
    production_share: float
    wage_bill: float
    sales_received: float
    production_value: float
    gross_operating_surplus: float
    net_operating_profit: float
    investment_quantity: float
    investment_value: float
    depreciation_quantity: float
    depreciation_value: float
    capital_open: float
    capital_close: float
    capital_price_open: float
    capital_price_close: float
    capital_value_open: float
    capital_value_close: float
    holding_gain: float
    equity_open: float
    equity_close: float
    retained_earnings_open: float
    retained_earnings_close: float
    revaluation_reserve_open: float
    revaluation_reserve_close: float
    contributed_equity: float
    dividends_paid: float
    operating_cash: float
    next_dividend_budget: float
    opening_cash: float
    closing_cash: float
    funding_binding: bool
    marginal_revenue_product: float
    minimum_cash: float


@dataclass(frozen=True)
class EconomyPeriod(_FrozenMappings):
    number: int
    households: tuple[Household, ...]
    firms: tuple[Firm, ...]
    ownership: Mapping[str, Mapping[str, float]]
    opening_cash: Mapping[str, float]
    post_dividend_cash: Mapping[str, float]
    closing_cash: Mapping[str, float]
    price: float
    wage: float
    work: Mapping[str, float]
    leisure: Mapping[str, float]
    wages: Mapping[str, float]
    dividends: Mapping[str, float]
    consumption: Mapping[str, float]
    purchases: Mapping[str, float]
    firm_accounts: Mapping[str, FirmAccount]
    allocations: tuple[HouseholdFirmAllocation, ...]
    transfers: tuple[Transfer, ...]
    events: tuple[Event, ...]
    checks: Mapping[str, bool]
    solution: Mapping

    @property
    def prices(self) -> dict[str, float]:
        return {GOOD: self.price, MONEY: 1.0, LABOR: self.wage}

    @property
    def produced(self) -> dict[str, float]:
        return {key: account.output for key, account in self.firm_accounts.items()}

    @property
    def consumed(self) -> Mapping[str, float]:
        return self.consumption

    def _sum(self, name: str) -> float:
        return fsum(getattr(account, name) for account in self.firm_accounts.values())


# Aggregate flows sum the immutable accounts. Firm identity remains explicit
# in the plural account mapping.
for _field in (
    "output",
    "wage_bill",
    "sales_received",
    "production_value",
    "gross_operating_surplus",
    "net_operating_profit",
    "investment_quantity",
    "investment_value",
    "depreciation_quantity",
    "depreciation_value",
    "capital_open",
    "capital_close",
    "capital_value_open",
    "capital_value_close",
    "holding_gain",
    "equity_open",
    "equity_close",
    "retained_earnings_open",
    "retained_earnings_close",
    "revaluation_reserve_open",
    "revaluation_reserve_close",
    "contributed_equity",
    "dividends_paid",
    "operating_cash",
    "next_dividend_budget",
):
    setattr(EconomyPeriod, _field, property(lambda self, name=_field: self._sum(name)))


# Short alias for internal report and persistence type contracts.
Period = EconomyPeriod
