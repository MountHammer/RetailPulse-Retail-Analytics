# RetailPulse Design Notes

## Architecture

Synthetic CSV producer → raw landing files → Pandas schema/business-rule validation → clean and quarantine CSV outputs → DuckDB dimensional warehouse → SQL analytics CSV reports.

## Grain and dimensional choices

The fact table grain is one row per order item. This preserves product-level detail and supports sales analysis by customer, product, order and order date. The four dimensions are customer, product, order and date. The fact stores quantity, unit price, discount percentage, gross amount, discount amount and net amount.

Integer surrogate keys decouple fact joins from source business identifiers. Customer, product and order keys are assigned deterministically from sorted distinct IDs; date keys use YYYYMMDD. This makes a rebuild over the same source snapshot reproducible. Because keys are regenerated from the current snapshot, inserting a new business ID that sorts before existing IDs can shift integer keys. This is acceptable for the current full-refresh demonstration, but a persistent key registry would be preferable for incremental production loads.

## Full refresh, idempotency and recovery

The warehouse loader uses a DuckDB transaction and drops/recreates the dimensional tables before loading them. Re-running the same validated input therefore replaces the warehouse contents instead of appending duplicate facts. If a load fails before commit, the transaction is rolled back. Re-running the pipeline from the data-generation step is the supported retry strategy.

This is a full-refresh design, not an incremental CDC pipeline. Backfills are performed by regenerating or replacing the relevant source snapshot and rerunning the pipeline. Late-arriving events are included when present in the next full snapshot; there is no separate late-arrival correction process.

## Data quality and traceability

Validation checks source schemas, required identifiers, duplicate keys, referential integrity, numeric ranges and gross/net amount calculations. Rejected rows are written to quarantine with a pipe-delimited list of rejection codes and a source row number. The quality report distinguishes rejected row counts from reason counts: one row can contribute more than one rejection reason, so reason totals can exceed the number of unique rejected rows.

## Operational visibility

Use `scripts/run_pipeline.py` to execute the pipeline in sequence and write a run record containing a UUID run ID, UTC start/end timestamps, step durations, source/valid/rejected/warehouse row counts, reconciliation results, total elapsed seconds and final status. The record is appended to `reports/pipeline_runs.jsonl`. A failed step is recorded with its failure reason and causes a non-zero process exit.

## Performance measurement and optimization

The pipeline runner records wall-clock duration for generation, quality validation, warehouse initialization/loading and analytics. It also records the total runtime for the selected dataset size. The first reasonable optimization is to avoid repeatedly materializing large intermediate Pandas DataFrames: for larger-than-memory datasets, move validation/transformation to DuckDB SQL or process source files in chunks. For the current 100,000-row demonstration, Pandas provides a simple and readable implementation.

## Limitations and next steps

- No slowly changing dimensions; customer/product attribute changes overwrite on the next full refresh.
- No incremental ingestion, CDC, or persistent surrogate-key registry.
- The generator produces synthetic data; it is not a production source connector.
- The runner provides local JSONL run history, not a centralized scheduler/monitoring service.
- Add schema-version handling, late-arriving dimension policies, and incremental merge logic if the workload grows.
