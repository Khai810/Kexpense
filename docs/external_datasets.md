# Hướng dẫn Tích hợp Dataset Mở: MC-OCR 2021 & ICDAR 2019 SROIE

> Kexpense hỗ trợ nhập trực tiếp và chuẩn hóa 2 bộ dataset hóa đơn phổ biến nhất vào hệ thống theo hợp đồng dữ liệu chuẩn `StandardInvoiceResult`.

---

## 1. TỔNG QUAN 2 BỘ DATASET

| Dataset | Xuất xứ | Ngôn ngữ | Đặc điểm | Nguồn tải |
|---|---|:---:|---|---|
| **Vietnamese Receipts MC-OCR 2021** | RIVF 2021 / Zalo AI Challenge | Tiếng Việt | Hóa đơn bán lẻ, nhà hàng chụp bằng điện thoại thật với đủ độ nghiêng, nhàu, mờ nhiệt | [Kaggle Dataset](https://www.kaggle.com/datasets/domixi1989/vietnamese-receipts-mc-ocr-2021) |
| **ICDAR 2019 SROIE** | Cuộc thi ICDAR 2019 Robust Reading | Tiếng Anh / Song ngữ | 1.000 hóa đơn bán lẻ siêu thị/tiện lợi quét scan rõ nét, có nhãn cấu trúc thực thể | [Hugging Face](https://huggingface.co/datasets/jsdnrs/ICDAR2019-SROIE) / [Kaggle](https://www.kaggle.com/datasets/urbikn/sroie-datasetv2) |

---

## 2. HƯỚNG DẪN TẢI VỀ MÁY (DOWNLOAD)

### Cách 1: Sử dụng Kaggle API CLI (Nhanh nhất)
Nếu bạn đã cài `kaggle` (`pip install kaggle`) và có file `~/.kaggle/kaggle.json`:

```bash
# 1. Tải bộ hóa đơn tiếng Việt MC-OCR 2021
kaggle datasets download -d domixi1989/vietnamese-receipts-mc-ocr-2021 -p data/external/mcocr --unzip

# 2. Tải bộ hóa đơn ICDAR 2019 SROIE
kaggle datasets download -d urbikn/sroie-datasetv2 -p data/external/sroie --unzip
```

### Cách 2: Tải trực tiếp bằng trình duyệt
* **MC-OCR 2021:** Truy cập [Kaggle MC-OCR 2021](https://www.kaggle.com/datasets/domixi1989/vietnamese-receipts-mc-ocr-2021) $\rightarrow$ Bấm **Download** $\rightarrow$ Giải nén toàn bộ vào thư mục `data/external/mcocr/`.
* **SROIE 2019:** Truy cập [Kaggle SROIE](https://www.kaggle.com/datasets/urbikn/sroie-datasetv2) $\rightarrow$ Bấm **Download** $\rightarrow$ Giải nén toàn bộ vào thư mục `data/external/sroie/`.

---

## 3. CHUYỂN ĐỔI TỰ ĐỘNG SANG CHUẨN KEXPENSE

Kexpense cung cấp sẵn script tự động map các nhãn thực thể (`seller`, `timestamp`, `total_cost`, `company`, `date`, `total`) sang Pydantic schema `StandardInvoiceResult`:

```bash
# 1. Nhập 100 hóa đơn tiếng Việt từ MC-OCR vào Kexpense (tự động phân bổ 80% dev, 20% test)
python -m scripts.import_external_datasets --source mcocr --data-dir data/external/mcocr --limit 100

# 2. Nhập 50 hóa đơn bán lẻ từ SROIE
python -m scripts.import_external_datasets --source sroie --data-dir data/external/sroie --limit 50
```

Script sẽ tự động:
1. Sao chép ảnh vào `data/samples/` (được bảo vệ trong `.gitignore`).
2. Sinh các file nhãn JSON chuẩn vào `data/labels/`.
3. Bổ sung các bản ghi tương ứng vào [data/manifest.csv](../data/manifest.csv).
4. Tự động tính toán lại và khóa mã băm checksum tập test tại [data/test_split.sha256](../data/test_split.sha256).

---

## 4. KIỂM TRA LẠI TẬP DỮ LIỆU SAU KHI NHẬP

Chạy lệnh xác thực dataset của Kexpense:

```bash
python -m scripts.validate_dataset --manifest data/manifest.csv
```
