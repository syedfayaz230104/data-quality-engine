import os
import json
import pytest
from src.pipeline.pipeline_runner import PipelineRunner
from src.utils.database import DatabaseManager

def test_rule_severity_warning_vs_error(temp_dir, sample_valid_data):
    # CUST_RANGE_01 has severity "WARNING" for country_code length outside 2-3 chars
    # We will provide a customer with country_code "UNITED_STATES" (length > 3)
    # It should pass into target customers table, but produce a WARNING in dq_audit_log and warning_count = 1
    warning_customer = {
        "customer_id": "CUST_WARN_01",
        "first_name": "Warn",
        "last_name": "User",
        "email": "warn@test.com",
        "country_code": "UNITED_STATES", # Warning trigger!
        "status": "ACTIVE",
        "created_at": "2026-01-15T08:00:00Z"
    }

    with open(os.path.join(temp_dir, "customers.json"), "w", encoding="utf-8") as f:
        json.dump([warning_customer], f)

    db_path = os.path.join(temp_dir, "test_severities.duckdb")
    db_mgr = DatabaseManager(db_path)
    runner = PipelineRunner(
        config_path="config/pipeline_config.yaml",
        rules_path="config/dq_rules.yaml",
        db_manager=db_mgr
    )

    metrics = runner.run(input_dir=temp_dir, run_id="TEST_SEVERITY")

    # Record should pass into target because severity was WARNING, not ERROR
    assert metrics.target_counts["customers"] == 1
    assert metrics.quarantine_counts.get("customers", 0) == 0

    # Operational metrics should show warning recorded
    assert metrics.warning_count >= 1

    # Verify audit log recorded warning status
    audit_row = db_mgr.fetch_one("""
        SELECT severity, status, records_failed FROM dq_audit_log
        WHERE dataset = 'customers' AND rule_id = 'CUST_RANGE_01'
    """)
    assert audit_row is not None
    assert audit_row[0] == "WARNING"
    assert audit_row[1] == "WARNING"
    assert audit_row[2] == 1
