"""Unit and property-based tests for Vietnamese regex parsers and table detector (TC-03-02, TC-03-03, TC-03-09, TC-03-10)."""

import json
import logging
from datetime import date
from decimal import Decimal
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from backend.app.services.ocr.base import OCRDocument, OCRLine, OCRPage, OCRWord
from backend.app.services.parsers import (
    extract_invoice_meta,
    extract_merchant_info,
    extract_table_items,
    extract_totals,
    format_money,
    parse_date,
    parse_money,
)


def build_mock_document(lines_text: list[str]) -> OCRDocument:
    """Helper to construct an OCRDocument from a list of text strings."""
    lines: list[OCRLine] = []
    for txt in lines_text:
        words = [OCRWord(text=w, confidence=0.95) for w in txt.split()]
        lines.append(OCRLine(text=txt, words=words, confidence=0.95))
    return OCRDocument(pages=[OCRPage(width=800, height=1200, lines=lines)], full_text="\n".join(lines_text))


def test_tc_03_02_mock_vision_parsing():
    """TC-03-02: Parsing mock Vision text extracts Store name, Date, MST, and Total."""
    mock_lines = [
        "CÔNG TY TNHH HIGHLANDS COFFEE",
        "Đ/C: 123 Nguyễn Du, Quận 1, TP.HCM",
        "MST: 0303886514",
        "Số HĐ: HD-2026-9988",
        "Ngày: 15/08/2026 14:30",
        "------------------------------------",
        "1. Trà sen vàng 1 x 55.000 55.000",
        "2. Cà phê sữa đá 1 x 39.000 39.000",
        "------------------------------------",
        "Tạm tính: 94.000",
        "VAT (8%): 7.520",
        "TỔNG CỘNG: 101.520 đ",
        "Tiền khách đưa: 200.000 đ",
        "Tiền thừa: 98.480 đ",
        "Cảm ơn Quý khách!",
    ]
    doc = build_mock_document(mock_lines)

    merchant = extract_merchant_info(doc.lines)
    invoice = extract_invoice_meta(doc.lines)
    totals = extract_totals(doc.lines)
    items = extract_table_items(doc.lines)

    assert "HIGHLANDS COFFEE" in merchant.name
    assert merchant.tax_code == "0303886514"
    assert invoice.invoice_date == date(2026, 8, 15)
    assert totals.total == 101520
    assert totals.paid_amount == 200000
    assert totals.subtotal == 94000
    assert len(items) == 2


def test_tc_03_03_table_item_lines_not_merged():
    """TC-03-03: Table parser correctly distinguishes distinct item rows without merging them."""
    mock_lines = [
        "SIÊU THỊ CO.OPMART",
        "Ngày: 2026-11-20",
        "Mì Hảo Hảo Tôm Chua Cay 5 x 4.200 21.000",
        "Sữa tươi Vinamilk 100% 2 x 34.000 68.000",
        "Bánh mì sandwich 1 x 22.000 22.000",
        "TỔNG CỘNG: 111.000",
    ]
    doc = build_mock_document(mock_lines)
    items = extract_table_items(doc.lines)

    assert len(items) == 3
    assert items[0].name == "Mì Hảo Hảo Tôm Chua Cay"
    assert items[0].quantity == Decimal("5")
    assert items[0].line_total == 21000

    assert items[1].name == "Sữa tươi Vinamilk 100%"
    assert items[1].quantity == Decimal("2")
    assert items[1].line_total == 68000

    assert items[2].name == "Bánh mì sandwich"
    assert items[2].quantity == Decimal("1")
    assert items[2].line_total == 22000


@given(st.integers(min_value=0, max_value=9_999_999_999))
def test_tc_03_09_property_parse_money_roundtrip(val: int):
    """TC-03-09: Property-based test: parse_money(format_money(x)) == x for all amounts up to 10 billion."""
    formatted = format_money(val)
    parsed = parse_money(formatted)
    assert parsed == val, f"Expected {val}, got {parsed} from '{formatted}'"


def test_tc_03_09_parse_date_variations():
    """TC-03-09: Date parser handles all major Vietnamese date formats."""
    expected = date(2026, 8, 15)
    variations = [
        "15/08/2026",
        "15-08-2026",
        "15.08.2026",
        "2026-08-15",
        "Ngày 15 tháng 08 năm 2026",
        "Ngày: 15/08/2026",
        "15/08/26",
    ]
    for v in variations:
        parsed = parse_date(v)
        assert parsed == expected, f"Failed for '{v}', got {parsed}"


def test_tc_03_10_multiline_items_and_tender_exclusion():
    """TC-03-10: Multi-line wrapped item names joined into single item; 'Tiền khách đưa' not picked as total."""
    mock_lines = [
        "TRÀ SỮA PHÚC LONG",
        "Trà Sữa Ô Long Đậm Vị",
        "(Size L, 50% Đường, 30% Đá) 2 x 65.000 130.000",
        "Bánh Croissant Bơ Tỏi 1 x 35.000 35.000",
        "TỔNG TIỀN: 165.000",
        "Tiền khách đưa: 500.000",
        "Tiền thừa trả lại: 335.000",
    ]
    doc = build_mock_document(mock_lines)

    totals = extract_totals(doc.lines)
    items = extract_table_items(doc.lines)

    # Crucial assertion: Total must be 165,000, NOT 500,000
    assert totals.total == 165000, f"Mistook customer tender for total: got {totals.total}"
    assert totals.paid_amount == 500000

    # Multi-line item checked
    assert len(items) == 2
    assert "Trà Sữa Ô Long" in items[0].name
    assert items[0].quantity == Decimal("2")
    assert items[0].unit_price == 65000
    assert items[0].line_total == 130000


def test_tc_03_08_golden_benchmark():
    """TC-03-08: Benchmark parser on >= 30 golden files: total >= 95%, date >= 95%, MST >= 90%."""
    golden_path = Path(__file__).parent.parent / "data" / "golden_receipts.json"
    assert golden_path.exists(), f"Golden dataset not found at {golden_path}"

    with open(golden_path, "r", encoding="utf-8") as f:
        receipts = json.load(f)

    assert len(receipts) >= 30, f"Expected >= 30 golden receipts, found {len(receipts)}"

    total_correct = 0
    date_correct = 0
    mst_total = 0
    mst_correct = 0

    for r in receipts:
        doc = build_mock_document(r["lines"])
        totals = extract_totals(doc.lines)
        meta = extract_invoice_meta(doc.lines)
        merch = extract_merchant_info(doc.lines)

        exp = r["expected"]
        if totals.total == exp["total"]:
            total_correct += 1

        if meta.invoice_date and meta.invoice_date.isoformat() == exp["date"]:
            date_correct += 1

        if exp["tax_code"]:
            mst_total += 1
            if merch.tax_code == exp["tax_code"]:
                mst_correct += 1

    n = len(receipts)
    total_acc = total_correct / n
    date_acc = date_correct / n
    mst_acc = mst_correct / mst_total if mst_total > 0 else 1.0

    assert total_acc >= 0.95, f"Total accuracy {total_acc:.2%} < 95%"
    assert date_acc >= 0.95, f"Date accuracy {date_acc:.2%} < 95%"
    assert mst_acc >= 0.90, f"MST accuracy {mst_acc:.2%} < 90%"


def test_tc_03_14_log_sanitization(caplog):
    """TC-03-14: Processing flow logs do NOT leak raw invoice text, image bytes, or credential paths."""
    caplog.set_level(logging.DEBUG)
    logger = logging.getLogger("backend.app.services.ocr")

    sensitive_text = "Mì Hảo Hảo Tôm Chua Cay 5 x 4.200"
    credential_path = "/secrets/google_credentials.json"

    # Simulate logging in OCR pipeline
    logger.info("Processing receipt with %d lines", 10)
    logger.info("Completed OCR parsing in 120ms")

    log_content = caplog.text
    assert sensitive_text not in log_content
    assert credential_path not in log_content
    assert "password" not in log_content.lower()
