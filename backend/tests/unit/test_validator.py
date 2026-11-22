"""Unit tests for ValidationReport matrix (V1-V7, TC-03-04, TC-03-11)."""

from datetime import date
from decimal import Decimal

from backend.app.models.schemas.ocr_schema import (
    InvoiceItem,
    InvoiceMeta,
    InvoiceTotals,
    MerchantInfo,
)
from backend.app.services.validation import validate_extraction


def test_tc_03_11_exact_math_match_pass():
    """TC-03-11: Perfect math match results in status PASS."""
    totals = InvoiceTotals(total=100000, subtotal=100000)
    items = [
        InvoiceItem(
            line_no=1,
            name="Cà phê",
            quantity=Decimal("2"),
            unit_price=50000,
            line_total=100000,
        )
    ]
    merchant = MerchantInfo(name="Highlands Coffee")
    invoice = InvoiceMeta(invoice_date=date.today())

    report = validate_extraction(totals, items, merchant, invoice, ocr_confidence=0.95)
    assert report.status == "PASS"
    assert report.score >= 0.80
    assert all(c.passed for c in report.checks)


def test_tc_03_11_tolerance_within_0_5_percent_pass():
    """TC-03-11: Math discrepancy within max(1.000, 0.5% * total) passes V3."""
    # Total = 1,000,000 -> 0.5% tolerance = 5,000 VND
    # Items sum = 997,000 (diff 3,000 VND <= 5,000 VND)
    totals = InvoiceTotals(total=1000000, subtotal=1000000)
    items = [
        InvoiceItem(
            line_no=1,
            name="Combo Lẩu",
            quantity=Decimal("1"),
            unit_price=997000,
            line_total=997000,
        )
    ]
    merchant = MerchantInfo(name="Haidilao")
    invoice = InvoiceMeta(invoice_date=date.today())

    report = validate_extraction(totals, items, merchant, invoice, ocr_confidence=0.90)
    v3_check = next(c for c in report.checks if c.code == "V3")
    assert v3_check.passed is True
    assert report.status == "PASS"


def test_tc_03_11_tolerance_exceeded_3_percent_fail():
    """TC-03-11: Math discrepancy of 3% (30,000 VND on 1,000,000) hard fails V3 -> FAIL."""
    totals = InvoiceTotals(total=1000000, subtotal=1000000)
    items = [
        InvoiceItem(
            line_no=1,
            name="Combo Lẩu",
            quantity=Decimal("1"),
            unit_price=970000,
            line_total=970000,
        )
    ]
    merchant = MerchantInfo(name="Haidilao")
    invoice = InvoiceMeta(invoice_date=date.today())

    report = validate_extraction(totals, items, merchant, invoice, ocr_confidence=0.90)
    v3_check = next(c for c in report.checks if c.code == "V3")
    assert v3_check.passed is False
    assert report.status == "FAIL"


def test_tc_03_11_missing_total_fail():
    """TC-03-11: Total = 0 or missing hard fails V1 -> FAIL."""
    totals = InvoiceTotals(total=0)
    items = [
        InvoiceItem(
            line_no=1,
            name="Bánh mì",
            quantity=Decimal("1"),
            unit_price=20000,
            line_total=20000,
        )
    ]
    report = validate_extraction(totals, items)
    v1_check = next(c for c in report.checks if c.code == "V1")
    assert v1_check.passed is False
    assert report.status == "FAIL"


def test_tc_03_11_zero_items_fail():
    """TC-03-11: Zero extracted items hard fails V4 -> FAIL."""
    totals = InvoiceTotals(total=50000)
    items = []
    report = validate_extraction(totals, items)
    v4_check = next(c for c in report.checks if c.code == "V4")
    assert v4_check.passed is False
    assert report.status == "FAIL"


def test_tc_03_11_discount_and_tax_matching_equation():
    """TC-03-11: Complex equation: sum(items) + tax + service - discount == total -> PASS."""
    # Items = 100k, tax = 8k, service = 5k, discount = 13k -> total = 100k
    totals = InvoiceTotals(
        subtotal=100000,
        tax_amount=8000,
        service_charge=5000,
        discount=13000,
        total=100000,
    )
    items = [
        InvoiceItem(
            line_no=1,
            name="Pizza Hải Sản",
            quantity=Decimal("1"),
            unit_price=100000,
            line_total=100000,
        )
    ]
    merchant = MerchantInfo(name="Pizza 4P's")
    invoice = InvoiceMeta(invoice_date=date.today())

    report = validate_extraction(totals, items, merchant, invoice, ocr_confidence=0.95)
    assert report.status == "PASS"
    v3_check = next(c for c in report.checks if c.code == "V3")
    assert v3_check.passed is True
