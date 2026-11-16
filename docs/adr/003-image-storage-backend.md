# ADR 003: Lưu trữ ảnh: StorageBackend Interface (Local Dev / Cloudflare R2 Prod)

## Trạng thái
Đã chấp thuận (Accepted)

## Bối cảnh
Quyết định kiến trúc chuẩn cho dự án Kexpense theo đặc tả ROADMAP v2.

## Quyết định
Không public bucket; truy cập ảnh qua signed URL có xác thực.

## Hệ quả
Hệ thống tuân thủ chặt chẽ theo quy chuẩn, dễ bảo trì và mở rộng trong tương lai.
