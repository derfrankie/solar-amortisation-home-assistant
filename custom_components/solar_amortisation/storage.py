"""Storage helpers for daily amortisation records."""

from __future__ import annotations

from datetime import date
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION
from .models import DailyRecord, MeterSnapshot


class DailyRecordStore:
    """Persist daily records in Home Assistant storage."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass,
            STORAGE_VERSION,
            STORAGE_KEY,
        )
        self._records: dict[str, list[DailyRecord]] = {}
        self._snapshots: dict[str, MeterSnapshot] = {}

    async def async_load(self) -> None:
        data = await self._store.async_load()
        if not data:
            self._records = {}
            self._snapshots = {}
            return

        self._records = {
            site_id: [DailyRecord.from_dict(item) for item in records]
            for site_id, records in data.get("sites", {}).items()
        }
        self._snapshots = {
            site_id: MeterSnapshot.from_dict(snapshot)
            for site_id, snapshot in data.get("snapshots", {}).items()
        }

    async def async_save(self) -> None:
        await self._store.async_save(
            {
                "sites": {
                    site_id: [record.as_dict() for record in records]
                    for site_id, records in self._records.items()
                },
                "snapshots": {
                    site_id: snapshot.as_dict()
                    for site_id, snapshot in self._snapshots.items()
                },
            }
        )

    def records_for_site(self, site_id: str) -> list[DailyRecord]:
        return sorted(
            self._records.get(site_id, []),
            key=lambda item: item.record_date,
        )

    def latest_for_site(self, site_id: str) -> DailyRecord | None:
        records = self.records_for_site(site_id)
        return records[-1] if records else None

    async def async_upsert(self, record: DailyRecord) -> None:
        await self.async_upsert_many([record])

    async def async_upsert_many(self, records_to_upsert: list[DailyRecord]) -> None:
        if not records_to_upsert:
            return

        affected_site_ids = {record.site_id for record in records_to_upsert}
        incoming = {
            (record.site_id, record.record_date): record
            for record in records_to_upsert
        }

        for site_id in affected_site_ids:
            records = [
                item
                for item in self._records.get(site_id, [])
                if (item.site_id, item.record_date) not in incoming
            ]
            records.extend(
                record for record in records_to_upsert if record.site_id == site_id
            )
            self._records[site_id] = sorted(records, key=lambda item: item.record_date)

        await self.async_save()

    def has_record(self, site_id: str, record_date: date) -> bool:
        return any(
            item.record_date == record_date
            for item in self._records.get(site_id, [])
        )

    def snapshot_for_site(self, site_id: str) -> MeterSnapshot | None:
        return self._snapshots.get(site_id)

    async def async_set_snapshot(self, snapshot: MeterSnapshot) -> None:
        self._snapshots[snapshot.site_id] = snapshot
        await self.async_save()
