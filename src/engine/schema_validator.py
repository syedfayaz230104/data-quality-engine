import re
from datetime import datetime
from typing import Dict, Any, List, Tuple

EXPECTED_SCHEMAS = {
    "customers": {
        "required": ["customer_id", "email", "country_code", "created_at"],
        "types": {
            "customer_id": str,
            "email": str,
            "first_name": (str, type(None)),
            "last_name": (str, type(None)),
            "country_code": str,
            "status": str,
            "created_at": str
        }
    },
    "products": {
        "required": ["product_id", "name", "category", "unit_price", "stock_quantity"],
        "types": {
            "product_id": str,
            "name": str,
            "category": str,
            "unit_price": (int, float),
            "stock_quantity": int,
            "is_active": (bool, type(None)),
            "created_at": str
        }
    },
    "orders": {
        "required": ["order_id", "customer_id", "order_date", "status", "total_amount"],
        "types": {
            "order_id": str,
            "customer_id": str,
            "order_date": str,
            "status": str,
            "total_amount": (int, float),
            "payment_method": (str, type(None)),
            "created_at": str
        }
    },
    "order_items": {
        "required": ["item_id", "order_id", "product_id", "quantity", "unit_price", "line_total"],
        "types": {
            "item_id": str,
            "order_id": str,
            "product_id": str,
            "quantity": int,
            "unit_price": (int, float),
            "line_total": (int, float),
            "created_at": str
        }
    }
}

class SchemaValidator:
    """Validates structural schemas, data types, and required fields."""

    @staticmethod
    def validate_record(dataset: str, record: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validates a single record against dataset schema.
        Returns (is_valid, list_of_errors).
        """
        if dataset not in EXPECTED_SCHEMAS:
            return True, []

        schema = EXPECTED_SCHEMAS[dataset]
        errors = []

        # 1. Required fields check
        for req in schema["required"]:
            if req not in record or record[req] is None or (isinstance(record[req], str) and record[req].strip() == ""):
                errors.append(f"Missing or null required field: '{req}'")

        # 2. Type validation
        for field_name, expected_type in schema["types"].items():
            if field_name in record and record[field_name] is not None:
                val = record[field_name]
                if not isinstance(val, expected_type):
                    errors.append(
                        f"Field '{field_name}' type mismatch: expected {expected_type}, got {type(val).__name__}"
                    )

        # 3. ISO Timestamp format validation for timestamp fields
        for time_col in ["created_at", "order_date"]:
            if time_col in record and record[time_col] is not None and isinstance(record[time_col], str):
                try:
                    # Clean ISO format parsing
                    val = record[time_col].replace("Z", "+00:00")
                    datetime.fromisoformat(val)
                except ValueError:
                    errors.append(f"Invalid ISO-8601 timestamp in field '{time_col}': '{record[time_col]}'")

        return len(errors) == 0, errors
