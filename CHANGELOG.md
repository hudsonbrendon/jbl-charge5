# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed

- Tooling refresh for Home Assistant 2026.10 / Python 3.14: `uv` with PEP 735
  dependency groups and a committed `uv.lock`, PEP 639 license metadata,
  `py.typed`, ruff `select = ["ALL"]`, strict mypy on the library,
  `pytest-cov`/`pytest-timeout`, and a uv-based tests workflow.
- `jbl_charge5.__version__` now comes from the installed package metadata.
- Integration: platforms use `AddConfigEntryEntitiesCallback`, declare
  `PARALLEL_UPDATES`, and the coordinator receives its config entry explicitly.
- Integration: `quality_scale.yaml`, `icons.json` (entity icons by state),
  diagnostics download (addresses redacted), and `loggers` in the manifest.
- HACS minimum Home Assistant raised to 2025.6.0 (required by the new
  platform callback type).
- GitHub release is created automatically when the manifest version changes.

### Removed

- Unused vendored `custom_components/jbl_charge5/tokens.py`.
