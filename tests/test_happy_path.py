import os
import json
import pytest
from src.pipeline.pipeline_runner import PipelineRunner
from src.utils.database import DatabaseManager

def test_pipeline_happy_path(temp_dir, sample_valid_data):
    # Setup input files
    for name, data in sample_valid_data.items():
        with open(os.path.join(temp_dir, f"{name}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f)

    db_path = os.path.join(temp_dir, "test_warehouse.duckdb")
    db_mgr = DatabaseManager(db_path)
    runner = PipelineRunner(
        config_path="config/pipeline_config.yaml",
        rules_path="config/dq_rules.yaml",
        db_manager=db_mgr
    )

    metrics = runner.run(input_dir=temp_dir, run_id="TEST_HAPPY_PATH")

    assert metrics.status == "SUCCESS"
    assert metrics.total_quarantined_rows == 0
    assert metrics.total_target_rows == 7
    assert metrics.total_input_rows == 7

    # Verify rows in target DuckDB
    assert db_mgr.fetch_one("SELECT COUNT(*) FROM customers")[0] == 2
    assert db_mgr.fetch_one("SELECT COUNT(*) FROM products")[0] == 2
    assert db_mgr.fetch_one("SELECT COUNT(*) FROM orders")[0] == 1
    assert db_mgr.fetch_one("SELECT COUNT(*) FROM order_items")[0] == 2
    assert db_mgr.fetch_one("SELECT COUNT(*) FROM quarantined_records")[0] == 0

    # Verify audit tables populated
    run_entry = db_mgr.fetch_one("SELECT status, target_row_count FROM pipeline_runs WHERE run_id = 'TEST_HAPPY_PATH'")
    assert run_entry[0] == "SUCCESS"
    assert run_entry[1] == 7
