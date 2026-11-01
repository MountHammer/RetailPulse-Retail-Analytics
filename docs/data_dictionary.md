# RetailPulse Data Dictionary

This document describes the source datasets and the DuckDB dimensional warehouse. Names use snake_case. Source identifiers are business keys; warehouse integer keys are surrogate keys.

## Source datasets

| Dataset | Business key | Grain | Important fields and rules |
|---|---|---|---|
| `customers.csv` | `customer_id` | One row per customer | `customer_name`, `email`, `city`, `customer_segment`, `signup_date`. Customer ID is required and unique. |
| `products.csv` | `product_id` | One row per product | `product_name`, `category`, `brand`, `list_price`, `is_active`. Product ID is required and unique; list price must be finite and greater than zero. |
| `orders.csv` | `order_id` | One row per order | `customer_id`, `order_timestamp`, `order_status`, `payment_method`. Order and customer IDs are required; customer must exist; timestamp and enumerated status/payment values are validated. |
| `order_items.csv` | `order_item_id` | One row per order line | `order_id`, `product_id`, `quantity`, `unit_price`, `discount_pct`, `gross_amount`, `net_amount`. IDs must resolve; quantity and price must be positive; discount is between 0 and 1; amounts must reconcile. |

CSV source row numbers are retained as `source_row_number` in clean/quarantine outputs to support traceability. The validation process records pipe-delimited `rejection_reasons` for rejected rows.

## Dimensional warehouse

The declared fact grain is **one row per order item**. A sales fact represents an individual product line within an order, not an order header.

### Dimensions

| Table | Primary key | Business key | Attributes |
|---|---|---|---|
| `dim_customer` | `customer_key BIGINT` | `customer_id VARCHAR` (unique, not null) | customer_name, email, city, customer_segment, signup_date |
| `dim_product` | `product_key BIGINT` | `product_id VARCHAR` (unique, not null) | product_name, category, brand, list_price, is_active |
| `dim_order` | `order_key BIGINT` | `order_id VARCHAR` (unique, not null) | customer_id, order_timestamp, order_status, payment_method |
| `dim_date` | `date_key INTEGER` (YYYYMMDD) | `full_date DATE` (unique, not null) | day_number, day_name, week_number, month_number, month_name, quarter_number, year_number, is_weekend |

Dimension surrogate keys are generated deterministically by sorting distinct business IDs and assigning integers from 1. Date keys use the calendar date in YYYYMMDD format.

### Fact table

| Column | Type | Meaning |
|---|---|---|
| `sales_key` | BIGINT | Sequential row surrogate key for the current full refresh |
| `order_item_id` | VARCHAR | Source order-line business identifier; unique and not null |
| `order_key` | BIGINT | FK to `dim_order` |
| `customer_key` | BIGINT | FK to `dim_customer` |
| `product_key` | BIGINT | FK to `dim_product` |
| `date_key` | INTEGER | FK to `dim_date`, based on order date |
| `source_row_number` | BIGINT | Original CSV data row number (header excluded) |
| `quantity` | INTEGER | Number of units on the order line |
| `unit_price` | DECIMAL(12,2) | Unit selling price |
| `discount_pct` | DECIMAL(8,4) | Discount fraction in the range 0–1 |
| `gross_amount` | DECIMAL(14,2) | quantity × unit_price |
| `discount_amount` | DECIMAL(14,2) | gross_amount − net_amount |
| `net_amount` | DECIMAL(14,2) | Revenue after discount |

All four fact foreign keys are not null and must resolve to a dimension row. Quantity and unit price must be positive; discount must be between 0 and 1; gross and net amounts must be non-negative.

## Measures and aggregation

- **Units sold:** SUM(quantity)
- **Gross sales:** SUM(gross_amount)
- **Discount value:** SUM(discount_amount)
- **Net revenue:** SUM(net_amount)
- **Orders:** COUNT(DISTINCT order_key)
- **Average order value:** SUM(net_amount) / COUNT(DISTINCT order_key), guarded against division by zero

Measures are additive across product, customer and date dimensions for this model. Order count is a distinct-count measure and must not be summed across overlapping groups.

## Nullability and history assumptions

The source validators enforce required business identifiers and critical numeric/timestamp fields. Descriptive attributes may be nullable where the source permits them. The current model is a transaction snapshot: it does not implement slowly changing dimensions or preserve customer/product attribute history. The warehouse is rebuilt with a transactional full refresh; see `design_notes.md` for the resulting surrogate-key and backfill trade-offs.
