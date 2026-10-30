import os
import json
import pytest
from src.pipeline.pipeline_runner import PipelineRunner
from src.utils.database import DatabaseManager

def test_pipeline_malformed_syntax_and_types(temp_dir, sample_valid_data):
    # Setup valid customers, products, orders
    with open(os.path.join(temp_dir, "customers.json"), "w", encoding="utf-8") as f:
        json.dump(sample_valid_data["customers"], f)

    with open(os.path.join(temp_dir, "products.json"), "w", encoding="utf-8") as f:
        json.dump(sample_valid_data["products"], f)

    with open(os.path.join(temp_dir, "orders.json"), "w", encoding="utf-8") as f:
        json.dump(sample_valid_data["orders"], f)

    # Ingest malformed order_items:
    # 1. quantity is string "NOT_A_NUMBER" instead of integer
    # 2. invalid timestamp format
    bad_items = [
        {
            "item_id": "ITEM_BAD_TYPE",
            "order_id": "ORD_001",
            "product_id": "PROD_001",
            "quantity": "INVALID_QUANTITY_STR",
            "unit_price": 29.99,
            "line_total": 29.99,
            "created_at": "2026-02-01T14:20:00Z"
        },
        {
            "item_id": "ITEM_BAD_TIMESTAMP",
            "order_id": "ORD_001",
            "product_id": "PROD_001",
            "quantity": 1,
            "unit_price": 29.99,
            "line_total": 29.99,
            "created_at": "BOGUS_TIME_FORMAT"
        }
    ]
    with open(os.path.join(temp_dir, "order_items.json"), "w", encoding="utf-8") as f:
        json.dump(bad_items, f)

    db_path = os.path.join(temp_dir, "test_malformed.duckdb")
    db_mgr = DatabaseManager(db_path)
    runner = PipelineRunner(
        config_path="config/pipeline_config.yaml",
        rules_path="config/dq_rules.yaml",
        db_manager=db_mgr
    )

    metrics = runner.run(input_dir=temp_dir, run_id="TEST_MALFORMED")

    assert metrics.quarantine_counts["order_items"] == 2
    assert metrics.target_counts["order_items"] == 0

    # Ensure quarantine table has root cause details
    quarantines = db_mgr.fetch_all("""
        SELECT source_record_key, rule_id, failure_reason FROM quarantined_records
        WHERE source_dataset = 'order_items'
    """)
    assert len(quarantines) == 2
    keys = [q[0] for q in quarantines]
    assert "ITEM_BAD_TYPE" in keys
    assert "ITEM_BAD_TIMESTAMP" in keys
