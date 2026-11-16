# ADR 001: MVP Đồng bộ (Synchronous HTTP) và lộ trình Job Queue Phase 2

## Trạng thái
Đã chấp thuận (Accepted)

## Bối cảnh
Quyết định kiến trúc chuẩn cho dự án Kexpense theo đặc tả ROADMAP v2.

## Quyết định
Chấp nhận request timeout 25s trong MVP để đơn giản hóa kiến trúc; chuẩn bị sẵn bảng ocr_jobs.

## Hệ quả
Hệ thống tuân thủ chặt chẽ theo quy chuẩn, dễ bảo trì và mở rộng trong tương lai.
