"""Data coordinator for Solar Amortisation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .calculations import (
    calculate_backfill_records,
    calculate_daily_record,
    calculate_days_since_start,
    calculate_energy_deltas,
    calculate_forecasts,
)
from .const import (
    CONF_DESCRIPTION,
    CONF_ELECTRICITY_PRICE,
    CONF_FEED_IN_TARIFF,
    CONF_GRID_EXPORT_ENTITY,
    CONF_GRID_IMPORT_ENTITY,
    CONF_INVESTMENT_AMOUNT,
    CONF_PV_GENERATION_ENTITIES,
    CONF_SITE_NAME,
    CONF_START_DATE,
    DEFAULT_SCAN_HOUR,
    DEFAULT_SCAN_MINUTE,
    DOMAIN,
)
from .models import DailyRecord, Forecasts, MeterSnapshot, SiteConfig
from .statistics import HistoricalStatisticsReader
from .storage import DailyRecordStore

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class BackfillStatus:
    """Diagnostic information about the latest historical backfill attempt."""

    attempted: bool = False
    start_date: date | None = None
    end_date: date | None = None
    existing_records: int = 0
    statistic_rows: dict[str, int] | None = None
    daily_deltas: int = 0
    records_created: int = 0
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""

        return {
            "attempted": self.attempted,
            "start_date": (
                self.start_date.isoformat() if self.start_date is not None else None
            ),
            "end_date": (
                self.end_date.isoformat() if self.end_date is not None else None
            ),
            "existing_records": self.existing_records,
            "statistic_rows": self.statistic_rows or {},
            "daily_deltas": self.daily_deltas,
            "records_created": self.records_created,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class SiteStatus:
    """Current published state for a site."""

    latest_record: DailyRecord | None
    current_snapshot: MeterSnapshot | None
    days_since_start: int
    forecasts: Forecasts
    setup_issue: str | None = None
    unavailable_entities: tuple[str, ...] = ()
    backfill_status: BackfillStatus = BackfillStatus()


class SolarAmortisationCoordinator(DataUpdateCoordinator[SiteStatus]):
    """Coordinate daily rollup and sensor state for one site."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        store: DailyRecordStore,
    ) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            config_entry=entry,
            always_update=False,
        )
        self.entry = entry
        self.store = store
        self._backfill_status = BackfillStatus()

        unsub = async_track_time_change(
            hass,
            self._handle_daily_tick,
            hour=DEFAULT_SCAN_HOUR,
            minute=DEFAULT_SCAN_MINUTE,
            second=0,
        )
        entry.async_on_unload(unsub)

    @property
    def site_config(self) -> SiteConfig:
        """Return merged site configuration."""

        data = {**self.entry.data, **self.entry.options}
        return SiteConfig(
            site_id=self.entry.entry_id,
            name=data[CONF_SITE_NAME],
            description=data.get(CONF_DESCRIPTION, ""),
            investment_amount=_parse_decimal(data[CONF_INVESTMENT_AMOUNT]),
            start_date=date.fromisoformat(data[CONF_START_DATE]),
            grid_import_entity=data[CONF_GRID_IMPORT_ENTITY],
            grid_export_entity=data[CONF_GRID_EXPORT_ENTITY],
            pv_generation_entities=tuple(
                _normalize_entities(data[CONF_PV_GENERATION_ENTITIES])
            ),
            electricity_prices=(),
            feed_in_tariffs=(),
        )

    async def _async_update_data(self) -> SiteStatus:
        """Refresh current state and perform a rollup when a new day starts."""

        config = self.site_config
        current_date = dt_util.now().date()
        current_snapshot, unavailable_entities = self._read_current_snapshot(
            config,
            current_date,
        )
        previous_snapshot = self.store.snapshot_for_site(config.site_id)

        await self._async_backfill_if_needed(config, current_date)

        setup_issue = None
        if current_snapshot is None:
            setup_issue = "One or more configured energy entities are not available"
            _LOGGER.debug(
                "Solar amortisation snapshot unavailable for %s: %s",
                config.name,
                ", ".join(unavailable_entities),
            )
        elif previous_snapshot is None:
            await self.store.async_set_snapshot(current_snapshot)
        elif previous_snapshot.snapshot_date < current_date:
            await self._async_rollup(config, previous_snapshot, current_snapshot)

        records = self.store.records_for_site(config.site_id)
        latest_record = records[-1] if records else None
        remaining = (
            latest_record.remaining_amount_eur
            if latest_record is not None
            else config.investment_amount
        )

        return SiteStatus(
            latest_record=latest_record,
            current_snapshot=current_snapshot,
            days_since_start=calculate_days_since_start(
                config.start_date,
                current_date,
            ),
            forecasts=calculate_forecasts(
                records=records,
                remaining_amount_eur=remaining,
            ),
            setup_issue=setup_issue,
            unavailable_entities=tuple(unavailable_entities),
            backfill_status=self._backfill_status,
        )

    async def _async_rollup(
        self,
        config: SiteConfig,
        previous_snapshot: MeterSnapshot,
        current_snapshot: MeterSnapshot,
    ) -> None:
        """Store one daily accounting record from two meter snapshots."""

        record_date = current_snapshot.snapshot_date - timedelta(days=1)
        if self.store.has_record(config.site_id, record_date):
            await self.store.async_set_snapshot(current_snapshot)
            return

        deltas = calculate_energy_deltas(
            previous=previous_snapshot,
            current=current_snapshot,
        )
        previous_records = self.store.records_for_site(config.site_id)
        data = {**self.entry.data, **self.entry.options}
        record = calculate_daily_record(
            site_id=config.site_id,
            record_date=record_date,
            investment_amount=config.investment_amount,
            deltas=deltas,
            electricity_price_eur_kwh=_parse_decimal(data[CONF_ELECTRICITY_PRICE]),
            feed_in_tariff_eur_kwh=_parse_decimal(data.get(CONF_FEED_IN_TARIFF, 0)),
            previous_records=previous_records,
        )
        await self.store.async_upsert(record)
        await self.store.async_set_snapshot(current_snapshot)

    async def _async_backfill_if_needed(
        self,
        config: SiteConfig,
        current_date: date,
    ) -> None:
        """Backfill historical daily records from HA recorder statistics."""

        records = self.store.records_for_site(config.site_id)
        if records:
            self._backfill_status = BackfillStatus(
                existing_records=len(records),
            )
            return

        end_date = current_date - timedelta(days=1)
        if config.start_date > end_date:
            self._backfill_status = BackfillStatus(
                start_date=config.start_date,
                end_date=end_date,
            )
            return

        data = {**self.entry.data, **self.entry.options}
        reader = HistoricalStatisticsReader(self.hass)
        try:
            daily_deltas, statistic_rows = await reader.async_get_daily_delta_result(
                start_date=config.start_date,
                end_date=end_date,
                pv_generation_entities=config.pv_generation_entities,
                grid_import_entity=config.grid_import_entity,
                grid_export_entity=config.grid_export_entity,
            )
        except Exception as err:
            self._backfill_status = BackfillStatus(
                attempted=True,
                start_date=config.start_date,
                end_date=end_date,
                error=str(err),
            )
            _LOGGER.exception(
                "Failed to backfill historical solar amortisation records",
            )
            return

        backfilled = calculate_backfill_records(
            site_id=config.site_id,
            start_date=config.start_date,
            end_date=end_date,
            investment_amount=config.investment_amount,
            daily_deltas=daily_deltas,
            electricity_price_eur_kwh=_parse_decimal(data[CONF_ELECTRICITY_PRICE]),
            feed_in_tariff_eur_kwh=_parse_decimal(data.get(CONF_FEED_IN_TARIFF, 0)),
            previous_records=[],
        )
        await self.store.async_upsert_many(backfilled)
        self._backfill_status = BackfillStatus(
            attempted=True,
            start_date=config.start_date,
            end_date=end_date,
            statistic_rows=statistic_rows,
            daily_deltas=len(daily_deltas),
            records_created=len(backfilled),
        )
        _LOGGER.debug(
            "Backfill for %s: rows=%s, daily_deltas=%s, records_created=%s",
            config.name,
            statistic_rows,
            len(daily_deltas),
            len(backfilled),
        )

    def _read_current_snapshot(
        self,
        config: SiteConfig,
        snapshot_date: date,
    ) -> tuple[MeterSnapshot | None, list[str]]:
        unavailable_entities: list[str] = []
        pv_values = []
        for entity_id in config.pv_generation_entities:
            value = self._state_as_float(entity_id)
            if value is None:
                unavailable_entities.append(entity_id)
            pv_values.append(value)

        grid_import = self._state_as_float(config.grid_import_entity)
        if grid_import is None:
            unavailable_entities.append(config.grid_import_entity)

        grid_export = self._state_as_float(config.grid_export_entity)
        if grid_export is None:
            unavailable_entities.append(config.grid_export_entity)

        if None in pv_values or grid_import is None or grid_export is None:
            return None, unavailable_entities

        return MeterSnapshot(
            site_id=config.site_id,
            snapshot_date=snapshot_date,
            pv_generation_kwh=sum(value for value in pv_values if value is not None),
            grid_import_kwh=grid_import,
            grid_export_kwh=grid_export,
        ), []

    def _state_as_float(self, entity_id: str) -> float | None:
        state = self.hass.states.get(entity_id)
        if state is None or state.state in {"unknown", "unavailable"}:
            return None

        try:
            return float(state.state)
        except ValueError:
            _LOGGER.debug(
                "Entity %s has a non-numeric state: %s",
                entity_id,
                state.state,
            )
            return None

    @callback
    def _handle_daily_tick(self, _now: Any) -> None:
        self.hass.async_create_task(self.async_request_refresh())


def _parse_decimal(value: Any) -> float:
    if isinstance(value, int | float):
        return float(value)

    normalized = str(value).strip().replace(" ", "")
    if "," in normalized and "." in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    else:
        normalized = normalized.replace(",", ".")
    return float(normalized)


def _normalize_entities(value: str | list[str] | tuple[str, ...]) -> list[str]:
    if isinstance(value, str):
        return [entity.strip() for entity in value.split(",") if entity.strip()]
    return [str(entity).strip() for entity in value if str(entity).strip()]
