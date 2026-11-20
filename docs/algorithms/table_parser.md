# Vietnamese Receipt Parser & Table Detector Algorithms

This document describes the pure deterministic parsing algorithms implemented in `backend/app/services/parsers/` (Feature 03).

## 1. Text Normalization & Cleaners (`regex_patterns.py`)
- **Unicode NFC Normalization:** All OCR strings undergo NFC normalization (`unicodedata.normalize("NFC", text)`) to eliminate decomposed vowel/tone mark variations (e.g. `e` + `\u0301` vs `é`).
- **Currency Parsing (`parse_money`):**
  - Parses Vietnamese monetary values directly into integer VND (`BIGINT`, ADR-004).
  - Handles thousands separators (`.` and `,`) and strips trailing currency abbreviations (`đ`, `vnđ`, `vnd`, `đồng`).
  - Filters out embedded date patterns (`DD/MM/YYYY`, `YYYY-MM-DD`), time patterns (`HH:MM`), and percentages (`8%`).
  - **Digit confusion healing:** Repairs common OCR misread digits (`O/o` $\to$ `0`, `l/I` $\to$ `1`, `S/s` $\to$ `5`, `B` $\to$ `8`) only within valid numeric candidate tokens containing actual digits.
- **Date Parsing (`parse_date`):**
  - Extracts dates in Vietnamese receipt formats:
    - `Ngày DD tháng MM năm YYYY`
    - `DD/MM/YYYY`, `DD-MM-YYYY`, `DD.MM.YYYY`
    - `YYYY-MM-DD`, `YYYY/MM/DD`
    - `DD/MM/YY`

## 2. Receipt Zone Segmentation & Metadata Extraction (`table_detector.py`)

A retail receipt is partitioned into three logical sections:
1. **Header:** Merchant name, address, tax code (MST), invoice number, date, cashier.
2. **Body (Table Items):** Item rows, quantities, unit prices, line totals, discounts.
3. **Footer:** Subtotal, VAT/tax, service charge, grand total, tender amount, change.

### 2.1 Tender Amount Exclusion (TC-03-10)
- In many Vietnamese POS receipts, the customer gives a large denomination bill (e.g., "Tiền khách đưa: 500.000 đ") while the actual bill total is smaller (e.g., "Tổng cộng: 165.000 đ").
- The parser explicitly separates `TENDER_KEYWORDS` (`tiền khách đưa`, `khách đưa`, `tiền mặt`) and `CHANGE_KEYWORDS` (`tiền thừa`, `tiền thối`, `trả lại`).
- Tender amounts are mapped to `totals.paid_amount` and are strictly barred from being selected as `totals.total`.

### 2.2 Table Line Item Detection & Multi-line Wrapping
- **Meta-line filtering:** Lines matching headers, tax codes, addresses, invoice numbers, or table column headers (`Tên hàng`, `Đơn giá`, `Thành tiền`) are pruned from body candidates.
- **Quantity $\times$ Price Detection:** Evaluates regex pattern `r"(\d+(?:[,\.]\d+)?)\s*[xX*]\s*([0-9\.,]+)"` (e.g., `2 x 65.000`).
- **Multi-line Wrapping (TC-03-10):**
  - When an item name overflows onto a preceding line (e.g. Line 1: `Trà Sữa Ô Long Đậm Vị`, Line 2: `(Size L, 50% Đường) 2 x 65.000 130.000`), the algorithm links the preceding description into a single coherent item name.
  - Line numbers (e.g. `1.`, `02/`) and internal SKU codes are automatically trimmed via `clean_item_name`.
