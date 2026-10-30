import os
import json
import pytest
from src.pipeline.pipeline_runner import PipelineRunner
from src.utils.database import DatabaseManager

def test_pipeline_empty_batch(temp_dir):
    # Empty directory with empty json files
    for name in ["customers", "products", "orders", "order_items"]:
        with open(os.path.join(temp_dir, f"{name}.json"), "w", encoding="utf-8") as f:
            json.dump([], f)

    db_path = os.path.join(temp_dir, "test_empty.duckdb")
    db_mgr = DatabaseManager(db_path)
    runner = PipelineRunner(
        config_path="config/pipeline_config.yaml",
        rules_path="config/dq_rules.yaml",
        db_manager=db_mgr
    )

    metrics = runner.run(input_dir=temp_dir, run_id="TEST_EMPTY")

    assert metrics.status == "SUCCESS"
    assert metrics.total_input_rows == 0
    assert metrics.total_target_rows == 0
    assert metrics.total_quarantined_rows == 0

def test_pipeline_missing_files_graceful(temp_dir):
    # Completely empty folder, no json files present
    db_path = os.path.join(temp_dir, "test_missing.duckdb")
    db_mgr = DatabaseManager(db_path)
    runner = PipelineRunner(
        config_path="config/pipeline_config.yaml",
        rules_path="config/dq_rules.yaml",
        db_manager=db_mgr
    )

    metrics = runner.run(input_dir=temp_dir, run_id="TEST_MISSING")

    assert metrics.status == "SUCCESS"
    assert metrics.total_input_rows == 0
    assert metrics.total_target_rows == 0
