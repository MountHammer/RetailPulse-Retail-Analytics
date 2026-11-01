
import pandas as pd

from src.quality import (
    validate_products,
    validate_orders,
    validate_order_items,
)


def make_order_item(**overrides):
    """Create a valid order item for testing."""

    record = {
        "order_item_id": "OI001",
        "order_id": "ORD001",
        "product_id": "PROD001",
        "quantity": 2,
        "unit_price": 10.00,
        "discount_pct": 0.10,
        "gross_amount": 20.00,
        "net_amount": 18.00,
    }

    record.update(overrides)
    return record


def test_valid_product_is_accepted():
    products = pd.DataFrame([
        {
            "product_id": "P001",
            "product_name": "Keyboard",
            "list_price": 500,
        }
    ])

    valid, rejected = validate_products(products)

    assert len(valid) == 1
    assert len(rejected) == 0


def test_invalid_product_price_is_rejected():
    products = pd.DataFrame([
        {
            "product_id": "P001",
            "product_name": "Keyboard",
            "list_price": 0,
        }
    ])

    valid, rejected = validate_products(products)

    assert len(valid) == 0
    assert len(rejected) == 1
    assert "INVALID_PRODUCT_PRICE" in (
        rejected.iloc[0]["rejection_reasons"]
    )


def test_invalid_customer_reference_is_rejected():
    orders = pd.DataFrame([
        {
            "order_id": "ORD001",
            "customer_id": "UNKNOWN",
            "order_timestamp": "2026-10-15 10:00:00",
            "order_status": "Completed",
            "payment_method": "UPI",
        }
    ])

    valid, rejected = validate_orders(
        orders,
        valid_customer_ids={"C001"},
    )

    assert len(valid) == 0
    assert len(rejected) == 1
    assert "INVALID_CUSTOMER_REFERENCE" in (
        rejected.iloc[0]["rejection_reasons"]
    )


def test_valid_order_item_is_accepted():
    items = pd.DataFrame([make_order_item()])

    valid, rejected = validate_order_items(
        items,
        valid_order_ids={"ORD001"},
        valid_product_ids={"PROD001"},
    )

    assert len(valid) == 1
    assert len(rejected) == 0


def test_negative_quantity_is_rejected():
    items = pd.DataFrame([
        make_order_item(quantity=-2)
    ])

    valid, rejected = validate_order_items(
        items,
        valid_order_ids={"ORD001"},
        valid_product_ids={"PROD001"},
    )

    assert len(valid) == 0
    assert len(rejected) == 1
    assert "INVALID_QUANTITY" in (
        rejected.iloc[0]["rejection_reasons"]
    )


def test_invalid_product_reference_is_rejected():
    items = pd.DataFrame([make_order_item()])

    valid, rejected = validate_order_items(
        items,
        valid_order_ids={"ORD001"},
        valid_product_ids={"PROD999"},
    )

    assert len(valid) == 0
    assert "INVALID_PRODUCT_REFERENCE" in (
        rejected.iloc[0]["rejection_reasons"]
    )


def test_duplicate_order_item_id_is_rejected():
    items = pd.DataFrame([
        make_order_item(),
        make_order_item(order_id="ORD002"),
    ])

    valid, rejected = validate_order_items(
        items,
        valid_order_ids={"ORD001", "ORD002"},
        valid_product_ids={"PROD001"},
    )

    assert len(valid) == 1
    assert len(rejected) == 1
    assert "DUPLICATE_ORDER_ITEM_ID" in (
        rejected.iloc[0]["rejection_reasons"]
    )


def test_gross_amount_mismatch_is_rejected():
    items = pd.DataFrame([
        make_order_item(gross_amount=100.00)
    ])

    valid, rejected = validate_order_items(
        items,
        valid_order_ids={"ORD001"},
        valid_product_ids={"PROD001"},
    )

    assert len(valid) == 0
    assert "GROSS_AMOUNT_MISMATCH" in (
        rejected.iloc[0]["rejection_reasons"]
    )
