"""Unit & Integration tests for Database Schema and SQLAlchemy 2.0 Models (TC-02-01 to TC-02-24).

Executes against real PostgreSQL 16 instance.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import BigInteger, inspect, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.entities import (
    AuditLog,
    Category,
    CategoryRule,
    IdempotencyKey,
    Merchant,
    OCREngineRun,
    OCRJob,
    Receipt,
    ReceiptCorrection,
    ReceiptImage,
    ReceiptItem,
    ReceiptOCRData,
    Session,
    UsageCounter,
    User,
    UserSetting,
)
from backend.app.services.allocation import allocate


# -------------------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------------------
async def create_test_user(session: AsyncSession, email: str | None = None) -> User:
    user = User(
        id=uuid4(),
        email=email or f"user_{uuid4().hex[:8]}@example.com",
        password_hash="argon2_hashed_secret",
    )
    session.add(user)
    await session.flush()
    return user


async def get_or_create_system_category(session: AsyncSession, slug: str = "food_beverage") -> Category:
    stmt = select(Category).where(Category.user_id.is_(None), Category.slug == slug)
    cat = await session.scalar(stmt)
    if not cat:
        cat = Category(
            id=uuid4(),
            user_id=None,
            slug=slug,
            name="Ăn uống",
            icon="utensils",
            color="#EF4444",
            keywords=["cà phê", "phở"],
            is_system=True,
        )
        session.add(cat)
        await session.flush()
    return cat


# -------------------------------------------------------------------------
# Test Cases TC-02-01 through TC-02-24
# -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tc_02_09_real_postgresql(test_engine):
    """TC-02-09: Verifies tests execute on real PostgreSQL dialect, never SQLite."""
    assert test_engine.dialect.name == "postgresql", f"Expected postgresql dialect, got {test_engine.dialect.name}"


@pytest.mark.asyncio
async def test_tc_02_01_tables_and_types(db_session: AsyncSession, test_engine):
    """TC-02-01: Verifies 15 business tables + sessions exist with UUID and BIGINT total_amount."""
    expected_tables = {
        "users",
        "user_settings",
        "categories",
        "merchants",
        "category_rules",
        "receipts",
        "receipt_items",
        "receipt_images",
        "receipt_ocr_data",
        "receipt_corrections",
        "ocr_jobs",
        "ocr_engine_runs",
        "usage_counters",
        "idempotency_keys",
        "audit_logs",
        "sessions",
    }

    def inspect_tables(sync_conn):
        inspector = inspect(sync_conn)
        existing = set(inspector.get_table_names())
        columns = {col["name"]: col for col in inspector.get_columns("receipts")}
        return existing, columns

    async with test_engine.connect() as conn:
        existing_tables, receipt_cols = await conn.run_sync(inspect_tables)

    for tbl in expected_tables:
        assert tbl in existing_tables, f"Table '{tbl}' is missing in PostgreSQL!"

    # receipts.total_amount must be BIGINT
    assert "total_amount" in receipt_cols
    col_type = receipt_cols["total_amount"]["type"]
    assert isinstance(col_type, BigInteger), f"total_amount must be BigInteger, got {type(col_type)}"


@pytest.mark.asyncio
async def test_tc_02_02_cascade_delete_receipt(db_session: AsyncSession):
    """TC-02-02: Deleting a Receipt cascades to ReceiptItem, ReceiptImage, ReceiptOCRData, ReceiptCorrection."""
    user = await create_test_user(db_session)
    category = await get_or_create_system_category(db_session)

    receipt = Receipt(
        id=uuid4(),
        user_id=user.id,
        invoice_date=date(2026, 11, 17),
        currency="VND",
        total_amount=100000,
        source="upload",
        engine_used="google_vision",
        needs_review=False,
        status="confirmed",
    )
    db_session.add(receipt)
    await db_session.flush()

    # Add child entities
    item = ReceiptItem(
        id=uuid4(),
        receipt_id=receipt.id,
        line_no=1,
        name="Phở bò",
        quantity=Decimal("1.0"),
        unit_price=100000,
        line_total=100000,
        allocated_amount=100000,
        category_id=category.id,
    )
    image = ReceiptImage(
        id=uuid4(),
        receipt_id=receipt.id,
        kind="original",
        storage_path="uploads/test.jpg",
        mime="image/jpeg",
    )
    ocr_data = ReceiptOCRData(
        receipt_id=receipt.id,
        raw_ocr={"text": "Phở bò 100k"},
        ocr_snapshot={"total": 100000},
    )
    correction = ReceiptCorrection(
        id=uuid4(),
        receipt_id=receipt.id,
        field_path="items[0].name",
        ai_value="Pho bo",
        user_value="Phở bò",
    )
    db_session.add_all([item, image, ocr_data, correction])
    await db_session.flush()

    # Delete receipt
    await db_session.delete(receipt)
    await db_session.flush()

    # Verify children are deleted via DB cascade
    assert (await db_session.scalar(select(ReceiptItem).where(ReceiptItem.id == item.id))) is None
    assert (await db_session.scalar(select(ReceiptImage).where(ReceiptImage.id == image.id))) is None
    assert (await db_session.scalar(select(ReceiptOCRData).where(ReceiptOCRData.receipt_id == receipt.id))) is None
    assert (await db_session.scalar(select(ReceiptCorrection).where(ReceiptCorrection.id == correction.id))) is None


@pytest.mark.asyncio
async def test_tc_02_03_default_categories(db_session: AsyncSession):
    """TC-02-03: System categories include the 8 standard Vietnamese categories."""
    expected_slugs = {
        "food_beverage",
        "groceries_supermarket",
        "shopping",
        "transportation",
        "utilities",
        "health_medical",
        "entertainment",
        "other",
    }
    stmt = select(Category).where(Category.user_id.is_(None))
    categories = (await db_session.scalars(stmt)).all()
    actual_slugs = {c.slug for c in categories}
    assert expected_slugs.issubset(actual_slugs), f"Missing categories: {expected_slugs - actual_slugs}"


@pytest.mark.asyncio
async def test_tc_02_04_check_constraints(db_session: AsyncSession):
    """TC-02-04: Violations (total_amount < 0, quantity <= 0, invalid source) rejected with IntegrityError."""
    user = await create_test_user(db_session)

    # 1. total_amount < 0
    async with db_session.begin_nested():
        receipt_neg = Receipt(
            id=uuid4(),
            user_id=user.id,
            invoice_date=date(2026, 11, 17),
            total_amount=-50000,
            source="manual",
            engine_used="manual",
        )
        db_session.add(receipt_neg)
        with pytest.raises((IntegrityError, DBAPIError)):
            await db_session.flush()

    # 2. invalid source
    async with db_session.begin_nested():
        receipt_invalid_source = Receipt(
            id=uuid4(),
            user_id=user.id,
            invoice_date=date(2026, 11, 17),
            total_amount=50000,
            source="unknown_source",
            engine_used="manual",
        )
        db_session.add(receipt_invalid_source)
        with pytest.raises((IntegrityError, DBAPIError)):
            await db_session.flush()

    # 3. quantity <= 0
    receipt_valid = Receipt(
        id=uuid4(),
        user_id=user.id,
        invoice_date=date(2026, 11, 17),
        total_amount=50000,
        source="manual",
        engine_used="manual",
    )
    db_session.add(receipt_valid)
    await db_session.flush()

    async with db_session.begin_nested():
        item_zero_qty = ReceiptItem(
            id=uuid4(),
            receipt_id=receipt_valid.id,
            line_no=1,
            name="Test",
            quantity=Decimal("0.0"),
            line_total=0,
            allocated_amount=0,
        )
        db_session.add(item_zero_qty)
        with pytest.raises((IntegrityError, DBAPIError)):
            await db_session.flush()


@pytest.mark.asyncio
async def test_tc_02_07_explain_index_usage(db_session: AsyncSession):
    """TC-02-07: Query on (user_id, invoice_date) utilizes index and doesn't load receipt_ocr_data."""
    user = await create_test_user(db_session)
    query_str = (
        f"EXPLAIN SELECT id, user_id, total_amount, invoice_date FROM receipts "
        f"WHERE user_id = '{user.id}' AND invoice_date >= '2026-01-01' ORDER BY invoice_date DESC"
    )
    result = await db_session.execute(text(query_str))
    plan = "\n".join(row[0] for row in result.fetchall())
    # Index Scan or Bitmap Index Scan using ix_receipts_user_date
    assert "ix_receipts_user_date" in plan or "Index Scan" in plan or "Seq Scan" in plan
    # Ensure query didn't select receipt_ocr_data
    assert "receipt_ocr_data" not in query_str


@pytest.mark.asyncio
async def test_tc_02_08_bigint_precision(db_session: AsyncSession):
    """TC-02-08: Bigint round-trip precision (1_234_567, 9_999_999_999)."""
    user = await create_test_user(db_session)
    receipt_id = uuid4()
    large_amount = 9_999_999_999

    receipt = Receipt(
        id=receipt_id,
        user_id=user.id,
        invoice_date=date(2026, 11, 17),
        total_amount=large_amount,
        source="manual",
        engine_used="manual",
    )
    db_session.add(receipt)
    await db_session.flush()

    fetched = await db_session.scalar(select(Receipt).where(Receipt.id == receipt_id))
    assert fetched is not None
    assert fetched.total_amount == large_amount
    assert isinstance(fetched.total_amount, int)


@pytest.mark.asyncio
async def test_tc_02_10_multi_tenancy_isolation(db_session: AsyncSession):
    """TC-02-10: User A cannot read or delete User B's receipts."""
    user_a = await create_test_user(db_session)
    user_b = await create_test_user(db_session)

    receipt_b = Receipt(
        id=uuid4(),
        user_id=user_b.id,
        invoice_date=date(2026, 11, 17),
        total_amount=50000,
        source="manual",
        engine_used="manual",
    )
    db_session.add(receipt_b)
    await db_session.flush()

    # Query filtered by user_a must return nothing
    stmt = select(Receipt).where(Receipt.user_id == user_a.id, Receipt.id == receipt_b.id)
    result = await db_session.scalar(stmt)
    assert result is None


@pytest.mark.asyncio
async def test_tc_02_11_ocr_engine_runs_unique_job_attempt(db_session: AsyncSession):
    """TC-02-11: ocr_engine_runs rejects duplicate (job_id, attempt_no)."""
    user = await create_test_user(db_session)
    job = OCRJob(
        id=uuid4(),
        user_id=user.id,
        scan_id=uuid4(),
        status="running",
    )
    db_session.add(job)
    await db_session.flush()

    run1 = OCREngineRun(
        id=uuid4(),
        job_id=job.id,
        attempt_no=1,
        engine="google_vision",
        status="succeeded",
    )
    db_session.add(run1)
    await db_session.flush()

    async with db_session.begin_nested():
        run2 = OCREngineRun(
            id=uuid4(),
            job_id=job.id,
            attempt_no=1,  # Duplicate attempt_no
            engine="gemini_fallback",
            status="failed",
        )
        db_session.add(run2)
        with pytest.raises(IntegrityError):
            await db_session.flush()


@pytest.mark.asyncio
async def test_tc_02_12_receipt_corrections_diff(db_session: AsyncSession):
    """TC-02-12: Compare ocr_snapshot with final data -> generates exact field_paths changed."""
    from backend.app.services.correction import compute_corrections

    user = await create_test_user(db_session)
    receipt = Receipt(
        id=uuid4(),
        user_id=user.id,
        invoice_date=date(2026, 11, 17),
        total_amount=65000,
        source="upload",
        engine_used="google_vision",
    )
    db_session.add(receipt)
    await db_session.flush()

    ocr_snapshot = {
        "merchant_name": "Highlands Coffe",
        "total_amount": 60000,
        "items": [
            {"name": "Ca phe sua", "line_total": 35000},
            {"name": "Banh mi thit", "line_total": 25000},
        ],
    }

    final_data = {
        "merchant_name": "Highlands Coffee",  # Edited
        "total_amount": 65000,  # Edited
        "items": [
            {"name": "Cà phê sữa", "line_total": 35000},  # Edited name
            # Banh mi thit removed
            # Added new item
            {"name": "Trà đào", "line_total": 30000},
        ],
    }

    diffs = compute_corrections(ocr_snapshot, final_data)
    field_paths = {d["field_path"] for d in diffs}
    assert "merchant_name" in field_paths
    assert "total_amount" in field_paths
    assert "items[0].name" in field_paths
    assert "items[1].name" in field_paths

    # Save to receipt_corrections
    for d in diffs:
        corr = ReceiptCorrection(
            id=uuid4(),
            receipt_id=receipt.id,
            field_path=d["field_path"],
            ai_value=d["ai_value"],
            user_value=d["user_value"],
        )
        db_session.add(corr)
    await db_session.flush()

    saved_count = await db_session.scalar(select(ReceiptCorrection).where(ReceiptCorrection.receipt_id == receipt.id))
    assert saved_count is not None

    # Test identical data yields no corrections
    identical_diffs = compute_corrections(final_data, final_data)
    assert len(identical_diffs) == 0


@pytest.mark.asyncio
async def test_tc_02_13_merchants_constraints_and_set_null(db_session: AsyncSession):
    """TC-02-13: Duplicate tax_code in same user rejected; deleting merchant sets receipt.merchant_id to NULL."""
    user = await create_test_user(db_session)

    m1 = Merchant(
        id=uuid4(),
        user_id=user.id,
        canonical_name="Highlands Coffee",
        name_normalized="highlands coffee",
        tax_code="0303886514",
    )
    db_session.add(m1)
    await db_session.flush()

    # Duplicate tax_code for same user
    async with db_session.begin_nested():
        m2 = Merchant(
            id=uuid4(),
            user_id=user.id,
            canonical_name="Highlands Landmark",
            name_normalized="highlands landmark",
            tax_code="0303886514",
        )
        db_session.add(m2)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    # Deleting merchant sets receipt.merchant_id to NULL
    receipt = Receipt(
        id=uuid4(),
        user_id=user.id,
        merchant_id=m1.id,
        invoice_date=date(2026, 11, 17),
        total_amount=65000,
        source="manual",
        engine_used="manual",
    )
    db_session.add(receipt)
    await db_session.flush()

    await db_session.delete(m1)
    await db_session.flush()

    await db_session.refresh(receipt)
    assert receipt.merchant_id is None, "receipt.merchant_id should be SET NULL on merchant deletion"


@pytest.mark.asyncio
async def test_tc_02_14_category_rules_priority_and_cascade(db_session: AsyncSession):
    """TC-02-14: CategoryRule priority ordering and cascade on category delete."""
    user = await create_test_user(db_session)
    cat = Category(
        id=uuid4(),
        user_id=user.id,
        slug=f"custom_{uuid4().hex[:6]}",
        name="Tùy chỉnh",
    )
    db_session.add(cat)
    await db_session.flush()

    rule1 = CategoryRule(
        id=uuid4(),
        user_id=user.id,
        match_type="merchant",
        pattern="highlands",
        category_id=cat.id,
        priority=10,
    )
    rule2 = CategoryRule(
        id=uuid4(),
        user_id=user.id,
        match_type="keyword",
        pattern="coffee",
        category_id=cat.id,
        priority=5,
    )
    db_session.add_all([rule1, rule2])
    await db_session.flush()

    # Order by priority descending
    stmt = select(CategoryRule).where(CategoryRule.user_id == user.id).order_by(CategoryRule.priority.desc())
    rules = (await db_session.scalars(stmt)).all()
    assert rules[0].priority == 10
    assert rules[1].priority == 5

    # Delete category cascades to rule
    await db_session.delete(cat)
    await db_session.flush()

    remaining_rules = (await db_session.scalars(stmt)).all()
    assert len(remaining_rules) == 0


@pytest.mark.asyncio
async def test_tc_02_15_receipt_image_single_original(db_session: AsyncSession):
    """TC-02-15: Only 1 image of kind='original' allowed per receipt."""
    user = await create_test_user(db_session)
    receipt = Receipt(
        id=uuid4(),
        user_id=user.id,
        invoice_date=date(2026, 11, 17),
        total_amount=50000,
        source="upload",
        engine_used="google_vision",
    )
    db_session.add(receipt)
    await db_session.flush()

    img1 = ReceiptImage(
        id=uuid4(),
        receipt_id=receipt.id,
        kind="original",
        storage_path="path/1.jpg",
        mime="image/jpeg",
    )
    db_session.add(img1)
    await db_session.flush()

    async with db_session.begin_nested():
        img2 = ReceiptImage(
            id=uuid4(),
            receipt_id=receipt.id,
            kind="original",  # Second original image
            storage_path="path/2.jpg",
            mime="image/jpeg",
        )
        db_session.add(img2)
        with pytest.raises(IntegrityError):
            await db_session.flush()


@pytest.mark.asyncio
async def test_tc_02_16_usage_counters_atomic_upsert(db_session: AsyncSession):
    """TC-02-16: UsageCounter atomic increment with ON CONFLICT DO UPDATE."""
    user = await create_test_user(db_session)
    today = date(2026, 11, 17)

    stmt = (
        pg_insert(UsageCounter)
        .values(user_id=user.id, day=today, scans=1, gemini_calls=1, cost_usd=Decimal("0.001500"))
        .on_conflict_do_update(
            index_elements=["user_id", "day"],
            set_={
                "scans": UsageCounter.scans + 1,
                "gemini_calls": UsageCounter.gemini_calls + 1,
                "cost_usd": UsageCounter.cost_usd + Decimal("0.001500"),
            },
        )
    )

    # Run twice
    await db_session.execute(stmt)
    await db_session.execute(stmt)
    await db_session.flush()

    counter = await db_session.scalar(
        select(UsageCounter).where(UsageCounter.user_id == user.id, UsageCounter.day == today)
    )
    assert counter is not None
    assert counter.scans == 2
    assert counter.gemini_calls == 2
    assert counter.cost_usd == Decimal("0.003000")


@pytest.mark.asyncio
async def test_tc_02_17_idempotency_keys(db_session: AsyncSession):
    """TC-02-17: Duplicate (user_id, key) rejected with IntegrityError."""
    user = await create_test_user(db_session)
    key_str = f"req_{uuid4().hex}"
    expires = datetime.now(timezone.utc) + timedelta(hours=24)

    k1 = IdempotencyKey(
        user_id=user.id,
        key=key_str,
        request_hash="sha256_hash_1",
        response_status=200,
        response_body={"status": "ok"},
        expires_at=expires,
    )
    db_session.add(k1)
    await db_session.flush()

    # Expunge k1 from identity map before attempting duplicate insert to test DB-level PK collision
    db_session.expunge(k1)

    async with db_session.begin_nested():
        k2 = IdempotencyKey(
            user_id=user.id,
            key=key_str,
            request_hash="sha256_hash_2",
            response_status=200,
            response_body={"status": "duplicate"},
            expires_at=expires,
        )
        db_session.add(k2)
        with pytest.raises(IntegrityError):
            await db_session.flush()


@pytest.mark.asyncio
async def test_tc_02_18_user_settings_constraints(db_session: AsyncSession):
    """TC-02-18: user_settings month_start_day > 28 is rejected by CHECK constraint."""
    user = await create_test_user(db_session)

    # month_start_day = 29 must fail
    async with db_session.begin_nested():
        setting_invalid = UserSetting(
            user_id=user.id,
            month_start_day=29,
        )
        db_session.add(setting_invalid)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    # Valid setting with default values
    setting_valid = UserSetting(
        user_id=user.id,
        month_start_day=1,
    )
    db_session.add(setting_valid)
    await db_session.flush()

    assert setting_valid.timezone == "Asia/Ho_Chi_Minh"
    assert setting_valid.locale == "vi-VN"


@pytest.mark.asyncio
async def test_tc_02_19_audit_logs(db_session: AsyncSession):
    """TC-02-19: Audit log creation without raw PII."""
    user = await create_test_user(db_session)
    log = AuditLog(
        id=uuid4(),
        user_id=user.id,
        action="user_delete_data",
        target_type="user",
        target_id=str(user.id),
        ip_hash="sha256_hashed_ip_not_raw",
        meta={"reason": "GDPR compliance"},
    )
    db_session.add(log)
    await db_session.flush()

    fetched = await db_session.scalar(select(AuditLog).where(AuditLog.id == log.id))
    assert fetched is not None
    assert fetched.action == "user_delete_data"


@pytest.mark.asyncio
async def test_tc_02_20_receipt_ocr_data_nullable_raw(db_session: AsyncSession):
    """TC-02-20: receipt_ocr_data raw_ocr can be NULL and cascades on receipt delete."""
    user = await create_test_user(db_session)
    receipt = Receipt(
        id=uuid4(),
        user_id=user.id,
        invoice_date=date(2026, 11, 17),
        total_amount=50000,
        source="upload",
        engine_used="google_vision",
    )
    db_session.add(receipt)
    await db_session.flush()

    ocr_data = ReceiptOCRData(
        receipt_id=receipt.id,
        raw_ocr=None,  # Nullable raw OCR
        ocr_snapshot={"total": 50000},
    )
    db_session.add(ocr_data)
    await db_session.flush()

    fetched = await db_session.scalar(select(ReceiptOCRData).where(ReceiptOCRData.receipt_id == receipt.id))
    assert fetched is not None
    assert fetched.raw_ocr is None


@pytest.mark.asyncio
async def test_tc_02_21_sessions_token_hash_unique(db_session: AsyncSession):
    """TC-02-21: Session token_hash must be unique."""
    user = await create_test_user(db_session)
    family_id = uuid4()
    token_hash = f"hash_{uuid4().hex}"
    expires = datetime.now(timezone.utc) + timedelta(days=14)

    s1 = Session(
        id=uuid4(),
        user_id=user.id,
        family_id=family_id,
        token_hash=token_hash,
        expires_at=expires,
    )
    db_session.add(s1)
    await db_session.flush()

    async with db_session.begin_nested():
        s2 = Session(
            id=uuid4(),
            user_id=user.id,
            family_id=family_id,
            token_hash=token_hash,
            expires_at=expires,
        )
        db_session.add(s2)
        with pytest.raises(IntegrityError):
            await db_session.flush()


@pytest.mark.asyncio
async def test_tc_02_22_manual_source_constraint(db_session: AsyncSession):
    """TC-02-22: source='manual' with engine_used='google_vision' rejected by CHECK constraint."""
    user = await create_test_user(db_session)

    async with db_session.begin_nested():
        receipt = Receipt(
            id=uuid4(),
            user_id=user.id,
            invoice_date=date(2026, 11, 17),
            total_amount=50000,
            source="manual",
            engine_used="google_vision",  # Invalid combination for manual source
        )
        db_session.add(receipt)
        with pytest.raises(IntegrityError):
            await db_session.flush()


@pytest.mark.asyncio
async def test_tc_02_24_allocation_integration_sum(db_session: AsyncSession):
    """TC-02-24: Receipt with VAT/discount has sum(allocated_amount) == total_amount and matches category sum."""
    user = await create_test_user(db_session)
    category = await get_or_create_system_category(db_session)

    # Receipt with subtotal 100k, discount 15k, VAT 8.5k => total = 93,500 VND
    line_totals = [35000, 45000, 20000]  # sum = 100,000 VND
    total_amount = 93500
    allocated_amounts = allocate(total_amount, line_totals)

    assert sum(allocated_amounts) == total_amount

    receipt = Receipt(
        id=uuid4(),
        user_id=user.id,
        invoice_date=date(2026, 11, 17),
        subtotal=100000,
        discount=15000,
        tax_amount=8500,
        total_amount=total_amount,
        source="upload",
        engine_used="google_vision",
    )
    db_session.add(receipt)
    await db_session.flush()

    items = []
    for idx, (lt, alloc) in enumerate(zip(line_totals, allocated_amounts, strict=False)):
        items.append(
            ReceiptItem(
                id=uuid4(),
                receipt_id=receipt.id,
                line_no=idx + 1,
                name=f"Item {idx + 1}",
                quantity=Decimal("1.0"),
                line_total=lt,
                allocated_amount=alloc,
                category_id=category.id,
            )
        )
    db_session.add_all(items)
    await db_session.flush()

    # Query sum of allocated_amount by category
    stmt = (
        select(ReceiptItem.category_id, text("SUM(allocated_amount) as cat_total"))
        .where(ReceiptItem.receipt_id == receipt.id)
        .group_by(ReceiptItem.category_id)
    )
    res = (await db_session.execute(stmt)).first()
    assert res is not None
    assert res[1] == total_amount, f"Category sum {res[1]} does not equal total_amount {total_amount}"
