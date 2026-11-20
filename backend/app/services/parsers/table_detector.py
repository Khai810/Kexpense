"""Table and line items detection for Vietnamese receipts (TC-03-02, TC-03-03, TC-03-10)."""

import re
from datetime import date, time
from decimal import Decimal

from backend.app.models.schemas.ocr_schema import (
    InvoiceItem,
    InvoiceMeta,
    InvoiceTotals,
    MerchantInfo,
)
from backend.app.services.ocr.base import OCRLine
from backend.app.services.parsers.regex_patterns import (
    CHANGE_KEYWORDS,
    DISCOUNT_KEYWORDS,
    QTY_PRICE_PATTERN,
    SERVICE_CHARGE_KEYWORDS,
    SUBTOTAL_KEYWORDS,
    TAX_KEYWORDS,
    TENDER_KEYWORDS,
    TOTAL_KEYWORDS,
    normalize_text_nfc,
    parse_date,
    parse_money,
    parse_tax_code,
)


def _matches_any(text: str, patterns: list[str]) -> bool:
    """Check if normalized text matches any regex keyword pattern."""
    return any(re.search(pat, text, re.IGNORECASE) for pat in patterns)


def extract_merchant_info(lines: list[OCRLine]) -> MerchantInfo:
    """Extract store name, tax code, phone and address using Vietnamese receipt heuristics."""
    store_name = "Cửa hàng"
    tax_code = None
    address = None
    phone = None

    # Skip generic header keywords
    skip_header_patterns = [
        r"^h[oó]a\s*đ[oơ]n",
        r"^phi[ếe]u\s*t[íi]nh\s*ti[ềe]n",
        r"^phi[ếe]u\s*thanh\s*to[áa]n",
        r"^receipt",
        r"^invoice",
        r"^bill",
        r"^b[ảa]n\s*in",
    ]

    candidate_names: list[str] = []

    # Check first 8 lines
    for _idx, line in enumerate(lines[:8]):
        text = normalize_text_nfc(line.text)
        if not text:
            continue

        # Look for tax code
        if tax_code is None:
            found_mst = parse_tax_code(text)
            if found_mst:
                tax_code = found_mst
                continue

        # Look for address
        if re.search(r"^(đ[iị]a\s*ch[iỉ]|đ\/c|add|address)\s*[:\.]?", text, re.IGNORECASE):
            address = text
            continue

        # Look for phone
        phone_match = re.search(r"(?:tel|sđt|phone|hotline)\s*[:\.]?\s*([0-9\.\s]{9,15})", text, re.IGNORECASE)
        if phone_match:
            phone = re.sub(r"[\s\.]", "", phone_match.group(1))
            continue

        if _matches_any(text, skip_header_patterns):
            continue

        # Check for prominent merchant keywords
        if re.search(
            r"\b(công ty|nhà hàng|quán|siêu thị|mart|coffee|cafe|trà sữa|bakery|shop|cửa hàng)\b", text, re.IGNORECASE
        ) or (len(text) >= 3 and not re.search(r"\d{5,}", text)):
            candidate_names.append(text)

    if candidate_names:
        store_name = candidate_names[0]

    return MerchantInfo(
        name=store_name[:255],
        tax_code=tax_code,
        address=address[:500] if address else None,
        phone=phone[:50] if phone else None,
    )


def extract_invoice_meta(lines: list[OCRLine]) -> InvoiceMeta:
    """Extract invoice number, date, time and payment method."""
    inv_date = date.today()
    inv_time = None
    inv_number = None
    payment_method = None

    for line in lines:
        text = normalize_text_nfc(line.text)

        # Date extraction
        if inv_date == date.today():
            parsed_d = parse_date(text)
            if parsed_d:
                inv_date = parsed_d

        # Time extraction (e.g. 14:30 or 14:30:15)
        time_match = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?\b", text)
        if time_match and not inv_time:
            try:
                h, m = int(time_match.group(1)), int(time_match.group(2))
                s = int(time_match.group(3)) if time_match.group(3) else 0
                inv_time = time(h, m, s)
            except ValueError:
                pass

        # Invoice number extraction (Số HĐ, Số phiếu, Số bill, Số HD)
        num_match = re.search(
            r"(?:s[ốo]\s*(?:h[đd]|phi[ếe]u|bill|h[oó]a\s*đ[oơ]n)|no\.?)\s*[:\.]?\s*([A-Za-z0-9\-_]+)",
            text,
            re.IGNORECASE,
        )
        if num_match and not inv_number:
            inv_number = num_match.group(1)

        # Payment method
        if re.search(r"\b(ti[ềe]n\s*m[ặa]t|cash)\b", text, re.IGNORECASE):
            payment_method = "Tiền mặt"
        elif re.search(r"\b(chuy[ểe]n\s*kho[ảa]n|banking|qr\s*code|momo|vnpay)\b", text, re.IGNORECASE):
            payment_method = "Chuyển khoản / QR"
        elif re.search(r"\b(th[ẻe]|card|visa|master)\b", text, re.IGNORECASE):
            payment_method = "Thẻ"

    return InvoiceMeta(
        invoice_number=inv_number,
        invoice_date=inv_date,
        invoice_time=inv_time,
        currency="VND",
        payment_method=payment_method,
    )


def extract_totals(lines: list[OCRLine]) -> InvoiceTotals:
    """Extract printed total, subtotal, discount, tax, service charge, and paid amount."""
    total_val: int | None = None
    subtotal_val: int | None = None
    discount_val = 0
    tax_val: int | None = None
    service_charge_val = 0
    paid_val: int | None = None

    # Search in reverse (totals are usually at bottom of receipts)
    for line in reversed(lines):
        text = normalize_text_nfc(line.text)

        # 1. Tendered / Cash Given (must be checked to avoid confusing with Total)
        if _matches_any(text, TENDER_KEYWORDS):
            amt = parse_money(text)
            if amt is not None and paid_val is None:
                paid_val = amt
            continue

        # 2. Change / Returned
        if _matches_any(text, CHANGE_KEYWORDS):
            continue

        # 3. Final Total
        if total_val is None and _matches_any(text, TOTAL_KEYWORDS):
            amt = parse_money(text)
            if amt is not None:
                total_val = amt
            continue

        # 4. Subtotal / Tạm tính
        if subtotal_val is None and _matches_any(text, SUBTOTAL_KEYWORDS):
            amt = parse_money(text)
            if amt is not None:
                subtotal_val = amt
            continue

        # 5. Discount
        if _matches_any(text, DISCOUNT_KEYWORDS):
            amt = parse_money(text)
            if amt is not None and discount_val == 0:
                discount_val = amt
            continue

        # 6. Tax / VAT
        if tax_val is None and _matches_any(text, TAX_KEYWORDS):
            amt = parse_money(text)
            if amt is not None:
                tax_val = amt
            continue

        # 7. Service charge
        if service_charge_val == 0 and _matches_any(text, SERVICE_CHARGE_KEYWORDS):
            amt = parse_money(text)
            if amt is not None:
                service_charge_val = amt
            continue

    return InvoiceTotals(
        subtotal=subtotal_val,
        discount=discount_val,
        tax_amount=tax_val,
        service_charge=service_charge_val,
        total=total_val if total_val is not None else (subtotal_val or 0),
        paid_amount=paid_val,
    )


META_HEADER_PATTERNS = [
    r"^(?:mst|mã\s*số\s*thuế|tax\s*code|tax\s*id)\b",
    r"^(?:đ\/c|địa\s*chỉ|add|address)\b",
    r"^(?:tel|sđt|phone|hotline)\b",
    r"^(?:số\s*(?:hđ|phiếu|bill|hóa\s*đơn)|no\.?)\b",
    r"^(?:ngày|date)\b",
    r"^\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2}$",
    r"^\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}$",
    r"^(?:thu\s*ngân|cashier|nv|nhân\s*viên)\b",
    r"^(?:khách\s*hàng|customer|bàn|table)\b",
    r"^(?:hóa\s*đơn|phiếu\s*tính\s*tiền|phiếu\s*thanh\s*toán|receipt|bill)\b",
    r"^[\-\=\*\._\s]{3,}$",
    r"^(?:stt|tên\s*hàng|mặt\s*hàng|đơn\s*giá|số\s*lượng|thành\s*tiền|đvt)\b",
]


def _is_meta_header_line(text: str) -> bool:
    return any(re.search(pat, text, re.IGNORECASE) for pat in META_HEADER_PATTERNS)


def extract_table_items(lines: list[OCRLine]) -> list[InvoiceItem]:
    """Parse item lines including multi-line wrapped item names and Qty x Price patterns (TC-03-03, TC-03-10)."""
    items: list[InvoiceItem] = []
    line_no = 1

    # Locate footer start index (e.g. Tạm tính, Tổng cộng) to exclude summary rows
    footer_idx = len(lines)
    for i, line in enumerate(lines):
        txt = normalize_text_nfc(line.text)
        if _matches_any(txt, TOTAL_KEYWORDS + SUBTOTAL_KEYWORDS + TENDER_KEYWORDS + CHANGE_KEYWORDS):
            footer_idx = i
            break

    # Look for items in the body section
    body_lines = lines[:footer_idx]

    # Filter candidate lines, excluding store header (idx 0), meta headers, and short separators
    candidate_entries: list[tuple[int, OCRLine, str]] = []
    for idx, line in enumerate(body_lines):
        txt = normalize_text_nfc(line.text)
        if idx == 0:  # store name header line
            continue
        if _is_meta_header_line(txt):
            continue
        if len(txt) < 2:
            continue
        candidate_entries.append((idx, line, txt))

    c_idx = 0
    while c_idx < len(candidate_entries):
        _orig_idx, line, text = candidate_entries[c_idx]

        qty_price_match = QTY_PRICE_PATTERN.search(text)
        if qty_price_match:
            raw_qty = qty_price_match.group(1).replace(",", ".")
            raw_price = qty_price_match.group(2)
            qty = Decimal(raw_qty) if float(raw_qty) > 0 else Decimal("1.0")
            u_price = parse_money(raw_price)

            name_part = text[: qty_price_match.start()].strip()

            # Handle multi-line continuation (TC-03-10):
            # If previous candidate line had no price and wasn't consumed as an item
            if c_idx > 0 and not QTY_PRICE_PATTERN.search(candidate_entries[c_idx - 1][2]):
                prev_text = candidate_entries[c_idx - 1][2]
                if not any(it.name in prev_text for it in items):
                    name_part = f"{prev_text} {name_part}".strip()

            if not name_part:
                name_part = f"Mặt hàng {line_no}"

            money_vals = [parse_money(token) for token in text.split() if parse_money(token) is not None]
            line_tot = money_vals[-1] if money_vals else None

            if line_tot is None and u_price is not None:
                line_tot = int(qty * u_price)
            elif line_tot is not None and u_price is None:
                u_price = int(line_tot / qty) if qty > 0 else line_tot

            item = InvoiceItem(
                line_no=line_no,
                name=clean_item_name(name_part),
                quantity=qty,
                unit=None,
                unit_price=u_price,
                line_total=line_tot or 0,
                category_slug=None,
                confidence=line.confidence,
                bbox=line.bbox,
            )
            items.append(item)
            line_no += 1
            c_idx += 1
            continue

        # Single line item with price at end (e.g., "Cà phê đen đá 25.000")
        tokens = text.split()
        if len(tokens) >= 2:
            price_cand = parse_money(tokens[-1])
            if price_cand is not None and price_cand > 0:
                name_part = " ".join(tokens[:-1])
                item = InvoiceItem(
                    line_no=line_no,
                    name=clean_item_name(name_part),
                    quantity=Decimal("1.0"),
                    unit=None,
                    unit_price=price_cand,
                    line_total=price_cand,
                    category_slug=None,
                    confidence=line.confidence,
                    bbox=line.bbox,
                )
                items.append(item)
                line_no += 1
                c_idx += 1
                continue

        c_idx += 1

    return items


def clean_item_name(name: str) -> str:
    """Clean item name, removing leading numbering or SKU codes."""
    cleaned = normalize_text_nfc(name)
    # Strip leading "1.", "01/", etc.
    cleaned = re.sub(r"^\d+[\.\/\-]\s*", "", cleaned)
    # Strip SKU prefix e.g. "SP01 "
    cleaned = re.sub(r"^[A-Z0-9]{4,10}\s+", "", cleaned)
    return cleaned.strip() or "Mặt hàng"
