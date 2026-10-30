from datetime import datetime, timezone
from typing import List, Dict, Any

class DataTransformer:
    """Applies deterministic transformations, data standardization, and lineage enrichment."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.ingested_at = datetime.now(timezone.utc).isoformat()

    def transform_customers(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        transformed = []
        for r in records:
            item = dict(r)
            item["customer_id"] = str(item["customer_id"]).strip()
            item["email"] = str(item["email"]).strip().lower()
            item["country_code"] = str(item["country_code"]).strip().upper()
            item["status"] = str(item.get("status", "ACTIVE")).strip().upper()
            item["first_name"] = str(item["first_name"]).strip() if item.get("first_name") else None
            item["last_name"] = str(item["last_name"]).strip() if item.get("last_name") else None
            item["created_at"] = self._normalize_timestamp(item.get("created_at"))
            item["ingested_at"] = self.ingested_at
            item["run_id"] = self.run_id
            transformed.append(item)
        return transformed

    def transform_products(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        transformed = []
        for r in records:
            item = dict(r)
            item["product_id"] = str(item["product_id"]).strip()
            item["name"] = str(item["name"]).strip()
            item["category"] = str(item["category"]).strip().upper()
            item["unit_price"] = round(float(item["unit_price"]), 2)
            item["stock_quantity"] = int(item["stock_quantity"])
            item["is_active"] = bool(item.get("is_active", True))
            item["created_at"] = self._normalize_timestamp(item.get("created_at"))
            item["ingested_at"] = self.ingested_at
            item["run_id"] = self.run_id
            transformed.append(item)
        return transformed

    def transform_orders(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        transformed = []
        for r in records:
            item = dict(r)
            item["order_id"] = str(item["order_id"]).strip()
            item["customer_id"] = str(item["customer_id"]).strip()
            item["order_date"] = self._normalize_timestamp(item.get("order_date"))
            item["status"] = str(item.get("status", "PENDING")).strip().upper()
            item["total_amount"] = round(float(item["total_amount"]), 2)
            item["payment_method"] = str(item["payment_method"]).strip().upper() if item.get("payment_method") else None
            item["created_at"] = self._normalize_timestamp(item.get("created_at"))
            item["ingested_at"] = self.ingested_at
            item["run_id"] = self.run_id
            transformed.append(item)
        return transformed

    def transform_order_items(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        transformed = []
        for r in records:
            item = dict(r)
            item["item_id"] = str(item["item_id"]).strip()
            item["order_id"] = str(item["order_id"]).strip()
            item["product_id"] = str(item["product_id"]).strip()
            item["quantity"] = int(item["quantity"])
            item["unit_price"] = round(float(item["unit_price"]), 2)
            item["line_total"] = round(float(item["line_total"]), 2)
            item["created_at"] = self._normalize_timestamp(item.get("created_at"))
            item["ingested_at"] = self.ingested_at
            item["run_id"] = self.run_id
            transformed.append(item)
        return transformed

    def _normalize_timestamp(self, ts: Any) -> str:
        if not ts:
            return datetime.now(timezone.utc).isoformat()
        try:
            val = str(ts).replace("Z", "+00:00")
            dt = datetime.fromisoformat(val)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except Exception:
            return str(ts)
