# Hướng dẫn Đóng góp & Quy trình Git (Git Workflow)

## 1. Quy ước Nhánh (Branching Strategy)
* `main`: Nhánh production. Luôn ổn định và có thể release bất kỳ lúc nào.
* `develop`: Nhánh tích hợp chính.
* `feature/<feature-name>`: Nhánh phát triển tính năng mới (tách từ `develop`).
* `fix/<issue-name>`: Nhánh sửa lỗi (tách từ `develop`).
* `hotfix/<issue-name>`: Nhánh sửa lỗi khẩn cấp (tách từ `main`).

## 2. Quy ước Commit (Conventional Commits)
Format: `<type>(<scope>): <mô tả ngắn>`
* `feat`: Tính năng mới (vd: `feat(ocr): add gemini fallback router`)
* `fix`: Sửa lỗi (vd: `fix(table): fix cell boundary parsing`)
* `refactor`: Tái cấu trúc mã nguồn
* `test`: Thêm hoặc sửa test case
* `docs`: Thêm hoặc cập nhật tài liệu
* `chore`: Cấu hình, dependencies

## 3. Quy trình làm việc chuẩn
1. `git checkout develop && git pull origin develop`
2. `git checkout -b feature/<tên-nhánh>`
3. Code và commit: `git add -p` -> `git commit -m "..."`
4. Chạy bộ test đầu ra theo đặc tả trong `ROADMAP.md`
5. Push và tạo Pull Request (PR) vào `develop`.
