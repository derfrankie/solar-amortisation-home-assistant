"""Config flow for Solar Amortisation."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

import voluptuous as vol

from homeassistant import config_entries

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
    DOMAIN,
)

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
        if user_input is not None:
            _LOGGER.debug("Received solar amortisation config input: %s", user_input)
            try:
                date.fromisoformat(user_input[CONF_START_DATE])
            except ValueError:
                errors[CONF_START_DATE] = "invalid_date"

            if not errors:
                return self.async_create_entry(
                    title=user_input[CONF_SITE_NAME],
                    data=_normalize_input(user_input),
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_site_schema(),
            errors=errors,
        )


def _site_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_SITE_NAME): str,
            vol.Optional(CONF_DESCRIPTION, default=""): str,
            vol.Required(CONF_INVESTMENT_AMOUNT): _money_selector(),
            vol.Required(
                CONF_START_DATE,
                default=date.today().isoformat(),
            ): _date_selector(),
            vol.Required(CONF_GRID_IMPORT_ENTITY): _sensor_entity_selector(),
            vol.Required(CONF_GRID_EXPORT_ENTITY): _sensor_entity_selector(),
            vol.Required(CONF_PV_GENERATION_ENTITIES): _sensor_entities_selector(),
            vol.Required(CONF_ELECTRICITY_PRICE): _price_selector(),
            vol.Required(CONF_FEED_IN_TARIFF, default="0"): _price_selector(),
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

        if user_input is not None:
            _LOGGER.debug("Received solar amortisation options input: %s", user_input)
            return self.async_create_entry(title="", data=_normalize_input(user_input))

        merged = {**self._entry.data, **self._entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(merged),
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
                CONF_GRID_IMPORT_ENTITY,
                default=defaults.get(CONF_GRID_IMPORT_ENTITY),
            ): _sensor_entity_selector(),
            vol.Required(
                CONF_GRID_EXPORT_ENTITY,
                default=defaults.get(CONF_GRID_EXPORT_ENTITY),
            ): _sensor_entity_selector(),
            vol.Required(
                CONF_PV_GENERATION_ENTITIES,
                default=_entities_as_text(defaults.get(CONF_PV_GENERATION_ENTITIES, "")),
            ): _sensor_entities_selector(),
            vol.Required(
                CONF_ELECTRICITY_PRICE,
                default=_as_text(defaults.get(CONF_ELECTRICITY_PRICE, "")),
            ): _price_selector(),
            vol.Required(
                CONF_FEED_IN_TARIFF,
                default=_as_text(defaults.get(CONF_FEED_IN_TARIFF, 0)),
            ): _price_selector(),
        }
    )


def _normalize_input(user_input: dict[str, Any]) -> dict[str, Any]:
    data = dict(user_input)
    data[CONF_INVESTMENT_AMOUNT] = _parse_decimal(data[CONF_INVESTMENT_AMOUNT])
    data[CONF_ELECTRICITY_PRICE] = _parse_decimal(data[CONF_ELECTRICITY_PRICE])
    data[CONF_FEED_IN_TARIFF] = _parse_decimal(data.get(CONF_FEED_IN_TARIFF, 0))
    data[CONF_PV_GENERATION_ENTITIES] = _normalize_pv_entities(
        data[CONF_PV_GENERATION_ENTITIES]
    )
    return data


def _money_selector() -> type:
    return str


def _price_selector() -> type:
    return str


def _date_selector() -> type:
    return str


def _sensor_entity_selector() -> type:
    return str


def _sensor_entities_selector() -> type:
    return str


def _normalize_pv_entities(value: list[str] | str) -> list[str]:
    if isinstance(value, str):
        return [entity.strip() for entity in value.split(",") if entity.strip()]
    return value


def _entities_as_text(value: list[str] | str) -> str:
    if isinstance(value, str):
        return value
    return ",".join(value)


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
