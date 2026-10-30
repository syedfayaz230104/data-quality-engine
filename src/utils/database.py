import duckdb
import os
from typing import Optional, List, Dict, Any

class DatabaseManager:
    """Manages DuckDB warehouse connections, schema migrations, and transactional updates."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.conn = duckdb.connect(database=self.db_path)
        self._initialize_schema()

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        return self.conn

    def _initialize_schema(self):
        """Initializes tables for target models, operational metrics, and quarantine audit logs."""
        # 1. Operational Run Audit Table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                run_id VARCHAR PRIMARY KEY,
                pipeline_name VARCHAR NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                status VARCHAR NOT NULL,
                input_row_count BIGINT DEFAULT 0,
                target_row_count BIGINT DEFAULT 0,
                quarantine_row_count BIGINT DEFAULT 0,
                warning_count BIGINT DEFAULT 0,
                error_count BIGINT DEFAULT 0,
                duration_seconds DOUBLE DEFAULT 0.0,
                error_summary VARCHAR
            );
        """)

        # 2. Granular Data Quality Evaluation Audit Table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS dq_audit_log (
                eval_id VARCHAR PRIMARY KEY,
                run_id VARCHAR NOT NULL,
                dataset VARCHAR NOT NULL,
                rule_id VARCHAR NOT NULL,
                rule_name VARCHAR NOT NULL,
                rule_type VARCHAR NOT NULL,
                severity VARCHAR NOT NULL,
                records_evaluated BIGINT NOT NULL,
                records_passed BIGINT NOT NULL,
                records_failed BIGINT NOT NULL,
                pass_rate DOUBLE NOT NULL,
                status VARCHAR NOT NULL,
                evaluated_at TIMESTAMP NOT NULL
            );
        """)

        # 3. Quarantined Records Table (Traceability)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS quarantined_records (
                quarantine_id VARCHAR PRIMARY KEY,
                run_id VARCHAR NOT NULL,
                source_dataset VARCHAR NOT NULL,
                source_record_key VARCHAR,
                rule_id VARCHAR NOT NULL,
                rule_name VARCHAR NOT NULL,
                severity VARCHAR NOT NULL,
                failure_reason VARCHAR NOT NULL,
                raw_record VARCHAR NOT NULL,
                quarantined_at TIMESTAMP NOT NULL
            );
        """)

        # 4. Target Warehouse Business Tables
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                customer_id VARCHAR PRIMARY KEY,
                first_name VARCHAR,
                last_name VARCHAR,
                email VARCHAR NOT NULL,
                country_code VARCHAR NOT NULL,
                status VARCHAR NOT NULL,
                created_at TIMESTAMP NOT NULL,
                ingested_at TIMESTAMP NOT NULL,
                run_id VARCHAR NOT NULL
            );
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                product_id VARCHAR PRIMARY KEY,
                name VARCHAR NOT NULL,
                category VARCHAR NOT NULL,
                unit_price DOUBLE NOT NULL,
                stock_quantity INTEGER NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL,
                ingested_at TIMESTAMP NOT NULL,
                run_id VARCHAR NOT NULL
            );
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id VARCHAR PRIMARY KEY,
                customer_id VARCHAR NOT NULL,
                order_date TIMESTAMP NOT NULL,
                status VARCHAR NOT NULL,
                total_amount DOUBLE NOT NULL,
                payment_method VARCHAR,
                created_at TIMESTAMP NOT NULL,
                ingested_at TIMESTAMP NOT NULL,
                run_id VARCHAR NOT NULL
            );
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                item_id VARCHAR PRIMARY KEY,
                order_id VARCHAR NOT NULL,
                product_id VARCHAR NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price DOUBLE NOT NULL,
                line_total DOUBLE NOT NULL,
                created_at TIMESTAMP NOT NULL,
                ingested_at TIMESTAMP NOT NULL,
                run_id VARCHAR NOT NULL
            );
        """)

    def execute(self, query: str, params: Optional[List[Any]] = None):
        if params:
            return self.conn.execute(query, params)
        return self.conn.execute(query)

    def fetch_df(self, query: str, params: Optional[List[Any]] = None):
        if params:
            return self.conn.execute(query, params).fetchdf()
        return self.conn.execute(query).fetchdf()

    def fetch_all(self, query: str, params: Optional[List[Any]] = None):
        if params:
            return self.conn.execute(query, params).fetchall()
        return self.conn.execute(query).fetchall()

    def fetch_one(self, query: str, params: Optional[List[Any]] = None):
        if params:
            return self.conn.execute(query, params).fetchone()
        return self.conn.execute(query).fetchone()

    def close(self):
        self.conn.close()
