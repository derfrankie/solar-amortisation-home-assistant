"""Helpers for discovering configuration from the Home Assistant Energy dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class EnergyDashboardConfig:
    """Resolved Energy dashboard sources relevant to amortisation."""

    grid_import_entity: str | None
    grid_export_entity: str | None
    pv_generation_entities: tuple[str, ...]
    battery_discharge_entities: tuple[str, ...]
    battery_charge_entities: tuple[str, ...]
    electricity_price: float | None
    feed_in_tariff: float | None


async def async_get_energy_dashboard_config(hass) -> EnergyDashboardConfig:
    """Read current Energy dashboard preferences through Home Assistant internals."""

    from homeassistant.components.energy.data import async_get_manager

    manager = await async_get_manager(hass)
    return energy_dashboard_config_from_prefs(manager.data or {})


def energy_dashboard_config_from_prefs(
    prefs: dict[str, Any],
) -> EnergyDashboardConfig:
    """Extract amortisation-relevant entities from Energy dashboard prefs."""

    grid_imports: list[str] = []
    grid_exports: list[str] = []
    solar_entities: list[str] = []
    battery_discharges: list[str] = []
    battery_charges: list[str] = []
    electricity_prices: list[float] = []
    feed_in_tariffs: list[float] = []

    for source in prefs.get("energy_sources", []):
        source_type = source.get("type")
        if source_type == "grid":
            _append_if_set(grid_imports, source.get("stat_energy_from"))
            _append_if_set(grid_exports, source.get("stat_energy_to"))
            _append_float_if_set(electricity_prices, source.get("number_energy_price"))
            _append_float_if_set(
                feed_in_tariffs,
                source.get("number_energy_price_export"),
            )
        elif source_type == "solar":
            _append_if_set(solar_entities, source.get("stat_energy_from"))
        elif source_type == "battery":
            _append_if_set(battery_discharges, source.get("stat_energy_from"))
            _append_if_set(battery_charges, source.get("stat_energy_to"))

    return EnergyDashboardConfig(
        grid_import_entity=_single_or_raise(grid_imports, "grid import"),
        grid_export_entity=_single_or_raise(grid_exports, "grid export"),
        pv_generation_entities=tuple(dict.fromkeys(solar_entities)),
        battery_discharge_entities=tuple(dict.fromkeys(battery_discharges)),
        battery_charge_entities=tuple(dict.fromkeys(battery_charges)),
        electricity_price=_single_float_or_raise(electricity_prices, "electricity price"),
        feed_in_tariff=_single_float_or_raise(feed_in_tariffs, "feed-in tariff"),
    )


def _append_if_set(values: list[str], value: Any) -> None:
    if isinstance(value, str) and value.strip():
        values.append(value.strip())


def _append_float_if_set(values: list[float], value: Any) -> None:
    if value is None or value == "":
        return
    values.append(float(value))


def _single_or_raise(values: list[str], label: str) -> str | None:
    unique = tuple(dict.fromkeys(values))
    if not unique:
        return None
    if len(unique) > 1:
        msg = f"Energy dashboard contains multiple {label} entities"
        raise ValueError(msg)
    return unique[0]


def _single_float_or_raise(values: list[float], label: str) -> float | None:
    unique = tuple(dict.fromkeys(values))
    if not unique:
        return None
    if len(unique) > 1:
        msg = f"Energy dashboard contains multiple {label} values"
        raise ValueError(msg)
    return unique[0]
