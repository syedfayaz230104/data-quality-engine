import os
import json
import csv
from typing import List, Dict, Any, Tuple
from ..engine.schema_validator import SchemaValidator
from ..engine.models import QuarantinedRecord

class IngestionManager:
    """Handles raw data ingestion from JSON/CSV files and performs preliminary schema validation."""

    def __init__(self, run_id: str):
        self.run_id = run_id

    def load_dataset_file(self, file_path: str, dataset_name: str) -> Tuple[List[Dict[str, Any]], List[QuarantinedRecord]]:
        """
        Loads records from a file (JSON or CSV) and validates basic schema structure.
        Malformed records are isolated into QuarantinedRecords.
        """
        if not os.path.exists(file_path):
            return [], []

        raw_records = []
        schema_quarantine = []

        if file_path.endswith(".json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        raw_records = data
                    elif isinstance(data, dict):
                        raw_records = [data]
            except Exception as e:
                # Entire file malformed
                schema_quarantine.append(QuarantinedRecord(
                    quarantine_id=f"QUAR_{self.run_id[:8]}_{dataset_name}_FILE_ERROR",
                    run_id=self.run_id,
                    source_dataset=dataset_name,
                    source_record_key="FILE_LEVEL",
                    rule_id="SCHEMA_JSON_PARSE_ERROR",
                    rule_name="malformed_json_file",
                    severity="CRITICAL",
                    failure_reason=f"Failed to parse JSON file: {str(e)}",
                    raw_record={"raw_file": file_path}
                ))
                return [], schema_quarantine

        elif file_path.endswith(".csv"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        raw_records.append(row)
            except Exception as e:
                schema_quarantine.append(QuarantinedRecord(
                    quarantine_id=f"QUAR_{self.run_id[:8]}_{dataset_name}_FILE_ERROR",
                    run_id=self.run_id,
                    source_dataset=dataset_name,
                    source_record_key="FILE_LEVEL",
                    rule_id="SCHEMA_CSV_PARSE_ERROR",
                    rule_name="malformed_csv_file",
                    severity="CRITICAL",
                    failure_reason=f"Failed to parse CSV file: {str(e)}",
                    raw_record={"raw_file": file_path}
                ))
                return [], schema_quarantine

        # Schema structural check
        key_map = {
            "customers": "customer_id",
            "products": "product_id",
            "orders": "order_id",
            "order_items": "item_id"
        }
        pk_col = key_map.get(dataset_name, f"{dataset_name[:-1]}_id")

        valid_records = []
        for idx, rec in enumerate(raw_records):
            is_valid, errors = SchemaValidator.validate_record(dataset_name, rec)
            pk = rec.get(pk_col) or rec.get("id") or str(idx)
            if not is_valid:
                schema_quarantine.append(QuarantinedRecord(
                    quarantine_id=f"QUAR_{self.run_id[:8]}_{dataset_name}_{pk}",
                    run_id=self.run_id,
                    source_dataset=dataset_name,
                    source_record_key=str(pk),
                    rule_id="SCHEMA_STRUCTURAL_INVALID",
                    rule_name="schema_structure_mismatch",
                    severity="ERROR",
                    failure_reason="; ".join(errors),
                    raw_record=rec
                ))
            else:
                valid_records.append(rec)

        return valid_records, schema_quarantine
