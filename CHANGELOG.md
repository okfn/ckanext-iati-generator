# Changelog

## 0.5.3 - 2026-09-16

### Added

- CKAN 2.12 compatibility and CI coverage.
- Configuration declarations for the extension settings.
- CSRF tokens in IATI generation forms.

### Changed

- Query CKAN 2.12 dataset extras through the new `Package.extras` JSON column.
- Use SQLAlchemy 2 `Session.get()` for IATI file lookups.
