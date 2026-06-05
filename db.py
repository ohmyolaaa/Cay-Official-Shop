import os
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

_client: Client | None = None

CATEGORIES_TABLE = "cay_shop_categories"
PRODUCTS_TABLE = "cay_shop_products"
USERS_TABLE = "cay_shop_users"


def get_client() -> Client:
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set.")
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


# ─── USERS ───────────────────────────────────────────────────────────────────

async def get_or_create_user(user_id: int, username: str | None, full_name: str) -> dict:
    c = get_client()
    r = c.table(USERS_TABLE).select("*").eq("user_id", user_id).limit(1).execute()
    if r.data:
        if r.data[0]["full_name"] != full_name or r.data[0]["username"] != username:
            c.table(USERS_TABLE).update({
                "full_name": full_name,
                "username": username,
            }).eq("user_id", user_id).execute()
            r.data[0]["full_name"] = full_name
            r.data[0]["username"] = username
        return r.data[0]
    ins = c.table(USERS_TABLE).insert({
        "user_id": user_id,
        "username": username,
        "full_name": full_name,
        "balance": 0.0,
        "total_purchases": 0,
        "total_spent": 0.0,
    }).execute()
    return ins.data[0]


async def get_user(user_id: int) -> dict | None:
    c = get_client()
    r = c.table(USERS_TABLE).select("*").eq("user_id", user_id).limit(1).execute()
    return r.data[0] if r.data else None


# ─── CATEGORIES ──────────────────────────────────────────────────────────────

async def get_categories() -> list[dict]:
    c = get_client()
    r = c.table(CATEGORIES_TABLE).select("*").order("position").order("id").execute()
    return r.data or []


async def get_category(cat_id: int) -> dict | None:
    c = get_client()
    r = c.table(CATEGORIES_TABLE).select("*").eq("id", cat_id).limit(1).execute()
    return r.data[0] if r.data else None


async def add_category(name: str, emoji: str = "📦") -> int:
    c = get_client()
    r = c.table(CATEGORIES_TABLE).select("position").order("position", desc=True).limit(1).execute()
    pos = (r.data[0]["position"] + 1) if r.data else 1
    ins = c.table(CATEGORIES_TABLE).insert({"name": name, "emoji": emoji, "position": pos}).execute()
    return ins.data[0]["id"]


async def delete_category(cat_id: int):
    c = get_client()
    c.table(CATEGORIES_TABLE).delete().eq("id", cat_id).execute()


# ─── PRODUCTS ────────────────────────────────────────────────────────────────

async def get_products(category_id: int) -> list[dict]:
    c = get_client()
    r = (
        c.table(PRODUCTS_TABLE)
        .select("*")
        .eq("category_id", category_id)
        .order("position")
        .order("id")
        .execute()
    )
    return r.data or []


async def get_product(product_id: int) -> dict | None:
    c = get_client()
    r = c.table(PRODUCTS_TABLE).select("*").eq("id", product_id).limit(1).execute()
    return r.data[0] if r.data else None


async def add_product(category_id: int, name: str, description: str, price: float, stock: int) -> int:
    c = get_client()
    r = (
        c.table(PRODUCTS_TABLE)
        .select("position")
        .eq("category_id", category_id)
        .order("position", desc=True)
        .limit(1)
        .execute()
    )
    pos = (r.data[0]["position"] + 1) if r.data else 1
    ins = c.table(PRODUCTS_TABLE).insert({
        "category_id": category_id,
        "name": name,
        "description": description,
        "price": price,
        "stock": stock,
        "position": pos,
    }).execute()
    return ins.data[0]["id"]


async def update_product_stock(product_id: int, stock: int):
    c = get_client()
    c.table(PRODUCTS_TABLE).update({"stock": stock}).eq("id", product_id).execute()


async def delete_product(product_id: int):
    c = get_client()
    c.table(PRODUCTS_TABLE).delete().eq("id", product_id).execute()


# ─── AVAILABILITY TEXT ────────────────────────────────────────────────────────

async def get_all_products_availability() -> str:
    categories = await get_categories()
    if not categories:
        return "📋 <b>What's Available</b>\n─────────────────────\n\nNo products added yet."

    lines = ["📋 <b>What's Available</b>\n─────────────────────"]
    for cat in categories:
        products = await get_products(cat["id"])
        if not products:
            continue
        lines.append(f"\n{cat['emoji']} <b>{cat['name']}</b>")
        for i, p in enumerate(products):
            prefix = "└" if i == len(products) - 1 else "├"
            stock_icon = "✅" if p["stock"] > 0 else "❌"
            stock_text = f"Available • {p['stock']}x" if p["stock"] > 0 else "Out of Stock"
            lines.append(f"{prefix} #{p['id']} {p['name']}")
            lines.append(f"│  {stock_icon} {stock_text}")
    return "\n".join(lines)
