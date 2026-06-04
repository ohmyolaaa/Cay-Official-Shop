import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    first_name = update.effective_user.first_name if update.effective_user else "there"
    await update.message.reply_text(
        f"👋 Hello, {first_name}! Welcome!\n\nChoose an option from the menu below:",
        reply_markup=MAIN_MENU,
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text

    responses = {
        "🛒 Products": (
            "🛒 *Products*\n\nHere you can browse and purchase our products."
        ),
        "👤 Profile": (
            "👤 *Your Profile*\n\nView and manage your account details here."
        ),
        "🎁 Invite Center": (
            "🎁 *Invite Center*\n\nShare your referral link and earn rewards!"
        ),
        "💰 Top up balance": (
            "💰 *Top Up Balance*\n\nChoose a payment method to add funds to your account."
        ),
        "🎫 Redeem Code": (
            "🎫 *Redeem Code*\n\nEnter your promo or gift code below to redeem it."
        ),
        "📋 Bot Policy": (
            "📋 *Bot Policy*\n\nPlease read our terms and policies before using the bot."
        ),
        "❓ Help": (
            "❓ *Help*\n\nNeed assistance? Contact our support team or browse the FAQ."
        ),
    }

    reply = responses.get(text, "Please choose an option from the menu below:")

    await update.message.reply_text(
        reply,
        parse_mode="Markdown",
        reply_markup=MAIN_MENU,
    )


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set.")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot started — polling for updates...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
