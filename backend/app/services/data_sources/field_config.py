"""
Standard Field Configuration for QuantBot Platform.
This module defines the standard field set that will be collected and stored
in Qlib format. All fields are passed to Qlib's dump_bin.py via --include_fields.

Educational Notes:
- Qlib requires minimum 6 fields: open, close, high, low, volume, factor
- Additional fields can be added via --include_fields parameter
- Fields are stored in .bin format and accessed via D.features()
- No custom DataProvider needed - Qlib handles everything

Design Philosophy:
- Configuration-based: Easy to extend without code changes
- Qlib-native: Leverage Qlib's built-in mechanism
- Flexible: Support both standard and custom fields
- Consistency: All data sources must provide the same field set
"""

from typing import List, Dict, Any


class QuantBotFieldConfig:
    """
    Standard field configuration for QuantBot platform.

    This configuration defines which fields will be collected from data sources
    and stored in Qlib format via dump_bin.py.

    All data collectors MUST provide these fields to ensure data source
    interchangeability. If a collector cannot provide a field, it must fill with
    NaN.

    Usage Example:
    ```python
    # Get all standard fields for data collection
    fields = QuantBotFieldConfig.get_all_fields()
    # Returns: ['open', 'high', 'low', 'close', 'volume', 'factor',
    #           'adj_close', 'vwap', 'amount', 'turnover']

    # Use in dump_bin.py command
    fields_arg = QuantBotFieldConfig.get_dump_bin_fields_arg()
    cmd = f"python scripts/dump.bin.py dump_all --include_fields {fields_arg}"
    ```

    Educational Notes:
    - These field names match CSV column names from data sources
    - Qlib will create .bin files for each field
    - Access via D.features() with $ prefix: D.features(fields=['$open', '$close'])
    """

    # ==================== CORE FIELDS ================================
    # Required by Qlib - MUST be present (Qlib documentation line 1903)

    CORE_FIELDS: Dict[str, str] = {
        "open": "Adjusted opening price",
        "high": "Adjusted highest price",
        "low": "Adjusted lowest price",
        "close": "Adjusted closing price",
        "volume": "Adjusted trading volume",
        "factor": "Adjusted factor (adjusted_price / original_price)",
    }

    # ==================== EXTENDED FIELDS ============================
    # Additional fields commonly used in quantitative analysis
    # All collectors MUST provide these to ensure consistency
    EXTENDED_FIELDS: Dict[str, str] = {
        "adj_close": "Forward-adjusted closing price (most commonly used)",
        "vwap": "Volume-weighted average price",
        "amount": "Trading amount (volume * price)",
        "turnover": "Turnover rate (volume / shares_outstanding)",
    }

    @classmethod
    def get_core_fields(cls) -> List[str]:
        """
        Get core fields required by Qlib.

        Returns:
            List of 6 core field names
        """
        return list(cls.CORE_FIELDS.keys())

    @classmethod
    def get_extended_fields(cls) -> List[str]:
        """
        Get extended fields for enhanced analysis.

        Returns:
            List of 4 extended field names
        """
        return list(cls.EXTENDED_FIELDS.keys())

    @classmethod
    def get_all_fields(cls) -> List[str]:
        """
        Get all fields (core + extended).

        This is the complete field list that ALL data collectors must provide.

        Returns:
            List of 10 field names
        """
        return cls.get_core_fields() + cls.get_extended_fields()

    @classmethod
    def get_field_description(cls, field: str) -> str:
        """
        Get description for a specific field.

        Args:
            field: Field name (without $ prefix)

        Returns:
            Field description string

        Raises:
            KeyError: If field is not defined
        """
        all_fields = {**cls.CORE_FIELDS, **cls.EXTENDED_FIELDS}

        if field not in all_fields:
            raise KeyError(
                f"Field '{field}' not defined in QuantBotFieldConfig. "
                f"Available fields: {list(all_fields.keys())}"
            )

        return all_fields[field]

    @classmethod
    def to_qlib_format(cls, fields: List[str]) -> List[str]:
        """
        Convert field names to Qlib format (with $ prefix).

        Args:
            fields: List of field names (without $ prefix)

        Returns:
            List of field names with $ prefix

        Example:
            >>> QuantBotFieldConfig.to_qlib_format(['open', 'close'])
            ['$open', '$close']
        """
        return [f"${field}" for field in fields]

    @classmethod
    def from_qlib_format(cls, fields: List[str]) -> List[str]:
        """
        Convert field names from Qlib format (remove $ prefix).

        Args:
            fields: List of field names (with $ prefix)

        Returns:
            List of field names without $ prefix

        Examples:
            >>> QuantBotFieldConfig.from_qlib_format(['$open', '$close'])
            ['open', 'close']
        """
        return [field.lstrip("$") for field in fields]

    @classmethod
    def get_dump_bin_fields_arg(cls) -> str:
        """
        Get the --include_fields argument value for dump_bin.py.

        Returns:
            Comma-separated field names string

        Examples:
            >>> QuantBotFieldConfig.get_dump_bin_fields_arg()
            'open,high,low,close,volume,factor,adj_close,vwap,amount,turnover'
        """
        return ",".join(cls.get_all_fields())

    @classmethod
    def validate_collector_compatibility(
        cls, collector_name: str, supported_fields: List[str]
    ) -> Dict[str, Any]:
        """
        Validate if a collector supports all required fields.

        This ensures all collectors provide the same field set for
        data source interchangeability.

        Args:
            collector_name: Name of the collector
            supported_fields: List of fields the collector can provide

        Returns:
            Validation result dictionary with keys:
            - is_fully_compatible: bool
            - coverage_percentage: float
            - supported_count: int
            - total_required: int
            - missing_fields: List[str]
            - warning: str or None
        """
        required = cls.get_all_fields()
        supported_set = set(supported_fields)
        required_set = set(required)

        missing = required_set - supported_set
        coverage = len(supported_set & required_set) / len(required_set) * 100

        result = {
            "collector": collector_name,
            "is_fully_compatible": len(missing) == 0,
            "coverage_percentage": coverage,
            "supported_count": len(supported_set & required_set),
            "total_required": len(required_set),
            "missing_fields": list(missing),
            "warning": None,
        }

        if missing:
            result["warning"] = (
                f"Collector '{collector_name}' cannot provide {len(missing)} fields: "
                f"{', '.join(missing)}. These fields will be NaN in the output data."
            )

        return result

    @classmethod
    def get_version(cls) -> str:
        """Get the version of this standard field set."""
        return "1.0"

    @classmethod
    def get_summary(cls) -> str:
        """
        Get a summary of the field configuration.

        Returns:
            Formatted summary string
        """
        summary = f"""
            QuantBot Field Configuration V{cls.get_version()}
            {'=' * 70}
            Core Fields (Required by Qlib - {len(cls.CORE_FIELDS)} fields):
            {chr(10).join(f'  - {k}: {v}' for k, v in cls.CORE_FIELDS.items())}
            Extended Fields ({len(cls.EXTENDED_FIELDS)} fields):
            {chr(10).join(f'  - {k}: {v}' for k, v in cls.EXTENDED_FIELDS.items())}
            Total Standard Fields: {len(cls.get_all_fields())}
            Usage in dump_bin.py:
            --include_fields {cls.get_dump_bin_fields_arg()}
            Usage in D.features():
            fields = {cls.to_qlib_format(cls.get_all_fields())}
            IMPORTANT: All data collectors MUST provide these {len(cls.get_all_fields())} fields
            to ensure data source interchangeability.
            {'=' * 70}
            """

        return summary.strip()


# Convenience constants for quick access
STANDARD_FIELDS = QuantBotFieldConfig.get_all_fields()
CORE_FIELDS = QuantBotFieldConfig.get_core_fields()
EXTENDED_FIELDS = QuantBotFieldConfig.get_extended_fields()
QLIB_STANDARD_FIELDS = QuantBotFieldConfig.to_qlib_format(STANDARD_FIELDS)
DUMP_BIN_FIELDS_ARG = QuantBotFieldConfig.get_dump_bin_fields_arg()
