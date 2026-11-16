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
