# ADR 007: Decision Gate: Đánh giá Hybrid so với Gemini-only

## Trạng thái
Đã chấp thuận & Hoàn thành kiểm định (Accepted & Validated via Baseline Benchmark)

## Bối cảnh
Trước khi triển khai mã nguồn bóc tách hóa đơn, hệ thống cần đánh giá thực nghiệm xem kiến trúc Hybrid (kết hợp Google Cloud Vision và Gemini Flash) có thực sự vượt trội hơn kiến trúc Gemini-only (đơn giản hơn về mặt triển khai) và Vision-only (rẻ hơn về mặt chi phí) hay không.

## Kết quả Thực nghiệm tại Feature 00
Xem báo cáo số liệu chi tiết tại [docs/benchmarks/baseline.md](../benchmarks/baseline.md):
- **Total Accuracy:** Hybrid đạt **96.0%** (so với 67.0% của Vision-only và 92.0% của Gemini-only).
- **Auto-accept Precision:** Hybrid đạt **98.7%** (vượt chỉ tiêu NFR $\ge 97\%$).
- **Độ trễ (Latency p50):** Hybrid đạt **1.65 s** (nhanh gấp 3.2 lần so với 5.40 s của Gemini-only).
- **Chi phí:** Hybrid đạt **$2.23 / 1.000 hóa đơn** (tiết kiệm 53% chi phí so với $4.80 / 1.000 hóa đơn của Gemini-only).

## Quyết định
1. **Chính thức lựa chọn Kiến trúc Hybrid**: Duy trì Google Cloud Vision làm engine sơ cấp (Primary Engine) xử lý siêu tốc cho ~80% hóa đơn thông thường, kết hợp Gemini Flash làm engine cứu cánh (Smart Fallback) cho ~20% ca khó hoặc bị lệch toán học.
2. Cố định các ngưỡng kiểm thử toán học cho `MathematicalValidator`: Dung sai tuyệt đối 1.000đ, dung sai tương đối 0.5%, ngưỡng tin cậy OCR trung bình 0.80.

## Hệ quả
- Hệ thống đạt được cả 3 mục tiêu: Tốc độ xử lý dưới 2s cho đại đa số người dùng, độ chính xác tài chính tiệm cận tuyệt đối, và chi phí vận hành tối ưu lâu dài.
- Kiến trúc đáp ứng yêu cầu suy giảm có kiểm soát (graceful degradation) theo runbook.
