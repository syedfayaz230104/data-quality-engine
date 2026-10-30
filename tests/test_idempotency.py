import os
import json
import pytest
from src.pipeline.pipeline_runner import PipelineRunner
from src.utils.database import DatabaseManager

def test_pipeline_rerun_idempotency(temp_dir, sample_valid_data):
    for name, data in sample_valid_data.items():
        with open(os.path.join(temp_dir, f"{name}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f)

    db_path = os.path.join(temp_dir, "test_idempotency.duckdb")
    db_mgr = DatabaseManager(db_path)
    runner = PipelineRunner(
        config_path="config/pipeline_config.yaml",
        rules_path="config/dq_rules.yaml",
        db_manager=db_mgr
    )

    # First Run
    metrics_run_1 = runner.run(input_dir=temp_dir, run_id="RUN_INITIAL")
    assert metrics_run_1.total_target_rows == 7

    cust_count_1 = db_mgr.fetch_one("SELECT COUNT(*) FROM customers")[0]
    prod_count_1 = db_mgr.fetch_one("SELECT COUNT(*) FROM products")[0]
    ord_count_1 = db_mgr.fetch_one("SELECT COUNT(*) FROM orders")[0]
    item_count_1 = db_mgr.fetch_one("SELECT COUNT(*) FROM order_items")[0]

    # Second Run (Identical input re-executed)
    metrics_run_2 = runner.run(input_dir=temp_dir, run_id="RUN_RETRY")
    assert metrics_run_2.total_target_rows == 7

    cust_count_2 = db_mgr.fetch_one("SELECT COUNT(*) FROM customers")[0]
    prod_count_2 = db_mgr.fetch_one("SELECT COUNT(*) FROM products")[0]
    ord_count_2 = db_mgr.fetch_one("SELECT COUNT(*) FROM orders")[0]
    item_count_2 = db_mgr.fetch_one("SELECT COUNT(*) FROM order_items")[0]

    # Target table counts must be invariant across reruns
    assert cust_count_1 == cust_count_2 == 2
    assert prod_count_1 == prod_count_2 == 2
    assert ord_count_1 == ord_count_2 == 1
    assert item_count_1 == item_count_2 == 2

    # Verify no duplicated primary keys in target tables
    assert db_mgr.fetch_one("SELECT COUNT(*) - COUNT(DISTINCT customer_id) FROM customers")[0] == 0
    assert db_mgr.fetch_one("SELECT COUNT(*) - COUNT(DISTINCT product_id) FROM products")[0] == 0
    assert db_mgr.fetch_one("SELECT COUNT(*) - COUNT(DISTINCT order_id) FROM orders")[0] == 0
    assert db_mgr.fetch_one("SELECT COUNT(*) - COUNT(DISTINCT item_id) FROM order_items")[0] == 0
