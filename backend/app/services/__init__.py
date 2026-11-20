"""Services package for Kexpense core engine."""

from backend.app.services.allocation import allocate
from backend.app.services.correction import compute_corrections
from backend.app.services.cv_preprocess import PreprocessPipeline
from backend.app.services.ocr import BaseOCREngine, GoogleVisionEngine, OCRDocument
from backend.app.services.parsers import (
    extract_invoice_meta,
    extract_merchant_info,
    extract_table_items,
    extract_totals,
    parse_date,
    parse_money,
    parse_tax_code,
)
from backend.app.services.validation import validate_extraction

__all__ = [
    "BaseOCREngine",
    "GoogleVisionEngine",
    "OCRDocument",
    "PreprocessPipeline",
    "allocate",
    "compute_corrections",
    "extract_invoice_meta",
    "extract_merchant_info",
    "extract_table_items",
    "extract_totals",
    "parse_date",
    "parse_money",
    "parse_tax_code",
    "validate_extraction",
]
