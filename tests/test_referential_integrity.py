import os
import json
import pytest
from src.pipeline.pipeline_runner import PipelineRunner
from src.utils.database import DatabaseManager

def test_pipeline_referential_integrity(temp_dir, sample_valid_data):
    # Valid customer CUST_001
    with open(os.path.join(temp_dir, "customers.json"), "w", encoding="utf-8") as f:
        json.dump([sample_valid_data["customers"][0]], f)

    # Valid product PROD_001
    with open(os.path.join(temp_dir, "products.json"), "w", encoding="utf-8") as f:
        json.dump([sample_valid_data["products"][0]], f)

    # Ingest orders:
    # 1. Valid order ORD_VALID referencing CUST_001
    # 2. Invalid order ORD_ORPHAN referencing non-existent CUST_9999
    orders = [
        {
            "order_id": "ORD_VALID",
            "customer_id": "CUST_001",
            "order_date": "2026-02-01T14:20:00Z",
            "status": "CONFIRMED",
            "total_amount": 100.0,
            "payment_method": "CREDIT_CARD",
            "created_at": "2026-02-01T14:20:00Z"
        },
        {
            "order_id": "ORD_ORPHAN",
            "customer_id": "CUST_9999", # Does not exist!
            "order_date": "2026-02-01T14:20:00Z",
            "status": "CONFIRMED",
            "total_amount": 50.0,
            "payment_method": "CREDIT_CARD",
            "created_at": "2026-02-01T14:20:00Z"
        }
    ]
    with open(os.path.join(temp_dir, "orders.json"), "w", encoding="utf-8") as f:
        json.dump(orders, f)

    # Ingest order_items:
    # 1. Valid item referencing ORD_VALID and PROD_001
    # 2. Invalid item referencing non-existent PROD_GHOST
    order_items = [
        {
            "item_id": "ITEM_VALID",
            "order_id": "ORD_VALID",
            "product_id": "PROD_001",
            "quantity": 1,
            "unit_price": 29.99,
            "line_total": 29.99,
            "created_at": "2026-02-01T14:20:00Z"
        },
        {
            "item_id": "ITEM_BAD_PRODUCT",
            "order_id": "ORD_VALID",
            "product_id": "PROD_GHOST", # Does not exist!
            "quantity": 1,
            "unit_price": 10.00,
            "line_total": 10.00,
            "created_at": "2026-02-01T14:20:00Z"
        }
    ]
    with open(os.path.join(temp_dir, "order_items.json"), "w", encoding="utf-8") as f:
        json.dump(order_items, f)

    db_path = os.path.join(temp_dir, "test_ri.duckdb")
    db_mgr = DatabaseManager(db_path)
    runner = PipelineRunner(
        config_path="config/pipeline_config.yaml",
        rules_path="config/dq_rules.yaml",
        db_manager=db_mgr
    )

    metrics = runner.run(input_dir=temp_dir, run_id="TEST_RI")

    # Verify orders
    assert metrics.target_counts["orders"] == 1
    assert metrics.quarantine_counts["orders"] == 1

    # Verify items
    assert metrics.target_counts["order_items"] == 1
    assert metrics.quarantine_counts["order_items"] == 1

    # Check reason in quarantine
    orphan_order = db_mgr.fetch_one("""
        SELECT failure_reason FROM quarantined_records
        WHERE source_dataset = 'orders' AND source_record_key = 'ORD_ORPHAN'
    """)
    assert "Referential integrity failure: customer_id='CUST_9999' does not exist in customers" in orphan_order[0]

    orphan_item = db_mgr.fetch_one("""
        SELECT failure_reason FROM quarantined_records
        WHERE source_dataset = 'order_items' AND source_record_key = 'ITEM_BAD_PRODUCT'
    """)
    assert "Referential integrity failure: product_id='PROD_GHOST' does not exist in products" in orphan_item[0]
