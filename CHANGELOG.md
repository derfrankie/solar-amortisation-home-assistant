# Changelog

All notable changes to Solar Amortisation are documented here.

This project uses GitHub Releases for HACS-visible versions. Keep the release
notes in GitHub aligned with the matching section in this file.

## [0.1.0alpha] - 2026-05-05

### Added

- Initial HACS custom integration structure.
- Config flow for site-based solar amortisation tracking.
- Daily accounting records for PV generation, grid import, grid export,
  self-consumed PV, daily return, cumulative return, and remaining amount.
- Historical backfill from Home Assistant long-term statistics.
- Sensors for return, remaining amount, days since start, forecasts, energy
  deltas, prices, and amortisation progress.
- German translation strings.
- Unit tests for pure calculation and backfill logic.
