# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-01-XX

### Added

- Initial release
- Core data models: `Person`, `Activity`, `Event`, `SettlementTransfer`
- Three split strategies: EQUAL, WEIGHTED, FIXED_SHARES
- Minimal cash flow algorithm for computing transfers
- Multi-payer activity support
- Money handling with `Decimal` and banker's rounding
- Remainder distribution using least-absolute-balance-first
- JSON and CSV I/O functionality
- Comprehensive test suite with ≥95% coverage
- Full type hints with mypy strict checking
- Documentation (README, DESIGN.md)
- CI workflow with GitHub Actions

### Features

- Compute net balances for all participants
- Generate minimal set of transfers to clear all balances
- Settlement summary with paid/owed/net for each person
- Deterministic output ordering
- Stable JSON serialization schema
- Custom exception hierarchy for clear error messages

