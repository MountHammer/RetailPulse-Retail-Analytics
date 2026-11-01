# RetailPulse – End-to-End Retail Data Engineering Pipeline

## Project Overview

RetailPulse is an end-to-end data engineering project that simulates a retail data environment, validates source data, builds a dimensional data warehouse, and generates analytical reports.

The pipeline demonstrates data ingestion, data quality management, referential integrity, dimensional modelling, SQL analytics, and automated testing.

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
- Rejected records are separated into quarantine files.

## Data Warehouse Design

The dimensional warehouse contains five tables:

- `dim_customer`
- `dim_product`
- `dim_order`
- `dim_date`
- `fact_sales`

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
│   └── quarantine/
├── database/
├── logs/
├── reports/
│   └── analytics/
├── scripts/
│   ├── generate_data.py
│   ├── init_warehouse.py
│   ├── load_warehouse.py
│   └── run_analytics.py
├── sql/
│   ├── analytics/
│   └── schema.sql
├── src/
│   └── quality.py
├── tests/
│   └── test_quality.py
├── requirements.txt
└── README.md
```

## Installation and Setup

Clone the repository and navigate to its directory.

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the Pipeline

Run the following commands from the project root in order:

```powershell
python scripts/generate_data.py
python -m src.quality
python scripts/init_warehouse.py
python scripts/load_warehouse.py
python scripts/run_analytics.py
```

Run automated tests:

```powershell
python -m pytest -v
```

## Testing

The current test suite contains eight passing tests covering:

- Valid product acceptance
- Invalid product price rejection
- Invalid customer reference rejection
- Valid order-item acceptance
- Negative quantity rejection
- Invalid product reference rejection
- Duplicate order-item ID rejection
- Gross amount mismatch rejection

## Project Status

The synthetic data generation, data-quality validation, dimensional warehouse loading, foreign-key validation, and six analytics report exports have been executed successfully.

The project uses synthetic retail data and is intended to demonstrate practical data engineering and analytics workflows.

## Data Dictionary and Design Decisions

See [docs/data_dictionary.md](docs/data_dictionary.md) for source and warehouse columns, data types, keys, nullability, measures, and fact grain. See [docs/design_notes.md](docs/design_notes.md) for architecture trade-offs, full-refresh idempotency, retry/backfill behavior, limitations, and optimization opportunities.

## One-command Pipeline Run and Observability

Run the complete pipeline from the repository root:

```powershell
python scripts/run_pipeline.py
```

Optional generator parameters:

```powershell
python scripts/run_pipeline.py --order-items 200000 --seed 42 --anomaly-rate 0.02
```

The runner executes generation, quality validation, warehouse initialization, warehouse loading, and analytics in order. It writes one JSON object per run to `reports/pipeline_runs.jsonl`, including a UUID `run_id`, UTC start/end timestamps, step and total durations, source/valid/rejected counts, warehouse row counts, source-to-fact reconciliation, status, and failure reason when applicable. A failed step stops the run and returns a non-zero exit code.

## Reconciliation

The runner compares validated order-item row count, net revenue, and total quantity against the loaded `fact_sales` table. All three comparisons must match for a successful run. Foreign-key orphan checks are also performed during warehouse loading.

## Expanded Tests

Run:

```powershell
python -m pytest -v
```

The tests cover valid and invalid records, empty batches, missing schema columns, null business identifiers, malformed numeric values, duplicate transaction IDs, invalid references, discount boundaries, and amount reconciliation.

## Sample Data

A compact, hand-inspectable synthetic input example is available in `data/sample/`. The default generator remains the reproducible way to create the larger 100,000-row workload.

## Run History and Generated Outputs

Generated raw/processed/quarantine CSVs, DuckDB files, analytics exports, and run history are local outputs and are excluded from Git where appropriate. The generator summary and source code are versioned so reviewers can reproduce the workload.
