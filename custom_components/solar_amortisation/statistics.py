"""Historical statistics helpers for Solar Amortisation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC, date, datetime, time, timedelta, tzinfo
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

from .models import EnergyDeltas

StatisticRows = Mapping[str, list[dict[str, Any]]]
STATISTIC_UNITS = {"energy": "kWh"}


class HistoricalStatisticsReader:
    """Read historical daily energy deltas from Home Assistant recorder statistics."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass

    async def async_get_daily_deltas(
        self,
        *,
        start_date: date,
        end_date: date,
        pv_generation_entities: Iterable[str],
        grid_import_entity: str,
        grid_export_entity: str,
    ) -> dict[date, EnergyDeltas]:
        """Return historical daily deltas for the configured site entities."""

        statistic_ids = [
            *pv_generation_entities,
            grid_import_entity,
            grid_export_entity,
        ]
        local_timezone = self._local_timezone()
        rows = await self._async_fetch_statistics(
            start_date=start_date,
            end_date=end_date,
            statistic_ids=statistic_ids,
        )
        return build_daily_deltas_from_statistics(
            rows=rows,
            start_date=start_date,
            end_date=end_date,
            pv_generation_entities=tuple(pv_generation_entities),
            grid_import_entity=grid_import_entity,
            grid_export_entity=grid_export_entity,
            local_timezone=local_timezone,
        )

    async def async_get_daily_delta_result(
        self,
        *,
        start_date: date,
        end_date: date,
        pv_generation_entities: Iterable[str],
        grid_import_entity: str,
        grid_export_entity: str,
    ) -> tuple[dict[date, EnergyDeltas], dict[str, int]]:
        """Return historical daily deltas and row counts for diagnostics."""

        statistic_ids = [
            *pv_generation_entities,
            grid_import_entity,
            grid_export_entity,
        ]
        local_timezone = self._local_timezone()
        rows = await self._async_fetch_statistics(
            start_date=start_date,
            end_date=end_date,
            statistic_ids=statistic_ids,
        )
        return (
            build_daily_deltas_from_statistics(
                rows=rows,
                start_date=start_date,
                end_date=end_date,
                pv_generation_entities=tuple(pv_generation_entities),
                grid_import_entity=grid_import_entity,
                grid_export_entity=grid_export_entity,
                local_timezone=local_timezone,
            ),
            {
                statistic_id: len(rows.get(statistic_id, []))
                for statistic_id in statistic_ids
            },
        )

    def _local_timezone(self) -> tzinfo:
        """Return Home Assistant's configured local timezone."""

        from homeassistant.util import dt as dt_util

        return dt_util.DEFAULT_TIME_ZONE

    async def _async_fetch_statistics(
        self,
        *,
        start_date: date,
        end_date: date,
        statistic_ids: list[str],
    ) -> StatisticRows:
        """Fetch daily statistics through Home Assistant's recorder API."""

        from homeassistant.components import recorder
        from homeassistant.components.recorder import statistics

        start_time = _start_of_day(start_date - timedelta(days=1))
        end_time = _start_of_day(end_date + timedelta(days=1))

        def _fetch() -> StatisticRows:
            return statistics.statistics_during_period(
                self._hass,
                start_time,
                end_time,
                statistic_ids,
                "day",
                units=STATISTIC_UNITS,
                types={"change", "sum"},
            )

        return await recorder.get_instance(self._hass).async_add_executor_job(_fetch)


def build_daily_deltas_from_statistics(
    *,
    rows: StatisticRows,
    start_date: date,
    end_date: date,
    pv_generation_entities: tuple[str, ...],
    grid_import_entity: str,
    grid_export_entity: str,
    entity_units: Mapping[str, str | None] | None = None,
    local_timezone: tzinfo | None = None,
) -> dict[date, EnergyDeltas]:
    """Build daily site deltas from HA statistic rows."""

    units = entity_units or {}
    pv_by_day = _sum_entities_by_day(
        rows,
        pv_generation_entities,
        start_date,
        end_date,
        entity_units=units,
        local_timezone=local_timezone,
    )
    import_by_day = _entity_by_day(
        rows,
        grid_import_entity,
        start_date,
        end_date,
        unit=units.get(grid_import_entity),
        local_timezone=local_timezone,
    )
    export_by_day = _entity_by_day(
        rows,
        grid_export_entity,
        start_date,
        end_date,
        unit=units.get(grid_export_entity),
        local_timezone=local_timezone,
    )

    deltas: dict[date, EnergyDeltas] = {}
    current_date = start_date
    while current_date <= end_date:
        if current_date in import_by_day and current_date in export_by_day:
            deltas[current_date] = EnergyDeltas(
                pv_generation_kwh=pv_by_day.get(current_date, 0),
                grid_import_kwh=import_by_day[current_date],
                grid_export_kwh=export_by_day[current_date],
            )
        current_date += timedelta(days=1)
    return deltas


def _sum_entities_by_day(
    rows: StatisticRows,
    entity_ids: Iterable[str],
    start_date: date,
    end_date: date,
    *,
    entity_units: Mapping[str, str | None],
    local_timezone: tzinfo | None,
) -> dict[date, float]:
    totals: dict[date, float] = {}
    for entity_id in entity_ids:
        for day, value in _entity_by_day(
            rows,
            entity_id,
            start_date,
            end_date,
            unit=entity_units.get(entity_id),
            local_timezone=local_timezone,
            allow_missing_baseline=True,
        ).items():
            totals[day] = totals.get(day, 0) + value
    return totals


def _entity_by_day(
    rows: StatisticRows,
    entity_id: str,
    start_date: date,
    end_date: date,
    *,
    unit: str | None = None,
    local_timezone: tzinfo | None = None,
    allow_missing_baseline: bool = False,
) -> dict[date, float]:
    values: dict[date, float] = {}
    previous_sum: float | None = None

    for row in sorted(rows.get(entity_id, []), key=_row_start):
        row_date = _row_date(row, local_timezone)
        if row_date < start_date - timedelta(days=1):
            continue

        row_sum = _as_float(row.get("sum"))
        row_change = _as_float(row.get("change"))

        if row_date <= start_date - timedelta(days=1):
            previous_sum = row_sum
            continue
        if row_date > end_date:
            break

        if row_change is not None:
            values[row_date] = _to_kwh(max(row_change, 0), unit)
        elif row_sum is not None and previous_sum is not None:
            values[row_date] = _to_kwh(max(row_sum - previous_sum, 0), unit)
        elif row_sum is not None and allow_missing_baseline:
            values[row_date] = _to_kwh(max(row_sum, 0), unit)

        if row_sum is not None:
            previous_sum = row_sum

    return values


def _row_start(row: dict[str, Any]) -> datetime:
    start = row.get("start")
    if isinstance(start, datetime):
        return start
    if isinstance(start, str):
        try:
            return datetime.fromisoformat(start.replace("Z", "+00:00"))
        except ValueError:
            return datetime.min
    if isinstance(start, int | float):
        seconds = start / 1000 if start > 10_000_000_000 else start
        return datetime.fromtimestamp(seconds, UTC)
    return datetime.min


def _row_date(row: dict[str, Any], local_timezone: tzinfo | None) -> date:
    start = _row_start(row)
    if start.tzinfo is None or local_timezone is None:
        return start.date()
    return start.astimezone(local_timezone).date()


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_kwh(value: float, unit: str | None) -> float:
    normalized = (unit or "").strip().lower()
    if normalized == "wh":
        return value / 1000
    if normalized == "mwh":
        return value * 1000
    return value


def _start_of_day(day: date) -> datetime:
    from homeassistant.util import dt as dt_util

    local = datetime.combine(day, time.min)
    return dt_util.as_utc(dt_util.as_local(local))
