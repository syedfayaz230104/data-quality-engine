import uuid
import os
import yaml
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from ..utils.logger import setup_logger
from ..utils.database import DatabaseManager
from ..utils.metrics import PipelineMetrics
from ..engine.dq_engine import DataQualityEngine
from .ingestion import IngestionManager
from .transformation import DataTransformer
from .quarantine import QuarantineManager
from .publisher import TargetPublisher

class PipelineRunner:
    """Orchestrates end-to-end ingestion, DQ validation, rejection quarantine, and target publishing."""

    def __init__(
        self,
        config_path: str = "config/pipeline_config.yaml",
        rules_path: str = "config/dq_rules.yaml",
        db_manager: Optional[DatabaseManager] = None
    ):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)["pipeline"]

        self.rules_path = rules_path
        self.logger = setup_logger("PipelineRunner", log_level=self.config.get("log_level", "INFO"))
        self.db = db_manager or DatabaseManager(self.config.get("target_db_path", ":memory:"))
        self.quarantine_mgr = QuarantineManager(
            self.db,
            self.config.get("quarantine_path", "data/quarantine")
        )
        self.publisher = TargetPublisher(self.db)

    def run(self, input_dir: str, run_id: Optional[str] = None) -> PipelineMetrics:
        """Executes a full pipeline run over the provided input directory."""
        run_id = run_id or f"RUN_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:6]}"
        self.logger.info(f"========== Starting Pipeline Run: {run_id} ==========")

        metrics = PipelineMetrics(run_id=run_id, pipeline_name=self.config.get("name", "data_quality_pipeline"))
        dq_engine = DataQualityEngine(self.rules_path, run_id=run_id)
        ingestion = IngestionManager(run_id=run_id)
        transformer = DataTransformer(run_id=run_id)

        try:
            # 1. Ingest Customers
            cust_file = self._find_file(input_dir, "customers")
            raw_cust, cust_schema_quar = ingestion.load_dataset_file(cust_file, "customers")
            metrics.input_counts["customers"] = len(raw_cust) + len(cust_schema_quar)

            # Evaluate DQ on Customers
            valid_cust, cust_dq_quar, cust_evals = dq_engine.evaluate_dataset("customers", raw_cust)
            all_cust_quar = cust_schema_quar + cust_dq_quar
            metrics.quarantine_counts["customers"] = len(all_cust_quar)
            self.quarantine_mgr.persist_quarantined_records(run_id, all_cust_quar)

            transformed_cust = transformer.transform_customers(valid_cust)
            cust_pub_count = self.publisher.publish_customers(transformed_cust)
            metrics.target_counts["customers"] = cust_pub_count

            # 2. Ingest Products
            prod_file = self._find_file(input_dir, "products")
            raw_prod, prod_schema_quar = ingestion.load_dataset_file(prod_file, "products")
            metrics.input_counts["products"] = len(raw_prod) + len(prod_schema_quar)

            valid_prod, prod_dq_quar, prod_evals = dq_engine.evaluate_dataset("products", raw_prod)
            all_prod_quar = prod_schema_quar + prod_dq_quar
            metrics.quarantine_counts["products"] = len(all_prod_quar)
            self.quarantine_mgr.persist_quarantined_records(run_id, all_prod_quar)

            transformed_prod = transformer.transform_products(valid_prod)
            prod_pub_count = self.publisher.publish_products(transformed_prod)
            metrics.target_counts["products"] = prod_pub_count

            # Map valid parent keys for referential integrity
            # Include both current batch and existing DB records to support incremental backfills
            existing_cust_ids = set(row[0] for row in self.db.fetch_all("SELECT customer_id FROM customers"))
            existing_prod_ids = set(row[0] for row in self.db.fetch_all("SELECT product_id FROM products"))
            parent_keys_map = {
                "customers": existing_cust_ids,
                "products": existing_prod_ids
            }

            # 3. Ingest Orders
            orders_file = self._find_file(input_dir, "orders")
            raw_orders, orders_schema_quar = ingestion.load_dataset_file(orders_file, "orders")
            metrics.input_counts["orders"] = len(raw_orders) + len(orders_schema_quar)

            valid_orders, orders_dq_quar, orders_evals = dq_engine.evaluate_dataset("orders", raw_orders, parent_keys_map)
            all_orders_quar = orders_schema_quar + orders_dq_quar
            metrics.quarantine_counts["orders"] = len(all_orders_quar)
            self.quarantine_mgr.persist_quarantined_records(run_id, all_orders_quar)

            transformed_orders = transformer.transform_orders(valid_orders)
            orders_pub_count = self.publisher.publish_orders(transformed_orders)
            metrics.target_counts["orders"] = orders_pub_count

            # Update parent keys with valid orders for order_items check
            existing_order_ids = set(row[0] for row in self.db.fetch_all("SELECT order_id FROM orders"))
            parent_keys_map["orders"] = existing_order_ids

            # 4. Ingest Order Items
            items_file = self._find_file(input_dir, "order_items")
            raw_items, items_schema_quar = ingestion.load_dataset_file(items_file, "order_items")
            metrics.input_counts["order_items"] = len(raw_items) + len(items_schema_quar)

            valid_items, items_dq_quar, items_evals = dq_engine.evaluate_dataset("order_items", raw_items, parent_keys_map)
            all_items_quar = items_schema_quar + items_dq_quar
            metrics.quarantine_counts["order_items"] = len(all_items_quar)
            self.quarantine_mgr.persist_quarantined_records(run_id, all_items_quar)

            transformed_items = transformer.transform_order_items(valid_items)
            items_pub_count = self.publisher.publish_order_items(transformed_items)
            metrics.target_counts["order_items"] = items_pub_count

            # 5. Persist DQ Audit Logs
            all_evals = cust_evals + prod_evals + orders_evals + items_evals
            self._persist_dq_audit(all_evals)

            # Compute Warnings and Errors
            metrics.warning_count = sum(1 for e in all_evals if e.status == "WARNING")
            metrics.error_count = sum(e.records_failed for e in all_evals if e.severity in ["ERROR", "CRITICAL"])
            metrics.error_count += len(cust_schema_quar) + len(prod_schema_quar) + len(orders_schema_quar) + len(items_schema_quar)

            metrics.mark_completed(
                status="SUCCESS" if metrics.total_quarantined_rows == 0 else "PARTIAL_SUCCESS",
                error_summary=f"Processed with {metrics.total_quarantined_rows} quarantined records." if metrics.total_quarantined_rows > 0 else None
            )

        except Exception as e:
            self.logger.error(f"Pipeline run failed with error: {str(e)}", exc_info=True)
            metrics.mark_completed(status="FAILED", error_summary=str(e))

        # Record Operational Run Metrics in Database
        self._persist_run_metrics(metrics)

        self.logger.info(
            f"Run Completed: {run_id} | Status: {metrics.status} | "
            f"Input: {metrics.total_input_rows} | Target: {metrics.total_target_rows} | "
            f"Quarantined: {metrics.total_quarantined_rows} | Duration: {metrics.duration_seconds}s"
        )
        return metrics

    def _find_file(self, directory: str, dataset_name: str) -> str:
        for ext in [".json", ".csv"]:
            path = os.path.join(directory, f"{dataset_name}{ext}")
            if os.path.exists(path):
                return path
        return os.path.join(directory, f"{dataset_name}.json")

    def _persist_dq_audit(self, evals):
        if not evals:
            return
        conn = self.db.get_connection()
        chunk_size = 500
        for i in range(0, len(evals), chunk_size):
            chunk = evals[i:i + chunk_size]
            tuples = [
                (
                    e.eval_id,
                    e.run_id,
                    e.dataset,
                    e.rule_id,
                    e.rule_name,
                    e.rule_type,
                    e.severity,
                    e.records_evaluated,
                    e.records_passed,
                    e.records_failed,
                    e.pass_rate,
                    e.status,
                    e.evaluated_at.isoformat()
                )
                for e in chunk
            ]
            placeholders = ", ".join(["(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"] * len(tuples))
            flat_params = [v for row in tuples for v in row]
            sql = f"""
                INSERT OR REPLACE INTO dq_audit_log (
                    eval_id, run_id, dataset, rule_id, rule_name, rule_type,
                    severity, records_evaluated, records_passed, records_failed,
                    pass_rate, status, evaluated_at
                ) VALUES {placeholders}
            """
            conn.execute(sql, flat_params)

    def _persist_run_metrics(self, m: PipelineMetrics):
        sql = """
            INSERT OR REPLACE INTO pipeline_runs (
                run_id, pipeline_name, start_time, end_time, status,
                input_row_count, target_row_count, quarantine_row_count,
                warning_count, error_count, duration_seconds, error_summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.db.execute(sql, [
            m.run_id,
            m.pipeline_name,
            m.start_time.isoformat(),
            m.end_time.isoformat() if m.end_time else None,
            m.status,
            m.total_input_rows,
            m.total_target_rows,
            m.total_quarantined_rows,
            m.warning_count,
            m.error_count,
            m.duration_seconds,
            m.error_summary
        ])
