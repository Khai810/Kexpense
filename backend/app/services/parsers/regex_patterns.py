"""Vietnamese receipt regex patterns, cleaners, and extraction functions (TC-03-02, TC-03-09, TC-03-10)."""

import re
import unicodedata
from datetime import date

# -------------------------------------------------------------------------
# Regex Pattern Definitions
# -------------------------------------------------------------------------

# Total amount keywords (high priority)
TOTAL_KEYWORDS = [
    r"t[ổo]ng\s*c[ộo]ng",
    r"t[ổo]ng\s*ti[ềe]n\s*thanh\s*to[áa]n",
    r"t[ổo]ng\s*thanh\s*to[áa]n",
    r"thanh\s*to[áa]n",
    r"t[ổo]ng\s*ti[ềe]n",
    r"c[ầa]n\s*thanh\s*to[áa]n",
    r"t[ổo]ng\s*ph[ảa]i\s*tr[ảa]",
    r"total\s*amount",
    r"grand\s*total",
    r"total",
]

# Exclusion keywords that must NOT be confused with Total (TC-03-10)
TENDER_KEYWORDS = [
    r"ti[ềe]n\s*kh[áa]ch\s*[đd][ưu]a",
    r"kh[áa]ch\s*[đd][ưu]a",
    r"ti[ềe]n\s*m[ặa]t",
    r"cash",
    r"tendered",
]

CHANGE_KEYWORDS = [
    r"ti[ềe]n\s*th[ừu]a",
    r"ti[ềe]n\s*th[ốo]i",
    r"tr[ảa]\s*l[ạa]i",
    r"change",
]

SUBTOTAL_KEYWORDS = [
    r"t[ạa]m\s*t[íi]nh",
    r"ti[ềe]n\s*h[àa]ng",
    r"c[ộo]ng\s*ti[ềe]n\s*h[àa]ng",
    r"subtotal",
    r"sub\s*total",
]

DISCOUNT_KEYWORDS = [
    r"gi[ảa]m\s*gi[áa]",
    r"chi[ếe]t\s*kh[ấa]u",
    r"khuy[ếe]n\s*m[ãa]i",
    r"voucher",
    r"coupon",
    r"discount",
]

TAX_KEYWORDS = [
    r"thu[ếe]\s*gtgt",
    r"thu[ếe]\s*su[ấa]t",
    r"thu[ếe]\s*vat",
    r"ti[ềe]n\s*thu[ếe]",
    r"vat",
    r"tax",
]

SERVICE_CHARGE_KEYWORDS = [
    r"ph[íi]\s*d[ịi]ch\s*v[ụu]",
    r"service\s*charge",
    r"service\s*fee",
]

TAX_CODE_KEYWORDS = [
    r"m[ãa]\s*s[ốo]\s*thu[ếe]",
    r"mst",
    r"tax\s*code",
    r"tax\s*id",
]

# Date patterns: dd/mm/yyyy, dd-mm-yyyy, dd.mm.yyyy, yyyy-mm-dd
DATE_PATTERNS = [
    # Ngày 15 tháng 08 năm 2026 or Ngày 15/08/2026
    r"ng[àa]y\s*(\d{1,2})\s*th[áa]ng\s*(\d{1,2})\s*n[ăa]m\s*(\d{4})",
    r"ng[àa]y\s*:\s*(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})",
    # YYYY-MM-DD
    r"(\d{4})[\/\-\.](\d{1,2})[\/\-\.](\d{1,2})",
    # DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
    r"(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})",
    # DD/MM/YY
    r"(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2})",
]

# Quantity x Price pattern (e.g., 2 x 35.000 or 2x35,000)
QTY_PRICE_PATTERN = re.compile(r"(?:^|\s)(\d{1,4}(?:[,\.]\d{1,3})?)\s*[xX*]\s*([0-9\.,OolISsBb]{3,12})")


# -------------------------------------------------------------------------
# Normalization and Helper Functions
# -------------------------------------------------------------------------


def normalize_text_nfc(text: str) -> str:
    """Normalize text into Unicode NFC form and strip control characters."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFC", text)
    # Remove non-printable control characters except newline and tab
    cleaned = "".join(
        ch for ch in normalized if ch == "\n" or ch == "\t" or not unicodedata.category(ch).startswith("C")
    )
    return cleaned.strip()


def fix_ocr_digit_confusions(num_str: str) -> str:
    """Repair common OCR character confusions in numeric currency fields."""
    replacements = {
        "O": "0",
        "o": "0",
        "I": "1",
        "l": "1",
        "S": "5",
        "s": "5",
        "B": "8",
    }
    res = []
    for ch in num_str:
        res.append(replacements.get(ch, ch))
    return "".join(res)


def format_money(val: int) -> str:
    """Format integer VND into canonical dotted string for testing."""
    return f"{val:,}".replace(",", ".")


def parse_money(val_str: str | None) -> int | None:
    """Parse a Vietnamese currency string into integer VND (ADR-004, TC-03-09).

    Handles thousands dots/commas and trailing currency indicators (đ, vnd, vnđ).
    Returns None if no valid monetary value can be extracted.
    """
    if not val_str:
        return None

    cleaned = normalize_text_nfc(val_str).strip()

    # Exclude if it is primarily a date or time
    if re.search(r"^\s*\d{1,4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,4}\s*$", cleaned):
        return None
    if re.search(r"^\s*\d{1,2}:\d{2}(?::\d{2})?\s*$", cleaned):
        return None

    # Remove dates and times embedded in string
    cleaned = re.sub(r"\b\d{1,4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,4}\b", "", cleaned)
    cleaned = re.sub(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", "", cleaned)
    # Remove percentage like (8%) or 10%
    cleaned = re.sub(r"\b\d+\s*%\b", "", cleaned)

    # Must contain at least one ASCII digit
    if not re.search(r"\d", cleaned):
        return None

    # Find monetary number patterns:
    tokens = re.findall(r"[0-9OolISsBb]+(?:[\.,][0-9OolISsBb]+)+|\b\d+\b", cleaned)
    if not tokens:
        return None

    # Filter tokens that have at least one digit
    valid_tokens = [t for t in tokens if re.search(r"\d", t)]
    if not valid_tokens:
        return None

    raw_num = valid_tokens[-1]
    raw_num = fix_ocr_digit_confusions(raw_num)
    raw_num = re.sub(r"[^\d\.,]", "", raw_num)
    if not raw_num:
        return None

    # Handle decimal / thousand separator conventions:
    if "." in raw_num and "," in raw_num:
        last_dot = raw_num.rfind(".")
        last_comma = raw_num.rfind(",")
        if last_dot > last_comma:
            integer_part = raw_num[:last_dot].replace(",", "")
        else:
            integer_part = raw_num[:last_comma].replace(".", "")
    elif "." in raw_num:
        parts = raw_num.split(".")
        if all(len(p) == 3 for p in parts[1:]):
            integer_part = "".join(parts)
        elif len(parts) == 2 and len(parts[1]) <= 2:
            integer_part = parts[0]
        else:
            integer_part = "".join(parts)
    elif "," in raw_num:
        parts = raw_num.split(",")
        if all(len(p) == 3 for p in parts[1:]):
            integer_part = "".join(parts)
        elif len(parts) == 2 and len(parts[1]) <= 2:
            integer_part = parts[0]
        else:
            integer_part = "".join(parts)
    else:
        integer_part = raw_num

    try:
        val = int(integer_part)
        return val if val >= 0 else None
    except ValueError:
        return None


def parse_date(date_str: str | None) -> date | None:
    """Parse date from Vietnamese invoice text into date object (YYYY-MM-DD)."""
    if not date_str:
        return None

    text = normalize_text_nfc(date_str).lower()

    # Try matching patterns
    for pat in DATE_PATTERNS:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            groups = match.groups()
            try:
                if len(groups) == 3:
                    p1, p2, p3 = int(groups[0]), int(groups[1]), int(groups[2])
                    # Case 1: YYYY-MM-DD
                    if p1 > 1000:
                        y, m, d = p1, p2, p3
                    else:
                        # Case 2: DD-MM-YYYY or DD-MM-YY
                        d, m = p1, p2
                        y = p3 + 2000 if p3 < 100 else p3

                    # Validate calendar constraints
                    if 1 <= m <= 12 and 1 <= d <= 31 and 2000 <= y <= 2099:
                        return date(y, m, d)
            except ValueError:
                continue

    return None


def parse_tax_code(text: str | None) -> str | None:
    """Extract 10 or 13-digit Vietnamese Mã Số Thuế (MST)."""
    if not text:
        return None

    normalized = normalize_text_nfc(text)

    # Search for tax code pattern: 10 digits optionally followed by -3 digits
    # First look around MST keywords
    for kw in TAX_CODE_KEYWORDS:
        pattern = rf"{kw}\s*[:\-]?\s*([0-9]{{10}}(?:[\s\-]?[0-9]{{3}})?)"
        match = re.search(pattern, normalized, re.IGNORECASE)
        if match:
            clean_mst = re.sub(r"[\s\-]", "", match.group(1))
            if len(clean_mst) in (10, 13):
                return clean_mst

    # Standalone 10 or 13 digit pattern
    match = re.search(r"\b(\d{10}(?:-\d{3})?)\b", normalized)
    if match:
        clean_mst = match.group(1).replace("-", "")
        if len(clean_mst) in (10, 13):
            return clean_mst

    return None
