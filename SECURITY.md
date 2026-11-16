# Chính sách Bảo mật (Security Policy)

## 1. Báo cáo lỗ hổng
Nếu phát hiện lỗ hổng bảo mật, vui lòng không mở Issue công khai. Hãy liên hệ trực tiếp với người quản trị dự án.

## 2. Nguyên tắc bảo mật bắt buộc
* **Không bao giờ commit credentials:** Tuyệt đối không commit file `.env`, file `google_key.json`, private keys.
* **EXIF Stripping:** Mọi ảnh hóa đơn upload lên hệ thống phải được strip toàn bộ metadata (đặc biệt là tọa độ GPS) trước khi lưu trữ hoặc gửi sang AI provider.
* **Data Isolation (Chống IDOR):** Mọi truy vấn database bắt buộc phải lọc theo `user_id`.
