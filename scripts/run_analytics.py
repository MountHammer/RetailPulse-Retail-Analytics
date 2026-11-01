
from pathlib import Path

import duckdb


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "retailpulse.duckdb"
OUTPUT_DIR = BASE_DIR / "reports" / "analytics"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


QUERIES = {
    "monthly_revenue": """
        SELECT
            DATE_TRUNC('month', d.full_date)::DATE AS sales_month,
            ROUND(SUM(f.net_amount), 2) AS total_revenue,
            COUNT(DISTINCT f.order_key) AS total_orders,
            SUM(f.quantity) AS units_sold
        FROM fact_sales f
        JOIN dim_date d ON f.date_key = d.date_key
        GROUP BY 1
        ORDER BY 1
    """,

    "category_performance": """
        SELECT
            p.category,
            ROUND(SUM(f.net_amount), 2) AS revenue,
            SUM(f.quantity) AS units_sold,
            COUNT(DISTINCT f.order_key) AS orders
        FROM fact_sales f
        JOIN dim_product p ON f.product_key = p.product_key
        GROUP BY p.category
        ORDER BY revenue DESC
    """,

    "top_customers": """
        SELECT
            c.customer_id,
            c.customer_name,
            c.customer_segment,
            ROUND(SUM(f.net_amount), 2) AS total_spent,
            COUNT(DISTINCT f.order_key) AS total_orders
        FROM fact_sales f
        JOIN dim_customer c ON f.customer_key = c.customer_key
        GROUP BY 1, 2, 3
        ORDER BY total_spent DESC
        LIMIT 10
    """,

    "average_order_value": """
        SELECT
            COUNT(DISTINCT order_key) AS total_orders,
            ROUND(SUM(net_amount), 2) AS total_revenue,
            ROUND(
                SUM(net_amount) /
                NULLIF(COUNT(DISTINCT order_key), 0),
                2
            ) AS average_order_value
        FROM fact_sales
    """,

    "top_products": """
        SELECT
            p.product_id,
            p.product_name,
            p.category,
            SUM(f.quantity) AS units_sold,
            ROUND(SUM(f.net_amount), 2) AS revenue
        FROM fact_sales f
        JOIN dim_product p ON f.product_key = p.product_key
        GROUP BY 1, 2, 3
        ORDER BY revenue DESC
        LIMIT 10
    """,

    "customer_segment_sales": """
        SELECT
            c.customer_segment,
            COUNT(DISTINCT c.customer_key) AS customers,
            COUNT(DISTINCT f.order_key) AS orders,
            ROUND(SUM(f.net_amount), 2) AS revenue,
            ROUND(
                SUM(f.net_amount) /
                NULLIF(COUNT(DISTINCT f.order_key), 0),
                2
            ) AS average_order_value
        FROM fact_sales f
        JOIN dim_customer c ON f.customer_key = c.customer_key
        GROUP BY c.customer_segment
        ORDER BY revenue DESC
    """
}


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    print("Starting RetailPulse analytics...")

    connection = duckdb.connect(str(DB_PATH), read_only=True)

    try:
        for report_name, query in QUERIES.items():
            print(f"\nRunning: {report_name}")

            result = connection.execute(query).df()

            output_path = OUTPUT_DIR / f"{report_name}.csv"
            result.to_csv(output_path, index=False)

            print(f"Rows: {len(result)}")
            print(f"Exported: {output_path}")

            print(result.head(5).to_string(index=False))

        print("\nAll six analytics reports generated successfully.")

    finally:
        connection.close()


if __name__ == "__main__":
    main()
