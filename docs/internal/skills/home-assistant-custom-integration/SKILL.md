---
name: home-assistant-custom-integration
description: Use when working on this repo's Home Assistant custom integration, especially config flows, setup_entry failures, DataUpdateCoordinator behavior, sensor entities, HACS metadata, diagnostics, release packaging, or runtime debugging.
---

# Home Assistant Custom Integration

Use this skill before changing Home Assistant integration code in this repo.

## First Checks

1. Confirm the integration folder and manifest domain match exactly:
   `custom_components/solar_amortisation` and `solar_amortisation`.
2. Check the entry lifecycle implied by the user report:
   `400` before form means handler/import/schema discovery; `500` while opening
   the form means form schema rendering; `create_entry` plus `setup_error` means
   `async_setup_entry` or initial refresh failed.
3. Prefer fixing the lifecycle layer that failed instead of adding broad catches.

## Related Home Assistant Best Practices

The external Home Assistant AI best-practices skill is useful background when
work touches automations, helpers, dashboards, service calls, or user-facing
setup guidance:

- https://github.com/homeassistant-ai/skills/tree/main/skills/home-assistant-best-practices

Use it as a companion reference, not as the primary guide for this repo's custom
integration internals. Its strongest lessons to carry into this project:

- Prefer native Home Assistant constructs over templates where possible.
- Prefer UI/config-flow managed configuration over direct YAML edits.
- Avoid direct edits to `.storage` files.
- Prefer stable `entity_id` references in user-facing guidance.
- Check impact before renaming entities because dashboards, helpers, and config
  entries can store entity IDs independently.
- For user docs, point users to Settings > Devices & services and Helpers before
  suggesting manual YAML.

## Optional Home Assistant MCP

The `homeassistant-ai/ha-mcp` server can be useful when a connected MCP is
available:

- https://github.com/homeassistant-ai/ha-mcp

Use it for runtime investigation instead of asking the user to manually dig
through the UI whenever possible.

Useful tool categories for this repo:

- Logs and health: `ha_get_logs`, `ha_get_system_health`, `ha_check_config`.
- Integration state: `ha_get_integration`, `ha_set_integration_enabled`.
- Entity lookup: `ha_search_entities`, `ha_get_state`, `ha_get_entity`.
- HACS: `ha_hacs_add_repository`, `ha_hacs_download`,
  `ha_hacs_repository_info`, `ha_hacs_search`.
- History/statistics: `ha_get_history` and statistics tools when validating
  backfill assumptions.
- Files, only when the companion `ha_mcp_tools` component and feature flags are
  explicitly enabled: `ha_read_file`, `ha_write_file`, `ha_list_files`.

Safety notes:

- Treat HA MCP access as privileged control of the user's home.
- Prefer read-only tools for investigation.
- Do not call destructive/control tools unless the user asked for that specific
  action.
- Do not edit `.storage` directly. Use HA APIs/config flows/options where
  possible.
- File and YAML editing tools are beta and require explicit feature flags in
  `ha-mcp`; use them cautiously and with backup/validation.
- The MCP provides access, not judgment. Pair it with the best-practices skill
  for automation/helper/dashboard decisions.

## Config Flow Rules

- Keep form schemas renderable by Home Assistant. If a flow crashes while
  opening, reduce fields to primitive `str`, `float`, `int`, or simple selectors.
- Do not validate live entity availability inside the config flow. Let the entry
  be created and surface runtime availability as diagnostics or sensor
  attributes.
- Normalize user input before storing it, but keep runtime parsing tolerant of
  older/manual entry data.
- Parse German decimal input defensively: accept `0,3485`, `0.3485`,
  `3000,50`, and `3.000,50`.
- For comma-separated entity input, trim whitespace and discard empty values.

## Setup Entry Rules

- `async_setup_entry` should not fail because a configured source entity is
  temporarily `unknown`, `unavailable`, missing, or non-numeric.
- Initial coordinator refresh should return a valid in-memory status with a
  clear `setup_issue` when source entities are unavailable.
- Use Home Assistant runtime imports lazily when local pure-Python tests import
  submodules without Home Assistant installed.
- Forward platforms with `Platform.SENSOR` during Home Assistant runtime.

## DataUpdateCoordinator

- Pass `config_entry=entry` to `DataUpdateCoordinator`.
- Use `always_update=False` when coordinator data is comparable and duplicate
  writes are not useful.
- Keep external/history reads inside coordinator update methods, not entity
  properties.
- A daily scheduler should request coordinator refresh, not write entity state
  directly.

## Sensor Rules

- Sensor properties must read memory only; no I/O in `native_value`,
  `extra_state_attributes`, or registry properties.
- Be conservative with `device_class` and `state_class`. Invalid combinations
  can become hard failures in newer Home Assistant versions.
- Daily historical/accounting values should be chart-friendly measurements, not
  Energy Dashboard source meters.
- Use `_attr_has_entity_name = True` for modern entity naming behavior, with
  explicit sensor names so entities do not all display as the device/site name.

## Historical Backfill

- Prefer Home Assistant long-term statistics for historical daily deltas.
- Support both `change` statistics and a `sum` baseline fallback.
- Backfill should not silently overwrite existing daily accounting records.
- Fixed electricity price and feed-in tariff can be stored on every backfilled
  daily record when the user accepts fixed historical values.

## Diagnostics

- Add diagnostics for setup/debuggability before relying on logs alone.
- Do not expose secrets. This integration has no credentials, but still use
  redaction utilities when returning entry data.
- Include entry data/options, current setup issue, and latest accounting record.

## HACS And Releases

- Custom integrations need `manifest.json` with `version`.
- HACS version choices come from GitHub Releases, not plain commits alone.
- Keep `CHANGELOG.md` aligned with GitHub Release notes.
- Put brand assets in `custom_components/solar_amortisation/brand/`; at minimum
  include `icon.png`.

## Validation

Run after edits:

```bash
python3 -m unittest discover -s tests
python3 -m compileall custom_components tests
```

If `ruff` is available:

```bash
python3 -m ruff check .
```

Remove generated `__pycache__` directories before finishing.
