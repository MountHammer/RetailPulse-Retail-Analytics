# RetailPulse – End-to-End Retail Data Engineering Pipeline

## Project Overview

RetailPulse is an end-to-end data engineering project built around a small but realistic retail data environment. It generates synthetic source data, checks it for common quality issues, separates rejected records, loads the trusted data into a dimensional warehouse, and produces reports that can be used to explore sales performance.

I built this project to practise the parts of a data pipeline that matter beyond simply getting data from one file into another: validation, referential integrity, repeatable warehouse loads, reconciliation, testing, and visibility into each run.

## Technology Stack

- Python 3.12
- Pandas
- NumPy
- DuckDB
- Pytest
- Faker
- SQL

## Pipeline Architecture

```text
Synthetic Data Generation
          |
          v
      Raw CSV Files
          |
          v
   Data Quality Validation
          |
      +---+---+
      |       |
      v       v
  Clean Data  Quarantine
      |
      v
Dimensional Data Warehouse
      |
      v
     DuckDB
      |
      v
   SQL Analytics
      |
      v
  CSV Reports
```

The pipeline can be run as individual steps or through the one-command runner. The runner also records operational details and checks that the warehouse agrees with the validated source data.

## Dataset Summary

| Dataset | Source Records |
|---|---:|
| Customers | 5,000 |
| Products | 500 |
| Orders | 40,000 |
| Order Items | 100,000 |

### Data Quality Results

- Valid order items: 98,002
- Rejected order items: 1,998
- Order-item data trust score: 98.0%
- Rejected records are separated into quarantine files with reason codes.

The sample deliberately includes invalid records so the validation and quarantine process can be demonstrated. A `REVIEW_REQUIRED` quality status means that records were rejected for review; it does not mean the pipeline itself failed.

## Data Warehouse Design

The dimensional warehouse contains four dimensions and one sales fact table:

- `dim_customer`
- `dim_product`
- `dim_order`
- `dim_date`
- `fact_sales`

The grain of `fact_sales` is one row per accepted order item. Surrogate keys are generated deterministically so that identical source inputs produce stable keys across repeat loads.

### Warehouse Load Results

| Table | Records |
|---|---:|
| dim_customer | 5,000 |
| dim_product | 500 |
| dim_order | 40,000 |
| dim_date | 731 |
| fact_sales | 98,002 |

Foreign-key validation completed successfully.

## Business Analytics

The pipeline generates six analytical reports:

1. Monthly Revenue
2. Category Performance
3. Top 10 Customers
4. Average Order Value
5. Top 10 Products
6. Customer Segment Sales

All six reports are exported as CSV files into `reports/analytics/`.

## Project Structure

```text
RetailPulse-Retail-Analytics/
├── data/
│   ├── raw/
│   ├── processed/
│   ├── quarantine/
│   └── sample/
├── database/
├── docs/
│   ├── data_dictionary.md
│   └── design_notes.md
├── logs/
├── reports/
│   ├── analytics/
│   ├── pipeline_runs.jsonl
│   └── quality_report.json
├── scripts/
│   ├── generate_data.py
│   ├── init_warehouse.py
│   ├── load_warehouse.py
│   ├── run_analytics.py
│   ├── run_pipeline.py
│   └── verify_idempotency.py
├── sql/
│   ├── analytics/
│   └── schema.sql
├── src/
│   └── quality.py
├── tests/
│   ├── test_pipeline.py
│   └── test_quality.py
├── requirements.txt
└── README.md
```

Generated data and database files are created when the pipeline runs; the sample inputs and documentation are included to help reviewers understand the project.

## Installation and Setup

Clone the repository and navigate to its directory:

```powershell
git clone https://github.com/MountHammer/RetailPulse-Retail-Analytics.git
cd RetailPulse-Retail-Analytics
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

## Running the Pipeline

For a complete run, use the pipeline runner from the repository root:

```powershell
python scripts/run_pipeline.py
```

The default run generates 100,000 order items with seed 42 and a 2% anomaly rate. You can change those settings:

```powershell
python scripts/run_pipeline.py --order-items 200000 --seed 42 --anomaly-rate 0.02
```

The runner executes data generation, quality validation, warehouse initialization, warehouse loading, and analytics in sequence. If a stage fails, the run stops and returns a non-zero exit code.

If you want to run the stages individually, use:

```powershell
python scripts/generate_data.py
python -m src.quality
python scripts/init_warehouse.py
python scripts/load_warehouse.py
python scripts/run_analytics.py
```

## Reliability and Verification

### Idempotency check

To check that loading the same processed inputs twice produces the same warehouse results and stable surrogate keys, run:

```powershell
python scripts/verify_idempotency.py
```

The verification compares the two warehouse snapshots, including row counts, net revenue, units sold, and the customer, product, order, and fact surrogate keys.

### Reconciliation and run history

The pipeline runner compares the validated order-item row count, net revenue, and total quantity against the loaded `fact_sales` table. All three comparisons must match for the run to be recorded as successful. Foreign-key orphan checks are also performed during warehouse loading.

Each run appends a JSON record to `reports/pipeline_runs.jsonl`. The record includes a run ID, UTC timestamps, parameters, step durations, source/valid/rejected counts, warehouse row counts, reconciliation results, status, and failure details when applicable.

The repository includes a run-history file as execution evidence. Running the pipeline again appends another record to that file.

## Testing

Run the automated tests with:

```powershell
python -m pytest -v
```

The test suite covers data-quality rules and edge cases such as invalid prices, missing or malformed values, invalid references, duplicate order-item IDs, amount mismatches, empty batches, and missing required columns. It also includes a pipeline failure-handling test to check that a failed stage is recorded and returns a non-zero result.

The latest local test run completed with **14 tests passing**.

## Data Dictionary and Design Decisions

See [docs/data_dictionary.md](docs/data_dictionary.md) for source and warehouse columns, data types, keys, nullability, measures, and fact grain.

See [docs/design_notes.md](docs/design_notes.md) for architecture trade-offs, full-refresh behaviour, deterministic surrogate keys, retry/backfill considerations, limitations, and optimization opportunities.

## Sample Data

A compact, hand-inspectable synthetic input example is available in `data/sample/`. The default generator is the reproducible way to create the larger workload.

## Generated Outputs

Raw, processed, and quarantined CSV files, the DuckDB database, and analytics exports are generated by the pipeline and are not required to be committed. The source code, sample inputs, documentation, quality summary, and pipeline run history provide reviewers with a way to understand and reproduce the work.
