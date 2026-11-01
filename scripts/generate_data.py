
"""
RetailPulse - Synthetic Retail Data Generator

Generates reproducible retail source data:
    customers.csv
    products.csv
    orders.csv
    order_items.csv

Usage:
    python scripts/generate_data.py
    python scripts/generate_data.py --order-items 200000
    python scripts/generate_data.py --order-items 100000 --anomaly-rate 0.04
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate synthetic retail data for RetailPulse."
    )
    parser.add_argument(
        "--order-items",
        type=int,
        default=100_000,
        help="Number of order-item transactions to generate.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible data.",
    )
    parser.add_argument(
        "--anomaly-rate",
        type=float,
        default=0.02,
        help="Approximate proportion of order items with injected issues (0 to 0.20).",
    )
    return parser.parse_args()


def generate_customers(rng, fake, count=5_000):
    print("Generating customers...")

    cities = [
        "Kolkata", "Mumbai", "Delhi", "Bengaluru",
        "Hyderabad", "Chennai", "Pune", "Jaipur",
    ]

    customers = pd.DataFrame({
        "customer_id": [f"C{i:06d}" for i in range(1, count + 1)],
        "customer_name": [fake.name() for _ in range(count)],
        "email": [f"customer{i}@example.com" for i in range(1, count + 1)],
        "city": rng.choice(cities, size=count),
        "customer_segment": rng.choice(
            ["Regular", "Premium", "Corporate"],
            size=count,
            p=[0.65, 0.25, 0.10],
        ),
        "signup_date": pd.to_datetime(
            rng.choice(
                pd.date_range("2021-01-01", "2025-12-31"),
                size=count,
            )
        ).strftime("%Y-%m-%d"),
    })

    return customers


def generate_products(rng, fake, count=500):
    print("Generating products...")

    categories = {
        "Electronics": (500, 50_000),
        "Fashion": (200, 8_000),
        "Home": (300, 25_000),
        "Books": (100, 2_000),
        "Sports": (250, 15_000),
    }

    category_names = list(categories.keys())
    selected_categories = rng.choice(category_names, size=count)

    prices = [
        round(rng.uniform(*categories[category]), 2)
        for category in selected_categories
    ]

    products = pd.DataFrame({
        "product_id": [f"P{i:05d}" for i in range(1, count + 1)],
        "product_name": [fake.catch_phrase() for _ in range(count)],
        "category": selected_categories,
        "brand": [fake.company() for _ in range(count)],
        "list_price": prices,
        "is_active": rng.choice([True, False], size=count, p=[0.95, 0.05]),
    })

    return products


def generate_orders(rng, customers, count):
    print("Generating orders...")

    customer_ids = customers["customer_id"].to_numpy()

    timestamps = (
        pd.Timestamp("2024-01-01")
        + pd.to_timedelta(
            rng.integers(
                0,
                int((pd.Timestamp("2026-01-01") - pd.Timestamp("2024-01-01")).total_seconds()),
                size=count,
            ),
            unit="s",
        )
    )

    orders = pd.DataFrame({
        "order_id": [f"O{i:07d}" for i in range(1, count + 1)],
        "customer_id": rng.choice(customer_ids, size=count),
        "order_timestamp": timestamps,
        "order_status": rng.choice(
            ["Completed", "Pending", "Cancelled", "Returned"],
            size=count,
            p=[0.78, 0.10, 0.08, 0.04],
        ),
        "payment_method": rng.choice(
            ["UPI", "Credit Card", "Debit Card", "Net Banking", "COD"],
            size=count,
            p=[0.40, 0.22, 0.18, 0.10, 0.10],
        ),
    })

    orders["order_timestamp"] = (
        orders["order_timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    )

    return orders


def inject_anomalies(order_items, rng, anomaly_rate):
    """Inject separate, controlled data-quality problems."""

    result = order_items.copy()
    total = len(result)

    anomaly_count = int(total * anomaly_rate)
    if anomaly_count == 0:
        return result, {}

    indices = rng.permutation(total)[:anomaly_count]
    groups = np.array_split(indices, 4)

    injected = {}

    # 1. Missing product references
    if len(groups[0]):
        result.loc[groups[0], "product_id"] = None
        injected["missing_product_id"] = len(groups[0])

    # 2. Product IDs that do not exist in the products table
    if len(groups[1]):
        result.loc[groups[1], "product_id"] = "P99999"
        injected["unknown_product_id"] = len(groups[1])

    # 3. Invalid non-positive quantities
    if len(groups[2]):
        result.loc[groups[2], "quantity"] = -1
        injected["negative_quantity"] = len(groups[2])

    # 4. Duplicate transaction identifiers
    if len(groups[3]) and total > 1:
        for target_index in groups[3]:
            source_index = int(rng.integers(0, total))
            while source_index == target_index:
                source_index = int(rng.integers(0, total))

            result.loc[target_index, "order_item_id"] = (
                result.loc[source_index, "order_item_id"]
            )

        injected["duplicate_order_item_id"] = len(groups[3])

    return result, injected


def generate_order_items(rng, products, orders, count, anomaly_rate):
    print(f"Generating {count:,} order items...")

    product_ids = products["product_id"].to_numpy()
    product_prices = products["list_price"].to_numpy()
    order_ids = orders["order_id"].to_numpy()

    product_positions = rng.integers(0, len(products), size=count)

    base_prices = product_prices[product_positions]
    quantities = rng.integers(1, 6, size=count)
    discounts = rng.choice(
        [0.00, 0.05, 0.10, 0.15, 0.20],
        size=count,
        p=[0.40, 0.20, 0.20, 0.15, 0.05],
    )

    order_items = pd.DataFrame({
        "order_item_id": [f"I{i:09d}" for i in range(1, count + 1)],
        "order_id": rng.choice(order_ids, size=count),
        "product_id": product_ids[product_positions],
        "quantity": quantities,
        "unit_price": np.round(base_prices, 2),
        "discount_pct": discounts,
    })

    order_items["gross_amount"] = (
        order_items["quantity"] * order_items["unit_price"]
    ).round(2)

    order_items["net_amount"] = (
        order_items["gross_amount"] * (1 - order_items["discount_pct"])
    ).round(2)

    order_items, injected = inject_anomalies(
        order_items, rng, anomaly_rate
    )

    return order_items, injected


def main():
    args = parse_args()

    if args.order_items < 1:
        raise ValueError("--order-items must be greater than zero.")

    if not 0 <= args.anomaly_rate <= 0.20:
        raise ValueError("--anomaly-rate must be between 0 and 0.20.")

    rng = np.random.default_rng(args.seed)
    fake = Faker("en_IN")
    fake.seed_instance(args.seed)

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    customer_count = 5_000
    product_count = 500

    # Approximately 2.5 line items per order.
    order_count = max(1, int(np.ceil(args.order_items / 2.5)))

    customers = generate_customers(
        rng, fake, customer_count
    )
    products = generate_products(
        rng, fake, product_count
    )
    orders = generate_orders(
        rng, customers, order_count
    )
    order_items, injected = generate_order_items(
        rng, products, orders, args.order_items, args.anomaly_rate
    )

    datasets = {
        "customers": customers,
        "products": products,
        "orders": orders,
        "order_items": order_items,
    }

    print("\nSaving CSV files...")

    for name, dataframe in datasets.items():
        output_path = RAW_DIR / f"{name}.csv"
        dataframe.to_csv(output_path, index=False)
        print(f"  {name}.csv: {len(dataframe):,} rows")

    summary = {
        "project": "RetailPulse",
        "seed": args.seed,
        "generated_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "requested_order_items": args.order_items,
        "anomaly_rate": args.anomaly_rate,
        "injected_anomalies": injected,
        "row_counts": {
            name: len(dataframe)
            for name, dataframe in datasets.items()
        },
    }

    summary_path = RAW_DIR / "generation_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=4),
        encoding="utf-8",
    )

    print("\n" + "=" * 55)
    print("RETAILPULSE DATA GENERATION COMPLETE")
    print("=" * 55)
    print(f"Customers:       {len(customers):,}")
    print(f"Products:        {len(products):,}")
    print(f"Orders:          {len(orders):,}")
    print(f"Order items:     {len(order_items):,}")
    print(f"Injected issues: {sum(injected.values()):,}")
    print(f"Output folder:   {RAW_DIR}")
    print("=" * 55)


if __name__ == "__main__":
    main()
