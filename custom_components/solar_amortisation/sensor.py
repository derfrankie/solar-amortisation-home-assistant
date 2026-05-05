"""Sensors for Solar Amortisation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SiteStatus, SolarAmortisationCoordinator


@dataclass(frozen=True, kw_only=True)
class SolarSensorEntityDescription(SensorEntityDescription):
    """Description for Solar Amortisation sensors."""

    fallback_name: str
    value_fn: Callable[[SiteStatus], float | int | str | None]
    extra_attrs_fn: Callable[[SiteStatus], dict[str, Any]] | None = None


EUR = "EUR"
EUR_PER_KWH = "EUR/kWh"


def _latest(status: SiteStatus, attr: str) -> float | None:
    if status.latest_record is None:
        return None
    return getattr(status.latest_record, attr)


def _forecast_attrs(status: SiteStatus) -> dict[str, Any]:
    return {"recommended_forecast": status.forecasts.recommended}


def _progress(status: SiteStatus) -> float | None:
    record = status.latest_record
    if record is None:
        return None
    investment = record.cumulative_return_eur + record.remaining_amount_eur
    if investment <= 0:
        return None
    return min(max(record.cumulative_return_eur / investment * 100, 0), 100)


SENSOR_DESCRIPTIONS: tuple[SolarSensorEntityDescription, ...] = (
    SolarSensorEntityDescription(
        key="daily_return",
        translation_key="daily_return",
        fallback_name="Daily return",
        native_unit_of_measurement=EUR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda status: _latest(status, "daily_return_eur"),
    ),
    SolarSensorEntityDescription(
        key="cumulative_return",
        translation_key="cumulative_return",
        fallback_name="Cumulative return",
        native_unit_of_measurement=EUR,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda status: _latest(status, "cumulative_return_eur"),
    ),
    SolarSensorEntityDescription(
        key="remaining_amount",
        translation_key="remaining_amount",
        fallback_name="Remaining amount",
        native_unit_of_measurement=EUR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda status: _latest(status, "remaining_amount_eur"),
    ),
    SolarSensorEntityDescription(
        key="days_since_start",
        translation_key="days_since_start",
        fallback_name="Days since start",
        native_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda status: status.days_since_start,
    ),
    SolarSensorEntityDescription(
        key="forecast_days_30",
        translation_key="forecast_days_30",
        fallback_name="Forecast days 30 days",
        native_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda status: status.forecasts.days_30,
        extra_attrs_fn=_forecast_attrs,
    ),
    SolarSensorEntityDescription(
        key="forecast_days_365",
        translation_key="forecast_days_365",
        fallback_name="Forecast days 365 days",
        native_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda status: status.forecasts.days_365,
        extra_attrs_fn=_forecast_attrs,
    ),
    SolarSensorEntityDescription(
        key="forecast_days_since_start",
        translation_key="forecast_days_since_start",
        fallback_name="Forecast days since start",
        native_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda status: status.forecasts.days_since_start,
        extra_attrs_fn=_forecast_attrs,
    ),
    SolarSensorEntityDescription(
        key="pv_generation_today",
        translation_key="pv_generation_today",
        fallback_name="PV generation today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda status: _latest(status, "pv_generation_kwh"),
    ),
    SolarSensorEntityDescription(
        key="self_consumed_pv_today",
        translation_key="self_consumed_pv_today",
        fallback_name="Self-consumed PV today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda status: _latest(status, "self_consumed_pv_kwh"),
    ),
    SolarSensorEntityDescription(
        key="grid_import_today",
        translation_key="grid_import_today",
        fallback_name="Grid import today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda status: _latest(status, "grid_import_kwh"),
    ),
    SolarSensorEntityDescription(
        key="grid_export_today",
        translation_key="grid_export_today",
        fallback_name="Grid export today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda status: _latest(status, "grid_export_kwh"),
    ),
    SolarSensorEntityDescription(
        key="electricity_price_today",
        translation_key="electricity_price_today",
        fallback_name="Electricity price today",
        native_unit_of_measurement=EUR_PER_KWH,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=4,
        value_fn=lambda status: _latest(status, "electricity_price_eur_kwh"),
    ),
    SolarSensorEntityDescription(
        key="feed_in_tariff_today",
        translation_key="feed_in_tariff_today",
        fallback_name="Feed-in tariff today",
        native_unit_of_measurement=EUR_PER_KWH,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=4,
        value_fn=lambda status: _latest(status, "feed_in_tariff_eur_kwh"),
    ),
    SolarSensorEntityDescription(
        key="amortisation_progress",
        translation_key="amortisation_progress",
        fallback_name="Amortisation progress",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=_progress,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Solar Amortisation sensors."""

    coordinator: SolarAmortisationCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SolarAmortisationSensor(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    )


class SolarAmortisationSensor(
    CoordinatorEntity[SolarAmortisationCoordinator],
    SensorEntity,
):
    """A Solar Amortisation sensor."""

    entity_description: SolarSensorEntityDescription

    def __init__(
        self,
        coordinator: SolarAmortisationCoordinator,
        description: SolarSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_has_entity_name = True
        self._attr_name = description.fallback_name
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.entry.entry_id)},
            "name": coordinator.site_config.name,
            "manufacturer": "Solar Amortisation",
        }

    @property
    def native_value(self) -> float | int | str | None:
        """Return the sensor value."""

        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra attributes."""

        if self.coordinator.data is None:
            return None

        attrs = {
            "site_name": self.coordinator.site_config.name,
            "last_record_date": (
                self.coordinator.data.latest_record.record_date.isoformat()
                if self.coordinator.data.latest_record
                else None
            ),
            "recommended_forecast": self.coordinator.data.forecasts.recommended,
            "setup_issue": self.coordinator.data.setup_issue,
            "unavailable_entities": self.coordinator.data.unavailable_entities,
            "backfill_status": self.coordinator.data.backfill_status.as_dict(),
        }
        if self.entity_description.extra_attrs_fn is not None:
            attrs.update(self.entity_description.extra_attrs_fn(self.coordinator.data))
        return attrs
