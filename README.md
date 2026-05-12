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

| Sensor | Unit | What it means | Long-term daily history |
| --- | --- | --- | --- |
| Daily return yesterday | EUR | Total financial return for the recorded day. This is `daily_savings + daily_revenue`. | Yes |
| Cumulative return | EUR | Sum of all recorded daily returns since the configured start date. | Yes |
| Remaining amount | EUR | Investment amount still not paid back. This is `investment_amount - cumulative_return`. | Yes |
| Days since start | days | Number of days between the configured start date and today. | No |
| Forecast days 30 days | days | Estimated remaining payoff days based on the average daily return of the last 30 records. | No |
| Forecast days 365 days | days | Estimated remaining payoff days based on the average daily return of the last 365 records. | No |
| Forecast days since start | days | Estimated remaining payoff days based on the average daily return across all records. | No |
| PV generation yesterday | kWh | Sum of daily PV generation from all configured PV generation entities. | Yes |
| Self-consumed PV yesterday | kWh | Locally covered usage from solar and battery flows. This is the energy value used for savings. | Yes |
| Total consumption yesterday | kWh | Site consumption for the day. This is `grid_import + self_consumed_pv`. | Yes |
| Grid import yesterday | kWh | Energy imported from the grid during the recorded day. | Yes |
| Grid export yesterday | kWh | Energy exported to the grid during the recorded day. | Yes |
| Battery discharge yesterday | kWh | Energy discharged from configured battery discharge entities during the recorded day. | Yes |
| Battery charge yesterday | kWh | Energy charged into configured battery charge entities during the recorded day. | Yes |
| Daily savings yesterday | EUR | Avoided grid cost from locally covered usage. This is `self_consumed_pv * electricity_price`. | Yes |
| Daily revenue yesterday | EUR | Feed-in revenue from exported energy. This is `grid_export * feed_in_tariff`. | Yes |
| Electricity price yesterday | EUR/kWh | Electricity price stored on that daily record. | Yes |
| Feed-in tariff yesterday | EUR/kWh | Feed-in tariff stored on that daily record. | Yes |
| Amortisation progress | % | Paid-back share of the investment. This is `cumulative_return / investment_amount * 100`. | Yes |

Sensors marked with long-term daily history are also imported as Home Assistant
statistics from the integration's stored daily records. They are the best values
to use for custom history graphs, Statistics Graph cards, or external analysis.
Forecast and day-count sensors are current-state estimates only.

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
