"""Seed default system categories and rules in an idempotent manner (TC-02-03, TC-02-06)."""

import asyncio
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.entities.category import Category
from backend.app.models.entities.category_rule import CategoryRule

DEFAULT_SYSTEM_CATEGORIES: list[dict[str, Any]] = [
    {
        "slug": "food_beverage",
        "name": "Ăn uống",
        "icon": "utensils",
        "color": "#EF4444",
        "keywords": [
            "cà phê",
            "coffee",
            "trà sữa",
            "nhà hàng",
            "quán ăn",
            "bún",
            "phở",
            "cơm",
            "bánh mì",
            "pizza",
            "nước ngọt",
            "bia",
            "lẩu",
            "nướng",
        ],
        "rules": [
            ("merchant", "highlands", 10),
            ("merchant", "phúc long", 10),
            ("merchant", "the coffee house", 10),
            ("merchant", "starbucks", 10),
            ("merchant", "kfc", 10),
            ("merchant", "lotteria", 10),
            ("merchant", "mcdonald", 10),
            ("keyword", "cà phê", 5),
            ("keyword", "trà sữa", 5),
            ("keyword", "bún bò", 5),
            ("keyword", "phở bò", 5),
            ("keyword", "cơm tấm", 5),
        ],
    },
    {
        "slug": "groceries_supermarket",
        "name": "Đi chợ & Siêu thị",
        "icon": "shopping-cart",
        "color": "#10B981",
        "keywords": [
            "siêu thị",
            "co.opmart",
            "winmart",
            "bách hóa xanh",
            "thịt",
            "cá",
            "rau",
            "trái cây",
            "sữa",
            "trứng",
            "gia vị",
            "gạo",
            "dầu ăn",
        ],
        "rules": [
            ("merchant", "co.opmart", 10),
            ("merchant", "winmart", 10),
            ("merchant", "bách hóa xanh", 10),
            ("merchant", "lotte mart", 10),
            ("merchant", "big c", 10),
            ("merchant", "mega market", 10),
            ("merchant", "circle k", 8),
            ("keyword", "siêu thị", 5),
            ("keyword", "thịt heo", 5),
            ("keyword", "thịt bò", 5),
            ("keyword", "rau củ", 5),
        ],
    },
    {
        "slug": "shopping",
        "name": "Mua sắm",
        "icon": "shopping-bag",
        "color": "#F59E0B",
        "keywords": [
            "quần áo",
            "giày dép",
            "mỹ phẩm",
            "shopee",
            "lazada",
            "tiki",
            "điện thoại",
            "máy tính",
            "thời trang",
            "phụ kiện",
        ],
        "rules": [
            ("merchant", "shopee", 10),
            ("merchant", "lazada", 10),
            ("merchant", "tiki", 10),
            ("merchant", "uniqlo", 10),
            ("merchant", "zara", 10),
            ("keyword", "quần áo", 5),
            ("keyword", "giày dép", 5),
            ("keyword", "mỹ phẩm", 5),
        ],
    },
    {
        "slug": "transportation",
        "name": "Di chuyển",
        "icon": "car",
        "color": "#3B82F6",
        "keywords": [
            "xăng",
            "petrolimex",
            "pvoil",
            "grab",
            "be",
            "taxi",
            "gửi xe",
            "vé xe",
            "bảo dưỡng xe",
            "rửa xe",
            "cầu đường",
        ],
        "rules": [
            ("merchant", "petrolimex", 10),
            ("merchant", "pvoil", 10),
            ("merchant", "grab", 10),
            ("merchant", "be group", 10),
            ("merchant", "xanh sm", 10),
            ("keyword", "xăng ron", 5),
            ("keyword", "gửi xe", 5),
            ("keyword", "vé xe", 5),
        ],
    },
    {
        "slug": "utilities",
        "name": "Hóa đơn & Tiện ích",
        "icon": "zap",
        "color": "#6366F1",
        "keywords": [
            "tiền điện",
            "evn",
            "tiền nước",
            "sawaco",
            "internet",
            "viettel",
            "vnpt",
            "fpt",
            "rác",
            "chung cư",
            "phí quản lý",
        ],
        "rules": [
            ("merchant", "evn", 10),
            ("merchant", "sawaco", 10),
            ("merchant", "fpt telecom", 10),
            ("merchant", "viettel telecom", 10),
            ("merchant", "vnpt", 10),
            ("keyword", "tiền điện", 5),
            ("keyword", "tiền nước", 5),
            ("keyword", "cước internet", 5),
        ],
    },
    {
        "slug": "health_medical",
        "name": "Sức khỏe & Y tế",
        "icon": "heart-pulse",
        "color": "#EC4899",
        "keywords": [
            "thuốc",
            "nhà thuốc",
            "pharmacity",
            "long châu",
            "an khang",
            "bệnh viện",
            "phòng khám",
            "bác sĩ",
            "khám bệnh",
            "vitamin",
        ],
        "rules": [
            ("merchant", "pharmacity", 10),
            ("merchant", "long châu", 10),
            ("merchant", "an khang", 10),
            ("keyword", "nhà thuốc", 5),
            ("keyword", "thuốc", 5),
            ("keyword", "khám bệnh", 5),
        ],
    },
    {
        "slug": "entertainment",
        "name": "Giải trí",
        "icon": "film",
        "color": "#8B5CF6",
        "keywords": [
            "xem phim",
            "cinema",
            "cgv",
            "lotte cinema",
            "bhd",
            "netflix",
            "spotify",
            "du lịch",
            "khách sạn",
            "karaoke",
            "game",
        ],
        "rules": [
            ("merchant", "cgv", 10),
            ("merchant", "lotte cinema", 10),
            ("merchant", "galaxy cinema", 10),
            ("merchant", "netflix", 10),
            ("merchant", "spotify", 10),
            ("keyword", "vé xem phim", 5),
            ("keyword", "karaoke", 5),
        ],
    },
    {
        "slug": "other",
        "name": "Khác",
        "icon": "more-horizontal",
        "color": "#6B7280",
        "keywords": [
            "khác",
            "chuyển khoản",
            "rút tiền",
            "phí dịch vụ",
            "chi tiêu khác",
        ],
        "rules": [
            ("keyword", "chi tiêu khác", 1),
        ],
    },
]


async def seed_categories(session: AsyncSession) -> dict[str, int]:
    """Idempotently seed the 8 default system categories and rules.

    Returns dict with counts of created categories and rules.
    """
    created_cats = 0
    created_rules = 0

    for cat_data in DEFAULT_SYSTEM_CATEGORIES:
        slug = cat_data["slug"]
        stmt = select(Category).where(
            Category.user_id.is_(None),
            Category.slug == slug,
        )
        existing_cat = (await session.execute(stmt)).scalar_one_or_none()

        if not existing_cat:
            cat = Category(
                id=uuid4(),
                user_id=None,
                slug=slug,
                name=cat_data["name"],
                icon=cat_data["icon"],
                color=cat_data["color"],
                keywords=cat_data["keywords"],
                is_system=True,
            )
            session.add(cat)
            await session.flush()
            created_cats += 1
        else:
            cat = existing_cat

        # Seed category rules associated with system categories
        for match_type, pattern, priority in cat_data.get("rules", []):
            rule_stmt = select(CategoryRule).where(
                CategoryRule.user_id.is_(None),
                CategoryRule.match_type == match_type,
                CategoryRule.pattern == pattern,
            )
            existing_rule = (await session.execute(rule_stmt)).scalar_one_or_none()
            if not existing_rule:
                rule = CategoryRule(
                    id=uuid4(),
                    user_id=None,
                    match_type=match_type,
                    pattern=pattern,
                    category_id=cat.id,
                    priority=priority,
                    hit_count=0,
                    source="seed",
                )
                session.add(rule)
                created_rules += 1

    await session.commit()
    return {"categories_created": created_cats, "rules_created": created_rules}


async def main() -> None:
    """CLI execution entrypoint."""
    async with AsyncSessionLocal() as session:
        result = await seed_categories(session)
        print(f"[+] Category seed finished: {result}")


if __name__ == "__main__":
    asyncio.run(main())
