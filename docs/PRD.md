# Product Requirements Document (PRD) - Kexpense
> **Phiên bản:** v1.0 (Đã hoàn thiện sau Feature 00 Benchmark)  
> **Trạng thái:** Approved  
> **Chủ sở hữu:** Kexpense Core Team

---

## 1. TỔNG QUAN & TẦM NHÌN SẢN PHẨM (PRODUCT VISION)

### 1.1. Vấn đề của người dùng
Ghi chép chi tiêu cá nhân là thói quen tốt nhưng tỷ lệ bỏ dở lên tới trên 85% sau 2 tuần. Nguyên nhân cốt lõi:
- Nhập liệu thủ công từng món đồ, từng gói gia vị từ hóa đơn siêu thị/nhà hàng quá tốn thời gian, tẻ nhạt và dễ nhầm lẫn.
- Các ứng dụng hiện nay chỉ cho phép nhập một con số tổng cộng thô, làm mất đi dữ liệu chi tiết (ví dụ: biết đi siêu thị hết 800k nhưng không biết bao nhiêu tiền mua thịt, bao nhiêu tiền mua đồ gia dụng).

### 1.2. Giải pháp sản phẩm (Kexpense)
Kexpense giải quyết triệt để vấn đề trên bằng **Tự động hóa 100% bằng Thị giác Máy tính & Trí tuệ Nhân tạo**:
1. **Chụp ảnh:** Mở ứng dụng PWA trên điện thoại, chụp hoặc chọn ảnh hóa đơn bán lẻ/siêu thị/nhà hàng/tiện ích.
2. **Bóc tách thông minh (Hybrid OCR):** Hệ thống tự động tiền xử lý ảnh (OpenCV), bóc tách từng dòng sản phẩm, đơn giá, số lượng, tổng tiền và tự động gán danh mục chi tiêu qua kiến trúc 2 lõi (Google Cloud Vision & Multimodal Gemini Flash).
3. **Đối chiếu 5 giây (Human-in-the-loop):** Giao diện Split-view cho phép người dùng lướt nhanh ảnh gốc bên cạnh bảng dữ liệu, chỉnh sửa trực quan nếu cần và bấm "Xác nhận & Lưu".
4. **Trực quan hóa:** Số liệu tự động cập nhật ngay lập tức lên Dashboard phân tích tài chính cá nhân đa chiều.

---

## 2. CHÂN DUNG NGƯỜI DÙNG (USER PERSONAS)

### Persona 1: Hoàng Nam (27 tuổi, Kỹ sư phần mềm, Độc thân)
* **Nhu cầu:** Thường xuyên ăn ngoài, cà phê cùng bạn bè, mua sắm đồ công nghệ. Muốn biết tiền lương hàng tháng trôi đi đâu mà không phải mất công mở app ghi chép mỗi tối.
* **Hành vi:** Thanh toán xong cầm bill chụp ngay tại bàn hoặc cuối ngày chụp một loạt bill từ ví. Cần tốc độ phản hồi cực nhanh (< 2 giây).

### Persona 2: Chị Mai Lan (34 tuổi, Nhân viên văn phòng, Mẹ của 2 con)
* **Nhu cầu:** Đi siêu thị Co.opmart/WinMart 2–3 lần/tuần, mỗi bill dài 20–30 món. Cần biết chính xác tỷ trọng tiền ăn uống tươi sống so với hóa đơn tiện ích và đồ dùng gia đình.
* **Hành vi:** Sử dụng điện thoại di động tầm trung, cần ứng dụng dễ thao tác, chữ to rõ ràng, không bị lỗi khi hóa đơn bị gấp mép hay in nhiệt mờ.

---

## 3. PHẠM VI SẢN PHẨM (SCOPE & NON-GOALS)

### 3.1. Trong phạm vi MVP (In-Scope v1)
* Hóa đơn 1 trang tiếng Việt (có thể lẫn tiếng Anh) từ bán lẻ, siêu thị, F&B, cửa hàng tiện lợi, hóa đơn điện tử VAT, hóa đơn điện/nước/viễn thông.
* Các định dạng ảnh chụp điện thoại phổ biến: JPEG, PNG, WebP, HEIC.
* Đơn vị tiền tệ duy nhất: **VND** (biểu diễn số nguyên đồng `BIGINT`, tuyệt đối không dùng số thực).
* Người dùng cá nhân độc lập: Mỗi tài khoản sở hữu kho dữ liệu cô lập 100%.
* Ứng dụng PWA (Progressive Web App): Cài đặt trực tiếp lên màn hình chính smartphone, hỗ trợ chụp camera native và offline fallback page.
* Màn hình Split-view đối chiếu ảnh và bảng chi tiết, có thể zoom/pan và sửa dữ liệu trước khi lưu.
* Dashboard báo cáo: Tỷ trọng danh mục (Donut Chart), biểu đồ cột chi tiêu theo tuần/tháng, top khoản chi lớn nhất.
* Xuất dữ liệu: Xuất file Excel `.xlsx` chuẩn và CSV UTF-8 có BOM.

### 3.2. Ngoài phạm vi MVP (Non-Goals v1)
* Hóa đơn PDF nhiều trang, chữ viết tay, bảng kê xuất khẩu.
* Đa tiền tệ, quy đổi ngoại tệ.
* Ảnh chụp màn hình chuyển khoản ngân hàng (App Banking / MoMo / ZaloPay) — dự kiến phát triển ở v2.
* Quản lý ví tiền nhóm, phân quyền gia đình nhiều thành viên.
* Tích hợp trực tiếp hệ thống kế toán doanh nghiệp hoặc cơ quan thuế e-Invoice.

---

## 4. CÁC LUỒNG NGHIỆP VỤ CỐT LÕI (CORE USER FLOWS)

```
[Chụp / Tải ảnh] ──> [Tiền xử lý & Nén] ──> [FastAPI /ocr/scan]
                                                    │
                 ┌──────────────────────────────────┴──────────────────────────────────┐
                 ▼ (PASS)                                                              ▼ (FAIL)
        [Google Vision + Rules]                                              [Gemini Flash Fallback]
                 │                                                                     │
                 └──────────────────────────────────┬──────────────────────────────────┘
                                                    ▼
                                     [StandardInvoiceResult]
                                                    │
                                                    ▼
                                          [Màn hình Split-view]
                                        (Kiểm tra & Sửa nhanh)
                                                    │
                                                    ▼
                                          [Lưu Hóa Đơn & Xem Báo Cáo]
```

---

## 5. CHỈ TIÊU PHI CHỨC NĂNG (NFR METRICS - CẬP NHẬT TỪ BASELINE F00)

Dựa trên kết quả đo lường thực nghiệm tại `docs/benchmarks/baseline.md`:

| Nhóm chỉ tiêu | Mục tiêu NFR | Kết quả Baseline Thực tế |
|---|:---:|:---:|
| **Độ chính xác Tổng tiền (Total Accuracy)** | $\ge 95.0\%$ | **96.0%** (Đạt) |
| **Độ chính xác Ngày hóa đơn (Date Accuracy)** | $\ge 95.0\%$ | **97.0%** (Đạt) |
| **Độ chính xác Tên cửa hàng (Merchant Match)** | $\ge 90.0\%$ | **95.0%** (Đạt) |
| **Item F1-Score** | $\ge 85.0\%$ | **89.1%** (Đạt) |
| **Auto-accept Precision** | $\ge 97.0\%$ | **98.7%** (Vượt trội) |
| **Tỷ lệ Fallback sang Gemini** | $\le 30.0\%$ | **22.0%** (Tối ưu) |
| **Độ trễ scan Vision (Server p50)** | $\le 2.5\text{ s}$ | **1.65 s** (Đạt) |
| **Độ trễ tổng thể (Server p95)** | $\le 10.0\text{ s}$ | **6.40 s** (Đạt) |
| **Timeout cứng hệ thống** | $25\text{ s}$ | $25\text{ s}$ |
| **Chi phí trung bình / 1.000 hóa đơn** | $\le \$3.00$ | **\$2.23** (Tiết kiệm) |
| **Quyền riêng tư & Bảo mật** | Strip 100% EXIF/GPS, TTL ảnh tạm 24h, cô lập `user_id` | Tuân thủ 100% |

---

## 6. MÔ HÌNH DỮ LIỆU & BẢO MẬT

1. **Chuẩn tiền tệ:** Mọi giá trị tiền lưu dưới dạng số nguyên đồng `BIGINT` (ADR-004).
2. **Múi giờ:** Ngày hóa đơn lưu theo kiểu `DATE` múi giờ Việt Nam `Asia/Ho_Chi_Minh` (ADR-005).
3. **Cô lập dữ liệu:** 100% API endpoints và truy vấn cơ sở dữ liệu bắt buộc lọc theo `user_id`. Truy cập trái phép trả về 404 (chống IDOR).
4. **Không lưu trữ bí mật:** Không bao giờ lưu raw image chứa GPS hoặc log thông tin hóa đơn cá nhân.
