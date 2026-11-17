"""Dataset Validation Script for Kexpense (Feature 00).

Validates data/manifest.csv and data/labels/*.json according to:
- TC-00-01: Manifest >= 140 rows, schema validity, stratification within +/-5%
- TC-00-02: Test split locked by checksum, zero data leakage between dev and test
- TC-00-06: Cross-annotation agreement rate >= 98%
"""

import argparse
import csv
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

from backend.app.models.schemas.ocr_schema import StandardInvoiceResult

TARGET_STRATIFICATION = {
    "supermarket": 0.30,
    "restaurant_cafe": 0.25,
    "vat_invoice": 0.15,
    "utilities": 0.10,
    "pharmacy_other": 0.05,
    "hard_cases": 0.15,
}

TARGET_DIFFICULTY = {
    "easy": 0.45,
    "medium": 0.40,
    "hard": 0.15,
}

TOLERANCE_POINTS = 0.05  # +/- 5 percentage points


def validate_manifest(manifest_path: str) -> dict:
    results = {
        "passed": True,
        "total_rows": 0,
        "dev_count": 0,
        "test_count": 0,
        "type_counts": {},
        "difficulty_counts": {},
        "errors": [],
        "warnings": [],
    }

    manifest_file = Path(manifest_path)
    if not manifest_file.exists():
        results["passed"] = False
        results["errors"].append(f"Manifest file not found: {manifest_path}")
        return results

    rows = []
    with open(manifest_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    results["total_rows"] = len(rows)
    if len(rows) < 140:
        results["passed"] = False
        results["errors"].append(f"TC-00-01 FAIL: Manifest has {len(rows)} rows, expected >= 140")

    dev_rows = [r for r in rows if r.get("split") == "dev"]
    test_rows = [r for r in rows if r.get("split") == "test"]
    results["dev_count"] = len(dev_rows)
    results["test_count"] = len(test_rows)

    if results["dev_count"] < 100:
        results["passed"] = False
        results["errors"].append(f"Dev split has {results['dev_count']} rows, expected >= 100")
    if results["test_count"] < 40:
        results["passed"] = False
        results["errors"].append(f"Test split has {results['test_count']} rows, expected >= 40")

    # Validate each label and schema
    type_counter = Counter()
    diff_counter = Counter()
    dev_hashes = set()
    test_hashes = set()
    dev_keys = set()
    test_keys = set()

    for idx, r in enumerate(rows, start=1):
        row_id = r.get("id", f"row-{idx}")
        rec_type = r.get("type")
        diff = r.get("difficulty")
        split = r.get("split")
        sha256 = r.get("sha256")
        label_file = r.get("label_file")

        type_counter[rec_type] += 1
        diff_counter[diff] += 1

        # Check hash format
        if not sha256 or len(sha256) != 64:
            results["passed"] = False
            results["errors"].append(f"{row_id}: Invalid sha256 hash format")

        composite_key = (
            r.get("merchant_name", "").strip().lower(),
            r.get("invoice_number", "").strip().lower(),
            r.get("invoice_date", "").strip(),
        )

        if split == "dev":
            dev_hashes.add(sha256)
            dev_keys.add(composite_key)
        elif split == "test":
            test_hashes.add(sha256)
            test_keys.add(composite_key)

        # Validate label file against StandardInvoiceResult schema
        if not label_file or not os.path.exists(label_file):
            results["passed"] = False
            results["errors"].append(f"{row_id}: Label file missing: {label_file}")
            continue

        try:
            with open(label_file, "r", encoding="utf-8") as lf:
                data = json.load(lf)
            validated = StandardInvoiceResult.model_validate(data)
            # Verify amounts consistency
            if validated.totals.total < 0:
                results["passed"] = False
                results["errors"].append(f"{row_id}: Negative total amount {validated.totals.total}")
        except Exception as e:
            results["passed"] = False
            results["errors"].append(f"{row_id}: Schema validation error: {e}")

    results["type_counts"] = dict(type_counter)
    results["difficulty_counts"] = dict(diff_counter)

    # Check stratification distribution
    total = len(rows)
    for cat, target_pct in TARGET_STRATIFICATION.items():
        actual_pct = type_counter[cat] / total if total > 0 else 0
        min_allowed = target_pct - TOLERANCE_POINTS
        max_allowed = target_pct + TOLERANCE_POINTS
        if not (min_allowed <= actual_pct <= max_allowed):
            results["passed"] = False
            results["errors"].append(
                f"TC-00-01 Stratification FAIL for '{cat}': actual {actual_pct:.1%}, "
                f"expected {target_pct:.1%} (+/- 5%)"
            )

    # Check difficulty distribution
    for diff, target_pct in TARGET_DIFFICULTY.items():
        actual_pct = diff_counter[diff] / total if total > 0 else 0
        min_allowed = target_pct - TOLERANCE_POINTS
        max_allowed = target_pct + TOLERANCE_POINTS
        if not (min_allowed <= actual_pct <= max_allowed):
            results["passed"] = False
            results["errors"].append(
                f"TC-00-01 Difficulty distribution FAIL for '{diff}': actual {actual_pct:.1%}, "
                f"expected {target_pct:.1%} (+/- 5%)"
            )

    # TC-00-02: Check for data leakage between dev and test
    hash_leakage = dev_hashes.intersection(test_hashes)
    if hash_leakage:
        results["passed"] = False
        results["errors"].append(f"TC-00-02 FAIL: Hash overlap between dev and test: {len(hash_leakage)} items")

    key_leakage = dev_keys.intersection(test_keys)
    if key_leakage:
        results["passed"] = False
        results["errors"].append(f"TC-00-02 FAIL: Duplicate invoice keys between dev and test: {len(key_leakage)} items")

    # Check test split lock checksum
    test_lock_file = Path("data/test_split.sha256")
    if test_lock_file.exists():
        with open(test_lock_file, "r", encoding="utf-8") as f:
            stored_checksum = f.read().split()[0].strip()
        test_rows_dump = json.dumps(test_rows, sort_keys=True)
        computed_checksum = hashlib.sha256(test_rows_dump.encode("utf-8")).hexdigest()
        if stored_checksum != computed_checksum:
            results["passed"] = False
            results["errors"].append(
                f"TC-00-02 FAIL: Test split checksum mismatch: stored={stored_checksum}, computed={computed_checksum}"
            )
        else:
            results["test_split_locked"] = True
    else:
        results["warnings"].append("data/test_split.sha256 not found")

    # TC-00-06: Cross-annotation verification
    cross_file = Path("data/cross_annotation.json")
    if cross_file.exists():
        with open(cross_file, "r", encoding="utf-8") as f:
            cross_data = json.load(f)
        total_agree = cross_data.get("total_agreement_rate", 0)
        date_agree = cross_data.get("date_agreement_rate", 0)
        pct_sampled = cross_data.get("percentage_sampled", 0)
        if pct_sampled < 20.0:
            results["passed"] = False
            results["errors"].append(f"TC-00-06 FAIL: Cross annotation sampled only {pct_sampled}%, required >= 20%")
        if total_agree < 98.0 or date_agree < 98.0:
            results["passed"] = False
            results["errors"].append(
                f"TC-00-06 FAIL: Cross annotation agreement rate: total={total_agree}%, date={date_agree}%, required >= 98%"
            )
        results["cross_annotation"] = cross_data
    else:
        results["warnings"].append("data/cross_annotation.json not found")

    return results


def print_report(res: dict) -> None:
    print("=" * 70)
    print("  KEXPENSE DATASET VALIDATION REPORT (FEATURE 00)")
    print("=" * 70)
    print(f"Total Receipts:       {res['total_rows']} (Dev: {res['dev_count']}, Test: {res['test_count']})")
    print("\n--- Phân bổ Loại Hóa Đơn (Stratification) ---")
    total = res["total_rows"]
    for cat, target in TARGET_STRATIFICATION.items():
        actual = res["type_counts"].get(cat, 0)
        pct = actual / total * 100 if total > 0 else 0
        print(f"  * {cat:16}: {actual:3d} ({pct:5.1f}%) [Mục tiêu: {target*100:4.1f}% ±5%]")

    print("\n--- Phân bổ Độ Khó (Difficulty) ---")
    for diff, target in TARGET_DIFFICULTY.items():
        actual = res["difficulty_counts"].get(diff, 0)
        pct = actual / total * 100 if total > 0 else 0
        print(f"  * {diff:16}: {actual:3d} ({pct:5.1f}%) [Mục tiêu: {target*100:4.1f}% ±5%]")

    if "cross_annotation" in res:
        ca = res["cross_annotation"]
        print("\n--- Đo lường Độ Nhất Quán Gán Nhãn Chéo (TC-00-06) ---")
        print(f"  * Mẫu kiểm tra chéo: {ca['total_sampled']} ({ca['percentage_sampled']}%)")
        print(f"  * Khớp Tổng tiền:    {ca['total_agreement_rate']}% (Yêu cầu >= 98%)")
        print(f"  * Khớp Ngày:         {ca['date_agreement_rate']}% (Yêu cầu >= 98%)")

    if res["warnings"]:
        print("\n[CẢNH BÁO]:")
        for w in res["warnings"]:
            print(f"  - {w}")

    if res["errors"]:
        print("\n[LỖI]:")
        for e in res["errors"]:
            print(f"  - {e}")

    print("=" * 70)
    if res["passed"]:
        print(">> KẾT LUẬN: TẤT CẢ TIÊU CHUẨN DATASET FEATURE 00 ĐÃ ĐẠT (PASS) <<")
    else:
        print(">> KẾT LUẬN: THẤT BẠI - CẦN KHẮC PHỤC CÁC LỖI TRÊN (FAIL) <<")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Validate Kexpense dataset manifest and labels")
    parser.add_argument("--manifest", default="data/manifest.csv", help="Path to manifest CSV file")
    args = parser.parse_args()

    results = validate_manifest(args.manifest)
    print_report(results)
    sys.exit(0 if results["passed"] else 1)


if __name__ == "__main__":
    main()
