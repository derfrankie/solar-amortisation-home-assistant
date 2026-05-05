"""Diagnostics support for Solar Amortisation."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data

from .const import DOMAIN

TO_REDACT: list[str] = []


async def async_get_config_entry_diagnostics(hass, entry) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    latest_record = None
    setup_issue = None
    backfill_status = {}
    if coordinator is not None and coordinator.data is not None:
        setup_issue = coordinator.data.setup_issue
        backfill_status = coordinator.data.backfill_status.as_dict()
        if coordinator.data.latest_record is not None:
            latest_record = coordinator.data.latest_record.as_dict()

    return {
        "entry": {
            "entry_id": entry.entry_id,
            "title": entry.title,
            "data": async_redact_data(entry.data, TO_REDACT),
            "options": async_redact_data(entry.options, TO_REDACT),
        },
        "runtime": {
            "setup_issue": setup_issue,
            "unavailable_entities": (
                coordinator.data.unavailable_entities
                if coordinator is not None and coordinator.data is not None
                else ()
            ),
            "backfill_status": backfill_status,
            "latest_record": latest_record,
        },
    }
