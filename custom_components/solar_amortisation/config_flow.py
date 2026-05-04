"""Config flow for Solar Amortisation."""

from __future__ import annotations

from datetime import date
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

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


class SolarAmortisationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Solar Amortisation."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> SolarAmortisationOptionsFlow:
        """Create the options flow."""

        return SolarAmortisationOptionsFlow(config_entry)

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Create a site."""

        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                date.fromisoformat(user_input[CONF_START_DATE])
            except ValueError:
                errors[CONF_START_DATE] = "invalid_date"

            if not errors:
                await self.async_set_unique_id(user_input[CONF_SITE_NAME].lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_SITE_NAME],
                    data=user_input,
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
            vol.Required(CONF_INVESTMENT_AMOUNT): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    mode=selector.NumberSelectorMode.BOX,
                    step=0.01,
                    unit_of_measurement="EUR",
                )
            ),
            vol.Required(CONF_START_DATE, default=date.today().isoformat()): str,
            vol.Required(CONF_GRID_IMPORT_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Required(CONF_GRID_EXPORT_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Required(CONF_PV_GENERATION_ENTITIES): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", multiple=True)
            ),
            vol.Required(CONF_ELECTRICITY_PRICE): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    mode=selector.NumberSelectorMode.BOX,
                    step=0.0001,
                    unit_of_measurement="EUR/kWh",
                )
            ),
            vol.Optional(CONF_FEED_IN_TARIFF, default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    mode=selector.NumberSelectorMode.BOX,
                    step=0.0001,
                    unit_of_measurement="EUR/kWh",
                )
            ),
        }
    )


class SolarAmortisationOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Solar Amortisation."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Manage site options."""

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

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
                default=defaults.get(CONF_INVESTMENT_AMOUNT, 0),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    mode=selector.NumberSelectorMode.BOX,
                    step=0.01,
                    unit_of_measurement="EUR",
                )
            ),
            vol.Required(
                CONF_START_DATE,
                default=defaults.get(CONF_START_DATE, date.today().isoformat()),
            ): str,
            vol.Required(
                CONF_GRID_IMPORT_ENTITY,
                default=defaults.get(CONF_GRID_IMPORT_ENTITY),
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            vol.Required(
                CONF_GRID_EXPORT_ENTITY,
                default=defaults.get(CONF_GRID_EXPORT_ENTITY),
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            vol.Required(
                CONF_PV_GENERATION_ENTITIES,
                default=defaults.get(CONF_PV_GENERATION_ENTITIES, []),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", multiple=True)
            ),
            vol.Required(
                CONF_ELECTRICITY_PRICE,
                default=defaults.get(CONF_ELECTRICITY_PRICE, 0),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    mode=selector.NumberSelectorMode.BOX,
                    step=0.0001,
                    unit_of_measurement="EUR/kWh",
                )
            ),
            vol.Optional(
                CONF_FEED_IN_TARIFF,
                default=defaults.get(CONF_FEED_IN_TARIFF, 0),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    mode=selector.NumberSelectorMode.BOX,
                    step=0.0001,
                    unit_of_measurement="EUR/kWh",
                )
            ),
        }
    )
