import os
import asyncio
import logging
from datetime import datetime
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Bot,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from telegram.error import Conflict, NetworkError
import db

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

ADMIN_IDS = [
    int(x.strip())
    for x in os.environ.get("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
]

MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("🛒 Products")],
        [KeyboardButton("👤 Profile"), KeyboardButton("🎁 Invite Center")],
        [KeyboardButton("💰 Top up balance"), KeyboardButton("🎫 Redeem Code")],
        [KeyboardButton("📋 Bot Policy"), KeyboardButton("❓ Help")],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

BOT_POLICY = (
    "🗒 <b>Bot Policy</b>\n\n"
    "We believe in complete transparency with our customers and do not seek to annoy or exploit anyone. "
    "Please read the following policy carefully before using our services:\n\n"
    "1️⃣ <b>Refund Policy:</b>\n"
    "Funds cannot be refunded after depositing to the bot, except in one case only: if you deposit and do not "
    "purchase any product (i.e., the transaction is incomplete), in this case your money will be fully refunded.\n\n"
    "2️⃣ <b>Warranty Policy:</b>\n"
    "We guarantee all products that mention warranty. In case of any problem during the warranty period, "
    "we will take one of the following actions:\n"
    "• Replace the service immediately and compensate the user.\n"
    "• Or if the user does not wish to replace, the amount will be returned as balance in the bot and can be "
    "used to purchase any other product.\n\n"
    "3️⃣ <b>Free Credits:</b>\n"
    "Funds received by the user through redeem codes or referral rewards cannot be refunded.\n\n"
    "4️⃣ <b>Our Commitment:</b>\n"
    "We are fully responsible for our services and strive to ensure that no customer is annoyed or harmed.\n\n"
    "5️⃣ <b>Our Promise:</b>\n"
    "We promise to always be honest and faithful with you, and strive to be the best in providing these services."
)

HELP_TEXT = (
    "💬 <b>Support &amp; Assistance</b>\n\n"
    "✉️ If you need help, please contact\n"
    "<b>Customer Support:</b> @caydigitals\n\n"
    "⏳ You will receive a response once your request has been reviewed"
)

MENU_BUTTONS = {
    "🛒 Products",
    "👤 Profile",
    "🎁 Invite Center",
    "💰 Top up balance",
    "🎫 Redeem Code",
    "📋 Bot Policy",
    "❓ Help",
}


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ─── USER-FACING KEYBOARDS ───────────────────────────────────────────────────

async def build_products_keyboard() -> InlineKeyboardMarkup:
    categories = await db.get_categories()
    rows = [[InlineKeyboardButton("✅ Official Subscriptions", callback_data="noop")]]
    pairs = []
    for cat in categories:
        pairs.append(InlineKeyboardButton(
            f"{cat['emoji']} {cat['name']}",
            callback_data=f"cat_{cat['id']}"
        ))
    for i in range(0, len(pairs), 2):
        rows.append(pairs[i:i+2])
    rows.append([InlineKeyboardButton("🟢 What's Available", callback_data="whats_available")])
    rows.append([InlineKeyboardButton("✕ Close", callback_data="close")])
    return InlineKeyboardMarkup(rows)


def build_profile_text(user) -> str:
    reg_date = datetime.now().strftime("%m/%d/%Y, %H:%M")
    full_name = user.full_name if user else "Unknown"
    user_id = user.id if user else "N/A"
    return (
        f"👤 <b>Profile</b>\n\n"
        f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
        f"👤 <b>Name:</b> {full_name}\n"
        f"💰 <b>Balance:</b> $0.00\n"
        f"⭐ <b>Level:</b> Newbie (1)\n"
        f"🏷️ <b>Product discount:</b> 0%\n"
        f"🛒 <b>Total purchases:</b> 0\n"
        f"💸 <b>Spent (net):</b> $0.00\n"
        f"🤝 <b>Reseller discount:</b> ❌\n"
        f"📅 <b>Registration date:</b> {reg_date}"
    )

PROFILE_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("🏅 My Status", callback_data="profile_status"),
        InlineKeyboardButton("📋 My Orders", callback_data="profile_orders"),
    ],
    [
        InlineKeyboardButton("💸 Withdraw", callback_data="profile_withdraw"),
        InlineKeyboardButton("👛 Wallet statement", callback_data="profile_wallet"),
    ],
    [
        InlineKeyboardButton("📝 Withdraw requests", callback_data="profile_withdraw_req"),
        InlineKeyboardButton("📄 Withdraw profile", callback_data="profile_withdraw_pro"),
    ],
    [InlineKeyboardButton("✕ Close", callback_data="close")],
])


# ─── ADMIN PANEL BUILDERS ────────────────────────────────────────────────────

def admin_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📂 Manage Categories", callback_data="admin_categories")],
        [InlineKeyboardButton("📦 Manage Products", callback_data="admin_products")],
        [InlineKeyboardButton("✕ Close", callback_data="close")],
    ])


async def admin_categories_keyboard() -> InlineKeyboardMarkup:
    cats = await db.get_categories()
    rows = []
    for cat in cats:
        rows.append([
            InlineKeyboardButton(f"{cat['emoji']} {cat['name']}", callback_data=f"admin_cat_{cat['id']}"),
            InlineKeyboardButton("🗑 Delete", callback_data=f"admin_delcat_{cat['id']}"),
        ])
    rows.append([InlineKeyboardButton("➕ Add Category", callback_data="admin_addcat")])
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="admin_main")])
    return InlineKeyboardMarkup(rows)


async def admin_products_pick_cat_keyboard() -> InlineKeyboardMarkup:
    cats = await db.get_categories()
    rows = []
    for cat in cats:
        rows.append([InlineKeyboardButton(
            f"{cat['emoji']} {cat['name']}",
            callback_data=f"admin_prodcat_{cat['id']}"
        )])
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="admin_main")])
    return InlineKeyboardMarkup(rows)


async def admin_products_keyboard(cat_id: int):
    products = await db.get_products(cat_id)
    cat = await db.get_category(cat_id)
    rows = []
    for p in products:
        stock_icon = "✅" if p["stock"] > 0 else "❌"
        rows.append([
            InlineKeyboardButton(
                f"{stock_icon} #{p['id']} {p['name']} (${p['price']:.2f}, {p['stock']}x)",
                callback_data=f"admin_prod_{p['id']}"
            ),
        ])
        rows.append([
            InlineKeyboardButton("✏️ Stock", callback_data=f"admin_stock_{p['id']}"),
            InlineKeyboardButton("🗑 Delete", callback_data=f"admin_delprod_{p['id']}"),
        ])
    rows.append([InlineKeyboardButton(
        "➕ Add Product",
        callback_data=f"admin_addprod_{cat_id}"
    )])
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="admin_products")])
    cat_name = f"{cat['emoji']} {cat['name']}" if cat else "Category"
    return InlineKeyboardMarkup(rows), cat_name


# ─── USER COMMAND HANDLERS ───────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    first_name = update.effective_user.first_name if update.effective_user else "there"
    await update.message.reply_text(
        f"👋 Hello, {first_name}! Welcome to CayShop Bot!!\n\nI'm here to help you purchase subscriptions and digital services easily and securely.",
        reply_markup=MAIN_MENU,
    )


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 أهلاً بك في ToolAI Bot\nالرجاء اختيار لغتك المفضلة / Please select your preferred language:",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🇸🇦 Arabic عربي", callback_data="lang_ar"),
                InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"),
            ]
        ]),
    )


async def contactadmin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        HELP_TEXT,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✕ Close", callback_data="close")]
        ]),
    )


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ You are not authorized to use this command.")
        return
    await update.message.reply_text(
        "🔧 <b>Admin Panel</b>\n\nManage your bot's categories and products below:",
        parse_mode="HTML",
        reply_markup=admin_main_keyboard(),
    )


# ─── COMBINED MESSAGE HANDLER ─────────────────────────────────────────────────
# Single handler for ALL text messages. For admins with an active flow,
# it processes the admin input first; otherwise it handles menu buttons.

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    user_id = update.effective_user.id

    # ── Admin input flow (only when awaiting a response) ──
    if is_admin(user_id) and context.user_data.get("awaiting"):
        # Only intercept if the text is NOT a menu button press
        if text not in MENU_BUTTONS:
            await _process_admin_input(update, context)
            return

    # ── Menu buttons ──
    if text == "🛒 Products":
        kb = await build_products_keyboard()
        await update.message.reply_text("Choose a service:", reply_markup=kb)

    elif text == "👤 Profile":
        await update.message.reply_text(
            build_profile_text(update.effective_user),
            parse_mode="HTML",
            reply_markup=PROFILE_KEYBOARD,
        )

    elif text == "🎁 Invite Center":
        await update.message.reply_text(
            "🎁 <b>Invite Center</b>\n\nShare your referral link and earn rewards!",
            parse_mode="HTML",
            reply_markup=MAIN_MENU,
        )

    elif text == "💰 Top up balance":
        await update.message.reply_text(
            "💰 <b>Top Up Balance</b>\n\nChoose a payment method to add funds to your account.",
            parse_mode="HTML",
            reply_markup=MAIN_MENU,
        )

    elif text == "🎫 Redeem Code":
        await update.message.reply_text(
            "Please send your redeem code:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💬 Request Redeem Code", url="https://t.me/caydigitals")],
                [InlineKeyboardButton("✕ Close", callback_data="close")],
            ]),
        )

    elif text == "📋 Bot Policy":
        await update.message.reply_text(
            BOT_POLICY,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✕ Close", callback_data="close")]
            ]),
        )

    elif text == "❓ Help":
        await update.message.reply_text(
            HELP_TEXT,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✕ Close", callback_data="close")]
            ]),
        )

    else:
        await update.message.reply_text(
            "Please choose an option from the menu below:",
            reply_markup=MAIN_MENU,
        )


# ─── ADMIN TEXT INPUT LOGIC ──────────────────────────────────────────────────

async def _process_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    awaiting = context.user_data.get("awaiting")
    text = update.message.text.strip()

    # ── Category flow ──
    if awaiting == "cat_name":
        context.user_data["new_cat_name"] = text
        context.user_data["awaiting"] = "cat_emoji"
        await update.message.reply_text("Now send an <b>emoji</b> for this category (e.g. 🌟):", parse_mode="HTML")

    elif awaiting == "cat_emoji":
        name = context.user_data.pop("new_cat_name")
        emoji = text
        context.user_data.pop("awaiting", None)
        await db.add_category(name, emoji)
        await update.message.reply_text(
            f"✅ Category <b>{emoji} {name}</b> added!\n\nUse /admin to manage products.",
            parse_mode="HTML",
            reply_markup=MAIN_MENU,
        )

    # ── Product flow ──
    elif awaiting == "prod_name":
        context.user_data["new_prod_name"] = text
        context.user_data["awaiting"] = "prod_desc"
        await update.message.reply_text("Enter a <b>description</b> for this product:", parse_mode="HTML")

    elif awaiting == "prod_desc":
        context.user_data["new_prod_desc"] = text
        context.user_data["awaiting"] = "prod_price"
        await update.message.reply_text("Enter the <b>price</b> (e.g. 4.99):", parse_mode="HTML")

    elif awaiting == "prod_price":
        try:
            price = float(text)
        except ValueError:
            await update.message.reply_text("❌ Invalid price. Please enter a number like 4.99:")
            return
        context.user_data["new_prod_price"] = price
        context.user_data["awaiting"] = "prod_stock"
        await update.message.reply_text("Enter the <b>stock quantity</b> (e.g. 10):", parse_mode="HTML")

    elif awaiting == "prod_stock":
        try:
            stock = int(text)
        except ValueError:
            await update.message.reply_text("❌ Invalid quantity. Enter a whole number:")
            return
        cat_id = context.user_data.pop("new_prod_cat_id")
        name = context.user_data.pop("new_prod_name")
        desc = context.user_data.pop("new_prod_desc")
        price = context.user_data.pop("new_prod_price")
        context.user_data.pop("awaiting", None)
        await db.add_product(cat_id, name, desc, price, stock)
        cat = await db.get_category(cat_id)
        cat_name = f"{cat['emoji']} {cat['name']}" if cat else "category"
        await update.message.reply_text(
            f"✅ Product <b>{name}</b> added to <b>{cat_name}</b>!\n"
            f"💵 ${price:.2f} | 📦 {stock}x in stock",
            parse_mode="HTML",
            reply_markup=MAIN_MENU,
        )

    # ── Stock update flow ──
    elif awaiting == "stock":
        try:
            stock = int(text)
        except ValueError:
            await update.message.reply_text("❌ Invalid quantity. Enter a whole number:")
            return
        prod_id = context.user_data.pop("stock_prod_id")
        context.user_data.pop("stock_cat_id", None)
        context.user_data.pop("awaiting", None)
        prod = await db.get_product(prod_id)
        await db.update_product_stock(prod_id, stock)
        await update.message.reply_text(
            f"✅ Stock for <b>{prod['name']}</b> updated to <b>{stock}x</b>.",
            parse_mode="HTML",
            reply_markup=MAIN_MENU,
        )


# ─── MAIN CALLBACK HANDLER ───────────────────────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    # ── General ──
    if data == "close":
        await query.message.delete()
        return

    if data == "noop":
        return

    # ── Language ──
    if data == "lang_ar":
        await query.message.edit_text(
            "✅ تم اختيار اللغة العربية\n\nاللغة العربية غير متاحة حالياً، سيتم إضافتها قريباً."
        )
        return

    if data == "lang_en":
        await query.message.edit_text(
            "✅ English language selected.\n\nYou are now using the bot in English."
        )
        return

    # ── Profile ──
    if data in ("profile_status", "profile_orders", "profile_withdraw",
                "profile_wallet", "profile_withdraw_req", "profile_withdraw_pro"):
        labels = {
            "profile_status": "🏅 My Status",
            "profile_orders": "📋 My Orders",
            "profile_withdraw": "💸 Withdraw",
            "profile_wallet": "👛 Wallet statement",
            "profile_withdraw_req": "📝 Withdraw requests",
            "profile_withdraw_pro": "📄 Withdraw profile",
        }
        await query.answer(f"{labels[data]} — coming soon", show_alert=True)
        return

    # ── Products (user) ──
    if data == "whats_available":
        text = await db.get_all_products_availability()
        await query.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back", callback_data="back_to_products")]
            ]),
        )
        return

    if data == "back_to_products":
        kb = await build_products_keyboard()
        await query.message.edit_text("Choose a service:", reply_markup=kb)
        return

    if data.startswith("cat_"):
        cat_id = int(data.split("_")[1])
        cat = await db.get_category(cat_id)
        products = await db.get_products(cat_id)
        if not products:
            await query.answer("No products in this category yet.", show_alert=True)
            return
        lines = [f"{cat['emoji']} <b>{cat['name']}</b>\n"]
        for p in products:
            stock_icon = "✅" if p["stock"] > 0 else "❌"
            stock_text = f"Available • {p['stock']}x" if p["stock"] > 0 else "Out of Stock"
            lines.append(
                f"<b>#{p['id']} {p['name']}</b>\n"
                f"💵 ${p['price']:.2f}  {stock_icon} {stock_text}\n"
                f"{p['description']}\n"
            )
        await query.message.edit_text(
            "\n".join(lines),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back", callback_data="back_to_products")]
            ]),
        )
        return

    # ── ADMIN PANEL ──────────────────────────────────────────────────────────
    if not is_admin(user_id):
        await query.answer("⛔ Admins only.", show_alert=True)
        return

    if data == "admin_main":
        await query.message.edit_text(
            "🔧 <b>Admin Panel</b>\n\nManage your bot's categories and products below:",
            parse_mode="HTML",
            reply_markup=admin_main_keyboard(),
        )
        return

    if data == "admin_categories":
        kb = await admin_categories_keyboard()
        await query.message.edit_text(
            "📂 <b>Categories</b>\n\nAdd, view or delete categories:",
            parse_mode="HTML",
            reply_markup=kb,
        )
        return

    if data == "admin_products":
        cats = await db.get_categories()
        if not cats:
            await query.answer("No categories yet. Add a category first.", show_alert=True)
            return
        kb = await admin_products_pick_cat_keyboard()
        await query.message.edit_text(
            "📦 <b>Products</b>\n\nSelect a category to manage its products:",
            parse_mode="HTML",
            reply_markup=kb,
        )
        return

    if data.startswith("admin_prodcat_"):
        cat_id = int(data.split("_")[2])
        kb, cat_name = await admin_products_keyboard(cat_id)
        await query.message.edit_text(
            f"📦 <b>Products — {cat_name}</b>\n\nManage products below:",
            parse_mode="HTML",
            reply_markup=kb,
        )
        return

    if data.startswith("admin_delcat_"):
        cat_id = int(data.split("_")[2])
        cat = await db.get_category(cat_id)
        if cat:
            await db.delete_category(cat_id)
        kb = await admin_categories_keyboard()
        await query.message.edit_text(
            "✅ Category deleted.\n\n📂 <b>Categories</b>:",
            parse_mode="HTML",
            reply_markup=kb,
        )
        return

    if data.startswith("admin_delprod_"):
        prod_id = int(data.split("_")[2])
        prod = await db.get_product(prod_id)
        if prod:
            cat_id = prod["category_id"]
            await db.delete_product(prod_id)
            kb, cat_name = await admin_products_keyboard(cat_id)
            await query.message.edit_text(
                f"✅ Product deleted.\n\n📦 <b>Products — {cat_name}</b>:",
                parse_mode="HTML",
                reply_markup=kb,
            )
        return

    if data.startswith("admin_stock_"):
        prod_id = int(data.split("_")[2])
        prod = await db.get_product(prod_id)
        context.user_data["stock_prod_id"] = prod_id
        context.user_data["stock_cat_id"] = prod["category_id"]
        context.user_data["awaiting"] = "stock"
        await query.message.reply_text(
            f"✏️ Enter new stock quantity for <b>{prod['name']}</b>:",
            parse_mode="HTML",
        )
        return

    if data == "admin_addcat":
        context.user_data["awaiting"] = "cat_name"
        await query.message.reply_text("📂 Enter the <b>category name</b>:", parse_mode="HTML")
        return

    if data.startswith("admin_addprod_"):
        cat_id = int(data.split("_")[2])
        context.user_data["awaiting"] = "prod_name"
        context.user_data["new_prod_cat_id"] = cat_id
        await query.message.reply_text("📦 Enter the <b>product name</b>:", parse_mode="HTML")
        return


# ─── ERROR HANDLER ────────────────────────────────────────────────────────────

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    if isinstance(context.error, Conflict):
        logger.warning("Conflict error — another bot instance may still be shutting down. Will retry.")
    elif isinstance(context.error, NetworkError):
        logger.warning(f"Network error: {context.error}")
    else:
        logger.error(f"Unhandled error: {context.error}", exc_info=context.error)


# ─── STARTUP ─────────────────────────────────────────────────────────────────

async def post_init(application: Application) -> None:
    await application.bot.delete_webhook(drop_pending_updates=True)
    # Wait for any competing instance to fully release its polling hold.
    # Telegram gives a 409 Conflict until the old session times out (~30–60s).
    for attempt in range(20):
        try:
            await application.bot.get_updates(offset=-1, timeout=1)
            break  # Got a clean response — we own the session now
        except Conflict:
            wait = min(3 * (attempt + 1), 15)
            logger.warning(f"409 Conflict on startup — another instance is still running. Waiting {wait}s… (attempt {attempt + 1}/20)")
            await asyncio.sleep(wait)
        except Exception:
            break
    logger.info(f"Bot ready — admins: {ADMIN_IDS}")


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set.")

    app = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("language", language_command))
    app.add_handler(CommandHandler("contactadmin", contactadmin_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()