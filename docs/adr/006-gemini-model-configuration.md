# ADR 006: Cấu hình Model Gemini qua Biến môi trường

## Trạng thái
Đã chấp thuận (Accepted)

## Bối cảnh
Quyết định kiến trúc chuẩn cho dự án Kexpense theo đặc tả ROADMAP v2.

## Quyết định
Không hardcode tên model; hỗ trợ model dự phòng khi có deprecation.

## Hệ quả
Hệ thống tuân thủ chặt chẽ theo quy chuẩn, dễ bảo trì và mở rộng trong tương lai.
