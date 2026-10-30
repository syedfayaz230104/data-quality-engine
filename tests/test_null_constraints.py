import os
import json
import pytest
from src.pipeline.pipeline_runner import PipelineRunner
from src.utils.database import DatabaseManager

def test_pipeline_null_and_missing_required_fields(temp_dir, sample_valid_data):
    # Customers with null email and blank country_code
    bad_customers = [
        {
            "customer_id": "CUST_NULL_EMAIL",
            "first_name": "No",
            "last_name": "Email",
            "email": None,
            "country_code": "US",
            "status": "ACTIVE",
            "created_at": "2026-01-15T08:00:00Z"
        },
        {
            "customer_id": "CUST_BLANK_COUNTRY",
            "first_name": "Blank",
            "last_name": "Country",
            "email": "blank@test.com",
            "country_code": "   ",
            "status": "ACTIVE",
            "created_at": "2026-01-15T08:00:00Z"
        }
    ]

    with open(os.path.join(temp_dir, "customers.json"), "w", encoding="utf-8") as f:
        json.dump(bad_customers, f)

    db_path = os.path.join(temp_dir, "test_nulls.duckdb")
    db_mgr = DatabaseManager(db_path)
    runner = PipelineRunner(
        config_path="config/pipeline_config.yaml",
        rules_path="config/dq_rules.yaml",
        db_manager=db_mgr
    )

    metrics = runner.run(input_dir=temp_dir, run_id="TEST_NULLS")

    assert metrics.quarantine_counts["customers"] == 2
    assert metrics.target_counts["customers"] == 0

    # Verify both records landed in quarantine
    quars = db_mgr.fetch_all("SELECT source_record_key FROM quarantined_records WHERE source_dataset = 'customers'")
    quar_keys = [q[0] for q in quars]
    assert "CUST_NULL_EMAIL" in quar_keys
    assert "CUST_BLANK_COUNTRY" in quar_keys
