"""Data Contract: StandardInvoiceResult schema for Kexpense OCR system.

Single source of truth for all OCR engines, parsers, and API responses.
"""

from datetime import date, time
from decimal import Decimal
from enum import StrEnum
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class EngineUsed(StrEnum):
    GOOGLE_VISION = "google_vision"
    GEMINI_FALLBACK = "gemini_fallback"
    MANUAL = "manual"


class CategorizerUsed(StrEnum):
    RULES = "rules"
    HISTORY = "history"
    LLM = "llm"
    DEFAULT = "default"
    MIXED = "mixed"


class FallbackReason(StrEnum):
    NONE = "none"
    TOTAL_MISSING = "total_missing"
    SUM_MISMATCH = "sum_mismatch"
    NO_ITEMS = "no_items"
    LOW_CONFIDENCE = "low_confidence"
    VISION_ERROR = "vision_error"
    PARSE_ERROR = "parse_error"


class BBox(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: float = Field(ge=0.0, le=1.0, description="Normalized X coordinate (0-1)")
    y: float = Field(ge=0.0, le=1.0, description="Normalized Y coordinate (0-1)")
    w: float = Field(ge=0.0, le=1.0, description="Normalized width (0-1)")
    h: float = Field(ge=0.0, le=1.0, description="Normalized height (0-1)")


class InvoiceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    line_no: int = Field(ge=1, description="Line number starting from 1")
    name: str = Field(min_length=1, max_length=200, description="Product or service name")
    quantity: Decimal = Field(gt=0, le=9999, description="Quantity")
    unit: str | None = Field(default=None, max_length=50, description="Unit of measurement (cái, kg, ly,...)")
    unit_price: int | None = Field(default=None, ge=0, description="Unit price in integer VND")
    line_total: int = Field(ge=0, description="Total amount for this line item in integer VND")
    category_slug: str | None = Field(default=None, description="Assigned category slug")
    confidence: float | None = Field(default=None, ge=0.0, le=1.0, description="OCR confidence score")
    bbox: BBox | None = Field(default=None, description="Bounding box on original receipt image")


class InvoiceTotals(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subtotal: int | None = Field(default=None, ge=0, description="Subtotal before taxes and discounts")
    discount: int = Field(default=0, ge=0, description="Discount amount in VND")
    tax_amount: int | None = Field(default=None, ge=0, description="VAT or tax amount in VND")
    tax_rate: Decimal | None = Field(default=None, ge=0, le=100, description="Tax rate percentage (e.g. 8.0, 10.0)")
    service_charge: int = Field(default=0, ge=0, description="Service charge in VND")
    total: int = Field(ge=0, description="Final printed total to pay in integer VND")
    paid_amount: int | None = Field(default=None, ge=0, description="Customer tender amount in VND")


class CheckResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(description="Check code (e.g. V1, V2, V3,...)")
    passed: bool = Field(description="Whether the check passed")
    severity: Literal["hard", "soft"] = Field(description="Hard failure triggers fallback; soft causes review")
    message_vi: str = Field(description="Human-readable explanation in Vietnamese")


class ValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["PASS", "REVIEW", "FAIL"] = Field(description="Overall validation status")
    score: float = Field(ge=0.0, le=1.0, description="Overall extraction confidence score")
    checks: list[CheckResult] = Field(default_factory=list, description="Detailed check results")


class MerchantInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255, description="Merchant or store name")
    tax_code: str | None = Field(default=None, max_length=20, description="Mã số thuế (10 or 13 digits)")
    address: str | None = Field(default=None, max_length=500, description="Store address")
    phone: str | None = Field(default=None, max_length=50, description="Store phone number")


class InvoiceMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invoice_number: str | None = Field(default=None, max_length=100, description="Invoice or receipt number")
    invoice_date: date = Field(description="Invoice date in local Vietnam timezone (YYYY-MM-DD)")
    invoice_time: time | None = Field(default=None, description="Invoice time printed on receipt")
    currency: Literal["VND"] = Field(default="VND", description="Currency, fixed to VND in v1")
    payment_method: str | None = Field(default=None, max_length=50, description="Cash, Card, QR, Banking, etc.")


class ImageQuality(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_blur: bool = Field(default=False, description="Whether image was flagged as blurry")
    is_dark: bool = Field(default=False, description="Whether image was flagged as dark")
    steps_applied: list[str] = Field(default_factory=list, description="Preprocessing operations applied")
    ocr_mean_confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Average OCR word confidence")


class Timings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preprocess_ms: int = Field(default=0, ge=0, description="OpenCV preprocessing duration (ms)")
    ocr_ms: int = Field(default=0, ge=0, description="Vision OCR API duration (ms)")
    parse_ms: int = Field(default=0, ge=0, description="Regex and table parsing duration (ms)")
    categorize_ms: int = Field(default=0, ge=0, description="Categorization duration (ms)")
    fallback_ms: int = Field(default=0, ge=0, description="Gemini fallback duration if triggered (ms)")
    total_ms: int = Field(default=0, ge=0, description="Total pipeline latency (ms)")


class StandardInvoiceResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default="1.0", description="Contract schema version")
    job_id: UUID = Field(description="Tracking job identifier")
    scan_id: UUID = Field(description="Temporary scan image identifier")
    engine_used: EngineUsed = Field(description="Primary or fallback engine used")
    categorizer_used: CategorizerUsed = Field(description="Method used for item categorization")
    fallback_reason: FallbackReason = Field(default=FallbackReason.NONE, description="Reason for fallback if any")
    merchant: MerchantInfo = Field(description="Extracted merchant information")
    invoice: InvoiceMeta = Field(description="Invoice metadata")
    items: list[InvoiceItem] = Field(default_factory=list, description="Extracted line items")
    totals: InvoiceTotals = Field(description="Extracted amounts and totals")
    validation: ValidationReport = Field(description="Mathematical and semantic validation report")
    quality: ImageQuality = Field(default_factory=ImageQuality, description="Image quality metrics")
    timings_ms: Timings = Field(default_factory=Timings, description="Latency breakdown")
    needs_review: bool = Field(default=False, description="Flag indicating user manual review recommended")
    warnings: list[str] = Field(default_factory=list, description="Non-fatal parsing warnings")
