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
yottaflex-data-engineering/
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