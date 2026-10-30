from typing import List, Dict, Any
from ..utils.database import DatabaseManager

class TargetPublisher:
    """Publishes validated data to target tables idempotently using chunked multi-value UPSERT semantics."""

    def __init__(self, db_manager: DatabaseManager, chunk_size: int = 1000):
        self.db = db_manager
        self.chunk_size = chunk_size

    def _bulk_upsert(self, table_name: str, columns: List[str], records: List[Dict[str, Any]], row_extractor) -> int:
        if not records:
            return 0

        conn = self.db.get_connection()
        col_list = ", ".join(columns)
        num_cols = len(columns)
        single_placeholder = f"({', '.join(['?'] * num_cols)})"

        for i in range(0, len(records), self.chunk_size):
            chunk = records[i:i + self.chunk_size]
            tuples = [row_extractor(r) for r in chunk]
            placeholders = ", ".join([single_placeholder] * len(tuples))
            flat_params = [val for row in tuples for val in row]
            sql = f"INSERT OR REPLACE INTO {table_name} ({col_list}) VALUES {placeholders}"
            conn.execute(sql, flat_params)

        return len(records)

    def publish_customers(self, records: List[Dict[str, Any]]) -> int:
        cols = [
            "customer_id", "first_name", "last_name", "email",
            "country_code", "status", "created_at", "ingested_at", "run_id"
        ]
        return self._bulk_upsert(
            "customers",
            cols,
            records,
            lambda r: (
                r["customer_id"],
                r.get("first_name"),
                r.get("last_name"),
                r["email"],
                r["country_code"],
                r["status"],
                r["created_at"],
                r["ingested_at"],
                r["run_id"]
            )
        )

    def publish_products(self, records: List[Dict[str, Any]]) -> int:
        cols = [
            "product_id", "name", "category", "unit_price",
            "stock_quantity", "is_active", "created_at", "ingested_at", "run_id"
        ]
        return self._bulk_upsert(
            "products",
            cols,
            records,
            lambda r: (
                r["product_id"],
                r["name"],
                r["category"],
                r["unit_price"],
                r["stock_quantity"],
                r.get("is_active", True),
                r["created_at"],
                r["ingested_at"],
                r["run_id"]
            )
        )

    def publish_orders(self, records: List[Dict[str, Any]]) -> int:
        cols = [
            "order_id", "customer_id", "order_date", "status",
            "total_amount", "payment_method", "created_at", "ingested_at", "run_id"
        ]
        return self._bulk_upsert(
            "orders",
            cols,
            records,
            lambda r: (
                r["order_id"],
                r["customer_id"],
                r["order_date"],
                r["status"],
                r["total_amount"],
                r.get("payment_method"),
                r["created_at"],
                r["ingested_at"],
                r["run_id"]
            )
        )

    def publish_order_items(self, records: List[Dict[str, Any]]) -> int:
        cols = [
            "item_id", "order_id", "product_id", "quantity",
            "unit_price", "line_total", "created_at", "ingested_at", "run_id"
        ]
        return self._bulk_upsert(
            "order_items",
            cols,
            records,
            lambda r: (
                r["item_id"],
                r["order_id"],
                r["product_id"],
                r["quantity"],
                r["unit_price"],
                r["line_total"],
                r["created_at"],
                r["ingested_at"],
                r["run_id"]
            )
        )
