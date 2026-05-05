# Internal Maintainer Notes

This directory contains maintainer-facing documentation that should not be part
of the user-facing README.

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
