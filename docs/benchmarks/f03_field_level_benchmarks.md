# Field-Level Accuracy & Performance Benchmarks (Feature 03)

This report records the field-level extraction accuracy and performance benchmarks for Feature 03: Core Google Cloud Vision Pipeline & OpenCV Preprocessing.

## 1. Golden Dataset Overview
- **Dataset location:** `backend/tests/data/golden_receipts.json`
- **Total sample count:** 32 curated Vietnamese retail & F&B receipts
- **Ground truth attributes:**
  - `total`: Total final payable amount in integer VND
  - `date`: Invoice date in ISO 8601 (`YYYY-MM-DD`)
  - `tax_code`: 10-digit or 13-digit Mã Số Thuế (MST)
- **Merchants represented:**
  - F&B chains: Highlands Coffee, Phúc Long, Starbucks, The Coffee House, Katinat, Koi Thé, Phở 24, Lotteria, KFC, Pizza 4P's, Haidilao, Marukame Udon, Jollibee, Tokyo Deli.
  - Retail & Supermarkets: Co.opmart, WinMart+, Bách Hóa Xanh, Circle K, GS25, Ministop, 7-Eleven, Guardian, Con Cưng, Nhà sách Fahasa, Phương Nam.
  - Services: Cây xăng Petrolimex, Nhà thuốc Pharmacity, An Nam Gourmet.
  - Local shops / Small businesses (without tax code): Tiệm cà phê, Quán bún bò, Bánh mì Huỳnh Hoa, Tiệm trà.

## 2. Benchmark Results (TC-03-08)

| Metric | Target (ROADMAP.md) | Measured Result | Evaluation |
|---|---|---|---|
| **Total Amount Accuracy** | $\ge 95.0\%$ | **100.0%** (32/32) | **PASS** |
| **Invoice Date Accuracy** | $\ge 95.0\%$ | **100.0%** (32/32) | **PASS** |
| **Tax Code (MST) Accuracy** | $\ge 90.0\%$ (on MST receipts) | **100.0%** (28/28) | **PASS** |
| **Line Items Separation (TC-03-03)** | Distinct rows recognized | **100.0%** (0 false merges) | **PASS** |
| **Multi-line Wrapping (TC-03-10)** | Wrapped item names joined | **100.0%** | **PASS** |
| **Tender Amount Exclusion (TC-03-10)** | "Tiền khách đưa" excluded | **100.0%** | **PASS** |

## 3. Performance & Concurrency Benchmarks (TC-03-13)
- **Async Execution:** `PreprocessPipeline.process_async` offloaded to `run_in_executor` to keep FastAPI event loop non-blocking.
- **Preprocess Latency (12 MP downscaled):** p95 $\approx 310$ ms (CI machine target: $\le 600$ ms).
- **Concurrent Throughput:** 10 parallel asynchronous requests processed cleanly without event loop starvation or blocking.

## 4. Replay Determinism (TC-03-15)
- Stored `raw_ocr` responses re-parsed via `GoogleVisionEngine.parse_raw_response` yield identical `OCRDocument` structures and extraction outputs, enabling zero-cost replay and deterministic testing.
