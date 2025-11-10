"""Custom exceptions for tripsettle package."""


class TripsettleError(Exception):
    """Base exception for all tripsettle errors."""

    pass


class ValidationError(TripsettleError):
    """Raised when validation fails (e.g., invalid amounts, missing participants)."""

    pass


class RoundingError(TripsettleError):
    """Raised when rounding operations fail or totals don't sum correctly."""

    pass


class StrategyError(TripsettleError):
    """Raised when split strategy configuration is invalid."""

    pass

