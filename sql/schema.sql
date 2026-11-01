
-- =========================================================
-- RetailPulse: Dimensional Warehouse Schema
-- Fact grain: One row per order item
-- =========================================================

CREATE TABLE IF NOT EXISTS dim_customer (
    customer_key BIGINT PRIMARY KEY,
    customer_id VARCHAR NOT NULL UNIQUE,
    customer_name VARCHAR,
    email VARCHAR,
    city VARCHAR,
    customer_segment VARCHAR,
    signup_date DATE
);

CREATE TABLE IF NOT EXISTS dim_product (
    product_key BIGINT PRIMARY KEY,
    product_id VARCHAR NOT NULL UNIQUE,
    product_name VARCHAR,
    category VARCHAR,
    brand VARCHAR,
    list_price DECIMAL(12, 2),
    is_active BOOLEAN
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_key INTEGER PRIMARY KEY,
    full_date DATE NOT NULL UNIQUE,
    day_number INTEGER,
    day_name VARCHAR,
    week_number INTEGER,
    month_number INTEGER,
    month_name VARCHAR,
    quarter_number INTEGER,
    year_number INTEGER,
    is_weekend BOOLEAN
);

CREATE TABLE IF NOT EXISTS dim_order (
    order_key BIGINT PRIMARY KEY,
    order_id VARCHAR NOT NULL UNIQUE,
    customer_id VARCHAR,
    order_timestamp TIMESTAMP,
    order_status VARCHAR,
    payment_method VARCHAR
);

CREATE TABLE IF NOT EXISTS fact_sales (
    sales_key BIGINT PRIMARY KEY,
    order_item_id VARCHAR NOT NULL UNIQUE,
    order_key BIGINT NOT NULL,
    customer_key BIGINT NOT NULL,
    product_key BIGINT NOT NULL,
    date_key INTEGER NOT NULL,
    source_row_number BIGINT,
    quantity INTEGER,
    unit_price DECIMAL(12, 2),
    discount_pct DECIMAL(8, 4),
    gross_amount DECIMAL(14, 2),
    discount_amount DECIMAL(14, 2),
    net_amount DECIMAL(14, 2),

    CHECK (quantity > 0),
    CHECK (unit_price > 0),
    CHECK (discount_pct >= 0 AND discount_pct <= 1),
    CHECK (gross_amount >= 0),
    CHECK (net_amount >= 0),

    FOREIGN KEY (order_key) REFERENCES dim_order(order_key),
    FOREIGN KEY (customer_key) REFERENCES dim_customer(customer_key),
    FOREIGN KEY (product_key) REFERENCES dim_product(product_key),
    FOREIGN KEY (date_key) REFERENCES dim_date(date_key)
);
