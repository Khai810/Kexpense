"""Receipt Correction Detection Service (TC-02-12).

Detects granular field-level edits made by the user relative to initial AI/OCR snapshots.
"""

from typing import Any


def compute_corrections(
    ocr_snapshot: dict[str, Any],
    final_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """Compare initial OCR snapshot against user-confirmed final data.

    Returns a list of correction dicts with keys:
    - 'field_path': string dot-notation path (e.g. 'merchant_name', 'items[0].name')
    - 'ai_value': original value in OCR snapshot
    - 'user_value': final edited value
    """
    corrections: list[dict[str, Any]] = []

    # 1. Compare top-level scalar fields
    scalar_fields = [
        "merchant_name",
        "merchant_tax_code",
        "invoice_number",
        "invoice_date",
        "total_amount",
        "subtotal",
        "discount",
        "tax_amount",
    ]

    for field in scalar_fields:
        ai_val = ocr_snapshot.get(field)
        final_val = final_data.get(field)

        # Normalize string comparison if needed
        if ai_val != final_val and not (ai_val is None and final_val is None):
            corrections.append(
                {
                    "field_path": field,
                    "ai_value": ai_val,
                    "user_value": final_val,
                }
            )

    # 2. Compare items list
    ai_items: list[dict[str, Any]] = ocr_snapshot.get("items") or []
    final_items: list[dict[str, Any]] = final_data.get("items") or []

    max_len = max(len(ai_items), len(final_items))
    item_fields = ["name", "quantity", "unit_price", "line_total", "category_id", "category_slug"]

    for idx in range(max_len):
        if idx >= len(ai_items):
            # Item added by user
            corrections.append(
                {
                    "field_path": f"items[{idx}]",
                    "ai_value": None,
                    "user_value": final_items[idx],
                }
            )
        elif idx >= len(final_items):
            # Item removed by user
            corrections.append(
                {
                    "field_path": f"items[{idx}]",
                    "ai_value": ai_items[idx],
                    "user_value": None,
                }
            )
        else:
            # Both exist - compare individual item fields
            ai_item = ai_items[idx]
            fin_item = final_items[idx]
            for f in item_fields:
                ai_f = ai_item.get(f)
                fin_f = fin_item.get(f)
                if ai_f != fin_f and not (ai_f is None and fin_f is None):
                    corrections.append(
                        {
                            "field_path": f"items[{idx}].{f}",
                            "ai_value": ai_f,
                            "user_value": fin_f,
                        }
                    )

    return corrections
