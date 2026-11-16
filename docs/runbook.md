# Operations Runbook - Kexpense

## 1. Sự cố Google Vision API gián đoạn (Outage / 5xx)
- **Hiện tượng:** Log xuất hiện lỗi `VISION_ERROR`.
- **Hành vi hệ thống:** Router tự động fallback 100% sang Gemini Vision.
- **Hành động quản trị:** Theo dõi Google Cloud Status dashboard và kiểm tra hạn mức API.

## 2. Sự cố Gemini Vision hết Quota / 429
- **Hiện tượng:** Log xuất hiện `GEMINI_QUOTA_EXCEEDED`.
- **Hành vi hệ thống:** Không gọi lại Gemini, trả về kết quả tốt nhất của Google Vision kèm cờ `needs_review=true`. Nếu cả 2 đều hỏng -> Trả 503 và hướng dẫn người dùng nhập tay.
