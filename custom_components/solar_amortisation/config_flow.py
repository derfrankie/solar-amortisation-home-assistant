"""Config flow for Solar Amortisation."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    CONF_BATTERY_CHARGE_ENTITIES,
    CONF_BATTERY_DISCHARGE_ENTITIES,
    CONF_DESCRIPTION,
    DOMAIN,
    CONF_ELECTRICITY_PRICE,
    CONF_FEED_IN_TARIFF,
    CONF_GRID_EXPORT_ENTITY,
    CONF_GRID_IMPORT_ENTITY,
    CONF_INVESTMENT_AMOUNT,
    CONF_PV_GENERATION_ENTITIES,
    CONF_START_DATE,
    CONF_SITE_NAME,
    CONF_USE_ENERGY_DASHBOARD,
)
from .energy_dashboard import async_get_energy_dashboard_config

_LOGGER = logging.getLogger(__name__)


class SolarAmortisationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Solar Amortisation."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry):
        """Create the options flow."""

        return SolarAmortisationOptionsFlow(config_entry)

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ):
        """Create a site."""

        errors: dict[str, str] = {}
        defaults = await _async_form_defaults(self.hass, None)
        if user_input is not None:
            _LOGGER.debug("Received solar amortisation config input: %s", user_input)
            errors = _validate_input(user_input, defaults)

            if not errors:
                return self.async_create_entry(
                    title=user_input[CONF_SITE_NAME],
                    data=_normalize_input(user_input),
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_site_schema(defaults),
            errors=errors,
        )


def _site_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_SITE_NAME, default=defaults.get(CONF_SITE_NAME, "")): str,
            vol.Optional(
                CONF_DESCRIPTION,
                default=defaults.get(CONF_DESCRIPTION, ""),
            ): str,
            vol.Required(
                CONF_INVESTMENT_AMOUNT,
                default=_as_text(defaults.get(CONF_INVESTMENT_AMOUNT, "")),
            ): _money_selector(),
            vol.Required(
                CONF_START_DATE,
                default=defaults.get(CONF_START_DATE, date.today().isoformat()),
            ): _date_selector(),
            vol.Required(
                CONF_USE_ENERGY_DASHBOARD,
                default=defaults.get(CONF_USE_ENERGY_DASHBOARD, True),
            ): bool,
            vol.Optional(
                CONF_GRID_IMPORT_ENTITY,
                default=defaults.get(CONF_GRID_IMPORT_ENTITY),
            ): _sensor_entity_selector(),
            vol.Optional(
                CONF_GRID_EXPORT_ENTITY,
                default=defaults.get(CONF_GRID_EXPORT_ENTITY),
            ): _sensor_entity_selector(),
            vol.Optional(
                CONF_PV_GENERATION_ENTITIES,
                default=_normalize_pv_entities(
                    defaults.get(CONF_PV_GENERATION_ENTITIES, []),
                ),
            ): _sensor_entities_selector(),
            vol.Optional(
                CONF_BATTERY_DISCHARGE_ENTITIES,
                default=_normalize_pv_entities(
                    defaults.get(CONF_BATTERY_DISCHARGE_ENTITIES, []),
                ),
            ): _sensor_entities_selector(),
            vol.Optional(
                CONF_BATTERY_CHARGE_ENTITIES,
                default=_normalize_pv_entities(
                    defaults.get(CONF_BATTERY_CHARGE_ENTITIES, []),
                ),
            ): _sensor_entities_selector(),
            vol.Optional(
                CONF_ELECTRICITY_PRICE,
                default=_as_text(defaults.get(CONF_ELECTRICITY_PRICE, "")),
            ): _price_selector(),
            vol.Optional(
                CONF_FEED_IN_TARIFF,
                default=_as_text(defaults.get(CONF_FEED_IN_TARIFF, 0)),
            ): _price_selector(),
        }
    )


class SolarAmortisationOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Solar Amortisation."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ):
        """Manage site options."""

        merged = {**self._entry.data, **self._entry.options}
        if user_input is not None:
            _LOGGER.debug("Received solar amortisation options input: %s", user_input)
            defaults = await _async_form_defaults(self.hass, merged)
            errors = _validate_input(user_input, defaults)
            if not errors:
                return self.async_create_entry(
                    title="",
                    data=_normalize_input(user_input),
                )
            return self.async_show_form(
                step_id="init",
                data_schema=_options_schema({**defaults, **user_input}),
                errors=errors,
            )

        defaults = await _async_form_defaults(self.hass, merged)
        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(defaults),
        )


def _options_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_SITE_NAME,
                default=defaults.get(CONF_SITE_NAME, ""),
            ): str,
            vol.Optional(
                CONF_DESCRIPTION,
                default=defaults.get(CONF_DESCRIPTION, ""),
            ): str,
            vol.Required(
                CONF_INVESTMENT_AMOUNT,
                default=_as_text(defaults.get(CONF_INVESTMENT_AMOUNT, "")),
            ): _money_selector(),
            vol.Required(
                CONF_START_DATE,
                default=defaults.get(CONF_START_DATE, date.today().isoformat()),
            ): _date_selector(),
            vol.Required(
                CONF_USE_ENERGY_DASHBOARD,
                default=defaults.get(CONF_USE_ENERGY_DASHBOARD, True),
            ): bool,
            vol.Optional(
                CONF_GRID_IMPORT_ENTITY,
                default=defaults.get(CONF_GRID_IMPORT_ENTITY),
            ): _sensor_entity_selector(),
            vol.Optional(
                CONF_GRID_EXPORT_ENTITY,
                default=defaults.get(CONF_GRID_EXPORT_ENTITY),
            ): _sensor_entity_selector(),
            vol.Optional(
                CONF_PV_GENERATION_ENTITIES,
                default=_normalize_pv_entities(
                    defaults.get(CONF_PV_GENERATION_ENTITIES, []),
                ),
            ): _sensor_entities_selector(),
            vol.Optional(
                CONF_BATTERY_DISCHARGE_ENTITIES,
                default=_normalize_pv_entities(
                    defaults.get(CONF_BATTERY_DISCHARGE_ENTITIES, []),
                ),
            ): _sensor_entities_selector(),
            vol.Optional(
                CONF_BATTERY_CHARGE_ENTITIES,
                default=_normalize_pv_entities(
                    defaults.get(CONF_BATTERY_CHARGE_ENTITIES, []),
                ),
            ): _sensor_entities_selector(),
            vol.Optional(
                CONF_ELECTRICITY_PRICE,
                default=_as_text(defaults.get(CONF_ELECTRICITY_PRICE, "")),
            ): _price_selector(),
            vol.Optional(
                CONF_FEED_IN_TARIFF,
                default=_as_text(defaults.get(CONF_FEED_IN_TARIFF, 0)),
            ): _price_selector(),
        }
    )


def _normalize_input(user_input: dict[str, Any]) -> dict[str, Any]:
    data = dict(user_input)
    data[CONF_INVESTMENT_AMOUNT] = _parse_decimal(data[CONF_INVESTMENT_AMOUNT])
    if data.get(CONF_ELECTRICITY_PRICE, "") not in ("", None):
        data[CONF_ELECTRICITY_PRICE] = _parse_decimal(data[CONF_ELECTRICITY_PRICE])
    else:
        data[CONF_ELECTRICITY_PRICE] = ""
    if data.get(CONF_FEED_IN_TARIFF, "") not in ("", None):
        data[CONF_FEED_IN_TARIFF] = _parse_decimal(data.get(CONF_FEED_IN_TARIFF, 0))
    else:
        data[CONF_FEED_IN_TARIFF] = ""
    data[CONF_PV_GENERATION_ENTITIES] = _normalize_pv_entities(
        data.get(CONF_PV_GENERATION_ENTITIES, [])
    )
    data[CONF_BATTERY_DISCHARGE_ENTITIES] = _normalize_pv_entities(
        data.get(CONF_BATTERY_DISCHARGE_ENTITIES, [])
    )
    data[CONF_BATTERY_CHARGE_ENTITIES] = _normalize_pv_entities(
        data.get(CONF_BATTERY_CHARGE_ENTITIES, [])
    )
    return data


async def _async_form_defaults(
    hass,
    existing: dict[str, Any] | None,
) -> dict[str, Any]:
    defaults = dict(existing or {})
    defaults.setdefault(CONF_USE_ENERGY_DASHBOARD, True)
    try:
        discovered = await async_get_energy_dashboard_config(hass)
    except Exception:
        return defaults

    defaults.setdefault(CONF_GRID_IMPORT_ENTITY, discovered.grid_import_entity)
    defaults.setdefault(CONF_GRID_EXPORT_ENTITY, discovered.grid_export_entity)
    defaults.setdefault(
        CONF_PV_GENERATION_ENTITIES,
        list(discovered.pv_generation_entities),
    )
    defaults.setdefault(
        CONF_BATTERY_DISCHARGE_ENTITIES,
        list(discovered.battery_discharge_entities),
    )
    defaults.setdefault(
        CONF_BATTERY_CHARGE_ENTITIES,
        list(discovered.battery_charge_entities),
    )
    if discovered.electricity_price is not None:
        defaults.setdefault(CONF_ELECTRICITY_PRICE, discovered.electricity_price)
    if discovered.feed_in_tariff is not None:
        defaults.setdefault(CONF_FEED_IN_TARIFF, discovered.feed_in_tariff)
    return defaults


def _validate_input(
    user_input: dict[str, Any],
    defaults: dict[str, Any],
) -> dict[str, str]:
    errors: dict[str, str] = {}
    try:
        date.fromisoformat(user_input[CONF_START_DATE])
    except ValueError:
        errors[CONF_START_DATE] = "invalid_date"

    merged = {**defaults, **user_input}
    use_energy_dashboard = merged.get(CONF_USE_ENERGY_DASHBOARD, True)

    if not _pick_value(merged.get(CONF_GRID_IMPORT_ENTITY)) and not use_energy_dashboard:
        errors[CONF_GRID_IMPORT_ENTITY] = "required"
    if not _pick_value(merged.get(CONF_GRID_EXPORT_ENTITY)) and not use_energy_dashboard:
        errors[CONF_GRID_EXPORT_ENTITY] = "required"
    if (
        not _normalize_pv_entities(merged.get(CONF_PV_GENERATION_ENTITIES, []))
        and not use_energy_dashboard
    ):
        errors[CONF_PV_GENERATION_ENTITIES] = "required"
    if not _effective_value(
        user_input.get(CONF_ELECTRICITY_PRICE),
        defaults.get(CONF_ELECTRICITY_PRICE),
    ):
        errors[CONF_ELECTRICITY_PRICE] = "required"

    for key in (CONF_INVESTMENT_AMOUNT, CONF_ELECTRICITY_PRICE, CONF_FEED_IN_TARIFF):
        value = merged.get(key)
        if value in (None, "") and key == CONF_FEED_IN_TARIFF:
            continue
        if value in (None, ""):
            continue
        try:
            _parse_decimal(value)
        except ValueError:
            errors[key] = "invalid_number"
    return errors


def _pick_value(value: Any) -> str | None:
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _effective_value(value: Any, fallback: Any) -> str | None:
    return _pick_value(value) or _pick_value(fallback)


def _money_selector() -> type:
    return str


def _price_selector() -> type:
    return str


def _date_selector() -> selector.DateSelector:
    return selector.DateSelector()


def _sensor_entity_selector() -> selector.EntitySelector:
    return selector.EntitySelector(
        selector.EntitySelectorConfig(
            filter=selector.EntityFilterSelectorConfig(
                domain="sensor",
                device_class="energy",
            ),
        ),
    )


def _sensor_entities_selector() -> selector.EntitySelector:
    return selector.EntitySelector(
        selector.EntitySelectorConfig(
            filter=selector.EntityFilterSelectorConfig(
                domain="sensor",
                device_class="energy",
            ),
            multiple=True,
        ),
    )


def _normalize_pv_entities(value: list[str] | str) -> list[str]:
    if isinstance(value, str):
        return [entity.strip() for entity in value.split(",") if entity.strip()]
    return [str(entity).strip() for entity in value if str(entity).strip()]


def _as_text(value: Any) -> str:
    return str(value)


def _parse_decimal(value: Any) -> float:
    if isinstance(value, int | float):
        return float(value)

    normalized = str(value).strip().replace(" ", "")
    if "," in normalized and "." in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    else:
        normalized = normalized.replace(",", ".")
    return float(normalized)
