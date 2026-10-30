import os
import json
import pytest
from src.pipeline.pipeline_runner import PipelineRunner
from src.utils.database import DatabaseManager

def test_pipeline_duplicate_primary_keys(temp_dir, sample_valid_data):
    # Customer dataset with duplicate customer_id
    dup_customers = list(sample_valid_data["customers"])
    dup_record = dict(sample_valid_data["customers"][0])
    dup_record["email"] = "duplicate_person@test.com"
    dup_customers.append(dup_record)

    with open(os.path.join(temp_dir, "customers.json"), "w", encoding="utf-8") as f:
        json.dump(dup_customers, f)

    db_path = os.path.join(temp_dir, "test_duplicates.duckdb")
    db_mgr = DatabaseManager(db_path)
    runner = PipelineRunner(
        config_path="config/pipeline_config.yaml",
        rules_path="config/dq_rules.yaml",
        db_manager=db_mgr
    )

    metrics = runner.run(input_dir=temp_dir, run_id="TEST_DUPLICATES")

    assert metrics.quarantine_counts["customers"] == 1
    assert metrics.target_counts["customers"] == 2 # 2 unique customers survive

    # Verify duplicate is recorded in quarantine
    quar_entry = db_mgr.fetch_one("""
        SELECT rule_name, failure_reason FROM quarantined_records
        WHERE source_dataset = 'customers' AND source_record_key = 'CUST_001'
    """)
    assert quar_entry is not None
    assert "Duplicate key detected" in quar_entry[1]
