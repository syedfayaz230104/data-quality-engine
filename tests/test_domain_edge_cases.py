import os
import json
import pytest
from datetime import datetime, timezone, timedelta
from src.pipeline.pipeline_runner import PipelineRunner
from src.utils.database import DatabaseManager

def test_pipeline_domain_edge_cases(temp_dir, sample_valid_data):
    # Valid customer and products
    with open(os.path.join(temp_dir, "customers.json"), "w", encoding="utf-8") as f:
        json.dump(sample_valid_data["customers"], f)

    # Edge 1: Product with negative price
    products = list(sample_valid_data["products"])
    products.append({
        "product_id": "PROD_NEG_PRICE",
        "name": "Negative Price Item",
        "category": "ELECTRONICS",
        "unit_price": -10.00, # Range failure!
        "stock_quantity": 5,
        "is_active": True,
        "created_at": "2026-01-10T12:00:00Z"
    })
    with open(os.path.join(temp_dir, "products.json"), "w", encoding="utf-8") as f:
        json.dump(products, f)

    # Edge 2: Future dated order (Freshness failure!)
    future_date = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
    orders = [
        {
            "order_id": "ORD_FUTURE_DATE",
            "customer_id": "CUST_001",
            "order_date": future_date,
            "status": "CONFIRMED",
            "total_amount": 50.0,
            "payment_method": "CREDIT_CARD",
            "created_at": future_date
        },
        sample_valid_data["orders"][0]
    ]
    with open(os.path.join(temp_dir, "orders.json"), "w", encoding="utf-8") as f:
        json.dump(orders, f)

    # Edge 3: Order Item Math Inconsistency (quantity * unit_price != line_total)
    # Edge 4: Order Item Quantity == 0 (Range failure!)
    items = [
        {
            "item_id": "ITEM_MATH_FAIL",
            "order_id": "ORD_001",
            "product_id": "PROD_001",
            "quantity": 2,
            "unit_price": 29.99,
            "line_total": 999.99, # Mathematical discrepancy!
            "created_at": "2026-02-01T14:20:00Z"
        },
        {
            "item_id": "ITEM_ZERO_QTY",
            "order_id": "ORD_001",
            "product_id": "PROD_001",
            "quantity": 0, # Min allowed is 1
            "unit_price": 29.99,
            "line_total": 0.0,
            "created_at": "2026-02-01T14:20:00Z"
        }
    ]
    with open(os.path.join(temp_dir, "order_items.json"), "w", encoding="utf-8") as f:
        json.dump(items, f)

    db_path = os.path.join(temp_dir, "test_edge_cases.duckdb")
    db_mgr = DatabaseManager(db_path)
    runner = PipelineRunner(
        config_path="config/pipeline_config.yaml",
        rules_path="config/dq_rules.yaml",
        db_manager=db_mgr
    )

    metrics = runner.run(input_dir=temp_dir, run_id="TEST_EDGE_CASES")

    # Check products
    assert metrics.quarantine_counts["products"] == 1
    assert "PROD_NEG_PRICE" in [r[0] for r in db_mgr.fetch_all("SELECT source_record_key FROM quarantined_records WHERE source_dataset='products'")]

    # Check orders freshness
    assert metrics.quarantine_counts["orders"] == 1
    assert "ORD_FUTURE_DATE" in [r[0] for r in db_mgr.fetch_all("SELECT source_record_key FROM quarantined_records WHERE source_dataset='orders'")]

    # Check order items
    assert metrics.quarantine_counts["order_items"] == 2
    item_quars = [r[0] for r in db_mgr.fetch_all("SELECT source_record_key FROM quarantined_records WHERE source_dataset='order_items'")]
    assert "ITEM_MATH_FAIL" in item_quars
    assert "ITEM_ZERO_QTY" in item_quars
