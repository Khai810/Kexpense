"""Unit tests for Dataset Validation (TC-00-01 to TC-00-06)."""

import csv
import json
import tempfile
from pathlib import Path
from scripts.validate_dataset import validate_manifest


def test_real_dataset_manifest_passes():
    """TC-00-01 & TC-00-02: Real dataset manifest must pass all validation checks."""
    result = validate_manifest("data/manifest.csv")
    assert result["passed"] is True
    assert result["total_rows"] >= 140
    assert result["dev_count"] >= 100
    assert result["test_count"] >= 40
    assert len(result["errors"]) == 0


def test_manifest_file_not_found():
    """Validates proper error handling when manifest file does not exist."""
    result = validate_manifest("data/non_existent_manifest.csv")
    assert result["passed"] is False
    assert any("not found" in err.lower() for err in result["errors"])


def test_manifest_insufficient_rows(tmp_path):
    """TC-00-01: Manifest with fewer than 140 rows must fail."""
    manifest_file = tmp_path / "small_manifest.csv"
    with open(manifest_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "split", "type", "difficulty", "sha256", "label_file"])
        writer.writeheader()
        writer.writerow({
            "id": "REC-001",
            "split": "dev",
            "type": "supermarket",
            "difficulty": "easy",
            "sha256": "a" * 64,
            "label_file": "none.json",
        })

    result = validate_manifest(str(manifest_file))
    assert result["passed"] is False
    assert any("expected >= 140" in err for err in result["errors"])


def test_manifest_data_leakage_detection(tmp_path):
    """TC-00-02: Hash overlap between dev and test split must be detected and failed."""
    manifest_file = tmp_path / "leaky_manifest.csv"
    dup_hash = "f" * 64

    rows = []
    # Create 140 minimal rows with a leakage
    for i in range(140):
        split = "dev" if i < 100 else "test"
        row_hash = dup_hash if (i == 0 or i == 100) else f"{i:064d}"
        rows.append({
            "id": f"REC-{i:04d}",
            "file_name": f"REC-{i:04d}.jpg",
            "sha256": row_hash,
            "type": "supermarket" if i < 42 else ("restaurant_cafe" if i < 77 else ("vat_invoice" if i < 98 else ("utilities" if i < 112 else ("pharmacy_other" if i < 119 else "hard_cases")))),
            "difficulty": "easy" if i < 63 else ("medium" if i < 119 else "hard"),
            "split": split,
            "merchant_name": f"Store {i}",
            "invoice_number": f"INV-{i}",
            "invoice_date": "2026-08-01",
            "total_amount": "100000",
            "label_file": "data/labels/REC-2026-0001.json",
        })

    with open(manifest_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    result = validate_manifest(str(manifest_file))
    assert result["passed"] is False
    assert any("Hash overlap between dev and test" in err for err in result["errors"])


def test_manifest_schema_validation_failure(tmp_path):
    """TC-00-01: Malformed JSON label failing Pydantic schema must be caught."""
    bad_label = tmp_path / "bad_label.json"
    bad_label.write_text('{"schema_version": "1.0", "invalid_key": true}')

    manifest_file = tmp_path / "bad_schema_manifest.csv"
    rows = []
    for i in range(140):
        split = "dev" if i < 100 else "test"
        rows.append({
            "id": f"REC-{i:04d}",
            "file_name": f"REC-{i:04d}.jpg",
            "sha256": f"{i:064x}",
            "type": "supermarket" if i < 42 else ("restaurant_cafe" if i < 77 else ("vat_invoice" if i < 98 else ("utilities" if i < 112 else ("pharmacy_other" if i < 119 else "hard_cases")))),
            "difficulty": "easy" if i < 63 else ("medium" if i < 119 else "hard"),
            "split": split,
            "merchant_name": f"Store {i}",
            "invoice_number": f"INV-{i}",
            "invoice_date": "2026-08-01",
            "total_amount": "100000",
            "label_file": str(bad_label) if i == 0 else "data/labels/REC-2026-0001.json",
        })

    with open(manifest_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    result = validate_manifest(str(manifest_file))
    assert result["passed"] is False
    assert any("Schema validation error" in err for err in result["errors"])
