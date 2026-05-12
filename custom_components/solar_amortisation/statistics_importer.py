"""Import Solar Amortisation daily records into HA long-term statistics."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, time, tzinfo
from typing import TYPE_CHECKING, Any

from .models import DailyRecord

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


@dataclass(frozen=True, slots=True)
class StatisticSensorDefinition:
    """One sensor statistic generated from a daily record value."""

    key: str
    unit: str
    unit_class: str | None
    value_fn: Callable[[DailyRecord], float]


EUR = "EUR"
EUR_PER_KWH = "EUR/kWh"
KWH = "kWh"
PERCENTAGE = "%"


def _progress_for_record(record: DailyRecord) -> float:
    investment = record.cumulative_return_eur + record.remaining_amount_eur
    if investment <= 0:
        return 0
    return min(max(record.cumulative_return_eur / investment * 100, 0), 100)


def _total_consumption_for_record(record: DailyRecord) -> float:
    return round(record.grid_import_kwh + record.self_consumed_pv_kwh, 6)


STATISTIC_SENSOR_DEFINITIONS: tuple[StatisticSensorDefinition, ...] = (
    StatisticSensorDefinition(
        key="daily_return_yesterday",
        unit=EUR,
        unit_class=None,
        value_fn=lambda record: record.daily_return_eur,
    ),
    StatisticSensorDefinition(
        key="cumulative_return",
        unit=EUR,
        unit_class=None,
        value_fn=lambda record: record.cumulative_return_eur,
    ),
    StatisticSensorDefinition(
        key="remaining_amount",
        unit=EUR,
        unit_class=None,
        value_fn=lambda record: record.remaining_amount_eur,
    ),
    StatisticSensorDefinition(
        key="pv_generation_yesterday",
        unit=KWH,
        unit_class="energy",
        value_fn=lambda record: record.pv_generation_kwh,
    ),
    StatisticSensorDefinition(
        key="self_consumed_pv_yesterday",
        unit=KWH,
        unit_class="energy",
        value_fn=lambda record: record.self_consumed_pv_kwh,
    ),
    StatisticSensorDefinition(
        key="total_consumption_yesterday",
        unit=KWH,
        unit_class="energy",
        value_fn=_total_consumption_for_record,
    ),
    StatisticSensorDefinition(
        key="grid_import_yesterday",
        unit=KWH,
        unit_class="energy",
        value_fn=lambda record: record.grid_import_kwh,
    ),
    StatisticSensorDefinition(
        key="grid_export_yesterday",
        unit=KWH,
        unit_class="energy",
        value_fn=lambda record: record.grid_export_kwh,
    ),
    StatisticSensorDefinition(
        key="battery_discharge_yesterday",
        unit=KWH,
        unit_class="energy",
        value_fn=lambda record: record.battery_discharge_kwh,
    ),
    StatisticSensorDefinition(
        key="battery_charge_yesterday",
        unit=KWH,
        unit_class="energy",
        value_fn=lambda record: record.battery_charge_kwh,
    ),
    StatisticSensorDefinition(
        key="daily_savings_yesterday",
        unit=EUR,
        unit_class=None,
        value_fn=lambda record: record.daily_savings_eur,
    ),
    StatisticSensorDefinition(
        key="daily_revenue_yesterday",
        unit=EUR,
        unit_class=None,
        value_fn=lambda record: record.daily_revenue_eur,
    ),
    StatisticSensorDefinition(
        key="electricity_price_yesterday",
        unit=EUR_PER_KWH,
        unit_class=None,
        value_fn=lambda record: record.electricity_price_eur_kwh,
    ),
    StatisticSensorDefinition(
        key="feed_in_tariff_yesterday",
        unit=EUR_PER_KWH,
        unit_class=None,
        value_fn=lambda record: record.feed_in_tariff_eur_kwh,
    ),
    StatisticSensorDefinition(
        key="amortisation_progress",
        unit=PERCENTAGE,
        unit_class=None,
        value_fn=_progress_for_record,
    ),
)


async def async_import_daily_record_statistics(
    hass: HomeAssistant,
    *,
    records: Iterable[DailyRecord],
    statistic_ids: Mapping[str, str],
) -> None:
    """Import stored daily records as HA long-term statistics."""

    records_list = list(records)
    if not records_list:
        return

    from homeassistant.components.recorder.const import DOMAIN as RECORDER_DOMAIN
    from homeassistant.components.recorder.models import StatisticMeanType
    from homeassistant.components.recorder.statistics import async_import_statistics
    from homeassistant.util import dt as dt_util

    local_timezone = dt_util.DEFAULT_TIME_ZONE
    for definition in STATISTIC_SENSOR_DEFINITIONS:
        statistic_id = statistic_ids.get(definition.key)
        if statistic_id is None:
            continue

        metadata = {
            "has_mean": True,
            "has_sum": False,
            "mean_type": StatisticMeanType.ARITHMETIC,
            "name": None,
            "source": RECORDER_DOMAIN,
            "statistic_id": statistic_id,
            "unit_class": definition.unit_class,
            "unit_of_measurement": definition.unit,
        }
        async_import_statistics(
            hass,
            metadata,
            build_measurement_statistics(
                records=records_list,
                local_timezone=local_timezone,
                value_fn=definition.value_fn,
            ),
        )


def build_measurement_statistics(
    *,
    records: Iterable[DailyRecord],
    local_timezone: tzinfo,
    value_fn: Callable[[DailyRecord], float],
) -> list[dict[str, Any]]:
    """Build hourly measurement statistics rows from daily records."""

    rows: list[dict[str, Any]] = []
    for record in sorted(records, key=lambda item: item.record_date):
        value = value_fn(record)
        rows.append(
            {
                "start": datetime.combine(
                    record.record_date,
                    time.min,
                    tzinfo=local_timezone,
                ),
                "mean": value,
                "min": value,
                "max": value,
            },
        )
    return rows
