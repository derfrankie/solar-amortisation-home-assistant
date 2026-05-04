# Solar Amortisation for Home Assistant

Custom Home Assistant integration for tracking solar amortisation per site.

The integration models one site with one shared grid connection and multiple PV
generation entities. This keeps the accounting honest for installations with a
battery or multiple inverters, where the exact economic contribution of a single
PV array cannot be separated from site-level import and export meters.

## Current scope

- Configure one or more sites.
- Track investment amount and start date.
- Use total energy entities for grid import, grid export, and PV generation.
- Store the electricity price and feed-in tariff used for each day.
- Backfill historical daily records from Home Assistant long-term statistics
  when the configured start date is in the past.
- Publish sensors for daily return, cumulative return, remaining amount, days
  since start, and forecast days based on 30-day, 365-day, and since-start
  averages.

When historical long-term statistics are available, the integration creates
daily records from the configured start date through yesterday during the first
setup. The configured electricity price and feed-in tariff are stored on every
backfilled day. After that, the integration keeps a daily meter snapshot and
continues forward from the next daily rollup.

## Accounting model

For each day:

```text
pv_generation = sum(daily delta of PV generation entities)
grid_export = daily delta of grid export entity
self_consumed_pv = max(pv_generation - grid_export, 0)

daily_savings = self_consumed_pv * electricity_price
daily_revenue = grid_export * feed_in_tariff
daily_return = daily_savings + daily_revenue
remaining_amount = investment_amount - cumulative_return
```

Grid import is stored for analysis and future refinements, but the site-level
return is derived from avoided import and export revenue.

## Installation

This repository is intended to be installed as a HACS custom repository.

1. Add this repository to HACS as an integration custom repository.
2. Install `Solar Amortisation`.
3. Restart Home Assistant.
4. Add the integration from Settings > Devices & services.

## Development

```bash
python3 -m unittest discover -s tests
```
