# Mathematical & Semantic Extraction Validator

This document details the validation framework implemented in `backend/app/services/validation/validator.py` (Feature 03).

## 1. Validation Matrix (Checks V1 – V7)

Rather than returning a naive boolean flag with a loose 10% tolerance, `validate_extraction` produces a detailed `ValidationReport` evaluating seven structural and mathematical rules:

| Check | Type | Description | Condition |
|---|---|---|---|
| **V1** | Hard | Total Amount Presence | `total_amount > 0` |
| **V2** | Soft | Unit Price Calculation | $|quantity \times unit\_price - line\_total| \le 1\text{ VND}$ for each item |
| **V3** | Hard | Mathematical Sum Balance | $|\sum line\_total + tax + service - discount - total| \le tolerance$ |
| **V4** | Hard | Minimum Item Count | Number of line items $\ge 1$ (except single-item utility bills) |
| **V5** | Soft | Valid Invoice Date | $2000 \le year \le 2099$ and date is not in the future |
| **V6** | Soft | Merchant Identity | Merchant name is recognized and not generic |
| **V7** | Soft | OCR Confidence Threshold | Average OCR confidence $\ge 0.80$ |

## 2. Tolerance Formulation

The mathematical balance check (V3) enforces an adaptive tolerance accounting for minor round-off differences and rounding conventions in Vietnamese currency:

$$\text{tolerance} = \max(1.000\text{ VND}, 0.005 \times \text{total\_amount})$$

- For a 100,000 VND bill: tolerance is $\max(1.000, 500) = 1.000$ VND.
- For a 2,000,000 VND bill: tolerance is $\max(1.000, 10.000) = 10.000$ VND ($0.5\%$).

## 3. Verdict Categorization

1. **`PASS`**:
   - Zero hard check failures.
   - Overall composite score $\ge 0.80$.
   - Directly accepted for processing and financial reporting.
2. **`REVIEW`**:
   - Zero hard check failures, but low confidence score ($< 0.80$) or minor soft warnings.
   - Flagged for user review or Gemini Vision fallback confirmation.
3. **`FAIL`**:
   - One or more hard check failures (e.g. total missing, math imbalance $> 0.5\%$, or zero items).
   - Automatically triggers the secondary OCR engine (Gemini Flash multimodal fallback in Feature 04/05).
