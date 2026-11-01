
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
QUARANTINE_DIR = PROJECT_ROOT / "data" / "quarantine"
REPORT_DIR = PROJECT_ROOT / "reports"

SOURCE_FILES = {
    "customers": RAW_DIR / "customers.csv",
    "products": RAW_DIR / "products.csv",
    "orders": RAW_DIR / "orders.csv",
    "order_items": RAW_DIR / "order_items.csv",
}


# ---------------------------------------------------------
# DATA LOADING
# ---------------------------------------------------------

def load_data():
    """Load all four source datasets."""

    datasets = {}

    for name, path in SOURCE_FILES.items():
        if not path.exists():
            raise FileNotFoundError(
                f"Required source file is missing: {path}"
            )

        datasets[name] = pd.read_csv(path)

    return datasets


def check_schema(df, required_columns, dataset_name):
    """Fail clearly when an expected source column is missing."""

    missing = set(required_columns) - set(df.columns)

    if missing:
        raise ValueError(
            f"{dataset_name} has missing columns: {sorted(missing)}"
        )


# ---------------------------------------------------------
# VALIDATION UTILITIES
# ---------------------------------------------------------

def add_reason(reasons, mask, code):
    """Add a validation error without overwriting earlier errors."""

    mask = pd.Series(mask, index=reasons.index).fillna(False).astype(bool)

    existing = reasons.loc[mask]

    reasons.loc[mask] = np.where(
        existing.eq(""),
        code,
        existing + "|" + code,
    )

def split_valid_rejected(
    df: pd.DataFrame,
    reasons: pd.Series,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separate valid and rejected records while preserving row numbers."""

    result = df.copy()
    result["rejection_reasons"] = reasons

    valid = result[result["rejection_reasons"] == ""].copy()
    rejected = result[result["rejection_reasons"] != ""].copy()

    return valid, rejected


def validate_unique_key(
    df: pd.DataFrame,
    key_column: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reject missing or duplicate business keys."""

    reasons = pd.Series("", index=df.index, dtype="object")

    add_reason(
        reasons,
        df[key_column].isna(),
        f"MISSING_{key_column.upper()}",
    )

    duplicate_mask = (
        df[key_column].notna()
        & df[key_column].duplicated(keep="first")
    )

    add_reason(
        reasons,
        duplicate_mask,
        f"DUPLICATE_{key_column.upper()}",
    )

    return split_valid_rejected(df, reasons)


# ---------------------------------------------------------
# CUSTOMER VALIDATION
# ---------------------------------------------------------

def validate_customers(customers):
    check_schema(
        customers,
        ["customer_id", "customer_name", "email"],
        "customers",
    )

    customers = customers.copy()
    customers.insert(
        0, "source_row_number", np.arange(2, len(customers) + 2)
    )

    return validate_unique_key(customers, "customer_id")


# ---------------------------------------------------------
# PRODUCT VALIDATION
# ---------------------------------------------------------


def validate_products(products):
    check_schema(
        products,
        ["product_id", "product_name", "list_price"],
        "products",
    )

    products = products.copy()
    products.insert(
        0, "source_row_number", np.arange(2, len(products) + 2)
    )

    # First validate product IDs.
    clean, rejected_keys = validate_unique_key(
        products, "product_id"
    )

    # Then validate product prices.
    prices = pd.to_numeric(
        clean["list_price"], errors="coerce"
    )

    invalid_price = (
        prices.isna()
        | ~np.isfinite(prices)
        | prices.le(0)
    )

    reasons = clean["rejection_reasons"].copy()

    add_reason(
        reasons,
        invalid_price,
        "INVALID_PRODUCT_PRICE",
    )

    valid_products, rejected_prices = split_valid_rejected(
        clean.drop(columns="rejection_reasons"),
        reasons,
    )

    # Combine both rejection groups into one DataFrame.
    rejected_products = pd.concat(
        [rejected_keys, rejected_prices],
        ignore_index=True,
    )

    return valid_products, rejected_products


# ---------------------------------------------------------
# ORDER VALIDATION
# ---------------------------------------------------------

def validate_orders(orders, valid_customer_ids):
    check_schema(
        orders,
        [
            "order_id",
            "customer_id",
            "order_timestamp",
            "order_status",
            "payment_method",
        ],
        "orders",
    )

    df = orders.copy()
    df.insert(
        0, "source_row_number", np.arange(2, len(df) + 2)
    )

    reasons = pd.Series("", index=df.index, dtype="object")

    add_reason(reasons, df["order_id"].isna(), "MISSING_ORDER_ID")
    add_reason(
        reasons,
        df["customer_id"].isna(),
        "MISSING_CUSTOMER_ID",
    )

    duplicate_mask = (
        df["order_id"].notna()
        & df["order_id"].duplicated(keep="first")
    )

    add_reason(
        reasons,
        duplicate_mask,
        "DUPLICATE_ORDER_ID",
    )

    add_reason(
        reasons,
        df["customer_id"].notna()
        & ~df["customer_id"].isin(valid_customer_ids),
        "INVALID_CUSTOMER_REFERENCE",
    )

    parsed_dates = pd.to_datetime(
        df["order_timestamp"], errors="coerce"
    )

    add_reason(
        reasons,
        parsed_dates.isna(),
        "INVALID_ORDER_TIMESTAMP",
    )

    add_reason(
        reasons,
        ~df["order_status"].isin(
            ["Completed", "Pending", "Cancelled", "Returned"]
        ),
        "INVALID_ORDER_STATUS",
    )

    add_reason(
        reasons,
        ~df["payment_method"].isin(
            ["UPI", "Credit Card", "Debit Card", "Net Banking", "COD"]
        ),
        "INVALID_PAYMENT_METHOD",
    )

    df["order_timestamp"] = parsed_dates

    return split_valid_rejected(df, reasons)


# ---------------------------------------------------------
# ORDER ITEM VALIDATION
# ---------------------------------------------------------

def validate_order_items(items, valid_order_ids, valid_product_ids):
    required = [
        "order_item_id",
        "order_id",
        "product_id",
        "quantity",
        "unit_price",
        "discount_pct",
        "gross_amount",
        "net_amount",
    ]

    check_schema(items, required, "order_items")

    df = items.copy()
    df.insert(
        0, "source_row_number", np.arange(2, len(df) + 2)
    )

    reasons = pd.Series("", index=df.index, dtype="object")

    # Required identifiers
    for column in [
        "order_item_id",
        "order_id",
        "product_id",
    ]:
        add_reason(
            reasons,
            df[column].isna(),
            f"MISSING_{column.upper()}",
        )

    # Duplicate transaction identifiers
    duplicate_mask = (
        df["order_item_id"].notna()
        & df["order_item_id"].duplicated(keep="first")
    )

    add_reason(
        reasons,
        duplicate_mask,
        "DUPLICATE_ORDER_ITEM_ID",
    )

    # Referential integrity
    add_reason(
        reasons,
        df["order_id"].notna()
        & ~df["order_id"].isin(valid_order_ids),
        "INVALID_ORDER_REFERENCE",
    )

    add_reason(
        reasons,
        df["product_id"].notna()
        & ~df["product_id"].isin(valid_product_ids),
        "INVALID_PRODUCT_REFERENCE",
    )

    # Numeric conversion
    quantity = pd.to_numeric(df["quantity"], errors="coerce")
    price = pd.to_numeric(df["unit_price"], errors="coerce")
    discount = pd.to_numeric(df["discount_pct"], errors="coerce")
    gross = pd.to_numeric(df["gross_amount"], errors="coerce")
    net = pd.to_numeric(df["net_amount"], errors="coerce")

    # Quantity validation
    add_reason(
        reasons,
        quantity.isna() | ~np.isfinite(quantity) | quantity.le(0),
        "INVALID_QUANTITY",
    )

    # Price validation
    add_reason(
        reasons,
        price.isna() | ~np.isfinite(price) | price.le(0),
        "INVALID_UNIT_PRICE",
    )

    # Discount validation
    add_reason(
        reasons,
        discount.isna()
        | ~np.isfinite(discount)
        | ~discount.between(0, 1),
        "INVALID_DISCOUNT",
    )

    # Amount reconciliation
    expected_gross = (quantity * price).round(2)

    add_reason(
        reasons,
        gross.isna()
        | ~np.isfinite(gross)
        | (expected_gross - gross).abs().gt(0.01),
        "GROSS_AMOUNT_MISMATCH",
    )

    expected_net = (
        expected_gross * (1 - discount)
    ).round(2)

    add_reason(
        reasons,
        net.isna()
        | ~np.isfinite(net)
        | (expected_net - net).abs().gt(0.01),
        "NET_AMOUNT_MISMATCH",
    )

    return split_valid_rejected(df, reasons)


# ---------------------------------------------------------
# QUALITY REPORT
# ---------------------------------------------------------

def build_quality_report(datasets, clean, rejected):
    total_items = len(datasets["order_items"])
    valid_items = len(clean["order_items"])
    rejected_items = len(rejected["order_items"])

    trust_score = (
        round(valid_items / total_items * 100, 2)
        if total_items else None
    )

    reason_counts = Counter()

    for reason_string in rejected["order_items"][
        "rejection_reasons"
    ]:
        for reason in reason_string.split("|"):
            if reason:
                reason_counts[reason] += 1

    return {
        "project": "RetailPulse",
        "total_source_records": {
            name: len(df) for name, df in datasets.items()
        },
        "valid_records": {
            name: len(df) for name, df in clean.items()
        },
        "rejected_records": {
            name: len(df) for name, df in rejected.items()
        },
        "order_item_data_trust_score": trust_score,
        "rejection_reasons": dict(reason_counts),
        "status": (
            "PASS" if not any(len(df) for df in rejected.values())
            else "REVIEW_REQUIRED"
        ),
    }


# ---------------------------------------------------------
# MAIN PIPELINE
# ---------------------------------------------------------

def run_quality_checks():
    for directory in [
        PROCESSED_DIR,
        QUARANTINE_DIR,
        REPORT_DIR,
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    print("\nLoading RetailPulse source data...")
    datasets = load_data()

    print("Validating customers...")
    clean_customers, rejected_customers = validate_customers(
        datasets["customers"]
    )

    print("Validating products...")
    (clean_products, rejected_products) = validate_products(
        datasets["products"]
    )

    print("Validating orders...")
    clean_orders, rejected_orders = validate_orders(
        datasets["orders"],
        set(clean_customers["customer_id"]),
    )

    print("Validating order items...")
    clean_items, rejected_items = validate_order_items(
        datasets["order_items"],
        set(clean_orders["order_id"]),
        set(clean_products["product_id"]),
    )

    clean = {
        "customers": clean_customers,
        "products": clean_products,
        "orders": clean_orders,
        "order_items": clean_items,
    }

    rejected = {
        "customers": rejected_customers,
        "products": rejected_products,
        "orders": rejected_orders,
        "order_items": rejected_items,
    }

    print("\nPublishing clean and rejected datasets...")

    for name, df in clean.items():
        df.to_csv(
            PROCESSED_DIR / f"clean_{name}.csv",
            index=False,
        )

    for name, df in rejected.items():
        df.to_csv(
            QUARANTINE_DIR / f"rejected_{name}.csv",
            index=False,
        )

    report = build_quality_report(datasets, clean, rejected)

    report_path = REPORT_DIR / "quality_report.json"

    report_path.write_text(
        json.dumps(report, indent=4),
        encoding="utf-8",
    )

    print("\n" + "=" * 55)
    print("          RETAILPULSE DATA QUALITY REPORT")
    print("=" * 55)

    for name in datasets:
        print(
            f"{name:15} | "
            f"Valid: {len(clean[name]):>8,} | "
            f"Rejected: {len(rejected[name]):>8,}"
        )

    print("-" * 55)
    print(
        "Order item Data Trust Score: "
        f"{report['order_item_data_trust_score']}%"
    )
    print(f"Overall status: {report['status']}")

    print("\nRejection reasons:")
    for reason, count in sorted(
        report["rejection_reasons"].items()
    ):
        print(f"  {reason:35} {count:>8,}")

    print("=" * 55)
    print(f"Report saved to: {report_path}")


if __name__ == "__main__":
    run_quality_checks()
