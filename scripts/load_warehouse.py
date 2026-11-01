
from pathlib import Path

import duckdb
import pandas as pd


# =========================================================
# 1. PROJECT PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DATA_DIR = BASE_DIR / "data" / "processed"
DATABASE_PATH = BASE_DIR / "database" / "retailpulse.duckdb"
SCHEMA_PATH = BASE_DIR / "sql" / "schema.sql"


# =========================================================
# 2. HELPER: GENERATE DETERMINISTIC SURROGATE KEYS
# =========================================================

def create_key_map(values):
    """Create stable integer keys from sorted unique business IDs."""

    unique_values = sorted(pd.Series(values).dropna().unique())

    return {
        value: index
        for index, value in enumerate(unique_values, start=1)
    }


# =========================================================
# 3. LOAD SOURCE DATA
# =========================================================

def read_source_data():
    """Read the four validated CSV datasets."""

    print("Reading processed source data...")

    required_files = [
        "clean_customers.csv",
        "clean_products.csv",
        "clean_orders.csv",
        "clean_order_items.csv",
    ]

    for filename in required_files:
        file_path = RAW_DATA_DIR / filename

        if not file_path.exists():
            raise FileNotFoundError(
                f"Source file not found: {file_path}"
            )

    customers = pd.read_csv(
        RAW_DATA_DIR / "clean_customers.csv"
    )

    products = pd.read_csv(
        RAW_DATA_DIR / "clean_products.csv"
    )

    orders = pd.read_csv(
        RAW_DATA_DIR / "clean_orders.csv"
    )

    items = pd.read_csv(
        RAW_DATA_DIR / "clean_order_items.csv"
    )

    return customers, products, orders, items


# =========================================================
# 4. BUILD DIMENSION TABLES
# =========================================================

def build_dimensions(customers, products, orders):
    """Build customer, product, order and date dimensions."""

    # -----------------------------------------------------
    # CUSTOMER DIMENSION
    # -----------------------------------------------------

    customer_keys = create_key_map(
        customers["customer_id"]
    )

    dim_customer = customers[
        [
            "customer_id",
            "customer_name",
            "email",
            "city",
            "customer_segment",
            "signup_date",
        ]
    ].copy()

    dim_customer["customer_key"] = (
        dim_customer["customer_id"].map(customer_keys)
    )

    dim_customer["signup_date"] = pd.to_datetime(
        dim_customer["signup_date"],
        errors="coerce",
    ).dt.date

    dim_customer = dim_customer[
        [
            "customer_key",
            "customer_id",
            "customer_name",
            "email",
            "city",
            "customer_segment",
            "signup_date",
        ]
    ]

    # -----------------------------------------------------
    # PRODUCT DIMENSION
    # -----------------------------------------------------

    product_keys = create_key_map(
        products["product_id"]
    )

    dim_product = products[
        [
            "product_id",
            "product_name",
            "category",
            "brand",
            "list_price",
            "is_active",
        ]
    ].copy()

    dim_product["product_key"] = (
        dim_product["product_id"].map(product_keys)
    )

    dim_product["list_price"] = pd.to_numeric(
        dim_product["list_price"],
        errors="coerce",
    )

    dim_product = dim_product[
        [
            "product_key",
            "product_id",
            "product_name",
            "category",
            "brand",
            "list_price",
            "is_active",
        ]
    ]

    # -----------------------------------------------------
    # PREPARE ORDER DATA
    # -----------------------------------------------------

    orders = orders.copy()

    orders["order_timestamp"] = pd.to_datetime(
        orders["order_timestamp"],
        errors="coerce",
    )

    order_keys = create_key_map(
        orders["order_id"]
    )

    date_values = sorted(
        orders["order_timestamp"].dt.date.dropna().unique()
    )

    date_keys = {
        date_value: int(date_value.strftime("%Y%m%d"))
        for date_value in date_values
    }

    # -----------------------------------------------------
    # ORDER DIMENSION
    # -----------------------------------------------------

    dim_order = orders[
        [
            "order_id",
            "customer_id",
            "order_timestamp",
            "order_status",
            "payment_method",
        ]
    ].copy()

    dim_order["order_key"] = (
        dim_order["order_id"].map(order_keys)
    )

    dim_order = dim_order[
        [
            "order_key",
            "order_id",
            "customer_id",
            "order_timestamp",
            "order_status",
            "payment_method",
        ]
    ]

    # -----------------------------------------------------
    # DATE DIMENSION
    # -----------------------------------------------------

    full_dates = pd.to_datetime(
        pd.Series(date_values),
        errors="raise",
    )

    dim_date = pd.DataFrame({
        "full_date": full_dates
    })

    dim_date["date_key"] = (
        full_dates.dt.strftime("%Y%m%d").astype("int32")
    )

    dim_date["day_number"] = full_dates.dt.day

    dim_date["day_name"] = full_dates.dt.day_name()

    dim_date["week_number"] = (
        full_dates.dt.isocalendar().week
    )

    dim_date["month_number"] = full_dates.dt.month

    dim_date["month_name"] = full_dates.dt.month_name()

    dim_date["quarter_number"] = (
        full_dates.dt.quarter
    )

    dim_date["year_number"] = (
        full_dates.dt.year
    )

    dim_date["is_weekend"] = (
        full_dates.dt.day_of_week >= 5
    )

    dim_date = dim_date[
        [
            "date_key",
            "full_date",
            "day_number",
            "day_name",
            "week_number",
            "month_number",
            "month_name",
            "quarter_number",
            "year_number",
            "is_weekend",
        ]
    ]

    return (
        dim_customer,
        dim_product,
        dim_order,
        dim_date,
        customer_keys,
        product_keys,
        order_keys,
        date_keys,
    )


# =========================================================
# 5. BUILD SALES FACT TABLE
# =========================================================

def build_fact_sales(
    items,
    orders,
    customer_keys,
    product_keys,
    order_keys,
    date_keys,
):
    """Build one fact record per valid order item."""

    print("Building sales fact table...")

    fact = items.copy()
    order_lookup = orders.copy()

    order_lookup["order_timestamp"] = pd.to_datetime(
        order_lookup["order_timestamp"],
        errors="coerce",
    )

    order_lookup["order_key"] = (
        order_lookup["order_id"].map(order_keys)
    )

    order_lookup["customer_key"] = (
        order_lookup["customer_id"].map(customer_keys)
    )

    order_lookup["date_key"] = (
        order_lookup["order_timestamp"]
        .dt.date
        .map(date_keys)
    )

    # Join each order item to its corresponding order.
    fact = fact.merge(
        order_lookup[
            [
                "order_id",
                "order_key",
                "customer_key",
                "date_key",
            ]
        ],
        on="order_id",
        how="left",
        validate="many_to_one",
    )

    # Resolve product surrogate keys.
    fact["product_key"] = (
        fact["product_id"].map(product_keys)
    )

    # -----------------------------------------------------
    # NUMERIC CONVERSION
    # -----------------------------------------------------

    numeric_columns = [
        "quantity",
        "unit_price",
        "discount_pct",
        "gross_amount",
        "net_amount",
    ]

    for column in numeric_columns:
        fact[column] = pd.to_numeric(
            fact[column],
            errors="raise",
        )

    # Quantity must be an integer.
    if not fact["quantity"].mod(1).eq(0).all():
        raise ValueError(
            "Order item quantity contains non-integer values."
        )

    fact["quantity"] = fact["quantity"].astype("int64")

    # -----------------------------------------------------
    # CALCULATE DISCOUNT AMOUNT
    # -----------------------------------------------------

    fact["discount_amount"] = (
        fact["gross_amount"] - fact["net_amount"]
    ).round(2)

    # -----------------------------------------------------
    # FOREIGN KEY VALIDATION
    # -----------------------------------------------------

    key_columns = [
        "order_key",
        "customer_key",
        "product_key",
        "date_key",
    ]

    if fact[key_columns].isna().any().any():
        raise ValueError(
            "Fact table contains unresolved dimension keys."
        )

    # -----------------------------------------------------
    # SALES SURROGATE KEY
    # -----------------------------------------------------

    fact["sales_key"] = range(
        1,
        len(fact) + 1,
    )

    # -----------------------------------------------------
    # FINAL FACT TABLE COLUMN ORDER
    # -----------------------------------------------------

    fact = fact[
        [
            "sales_key",
            "order_item_id",
            "order_key",
            "customer_key",
            "product_key",
            "date_key",
            "source_row_number",
            "quantity",
            "unit_price",
            "discount_pct",
            "gross_amount",
            "discount_amount",
            "net_amount",
        ]
    ]

    return fact


# =========================================================
# 6. LOAD DATA INTO DUCKDB
# =========================================================

def load_warehouse():
    """Perform a transactional full refresh of the warehouse."""

    # -----------------------------------------------------
    # CHECK REQUIRED FILES
    # -----------------------------------------------------

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DATABASE_PATH}. "
            "Run init_warehouse.py first."
        )

    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(
            f"Schema file not found: {SCHEMA_PATH}"
        )

    # -----------------------------------------------------
    # READ SOURCE DATA
    # -----------------------------------------------------

    customers, products, orders, items = read_source_data()

    # -----------------------------------------------------
    # BUILD DIMENSIONS
    # -----------------------------------------------------

    (
        dim_customer,
        dim_product,
        dim_order,
        dim_date,
        customer_keys,
        product_keys,
        order_keys,
        date_keys,
    ) = build_dimensions(
        customers,
        products,
        orders,
    )

    # -----------------------------------------------------
    # BUILD FACT TABLE
    # -----------------------------------------------------

    fact_sales = build_fact_sales(
        items,
        orders,
        customer_keys,
        product_keys,
        order_keys,
        date_keys,
    )

    # -----------------------------------------------------
    # CONNECT TO DUCKDB
    # -----------------------------------------------------

    print("\nConnecting to DuckDB...")

    connection = duckdb.connect(
        str(DATABASE_PATH)
    )

    try:
        connection.execute(
            "BEGIN TRANSACTION"
        )

        # -------------------------------------------------
        # REBUILD WAREHOUSE SCHEMA
        # -------------------------------------------------

        print("Rebuilding warehouse schema...")

        # Drop child table before parent tables.
        connection.execute(
            "DROP TABLE IF EXISTS fact_sales"
        )

        connection.execute(
            "DROP TABLE IF EXISTS dim_order"
        )

        connection.execute(
            "DROP TABLE IF EXISTS dim_customer"
        )

        connection.execute(
            "DROP TABLE IF EXISTS dim_product"
        )

        connection.execute(
            "DROP TABLE IF EXISTS dim_date"
        )

        # Recreate tables using schema.sql.
        schema_sql = SCHEMA_PATH.read_text(
            encoding="utf-8"
        )

        connection.execute(schema_sql)

        print("Warehouse schema recreated successfully.")

        # -------------------------------------------------
        # REGISTER DATAFRAMES
        # -------------------------------------------------

        dataframes = {
            "df_customer": dim_customer,
            "df_product": dim_product,
            "df_order": dim_order,
            "df_date": dim_date,
            "df_fact_sales": fact_sales,
        }

        for name, dataframe in dataframes.items():
            connection.register(
                name,
                dataframe,
            )

        # -------------------------------------------------
        # LOAD CUSTOMER DIMENSION
        # -------------------------------------------------

        connection.execute("""
            INSERT INTO dim_customer
            SELECT * FROM df_customer
        """)

        # -------------------------------------------------
        # LOAD PRODUCT DIMENSION
        # -------------------------------------------------

        connection.execute("""
            INSERT INTO dim_product
            SELECT * FROM df_product
        """)

        # -------------------------------------------------
        # LOAD ORDER DIMENSION
        # -------------------------------------------------

        connection.execute("""
            INSERT INTO dim_order
            SELECT * FROM df_order
        """)

        # -------------------------------------------------
        # LOAD DATE DIMENSION
        # -------------------------------------------------

        connection.execute("""
            INSERT INTO dim_date
            SELECT * FROM df_date
        """)

        # -------------------------------------------------
        # LOAD SALES FACT TABLE
        # -------------------------------------------------

        connection.execute("""
            INSERT INTO fact_sales
            SELECT * FROM df_fact_sales
        """)

        # -------------------------------------------------
        # VERIFY ROW COUNTS
        # -------------------------------------------------

        table_names = [
            "dim_customer",
            "dim_product",
            "dim_order",
            "dim_date",
            "fact_sales",
        ]

        row_counts = {}

        for table in table_names:
            result = connection.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()

            if result is None:
                raise RuntimeError(
                    f"Could not retrieve row count for {table}"
                )

            row_counts[table] = result[0]

        # -------------------------------------------------
        # VERIFY FOREIGN KEY RELATIONSHIPS
        # -------------------------------------------------

        orphan_checks = {
            "order_key": """
                SELECT COUNT(*)
                FROM fact_sales f
                LEFT JOIN dim_order d
                    ON f.order_key = d.order_key
                WHERE d.order_key IS NULL
            """,

            "customer_key": """
                SELECT COUNT(*)
                FROM fact_sales f
                LEFT JOIN dim_customer d
                    ON f.customer_key = d.customer_key
                WHERE d.customer_key IS NULL
            """,

            "product_key": """
                SELECT COUNT(*)
                FROM fact_sales f
                LEFT JOIN dim_product d
                    ON f.product_key = d.product_key
                WHERE d.product_key IS NULL
            """,

            "date_key": """
                SELECT COUNT(*)
                FROM fact_sales f
                LEFT JOIN dim_date d
                    ON f.date_key = d.date_key
                WHERE d.date_key IS NULL
            """,
        }

        for key_name, query in orphan_checks.items():
            result = connection.execute(
                query
            ).fetchone()

            if result is None or result[0] != 0:
                raise RuntimeError(
                    f"Foreign key validation failed: {key_name}"
                )

        # -------------------------------------------------
        # COMMIT TRANSACTION
        # -------------------------------------------------

        connection.execute("COMMIT")

        print("\nWarehouse load completed successfully!")

        print("\nLoaded row counts:")

        for table, count in row_counts.items():
            print(f"{table}: {count:,} rows")

        print("\nForeign key validation: PASSED")
        print("All warehouse tables loaded successfully.")

    except Exception:
        # Roll back any failed transaction.
        connection.execute("ROLLBACK")
        raise

    finally:
        # Always close the database connection.
        connection.close()


# =========================================================
# 7. MAIN ENTRY POINT
# =========================================================

if __name__ == "__main__":
    load_warehouse()
