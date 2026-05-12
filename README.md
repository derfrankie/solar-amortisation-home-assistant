# Simple Solar Amortisation

[![HACS Custom Repository](https://img.shields.io/badge/HACS-Custom%20Repository-41BDF5.svg)](https://github.com/custom-components/hacs)
[![HACS Supported](https://img.shields.io/badge/HACS-Supported-03a9f4)](https://github.com/custom-components/hacs)

Track how quickly a solar installation pays for itself in Home Assistant.

This custom integration calculates daily return, cumulative return, remaining investment, and payoff forecasts from your existing Home Assistant energy sensors.

## What it does

- Supports one or more configured sites.
- Can autodiscover grid, solar, battery, and fixed price sources from the Home Assistant Energy dashboard.
- Supports manual overrides for autodiscovered entities and prices.
- Stores the configured electricity price and feed-in tariff per recorded day.
- Backfills historical daily records from Home Assistant long-term statistics when your start date is in the past.
- Creates sensors for yesterday's return, cumulative return, remaining amount, amortisation progress, and multiple forecast windows.

## Requirements

Before installing, make sure you already have:

- Home Assistant with the recorder enabled.
- Energy sensors with `device_class: energy`.
- Total or increasing energy entities for:
  - Grid import
  - Grid export
  - One or more PV generation sources
- Historical long-term statistics available if you want automatic backfill for past dates.

The integration accepts energy values in `Wh`, `kWh`, or `MWh`.

## Installation

### HACS

This integration is installed through HACS as a custom repository.

[![Open your Home Assistant instance and add this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=custom-components&repository=solar-amortisation-ha&category=integration)

1. Open HACS in Home Assistant.
2. Go to `Integrations`.
3. Open the menu in the top-right corner and select `Custom repositories`.
4. Add `https://github.com/custom-components/solar-amortisation-ha` as an `Integration`.
5. Search for `Solar Amortisation`.
6. Open the repository and click `Download`.
7. Restart Home Assistant.

### Manual

1. Copy `custom_components/solar_amortisation` into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.

## Configuration

[![Open your Home Assistant instance and start setting up this integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=solar_amortisation)

1. Go to `Settings` > `Devices & services`.
2. Click `Add Integration`.
3. Search for `Simple Solar Amortisation`.
4. Fill in the site details:
   - `Site name`
   - `Investment amount`
   - `Start date`
   - Optional: enable `Use Energy dashboard configuration`
   - Optional manual overrides for grid, solar, battery, electricity price, and feed-in tariff
5. Submit the form.

You can create multiple entries if you want to track multiple sites.

## Created sensors

For each configured site, the integration creates sensors for:

- Daily return yesterday
- Cumulative return
- Remaining amount
- Days since start
- Forecast days based on 30-day average
- Forecast days based on 365-day average
- Forecast days based on since-start average
- PV generation yesterday
- Self-consumed PV yesterday
- Total consumption yesterday
- Grid import yesterday
- Grid export yesterday
- Battery discharge yesterday
- Battery charge yesterday
- Daily savings yesterday
- Daily revenue yesterday
- Electricity price yesterday
- Feed-in tariff yesterday
- Amortisation progress

## Accounting model

For each day:

```text
pv_generation = sum(daily delta of PV generation entities)
grid_import = daily delta of grid import entity
grid_export = daily delta of grid export entity
battery_discharge = sum(daily delta of battery discharge entities)
battery_charge = sum(daily delta of battery charge entities)
local_usage = max(
  pv_generation + battery_discharge - grid_export - battery_charge,
  0
)
total_consumption = grid_import + local_usage

daily_savings = local_usage * electricity_price
daily_revenue = grid_export * feed_in_tariff
daily_return = daily_savings + daily_revenue
remaining_amount = investment_amount - cumulative_return
```

This mirrors the Energy dashboard flow model better than the older `pv - export` approximation, especially when a battery is present.

## Notes

- Backfill only works when Home Assistant already has recorder statistics for the selected entities.
- If the selected entities are unavailable, the integration will keep the setup but the sensors will show a setup issue until the entities return.
- Electricity price and feed-in tariff are currently configured as fixed values in the integration options. When changed, future daily records use the new values.
- The integration is designed around a site-level view. If you have multiple inverters or a battery on one shared connection, configure them as one site and sum all PV generation entities there.
