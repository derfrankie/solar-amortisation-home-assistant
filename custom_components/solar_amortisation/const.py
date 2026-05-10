"""Constants for the Solar Amortisation integration."""

from __future__ import annotations

DOMAIN = "solar_amortisation"
PLATFORMS = ["sensor"]

CONF_SITE_NAME = "site_name"
CONF_DESCRIPTION = "description"
CONF_INVESTMENT_AMOUNT = "investment_amount"
CONF_START_DATE = "start_date"
CONF_USE_ENERGY_DASHBOARD = "use_energy_dashboard"
CONF_GRID_IMPORT_ENTITY = "grid_import_entity"
CONF_GRID_EXPORT_ENTITY = "grid_export_entity"
CONF_PV_GENERATION_ENTITIES = "pv_generation_entities"
CONF_BATTERY_DISCHARGE_ENTITIES = "battery_discharge_entities"
CONF_BATTERY_CHARGE_ENTITIES = "battery_charge_entities"
CONF_ELECTRICITY_PRICE = "electricity_price"
CONF_FEED_IN_TARIFF = "feed_in_tariff"

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.daily_records"

DEFAULT_SCAN_HOUR = 0
DEFAULT_SCAN_MINUTE = 5
