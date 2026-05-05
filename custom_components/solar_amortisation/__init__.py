"""Solar Amortisation integration."""

from __future__ import annotations

from .const import DOMAIN


async def async_setup(hass, config) -> bool:
    """Set up the Solar Amortisation integration."""

    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass, entry) -> bool:
    """Set up Solar Amortisation from a config entry."""

    from homeassistant.const import Platform

    from .coordinator import SolarAmortisationCoordinator
    from .storage import DailyRecordStore

    domain_data = hass.data.setdefault(DOMAIN, {})
    store = domain_data.get("store")
    if store is None:
        store = DailyRecordStore(hass)
        await store.async_load()
        domain_data["store"] = store

    coordinator = SolarAmortisationCoordinator(hass, entry, store)
    await coordinator.async_config_entry_first_refresh()
    domain_data[entry.entry_id] = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])
    return True


async def async_unload_entry(hass, entry) -> bool:
    """Unload a config entry."""

    from homeassistant.const import Platform

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry,
        [Platform.SENSOR],
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def _async_update_listener(hass, entry) -> None:
    """Refresh entities when options change."""

    coordinator = hass.data[DOMAIN].get(entry.entry_id)
    if coordinator is not None:
        await coordinator.async_request_refresh()
