import os
import pytest
import tempfile
import yaml
from src.utils.database import DatabaseManager
from src.pipeline.pipeline_runner import PipelineRunner
from src.engine.dq_engine import DataQualityEngine

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d

@pytest.fixture
def in_memory_db():
    db = DatabaseManager(":memory:")
    yield db
    db.close()

@pytest.fixture
def sample_valid_data():
    customers = [
        {
            "customer_id": "CUST_001",
            "first_name": "Alice",
            "last_name": "Smith",
            "email": "alice@example.com",
            "country_code": "US",
            "status": "ACTIVE",
            "created_at": "2026-01-15T08:00:00Z"
        },
        {
            "customer_id": "CUST_002",
            "first_name": "Bob",
            "last_name": "Jones",
            "email": "bob@example.com",
            "country_code": "CA",
            "status": "ACTIVE",
            "created_at": "2026-01-16T09:30:00Z"
        }
    ]

    products = [
        {
            "product_id": "PROD_001",
            "name": "Wireless Mouse",
            "category": "ELECTRONICS",
            "unit_price": 29.99,
            "stock_quantity": 100,
            "is_active": True,
            "created_at": "2026-01-10T12:00:00Z"
        },
        {
            "product_id": "PROD_002",
            "name": "Mechanical Keyboard",
            "category": "ELECTRONICS",
            "unit_price": 99.50,
            "stock_quantity": 50,
            "is_active": True,
            "created_at": "2026-01-10T12:00:00Z"
        }
    ]

    orders = [
        {
            "order_id": "ORD_001",
            "customer_id": "CUST_001",
            "order_date": "2026-02-01T14:20:00Z",
            "status": "CONFIRMED",
            "total_amount": 129.49,
            "payment_method": "CREDIT_CARD",
            "created_at": "2026-02-01T14:20:00Z"
        }
    ]

    order_items = [
        {
            "item_id": "ITEM_001",
            "order_id": "ORD_001",
            "product_id": "PROD_001",
            "quantity": 1,
            "unit_price": 29.99,
            "line_total": 29.99,
            "created_at": "2026-02-01T14:20:00Z"
        },
        {
            "item_id": "ITEM_002",
            "order_id": "ORD_001",
            "product_id": "PROD_002",
            "quantity": 1,
            "unit_price": 99.50,
            "line_total": 99.50,
            "created_at": "2026-02-01T14:20:00Z"
        }
    ]

    return {
        "customers": customers,
        "products": products,
        "orders": orders,
        "order_items": order_items
    }
