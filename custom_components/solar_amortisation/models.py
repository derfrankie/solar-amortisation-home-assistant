"""Data models for Solar Amortisation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass(frozen=True, slots=True)
class PricePeriod:
    """A price or tariff value that is valid from a specific date."""

    valid_from: date
    value: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PricePeriod:
        return cls(
            valid_from=date.fromisoformat(data["valid_from"]),
            value=float(data["value"]),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "valid_from": self.valid_from.isoformat(),
            "value": self.value,
        }


@dataclass(frozen=True, slots=True)
class SiteConfig:
    """Configuration for one amortisation site."""

    site_id: str
    name: str
    description: str
    investment_amount: float
    start_date: date
    grid_import_entity: str
    grid_export_entity: str
    pv_generation_entities: tuple[str, ...]
    electricity_prices: tuple[PricePeriod, ...]
    feed_in_tariffs: tuple[PricePeriod, ...]


@dataclass(frozen=True, slots=True)
class EnergyDeltas:
    """Daily energy deltas in kWh."""

    pv_generation_kwh: float
    grid_import_kwh: float
    grid_export_kwh: float


@dataclass(frozen=True, slots=True)
class MeterSnapshot:
    """Stored absolute meter values used to calculate the next daily delta."""

    site_id: str
    snapshot_date: date
    pv_generation_kwh: float
    grid_import_kwh: float
    grid_export_kwh: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MeterSnapshot:
        return cls(
            site_id=data["site_id"],
            snapshot_date=date.fromisoformat(data["snapshot_date"]),
            pv_generation_kwh=float(data["pv_generation_kwh"]),
            grid_import_kwh=float(data["grid_import_kwh"]),
            grid_export_kwh=float(data["grid_export_kwh"]),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "site_id": self.site_id,
            "snapshot_date": self.snapshot_date.isoformat(),
            "pv_generation_kwh": self.pv_generation_kwh,
            "grid_import_kwh": self.grid_import_kwh,
            "grid_export_kwh": self.grid_export_kwh,
        }


@dataclass(frozen=True, slots=True)
class DailyRecord:
    """Stored accounting record for one site and one day."""

    site_id: str
    record_date: date
    pv_generation_kwh: float
    grid_import_kwh: float
    grid_export_kwh: float
    self_consumed_pv_kwh: float
    electricity_price_eur_kwh: float
    feed_in_tariff_eur_kwh: float
    daily_savings_eur: float
    daily_revenue_eur: float
    daily_return_eur: float
    cumulative_return_eur: float
    remaining_amount_eur: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DailyRecord:
        return cls(
            site_id=data["site_id"],
            record_date=date.fromisoformat(data["record_date"]),
            pv_generation_kwh=float(data["pv_generation_kwh"]),
            grid_import_kwh=float(data["grid_import_kwh"]),
            grid_export_kwh=float(data["grid_export_kwh"]),
            self_consumed_pv_kwh=float(data["self_consumed_pv_kwh"]),
            electricity_price_eur_kwh=float(data["electricity_price_eur_kwh"]),
            feed_in_tariff_eur_kwh=float(data["feed_in_tariff_eur_kwh"]),
            daily_savings_eur=float(data["daily_savings_eur"]),
            daily_revenue_eur=float(data["daily_revenue_eur"]),
            daily_return_eur=float(data["daily_return_eur"]),
            cumulative_return_eur=float(data["cumulative_return_eur"]),
            remaining_amount_eur=float(data["remaining_amount_eur"]),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "site_id": self.site_id,
            "record_date": self.record_date.isoformat(),
            "pv_generation_kwh": self.pv_generation_kwh,
            "grid_import_kwh": self.grid_import_kwh,
            "grid_export_kwh": self.grid_export_kwh,
            "self_consumed_pv_kwh": self.self_consumed_pv_kwh,
            "electricity_price_eur_kwh": self.electricity_price_eur_kwh,
            "feed_in_tariff_eur_kwh": self.feed_in_tariff_eur_kwh,
            "daily_savings_eur": self.daily_savings_eur,
            "daily_revenue_eur": self.daily_revenue_eur,
            "daily_return_eur": self.daily_return_eur,
            "cumulative_return_eur": self.cumulative_return_eur,
            "remaining_amount_eur": self.remaining_amount_eur,
        }


@dataclass(frozen=True, slots=True)
class Forecasts:
    """Forecasted remaining amortisation days."""

    days_30: int | None
    days_365: int | None
    days_since_start: int | None
    recommended: str | None
