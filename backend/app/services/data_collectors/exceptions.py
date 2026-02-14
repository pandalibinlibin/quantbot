"""
Custom exceptions for data collectors module.
This module defines specific exceptions for data collection operations,
providing clear error handling and debugging information.

Educational Notes:
- All exceptions inherit from standard Python exceptions
- Provides specific error types for different failure scenarios
- Includes detailed error messages for debugging
- Follows Python exception handling best practices
"""

from typing import Optional, Any


class DataCollectionError(Exception):
    """
    Base exception for all data collection related errors.

    This is the parent class for all data collection exceptions,
    providing common functionality and error handling patterns.

    Educational Notes:
    - Inherits from Python's built-in Exception class
    - Serves as base class for more specific exceptions
    - Provides consistent error message formatting
    """

    def __init__(self, message: str, details: Optional[dict] = None):
        """
        Initialize DataCollectionError.

        Args:
            message: Human-readable error description
            details: Optional dictionary with additional error context
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        """Return formatted error message with details."""
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} (Details: {details_str})"

        return self.message


class CollectorNotFoundError(DataCollectionError):
    """
    Exception raised when a requested data collector is not found.

    This exception is raised when trying to access a collector that
    hasn't been registered or doesn't exist in the system.

    Educational Notes:
    - Specific exception for collector registration issues
    - Helps identify configuration or setup problems
    - Provides clear feedback for missing collectors
    """

    def __init__(
        self, collector_name: str, available_collectors: Optional[list] = None
    ):
        """
        Initialize CollectorNotFoundError.

        Args:
            collector_name: Name of the collector that was not found
            available_collectors: List of available collector names
        """
        message = f"Data collector '{collector_name}' not found"
        details = {"requested_collector": collector_name}

        if available_collectors:
            details["available_collectors"] = available_collectors
            message += f". Available collectors: {', '.join(available_collectors)}"

        super().__init__(message, details)
        self.collector_name = collector_name
        self.available_collectors = available_collectors or []


class DataSourceError(DataCollectionError):
    """
    Exception raised when data source access fails.

    This exception covers issues with external data sources.
    such as network failures, API errors, or authentication problems.

    Educational Notes:
    - Handles external data source connectivity issues
    - Provides context for network and API failures
    - Helps distinguish between local and remote errors
    """

    def __init__(
        self, source: str, operation: str, original_error: Optional[Exception] = None
    ):
        """
        Initialize DataSourceError.

        Args:
            source: Name or URL of the data source
            operation: Operation that failed (e.g., 'fetch', 'connect')
            original_error: Original exception that caused this error
        """
        message = f"Data source '{source}' failed during '{operation}'"
        details = {"source": source, "operation": operation}

        if original_error:
            details["original_error"] = str(original_error)
            details["error_type"] = type(original_error).__name__
            message += f": {original_error}"

        super().__init__(message, details)
        self.source = source
        self.operation = operation
        self.original_error = original_error


class DataValidationError(DataCollectionError):
    """
    Exception raised when collected data fails validation.

    This exception is raised when data doesn't meet expected
    quality standards, format requirements, or business rules.

    Educational Notes:
    - Handles data quality and format validation issues
    - Provides specific information about validation failures
    - Helps maintain data integrity in the system
    """

    def __init__(
        self,
        validation_type: str,
        expected: Any,
        actual: Any,
        field: Optional[str] = None,
    ):
        """
        Initialize DataValidationError.

        Args:
            validation_type: Type of validation that failed
            expected: Expected value or format
            actual: Actual value that failed validation
            field: Optional field name that failed validation
        """
        field_info = f" in field '{field}'" if field else ""
        message = f"Data validation failed ({validation_type}){field_info}: expected {expected}, got {actual}"

        details = {
            "validation_type": validation_type,
            "expected": expected,
            "actual": actual,
        }

        if field:
            details["field"] = field

        super().__init__(message, details)
        self.validation_type = validation_type
        self.expected = expected
        self.actual = actual
        self.field = field


class CollectorConfigurationError(DataCollectionError):
    """
    Exception raised when collector configuration is invalid.

    This exception handles issues with collector setup,
    missing parameters, or invalid configuration values.

    Educational Notes:
    - Handles collector setup and configuration issues
    - Provides clear feedback on configuration problems
    - Helps users fix setup issues quickly
    """

    def __init__(
        self, collector_name: str, config_issue: str, suggestion: Optional[str] = None
    ):
        """
        Initialize CollectorConfigurationError.

        Args:
            collector_name: Name of the collector with configuration issues
            config_issue: Description of the configuration problem
            suggestion: Optional suggestion for fixing the issue
        """
        message = f"Configuration error in collector '{collector_name}': {config_issue}"
        details = {"collector": collector_name, "issue": config_issue}

        if suggestion:
            details["suggestion"] = suggestion
            message += f". Suggestion: {suggestion}"

        super().__init__(message, details)
        self.collector_name = collector_name
        self.config_issue = config_issue
        self.suggestion = suggestion
