# Architecture Overview - Kexpense

## 1. Sơ đồ luồng dữ liệu 4 tầng
1. **Client Layer:** Next.js 15 PWA (Mobile-first, camera capture, split-view review, Recharts dashboard).
2. **Gateway & API Layer:** FastAPI Gateway nhận request, xác thực JWT, kiểm tra rate limit.
3. **Hybrid Processing Engine:**
   - Preprocessing: OpenCV (deskew, CLAHE contrast, perspective correction).
   - Primary: Google Cloud Vision API + Bounding Box Table Heuristics.
   - Fallback: Gemini 2.5 Flash Structured JSON Mode (kích hoạt khi lệch toán học hoặc gãy bảng).
   - Categorizer: Rule-based -> History -> LLM text batch.
4. **Data Persistence:** PostgreSQL (Supabase / Neon), cô lập dữ liệu theo `user_id`.

---

## 2. Mô hình Cơ sở Dữ liệu & Sơ đồ Thực thể Quan hệ (ERD)

Hệ thống quản lý chi tiêu Kexpense sử dụng kiến trúc PostgreSQL 16 quan hệ với 15 bảng nghiệp vụ chính (+ bảng `sessions` quản lý refresh token rotation). 

### 2.1. Quy chuẩn Dữ liệu Bắt buộc
- **Tiền tệ (Currency):** 100% các cột tiền tệ (`total_amount`, `subtotal`, `discount`, `tax_amount`, `service_charge`, `line_total`, `allocated_amount`, `unit_price`) sử dụng kiểu `BIGINT` biểu diễn số tiền đồng (VND nguyên, cấm `float` theo ADR-004).
- **Phân bổ chi tiêu (ADR-010):** Cột `allocated_amount` trên từng món (`receipt_items`) áp dụng thuật toán chia dư lớn nhất (largest-remainder), đảm bảo bất biến:
  $$\sum \text{allocated\_amount} == \text{receipts.total\_amount}$$
- **Multi-tenancy Isolation:** Mọi bảng chứa dữ liệu người dùng đều có khóa ngoại `user_id` và index bắt đầu bằng `user_id`.
- **Tách dữ liệu OCR nặng:** Các trường JSON lớn (`raw_ocr`, `ocr_snapshot`) được tách sang bảng `receipt_ocr_data` (1-1 với `receipts`), giúp danh sách hóa đơn truy vấn nhanh mà không bị phình bộ nhớ.

### 2.2. Mermaid Entity Relationship Diagram (ERD)

```mermaid
erDiagram
    users ||--|| user_settings : "has (1:1)"
    users ||--o{ categories : "creates"
    users ||--o{ merchants : "owns"
    users ||--o{ category_rules : "owns"
    users ||--o{ receipts : "owns"
    users ||--o{ ocr_jobs : "triggers"
    users ||--o{ usage_counters : "tracked_by"
    users ||--o{ idempotency_keys : "owns"
    users ||--o{ audit_logs : "records"
    users ||--o{ sessions : "authenticates"

    categories ||--o{ category_rules : "defines (CASCADE)"
    categories ||--o{ merchants : "default_category (SET NULL)"
    categories ||--o{ receipt_items : "classifies (SET NULL)"

    merchants ||--o{ receipts : "merchant_id (SET NULL)"

    ocr_jobs ||--o{ ocr_engine_runs : "executes (CASCADE)"
    ocr_jobs ||--o{ receipts : "ocr_job_id"

    receipts ||--o{ receipt_items : "contains (CASCADE)"
    receipts ||--o{ receipt_images : "has (CASCADE)"
    receipts ||--|| receipt_ocr_data : "stores (1:1 CASCADE)"
    receipts ||--o{ receipt_corrections : "tracks (CASCADE)"

    users {
        uuid id PK
        varchar email UK
        varchar password_hash
        timestamptz created_at
        timestamptz deleted_at
    }

    user_settings {
        uuid user_id PK_FK
        varchar timezone
        varchar locale
        smallint month_start_day
        boolean small_number_as_thousand
        jsonb notification_prefs
        timestamptz consent_ocr_at
        varchar consent_version
    }

    categories {
        uuid id PK
        uuid user_id FK "nullable (NULL = system)"
        varchar slug
        varchar name
        varchar icon
        varchar color
        jsonb keywords
        boolean is_system
        timestamptz archived_at
    }

    merchants {
        uuid id PK
        uuid user_id FK
        varchar canonical_name
        varchar name_normalized
        varchar tax_code
        uuid default_category_id FK
        jsonb aliases
        timestamptz created_at
    }

    category_rules {
        uuid id PK
        uuid user_id FK
        varchar match_type
        varchar pattern
        uuid category_id FK
        integer priority
        integer hit_count
        varchar source
        timestamptz created_at
    }

    receipts {
        uuid id PK
        uuid user_id FK
        uuid merchant_id FK
        varchar merchant_name
        varchar merchant_tax_code
        varchar invoice_number
        date invoice_date
        time invoice_time
        char currency
        bigint subtotal
        bigint discount
        bigint tax_amount
        bigint service_charge
        bigint total_amount
        varchar payment_method
        varchar notes
        varchar source
        varchar content_hash
        uuid ocr_job_id FK
        varchar engine_used
        varchar categorizer_used
        varchar fallback_reason
        varchar validation_status
        float ocr_confidence
        boolean needs_review
        varchar status
        uuid recurring_rule_id
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    receipt_items {
        uuid id PK
        uuid receipt_id FK
        integer line_no
        varchar name
        varchar original_name
        varchar sku
        numeric quantity
        varchar unit
        bigint unit_price
        bigint line_total
        bigint discount
        numeric tax_rate
        bigint allocated_amount
        uuid category_id FK
        float confidence
        jsonb bbox
        boolean is_user_edited
    }

    receipt_images {
        uuid id PK
        uuid receipt_id FK
        varchar kind
        varchar storage_path
        varchar mime
        integer width
        integer height
        bigint size_bytes
        varchar sha256
        timestamptz created_at
    }

    receipt_ocr_data {
        uuid receipt_id PK_FK
        jsonb raw_ocr
        jsonb ocr_snapshot
        varchar prompt_version
        varchar parser_version
        timestamptz created_at
    }

    receipt_corrections {
        uuid id PK
        uuid receipt_id FK
        varchar field_path
        jsonb ai_value
        jsonb user_value
        timestamptz created_at
    }

    ocr_jobs {
        uuid id PK
        uuid user_id FK
        uuid scan_id
        varchar content_hash
        varchar final_engine
        varchar fallback_reason
        varchar status
        integer total_latency_ms
        varchar error_code
        timestamptz created_at
    }

    ocr_engine_runs {
        uuid id PK
        uuid job_id FK
        integer attempt_no
        varchar engine
        varchar model_version
        varchar prompt_version
        varchar parser_version
        varchar status
        integer latency_ms
        integer tokens_in
        integer tokens_out
        numeric cost_usd
        varchar error_code
        float validation_score
    }

    usage_counters {
        uuid user_id PK_FK
        date day PK
        integer scans
        integer gemini_calls
        numeric cost_usd
    }

    idempotency_keys {
        uuid user_id PK_FK
        varchar key PK
        varchar request_hash
        integer response_status
        jsonb response_body
        timestamptz created_at
        timestamptz expires_at
    }

    audit_logs {
        uuid id PK
        uuid user_id FK
        varchar action
        varchar target_type
        varchar target_id
        varchar ip_hash
        jsonb meta
        timestamptz created_at
    }

    sessions {
        uuid id PK
        uuid user_id FK
        uuid family_id
        varchar token_hash UK
        varchar device_name
        varchar ip_hash
        timestamptz last_used_at
        timestamptz expires_at
        timestamptz revoked_at
        timestamptz created_at
    }
```
