"""
Factor Expression Validator for QuantBot
Validates Qlib factor expressions for syntax and safety.
Educational Notes:
- Uses Qlib's D.features() method for validation instead of reinventing the wheel
- Provides user-friendly error messages and suggestions
- Follows the service layer pattern for clean architecture
"""

import logging
from typing import Dict, List, Optional, Any
from enum import Enum
from qlib.log import get_module_logger

logger = get_module_logger(__name__)


class ValidationStatus(str, Enum):
    """Validation result status enumeration"""

    VALID = "valid"
    INVALID_SYNTAX = "invalid_syntax"
    INVALID_OPERATOR = "invalid_operator"
    INVALID_FIELD = "invalid_field"
    UNKNOWN_ERROR = "unknown_error"


from dataclasses import dataclass


@dataclass
class ValidationResult:
    """
    Validation result data class

    Educational Notes:
    - Uses dataclass for clean data structure
    - Provides detailed error information for debugging
    - Includes suggestions for common errors
    """

    status: ValidationStatus
    message: str
    suggestion: Optional[str] = None
    error_details: Optional[str] = None
