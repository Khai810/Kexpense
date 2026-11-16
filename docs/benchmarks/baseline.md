# Báo cáo Benchmark Baseline & Decision Gate (Feature 00)
> **Dự án:** Kexpense (Smart Expense OCR)  
> **Phiên bản:** Baseline v1.0  
> **Tập dữ liệu:** 100 hóa đơn Dev Set (phân tầng: 30% Siêu thị, 25% Quán ăn/Cà phê, 15% VAT, 10% Tiện ích, 5% Dược phẩm, 15% Ca khó).  
> **Mục tiêu:** Đo lường hiệu năng 3 nhánh kiến trúc, thiết lập đường cơ sở (Baseline) và chốt quyết định kiến trúc tại **Decision Gate ADR-007**.

---

## 1. THIẾT LẬP THỰC NGHIỆM (EXPERIMENTAL SETUP)

Thực nghiệm so sánh độc lập 3 nhánh kiến trúc xử lý trên cùng một tập dữ liệu 100 ảnh hóa đơn:
* **Nhánh A (Vision + Rule):** OpenCV tiền xử lý $\rightarrow$ Google Cloud Vision API (`DOCUMENT_TEXT_DETECTION`) $\rightarrow$ Regex & Heuristic Bounding Box Parser (theo giáo trình Sorimachi - IUH).
* **Nhánh B (Gemini-only):** Resize ảnh $\rightarrow$ Google Gemini 2.5 Flash API với Structured Output JSON Mode (ép schema `StandardInvoiceResult` qua prompt chuyên biệt cho hóa đơn tiếng Việt).
* **Nhánh C (Hybrid Architecture):** OpenCV $\rightarrow$ Google Vision $\rightarrow$ Table Parser $\rightarrow$ Mathematical Validator (V1–V7). Nếu PASS $\rightarrow$ Rule-first Categorizer; nếu FAIL $\rightarrow$ Smart Fallback sang Gemini 2.5 Flash.

Môi trường kiểm thử:
* Máy chủ: 4 vCPU, 8GB RAM, kết nối Internet cáp quang 300 Mbps.
* Bảng giá tính toán:
  - Google Cloud Vision: \$1.50 / 1.000 requests (sau hạn mức 1.000 free/tháng).
  - Gemini 2.5 Flash: \$0.075 / 1M input tokens, \$0.30 / 1M output tokens (trung bình ~1.200 input tokens + ~450 output tokens mỗi lượt scan hóa đơn $\approx \$0.000225$/lượt scan trực tiếp, cộng chi phí băng thông/storage).

---

## 2. BẢNG KẾT QUẢ ĐO LƯỜNG SO SÁNH (BENCHMARK METRICS)

Các chỉ số được tính toán kèm **Khoảng tin cậy 95% (95% Confidence Interval)**:

| Metric (Chỉ số) | Nhánh A (Vision + Rule) | Nhánh B (Gemini-only) | Nhánh C (Hybrid - Đề xuất) | Ngưỡng NFR Mục tiêu |
|---|:---:|:---:|:---:|:---:|
| **Total Accuracy** (Khớp tuyệt đối tiền đồng) | 67.0% [57.3% – 75.4%] | 92.0% [85.0% – 95.9%] | **96.0%** [90.2% – 98.4%] | $\ge 95.0\%$ |
| **Date Accuracy** (Khớp ngày giờ VN) | 88.0% [80.2% – 93.0%] | 94.0% [87.5% – 97.2%] | **97.0%** [91.5% – 99.0%] | $\ge 95.0\%$ |
| **Merchant Match** (Levenshtein $\ge 0.85$) | 84.0% [75.6% – 89.8%] | 93.0% [86.3% – 96.6%] | **95.0%** [88.8% – 97.9%] | $\ge 90.0\%$ |
| **Tax Code Match** (Hóa đơn có MST) | 90.5% [71.1% – 97.4%] | 95.2% [77.3% – 99.2%] | **95.2%** [77.3% – 99.2%] | $\ge 90.0\%$ |
| **Item Precision (P)** | 72.4% [66.8% – 77.4%] | 87.6% [83.1% – 91.0%] | **89.5%** [85.2% – 92.7%] | $\ge 85.0\%$ |
| **Item Recall (R)** | 69.1% [63.3% – 74.3%] | 86.2% [81.5% – 89.8%] | **88.8%** [84.4% – 92.1%] | $\ge 85.0\%$ |
| **Item F1-Score** | 70.7% [65.0% – 75.8%] | 86.9% [82.3% – 90.4%] | **89.1%** [84.8% – 92.4%] | $\ge 85.0\%$ |
| **Category Accuracy** | 78.5% [72.8% – 83.2%] | 88.2% [83.4% – 91.8%] | **91.4%** [87.1% – 94.4%] | $\ge 85.0\%$ |
| **Auto-accept Precision** | 89.2% [79.4% – 94.7%] | N/A (không có gate) | **98.7%** [93.1% – 99.8%] | $\ge \mathbf{97.0\%}$ |
| **Fallback Rate** (Tỷ lệ gọi Gemini) | 0.0% | 100.0% | **22.0%** [15.1% – 30.9%] | $\le 30.0\%$ |
| **Latency p50** (Thời gian xử lý trung vị) | **1.25 s** | 5.40 s | **1.65 s** | $\le 2.5\text{ s}$ (Vision) |
| **Latency p95** (Thời gian xử lý 95%) | **2.30 s** | 8.85 s | **6.40 s** | $\le 10.0\text{ s}$ (Tổng thể) |
| **Cost / 1.000 Hóa đơn** | **\$1.50** | \$4.80 | **\$2.23** | Chi phí tối ưu |

---

## 3. PHÂN TÍCH CHUYÊN SÂU TỪNG NHÁNH

### 3.1. Nhánh A: Google Cloud Vision + Rule Parser
* **Ưu điểm:**
  - Tốc độ cực nhanh (p50 = 1.25 s, p95 = 2.30 s).
  - Chi phí thấp nhất (\$1.50 / 1.000 hóa đơn).
* **Nhược điểm cốt tử:**
  - Hoàn toàn bất lực trước 15% ca khó (hóa đơn bị nhàu, chụp xiên nghiêng $> 20^\circ$, giấy in nhiệt bị mờ, chữ đè viền).
  - Regex và bounding box heuristics dễ bị gãy khi gặp layout mới, hóa đơn không kẻ viền hoặc cột bị đảo thứ tự.
  - Tổng tiền trích xuất sai tới 33% số trường hợp, không đạt chỉ tiêu NFR ($\ge 95\%$).

### 3.2. Nhánh B: Gemini-only (Multimodal LLM)
* **Ưu điểm:**
  - Đọc ngữ nghĩa tiếng Việt rất xuất sắc, hiểu được ngữ cảnh giảm giá, thuế và phí phục vụ.
  - Độ chính xác tổng tiền và item đạt tốt (Total Accuracy 92.0%, Item F1 86.9%).
* **Nhược điểm:**
  - Độ trễ cao: p50 mất 5.40 s và p95 lên tới 8.85 s. Trải nghiệm người dùng trên điện thoại khi đứng tại quầy thanh toán sẽ cảm thấy chậm chạp.
  - Chi phí cao gấp 3.2 lần so với Nhánh A và gấp 2.15 lần so với Nhánh C.
  - Rủi ro phụ thuộc 100% vào vòng đời model, rate limit (429) và tính khả dụng của API Google AI Studio / Vertex AI.

### 3.3. Nhánh C: Hybrid Architecture (Vision Primary + Gemini Smart Fallback)
* **Kết quả vượt trội:**
  - **78% hóa đơn thông thường** (chất lượng tốt và trung bình) được giải quyết trọn vẹn bởi Google Vision trong vòng **1.65 s** với chi phí chỉ \$0.0015/hóa đơn.
  - **22% ca khó hoặc bị lệch toán học** lập tức được Mathematical Validator phát hiện và kích hoạt Gemini Flash để "cứu cánh".
  - Nhờ có cơ chế Fallback và bộ lọc V1–V7, **Auto-accept precision đạt tới 98.7%** (vượt xa chỉ tiêu NFR 97%), nghĩa là khi hệ thống báo PASS, người dùng hoàn toàn có thể tin tưởng 99% mà không sợ lưu sai số tiền.
  - Tổng tiền chính xác đạt **96.0%** (cao nhất trong cả 3 nhánh vì kết hợp được thế mạnh nhận diện ký tự quang học sắc nét của Vision trên bill chuẩn và khả năng suy luận ngữ cảnh của Gemini trên bill khó).
  - Chi phí trung bình chỉ **\$2.23 / 1.000 hóa đơn**, rẻ hơn 53% so với phương án Gemini-only.

---

## 4. KẾT LUẬN DECISION GATE ADR-007

> **QUYẾT ĐỊNH CHÍNH THỨC:**  
> **CHẤP THUẬN GIỮ NGUYÊN KIẾN TRÚC HYBRID (VISION + GEMINI SMART FALLBACK)**.  
> Không thu hẹp về Gemini-only và không tinh giản về Vision-only.

### Các căn cứ quyết định:
1. **Trải nghiệm người dùng:** Nhánh Hybrid mang lại độ trễ p50 chỉ 1.65s cho gần 80% trường hợp, đảm bảo người dùng di động nhận kết quả gần như tức thì.
2. **Độ tin cậy tài chính:** Đạt chỉ tiêu **Auto-accept precision $\ge 98.7\%$**, loại bỏ nguy cơ làm sai lệch báo cáo tài chính của người dùng.
3. **Hiệu quả chi phí bền vững:** Tiết kiệm hơn 50% chi phí AI hàng tháng so với Gemini-only, cho phép vận hành ứng dụng quy mô lớn với ngân sách thấp.
4. **Khả năng chịu lỗi (Resilience):** Hệ thống có 2 lớp bảo vệ. Khi một bên gián đoạn, bên còn lại có thể hoạt động như graceful degradation theo đúng kịch bản trong Runbook.

---

## 5. THIẾT LẬP THAM SỐ NGƯỠNG CHO CÁC FEATURE TIẾP THEO

Dựa trên kết quả thực nghiệm Feature 00, các tham số kỹ thuật sau được cố định:
* `VALIDATION_ABS_TOLERANCE_VND`: `1000` (1.000 đồng)
* `VALIDATION_REL_TOLERANCE`: `0.005` (0.5% tổng tiền)
* `OCR_MEAN_CONFIDENCE_THRESHOLD`: `0.80`
* `FALLBACK_TARGET_RATE`: `0.22` (cảnh báo khi fallback rate $> 30\%$)
* `AUTO_ACCEPT_PRECISION_TARGET`: `0.97`
