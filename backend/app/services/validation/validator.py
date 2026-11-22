"""Mathematical integrity and semantic validation service (V1-V7, TC-03-04, TC-03-11)."""

from datetime import date, timedelta
from decimal import Decimal

from backend.app.models.schemas.ocr_schema import (
    CheckResult,
    InvoiceItem,
    InvoiceMeta,
    InvoiceTotals,
    MerchantInfo,
    ValidationReport,
)


def validate_extraction(
    totals: InvoiceTotals,
    items: list[InvoiceItem],
    merchant: MerchantInfo | None = None,
    invoice: InvoiceMeta | None = None,
    ocr_confidence: float = 1.0,
) -> ValidationReport:
    """Validate extraction results against math equations and semantic constraints (V1-V7).

    Returns a structured ValidationReport with status PASS, REVIEW, or FAIL.
    """
    checks: list[CheckResult] = []
    hard_failed = False
    passed_count = 0
    total_checks = 7

    # ---------------------------------------------------------------------
    # V1 (hard): Total amount > 0
    # ---------------------------------------------------------------------
    v1_passed = totals.total is not None and totals.total > 0
    if not v1_passed:
        hard_failed = True
    else:
        passed_count += 1
    checks.append(
        CheckResult(
            code="V1",
            passed=v1_passed,
            severity="hard",
            message_vi="Tổng tiền hóa đơn lớn hơn 0" if v1_passed else "Hóa đơn thiếu hoặc tổng tiền bằng 0",
        )
    )

    # ---------------------------------------------------------------------
    # V2 (soft): quantity * unit_price == line_total (±1 VND)
    # ---------------------------------------------------------------------
    v2_passed = True
    for item in items:
        if item.unit_price is not None and item.quantity is not None:
            expected_lt = Decimal(item.quantity) * Decimal(item.unit_price)
            if abs(expected_lt - Decimal(item.line_total)) > Decimal("1.0"):
                v2_passed = False
                break

    if v2_passed:
        passed_count += 1
    checks.append(
        CheckResult(
            code="V2",
            passed=v2_passed,
            severity="soft",
            message_vi="Số lượng nhân đơn giá khớp thành tiền món"
            if v2_passed
            else "Thành tiền của món bị lệch so với đơn giá x số lượng",
        )
    )

    # ---------------------------------------------------------------------
    # V3 (hard): Σ line_total + tax + service - discount ≈ total
    # Tolerance: max(1.000đ; 0.5% * total)
    # ---------------------------------------------------------------------
    items_sum = sum(item.line_total for item in items)
    tax = totals.tax_amount or 0
    service = totals.service_charge or 0
    discount = totals.discount or 0
    calculated_total = items_sum + tax + service - discount

    # Tolerance calculation (ADR-004, TC-03-11)
    tolerance = max(1000, int(0.005 * totals.total))
    diff = abs(calculated_total - totals.total)
    v3_passed = diff <= tolerance

    # If no items or only 1 single item matching total without subtotal
    if not items and totals.total > 0:
        v3_passed = False

    if not v3_passed:
        hard_failed = True
    else:
        passed_count += 1

    checks.append(
        CheckResult(
            code="V3",
            passed=v3_passed,
            severity="hard",
            message_vi=f"Tổng chi tiết khớp tổng in trên hóa đơn (lệch {diff:,} đ, trong dung sai {tolerance:,} đ)"
            if v3_passed
            else f"Lệch phương trình tổng tiền: tính {calculated_total:,} đ vs in {totals.total:,} đ (vượt dung sai {tolerance:,} đ)",
        )
    )

    # ---------------------------------------------------------------------
    # V4 (hard): At least 1 item extracted
    # ---------------------------------------------------------------------
    v4_passed = len(items) >= 1
    if not v4_passed:
        hard_failed = True
    else:
        passed_count += 1
    checks.append(
        CheckResult(
            code="V4",
            passed=v4_passed,
            severity="hard",
            message_vi="Nhận diện được danh sách món" if v4_passed else "Không tìm thấy dòng món hàng nào",
        )
    )

    # ---------------------------------------------------------------------
    # V5 (soft): Invoice date valid (not in future, not older than 1 year)
    # ---------------------------------------------------------------------
    today = date.today()
    one_year_ago = today - timedelta(days=365)
    inv_date = invoice.invoice_date if invoice else today
    v5_passed = one_year_ago <= inv_date <= today
    if v5_passed:
        passed_count += 1
    checks.append(
        CheckResult(
            code="V5",
            passed=v5_passed,
            severity="soft",
            message_vi=f"Ngày hóa đơn hợp lệ ({inv_date})" if v5_passed else f"Ngày hóa đơn bất thường ({inv_date})",
        )
    )

    # ---------------------------------------------------------------------
    # V6 (soft): Merchant name present and not placeholder
    # ---------------------------------------------------------------------
    m_name = merchant.name if merchant else ""
    v6_passed = bool(m_name and len(m_name.strip()) >= 3 and m_name.strip() != "Cửa hàng")
    if v6_passed:
        passed_count += 1
    checks.append(
        CheckResult(
            code="V6",
            passed=v6_passed,
            severity="soft",
            message_vi=f"Có tên cửa hàng: {m_name}" if v6_passed else "Chưa nhận diện rõ tên cửa hàng",
        )
    )

    # ---------------------------------------------------------------------
    # V7 (soft): Average OCR confidence >= 0.80
    # ---------------------------------------------------------------------
    v7_passed = ocr_confidence >= 0.80
    if v7_passed:
        passed_count += 1
    checks.append(
        CheckResult(
            code="V7",
            passed=v7_passed,
            severity="soft",
            message_vi=f"Độ tin cậy OCR cao ({ocr_confidence:.2f})"
            if v7_passed
            else f"Độ tin cậy OCR thấp ({ocr_confidence:.2f})",
        )
    )

    # Calculate score
    score = round(passed_count / total_checks, 2)

    # Determine status
    if hard_failed:
        status = "FAIL"
    elif score >= 0.80:
        status = "PASS"
    else:
        status = "REVIEW"

    return ValidationReport(status=status, score=score, checks=checks)
