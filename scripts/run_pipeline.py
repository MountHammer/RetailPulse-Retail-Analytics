"""Run the complete RetailPulse pipeline and persist run-level metrics.

Example:
    python scripts/run_pipeline.py
    python scripts/run_pipeline.py --order-items 200000 --seed 42
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
REPORT_DIR = BASE_DIR / "reports"
RUN_LOG = REPORT_DIR / "pipeline_runs.jsonl"
DB_PATH = BASE_DIR / "database" / "retailpulse.duckdb"
QUALITY_REPORT = REPORT_DIR / "quality_report.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run_step(name: str, command: list[str], metrics: dict) -> None:
    started = time.perf_counter()
    print(f"\n{'=' * 12} {name} {'=' * 12}", flush=True)
    subprocess.run(command, cwd=BASE_DIR, check=True)
    metrics[name] = round(time.perf_counter() - started, 3)


def collect_counts(record: dict) -> None:
    if QUALITY_REPORT.exists():
        quality = json.loads(QUALITY_REPORT.read_text(encoding="utf-8"))
        record["source_row_counts"] = quality.get("total_source_records", {})
        record["valid_row_counts"] = quality.get("valid_records", {})
        record["rejected_row_counts"] = quality.get("rejected_records", {})
        record["quality_status"] = quality.get("status")

    if DB_PATH.exists():
        with duckdb.connect(str(DB_PATH), read_only=True) as con:
            tables = ["dim_customer", "dim_product", "dim_order", "dim_date", "fact_sales"]
            record["warehouse_row_counts"] = {
                table: con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in tables
            }
            fact = con.execute(
                "SELECT COUNT(*), COALESCE(SUM(net_amount), 0), "
                "COALESCE(SUM(quantity), 0) FROM fact_sales"
            ).fetchone()
            record["warehouse_totals"] = {
                "fact_sales_rows": fact[0],
                "net_revenue": round(float(fact[1]), 2),
                "units_sold": int(fact[2]),
            }

            clean_items_path = BASE_DIR / "data" / "processed" / "clean_order_items.csv"
            if clean_items_path.exists():
                clean_items = pd.read_csv(clean_items_path)
                source_revenue = round(float(clean_items["net_amount"].sum()), 2)
                source_units = int(clean_items["quantity"].sum())
                record["reconciliation"] = {
                    "valid_source_order_items": int(len(clean_items)),
                    "fact_sales_rows": int(fact[0]),
                    "row_count_match": int(len(clean_items)) == int(fact[0]),
                    "valid_source_net_revenue": source_revenue,
                    "warehouse_net_revenue": round(float(fact[1]), 2),
                    "net_revenue_match": abs(source_revenue - float(fact[1])) <= 0.01,
                    "valid_source_units": source_units,
                    "warehouse_units_sold": int(fact[2]),
                    "units_match": source_units == int(fact[2]),
                }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the full RetailPulse pipeline.")
    parser.add_argument("--order-items", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--anomaly-rate", type=float, default=0.02)
    args = parser.parse_args()

    if args.order_items < 1:
        parser.error("--order-items must be greater than zero")
    if not 0 <= args.anomaly_rate <= 0.20:
        parser.error("--anomaly-rate must be between 0 and 0.20")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "run_id": str(uuid.uuid4()),
        "started_at_utc": utc_now(),
        "parameters": vars(args),
        "status": "RUNNING",
        "step_durations_seconds": {},
        "source_files": [
            "data/raw/customers.csv",
            "data/raw/products.csv",
            "data/raw/orders.csv",
            "data/raw/order_items.csv",
        ],
    }
    overall_start = time.perf_counter()
    python = sys.executable

    commands = [
        ("generate_data", [python, "scripts/generate_data.py", "--order-items", str(args.order_items), "--seed", str(args.seed), "--anomaly-rate", str(args.anomaly_rate)]),
        ("quality_validation", [python, "-m", "src.quality"]),
        ("warehouse_initialization", [python, "scripts/init_warehouse.py"]),
        ("warehouse_load", [python, "scripts/load_warehouse.py"]),
        ("analytics", [python, "scripts/run_analytics.py"]),
    ]

    try:
        for name, command in commands:
            run_step(name, command, record["step_durations_seconds"])
        collect_counts(record)
        reconciliation = record.get("reconciliation", {})
        if reconciliation and not all(
            reconciliation.get(key, False)
            for key in ("row_count_match", "net_revenue_match", "units_match")
        ):
            raise RuntimeError("Source-to-warehouse reconciliation failed.")
        record["status"] = "SUCCESS"
        return_code = 0
    except Exception as exc:
        record["status"] = "FAILED"
        record["failure_reason"] = f"{type(exc).__name__}: {exc}"
        return_code = 1
    finally:
        record["ended_at_utc"] = utc_now()
        record["total_duration_seconds"] = round(time.perf_counter() - overall_start, 3)
        with RUN_LOG.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, default=str) + "\n")
        print("\nPipeline run record:")
        print(json.dumps(record, indent=2, default=str))
        print(f"\nRun history appended to: {RUN_LOG}")

    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
