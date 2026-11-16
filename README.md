# Kexpense (Smart Expense OCR)
> **Hệ thống Quản lý Chi tiêu Cá nhân thông minh ứng dụng Kiến trúc Hybrid OCR (Google Cloud Vision & Multimodal Gemini Flash)**

---

## 📖 Giới thiệu
Kexpense là ứng dụng giúp tự động hóa 100% việc ghi chép chi tiêu từ hóa đơn bán lẻ, nhà hàng, siêu thị:
* **Perception:** Nắn chỉnh góc chụp, khử mờ, tăng tương phản với OpenCV.
* **Extraction:** Hybrid OCR kết hợp Google Cloud Vision (bóc tách bảng & regex siêu tốc) với Gemini 2.5 Flash (fallback thông minh & tự động gán danh mục).
* **Application:** Giao diện Next.js 15 PWA cài trực tiếp trên điện thoại, hỗ trợ Split-view đối chiếu ảnh và Dashboard phân tích tài chính cá nhân.

---

## 🚀 Tài liệu Dự án
* 📋 **Lộ trình & Đặc tả kỹ thuật:** [ROADMAP.md](ROADMAP.md)
* 📐 **Kiến trúc hệ thống:** [docs/architecture.md](docs/architecture.md)
* 🔒 **Chính sách quyền riêng tư & Dữ liệu:** [docs/privacy.md](docs/privacy.md)
* 🛠️ **Sổ tay vận hành (Runbook):** [docs/runbook.md](docs/runbook.md)
* 💡 **Các quyết định kiến trúc (ADR):** [docs/adr/](docs/adr/)

---

## 🛠️ Quy chuẩn Kỹ thuật
* **Git Workflow:** Xem [CONTRIBUTING.md](CONTRIBUTING.md)
* **Bảo mật:** Xem [SECURITY.md](SECURITY.md)
* **Lịch sử thay đổi:** Xem [CHANGELOG.md](CHANGELOG.md)
