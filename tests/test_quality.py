import pandas as pd
import pytest

from src.quality import (
    validate_products,
    validate_orders,
    validate_order_items,
    check_schema,
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
    products = pd.DataFrame([{
        "product_id": "P001", "product_name": "Keyboard", "list_price": 500,
    }])
    valid, rejected = validate_products(products)
    assert len(valid) == 1
    assert rejected.empty


def test_invalid_product_price_is_rejected():
    products = pd.DataFrame([{
        "product_id": "P001", "product_name": "Keyboard", "list_price": 0,
    }])
    valid, rejected = validate_products(products)
    assert valid.empty
    assert len(rejected) == 1
    assert "INVALID_PRODUCT_PRICE" in rejected.iloc[0]["rejection_reasons"]


def test_invalid_customer_reference_is_rejected():
    orders = pd.DataFrame([{
        "order_id": "ORD001", "customer_id": "UNKNOWN",
        "order_timestamp": "2026-10-15 10:00:00",
        "order_status": "Completed", "payment_method": "UPI",
    }])
    valid, rejected = validate_orders(orders, valid_customer_ids={"C001"})
    assert valid.empty
    assert len(rejected) == 1
    assert "INVALID_CUSTOMER_REFERENCE" in rejected.iloc[0]["rejection_reasons"]


def test_valid_order_item_is_accepted():
    valid, rejected = validate_order_items(
        pd.DataFrame([make_order_item()]),
        valid_order_ids={"ORD001"}, valid_product_ids={"PROD001"},
    )
    assert len(valid) == 1
    assert rejected.empty


def test_negative_quantity_is_rejected():
    valid, rejected = validate_order_items(
        pd.DataFrame([make_order_item(quantity=-2)]),
        valid_order_ids={"ORD001"}, valid_product_ids={"PROD001"},
    )
    assert valid.empty
    assert "INVALID_QUANTITY" in rejected.iloc[0]["rejection_reasons"]


def test_invalid_product_reference_is_rejected():
    valid, rejected = validate_order_items(
        pd.DataFrame([make_order_item()]),
        valid_order_ids={"ORD001"}, valid_product_ids={"PROD999"},
    )
    assert valid.empty
    assert "INVALID_PRODUCT_REFERENCE" in rejected.iloc[0]["rejection_reasons"]


def test_duplicate_order_item_id_is_rejected():
    items = pd.DataFrame([
        make_order_item(), make_order_item(order_id="ORD002"),
    ])
    valid, rejected = validate_order_items(
        items, valid_order_ids={"ORD001", "ORD002"},
        valid_product_ids={"PROD001"},
    )
    assert len(valid) == 1
    assert len(rejected) == 1
    assert "DUPLICATE_ORDER_ITEM_ID" in rejected.iloc[0]["rejection_reasons"]


def test_gross_amount_mismatch_is_rejected():
    valid, rejected = validate_order_items(
        pd.DataFrame([make_order_item(gross_amount=100.00)]),
        valid_order_ids={"ORD001"}, valid_product_ids={"PROD001"},
    )
    assert valid.empty
    assert "GROSS_AMOUNT_MISMATCH" in rejected.iloc[0]["rejection_reasons"]


def test_empty_order_item_batch_is_valid_empty_output():
    columns = [
        "order_item_id", "order_id", "product_id", "quantity",
        "unit_price", "discount_pct", "gross_amount", "net_amount",
    ]
    valid, rejected = validate_order_items(
        pd.DataFrame(columns=columns),
        valid_order_ids={"ORD001"}, valid_product_ids={"PROD001"},
    )
    assert valid.empty
    assert rejected.empty


def test_missing_required_column_fails_clearly():
    with pytest.raises(ValueError, match="missing columns"):
        check_schema(pd.DataFrame([{"order_item_id": "OI001"}]),
                     ["order_item_id", "order_id"], "order_items")


def test_null_required_product_id_is_quarantined():
    products = pd.DataFrame([{
        "product_id": None, "product_name": "Keyboard", "list_price": 500,
    }])
    valid, rejected = validate_products(products)
    assert valid.empty
    assert len(rejected) == 1
    assert "MISSING_PRODUCT_ID" in rejected.iloc[0]["rejection_reasons"]


def test_malformed_numeric_quantity_is_quarantined():
    valid, rejected = validate_order_items(
        pd.DataFrame([make_order_item(quantity="not-a-number")]),
        valid_order_ids={"ORD001"}, valid_product_ids={"PROD001"},
    )
    assert valid.empty
    assert len(rejected) == 1
    assert "INVALID_QUANTITY" in rejected.iloc[0]["rejection_reasons"]


def test_discount_outside_business_range_is_rejected():
    valid, rejected = validate_order_items(
        pd.DataFrame([make_order_item(discount_pct=1.5)]),
        valid_order_ids={"ORD001"}, valid_product_ids={"PROD001"},
    )
    assert valid.empty
    assert "INVALID_DISCOUNT" in rejected.iloc[0]["rejection_reasons"]
