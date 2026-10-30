import os
import json
from typing import List, Dict, Any
from ..engine.models import QuarantinedRecord
from ..utils.database import DatabaseManager

class QuarantineManager:
    """Manages rejection isolation, audit persistence, and line-level traceability for data quality failures."""

    def __init__(self, db_manager: DatabaseManager, quarantine_dir: str):
        self.db = db_manager
        self.quarantine_dir = quarantine_dir
        os.makedirs(self.quarantine_dir, exist_ok=True)

    def persist_quarantined_records(self, run_id: str, quarantined_records: List[QuarantinedRecord]):
        """Persists quarantined records to both DuckDB database and JSONL file."""
        if not quarantined_records:
            return

        # 1. Insert into DuckDB table using chunked multi-value batching
        conn = self.db.get_connection()
        chunk_size = 500
        for i in range(0, len(quarantined_records), chunk_size):
            chunk = quarantined_records[i:i + chunk_size]
            tuples = [
                (
                    q.quarantine_id,
                    q.run_id,
                    q.source_dataset,
                    q.source_record_key,
                    q.rule_id,
                    q.rule_name,
                    q.severity,
                    q.failure_reason,
                    json.dumps(q.raw_record),
                    q.quarantined_at.isoformat()
                )
                for q in chunk
            ]
            placeholders = ", ".join(["(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"] * len(tuples))
            flat_params = [v for row in tuples for v in row]
            sql = f"""
                INSERT OR REPLACE INTO quarantined_records (
                    quarantine_id, run_id, source_dataset, source_record_key,
                    rule_id, rule_name, severity, failure_reason, raw_record, quarantined_at
                ) VALUES {placeholders}
            """
            conn.execute(sql, flat_params)

        # 2. Append to JSONL audit file
        log_file = os.path.join(self.quarantine_dir, f"quarantine_{run_id}.jsonl")
        with open(log_file, "a", encoding="utf-8") as f:
            for q in quarantined_records:
                payload = {
                    "quarantine_id": q.quarantine_id,
                    "run_id": q.run_id,
                    "source_dataset": q.source_dataset,
                    "source_record_key": q.source_record_key,
                    "rule_id": q.rule_id,
                    "rule_name": q.rule_name,
                    "severity": q.severity,
                    "failure_reason": q.failure_reason,
                    "raw_record": q.raw_record,
                    "quarantined_at": q.quarantined_at.isoformat()
                }
                f.write(json.dumps(payload) + "\n")
