import os
import sys
import argparse
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.pipeline.pipeline_runner import PipelineRunner
from src.utils.database import DatabaseManager

def main():
    parser = argparse.ArgumentParser(description="Execute the Data Quality & Ingestion Pipeline.")
    parser.add_argument("--input-dir", default="data/input/small", help="Path to input data directory")
    parser.add_argument("--config", default="config/pipeline_config.yaml", help="Path to pipeline configuration YAML")
    parser.add_argument("--rules", default="config/dq_rules.yaml", help="Path to data quality rules YAML")
    parser.add_argument("--db-path", default="data/target/warehouse.duckdb", help="Path to DuckDB target database")
    parser.add_argument("--run-id", default=None, help="Explicit run ID (optional)")

    args = parser.parse_args()

    print("=================================================================")
    print("      DATA QUALITY & INGESTION ENGINE - PIPELINE EXECUTION       ")
    print("=================================================================")
    print(f"Input Directory:  {args.input_dir}")
    print(f"Pipeline Config:  {args.config}")
    print(f"DQ Rules Config:  {args.rules}")
    print(f"Target Database:  {args.db_path}")

    db_mgr = DatabaseManager(db_path=args.db_path)
    runner = PipelineRunner(config_path=args.config, rules_path=args.rules, db_manager=db_mgr)
    metrics = runner.run(input_dir=args.input_dir, run_id=args.run_id)

    print("\n-----------------------------------------------------------------")
    print("                     EXECUTION SUMMARY REPORT                    ")
    print("-----------------------------------------------------------------")
    print(f"Run ID:             {metrics.run_id}")
    print(f"Pipeline Status:    {metrics.status}")
    print(f"Duration:           {metrics.duration_seconds} seconds")
    print(f"Total Input Rows:   {metrics.total_input_rows}")
    print(f"Total Target Rows:  {metrics.total_target_rows}")
    print(f"Total Quarantined:  {metrics.total_quarantined_rows}")
    print(f"Warnings Logged:    {metrics.warning_count}")
    print(f"Errors Caught:      {metrics.error_count}")
    print("\nBreakdown by Dataset:")
    print(f"{'Dataset':<15} | {'Input':<8} | {'Target':<8} | {'Quarantine':<10}")
    print("-" * 50)
    for ds in ["customers", "products", "orders", "order_items"]:
        inp = metrics.input_counts.get(ds, 0)
        tgt = metrics.target_counts.get(ds, 0)
        quar = metrics.quarantine_counts.get(ds, 0)
        print(f"{ds:<15} | {inp:<8} | {tgt:<8} | {quar:<10}")

    print("=================================================================\n")

if __name__ == "__main__":
    main()
