
import duckdb

from load_warehouse import DATABASE_PATH, load_warehouse


def fetch_scalar(connection, query):
    """Execute a query that should return one value."""
    row = connection.execute(query).fetchone()

    if row is None:
        raise RuntimeError(f"Query returned no result: {query}")

    return row[0]


def fetch_all(connection, query):
    """Execute a query and return all rows."""
    return connection.execute(query).fetchall()


def get_warehouse_snapshot():
    """Capture warehouse counts, measures and surrogate keys."""

    connection = duckdb.connect(str(DATABASE_PATH), read_only=True)

    try:
        snapshot = {}

        tables = [
            "dim_customer",
            "dim_product",
            "dim_order",
            "dim_date",
            "fact_sales",
        ]

        # Capture row counts.
        for table in tables:
            snapshot[f"{table}_count"] = fetch_scalar(
                connection,
                f"SELECT COUNT(*) FROM {table}"
            )

        # Capture business measures.
        snapshot["net_revenue"] = fetch_scalar(
            connection,
            "SELECT COALESCE(SUM(net_amount), 0) FROM fact_sales"
        )

        snapshot["units_sold"] = fetch_scalar(
            connection,
            "SELECT COALESCE(SUM(quantity), 0) FROM fact_sales"
        )

        # Capture dimension surrogate-key mappings.
        snapshot["customer_keys"] = fetch_all(
            connection,
            """
            SELECT customer_id, customer_key
            FROM dim_customer
            ORDER BY customer_id
            """
        )

        snapshot["product_keys"] = fetch_all(
            connection,
            """
            SELECT product_id, product_key
            FROM dim_product
            ORDER BY product_id
            """
        )

        snapshot["order_keys"] = fetch_all(
            connection,
            """
            SELECT order_id, order_key
            FROM dim_order
            ORDER BY order_id
            """
        )

        # Capture fact-table keys.
        snapshot["fact_keys"] = fetch_all(
            connection,
            """
            SELECT order_item_id, sales_key
            FROM fact_sales
            ORDER BY order_item_id
            """
        )

        return snapshot

    finally:
        connection.close()


def main():
    print("=" * 60)
    print("RETAILPULSE IDEMPOTENCY VERIFICATION")
    print("=" * 60)

    print("\nRunning first warehouse load...")
    load_warehouse()
    first_snapshot = get_warehouse_snapshot()

    print("\nRunning second warehouse load with identical inputs...")
    load_warehouse()
    second_snapshot = get_warehouse_snapshot()

    print("\nComparing both warehouse snapshots...")

    if first_snapshot != second_snapshot:
        raise AssertionError(
            "IDEMPOTENCY FAILED: warehouse snapshots are different."
        )

    print("\nIDEMPOTENCY VERIFICATION: PASSED")
    print("- Row counts are identical.")
    print("- Net revenue is identical.")
    print("- Units sold are identical.")
    print("- Customer surrogate keys are stable.")
    print("- Product surrogate keys are stable.")
    print("- Order surrogate keys are stable.")
    print("- Fact surrogate keys are stable.")

    print("\nVerified warehouse metrics:")
    print(f"Fact rows: {second_snapshot['fact_sales_count']:,}")
    print(f"Net revenue: {second_snapshot['net_revenue']}")
    print(f"Units sold: {second_snapshot['units_sold']:,}")

    print("\nVerification completed successfully.")


if __name__ == "__main__":
    main()
