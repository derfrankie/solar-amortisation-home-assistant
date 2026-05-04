"""Data coordinator for Solar Amortisation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
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
class SiteStatus:
    """Current published state for a site."""

    latest_record: DailyRecord | None
    current_snapshot: MeterSnapshot
    days_since_start: int
    forecasts: Forecasts


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
        )
        self.entry = entry
        self.store = store

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
            investment_amount=float(data[CONF_INVESTMENT_AMOUNT]),
            start_date=date.fromisoformat(data[CONF_START_DATE]),
            grid_import_entity=data[CONF_GRID_IMPORT_ENTITY],
            grid_export_entity=data[CONF_GRID_EXPORT_ENTITY],
            pv_generation_entities=tuple(data[CONF_PV_GENERATION_ENTITIES]),
            electricity_prices=(),
            feed_in_tariffs=(),
        )

    async def _async_update_data(self) -> SiteStatus:
        """Refresh current state and perform a rollup when a new day starts."""

        config = self.site_config
        current_date = dt_util.now().date()
        current_snapshot = self._read_current_snapshot(config, current_date)
        previous_snapshot = self.store.snapshot_for_site(config.site_id)

        await self._async_backfill_if_needed(config, current_date)

        if previous_snapshot is None:
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
            days_since_start=calculate_days_since_start(config.start_date, current_date),
            forecasts=calculate_forecasts(
                records=records,
                remaining_amount_eur=remaining,
            ),
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
            electricity_price_eur_kwh=float(data[CONF_ELECTRICITY_PRICE]),
            feed_in_tariff_eur_kwh=float(data.get(CONF_FEED_IN_TARIFF, 0)),
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
            return

        end_date = current_date - timedelta(days=1)
        if config.start_date > end_date:
            return

        data = {**self.entry.data, **self.entry.options}
        reader = HistoricalStatisticsReader(self.hass)
        try:
            daily_deltas = await reader.async_get_daily_deltas(
                start_date=config.start_date,
                end_date=end_date,
                pv_generation_entities=config.pv_generation_entities,
                grid_import_entity=config.grid_import_entity,
                grid_export_entity=config.grid_export_entity,
            )
        except Exception:
            _LOGGER.exception("Failed to backfill historical solar amortisation records")
            return

        backfilled = calculate_backfill_records(
            site_id=config.site_id,
            start_date=config.start_date,
            end_date=end_date,
            investment_amount=config.investment_amount,
            daily_deltas=daily_deltas,
            electricity_price_eur_kwh=float(data[CONF_ELECTRICITY_PRICE]),
            feed_in_tariff_eur_kwh=float(data.get(CONF_FEED_IN_TARIFF, 0)),
            previous_records=[],
        )
        await self.store.async_upsert_many(backfilled)

    def _read_current_snapshot(
        self,
        config: SiteConfig,
        snapshot_date: date,
    ) -> MeterSnapshot:
        return MeterSnapshot(
            site_id=config.site_id,
            snapshot_date=snapshot_date,
            pv_generation_kwh=sum(
                self._state_as_float(entity_id)
                for entity_id in config.pv_generation_entities
            ),
            grid_import_kwh=self._state_as_float(config.grid_import_entity),
            grid_export_kwh=self._state_as_float(config.grid_export_entity),
        )

    def _state_as_float(self, entity_id: str) -> float:
        state = self.hass.states.get(entity_id)
        if state is None or state.state in {"unknown", "unavailable"}:
            msg = f"Entity {entity_id} is not available"
            raise UpdateFailed(msg)

        try:
            return float(state.state)
        except ValueError as err:
            msg = f"Entity {entity_id} has a non-numeric state: {state.state}"
            raise UpdateFailed(msg) from err

    @callback
    def _handle_daily_tick(self, _now: Any) -> None:
        self.hass.async_create_task(self.async_request_refresh())
