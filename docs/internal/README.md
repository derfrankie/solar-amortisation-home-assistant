# Internal Maintainer Notes

This directory contains maintainer-facing documentation that should not be part
of the user-facing README.

## Internal Skills

- `skills/home-assistant-custom-integration/SKILL.md`: repo-local workflow notes
  for Home Assistant config flows, setup entries, sensors, diagnostics, HACS,
  and release handling.
- External companion reference for HA automations/helpers/dashboards:
  https://github.com/homeassistant-ai/skills/tree/main/skills/home-assistant-best-practices
- Optional MCP server for live HA investigation/debugging:
  https://github.com/homeassistant-ai/ha-mcp

## Releases for HACS

HACS can install from the default branch, but proper versions are shown from
GitHub Releases. For each release:

1. Update `custom_components/solar_amortisation/manifest.json` with the new
   `version`.
2. Update `CHANGELOG.md`.
3. Commit the change.
4. Create an annotated tag matching the manifest version, for example:

```bash
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin main
git push origin v0.1.0
```

5. Create a GitHub Release from that tag and paste the relevant changelog
   section into the release notes.

HACS presents the latest GitHub Releases as selectable versions. If no GitHub
Releases exist, HACS uses the repository default branch.

## Home Assistant Integration Checklist

Use this checklist when setup, config flow, or entity loading fails.

### File Structure

- The folder name must match the manifest domain exactly:
  `custom_components/solar_amortisation`.
- `manifest.json` and `__init__.py` are required.
- `config_flow.py` is required when `manifest.json` has `"config_flow": true`.
- Custom brand assets live in `custom_components/solar_amortisation/brand/`.

### Manifest

- Custom integrations must define `version`.
- `domain` must match the integration folder name.
- `integration_type` should be set explicitly. This integration uses `helper`.
- `iot_class` should describe the integration behavior. This integration uses
  `calculated`.

### Config Flow

- Keep the initial flow schema simple and renderable by Home Assistant.
- Store normalized config values in the config entry where possible.
- Runtime setup must still tolerate older or manually edited entry data.
- Do not validate live entity state in the config flow. Missing entities should
  not prevent the entry from being created.

### Setup Entry

- `async_setup_entry` should not fail just because source entities are currently
  unavailable.
- Initial coordinator refresh should produce valid in-memory data or a clear
  `setup_issue`, instead of raising for normal unavailable states.
- Platform forwarding should use `Platform.SENSOR` inside Home Assistant runtime
  code.

### Sensors

- Sensor properties must return data from memory only.
- Invalid `device_class` and `state_class` combinations can raise exceptions in
  newer Home Assistant versions.
- Daily historical values are exposed as measurement-style chart sensors, not as
  energy dashboard source meters.
- Add `has_entity_name = True` for modern entity naming behavior.

### Diagnostics

- Keep diagnostics free of secrets.
- Expose normalized entry data, current setup issue, and latest accounting
  record to make setup problems debuggable from the Home Assistant UI.
