import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from config import settings
from conversation import ConversationManager
from llm_client import get_llm_client
from memory_store import MemoryStore
from scheduler import save_chat_id, setup_scheduler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

conversation_manager: ConversationManager | None = None


async def start(update: Update, _context):
    chat_id = update.effective_chat.id
    save_chat_id(chat_id)
    if conversation_manager:
        conversation_manager.clear_history(chat_id)
    await update.message.reply_text(
        "Hallo! Ich bin dein Sprachbuddy. 👋\n"
        "Ich helfe dir, Deutsch zu üben. Schreib mir einfach "
        "eine Nachricht auf Deutsch!\n\n"
        "Ich werde dir auch ab und zu eine Nachricht schreiben, "
        "damit du üben kannst."
    )


async def bye(update: Update, _context):
    if conversation_manager:
        conversation_manager.clear_history(update.effective_chat.id)
    await update.message.reply_text(
        "Tschüss! Es hat Spaß gemacht, mit dir zu reden. 👋\n"
        "Schreib mir einfach, wenn du wieder üben willst!"
    )


async def handle_message(update: Update, _context):
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    user_message = update.message.text

    try:
        bot_reply = await conversation_manager.process_message(chat_id, user_message)
        await update.message.reply_text(bot_reply)
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        await update.message.reply_text(
            "Entschuldigung, ich habe einen Fehler gemacht. "
            "Kannst du das nochmal sagen?"
        )


def main():
    global conversation_manager

    logger.info("Initializing LLM client...")
    llm = get_llm_client()

    logger.info("Initializing memory store...")
    memory = MemoryStore()
    logger.info(f"Memory store ready. Existing entries: {memory.count()}")

    conversation_manager = ConversationManager(llm, memory)

    app = Application.builder().token(settings.telegram_token).build()
    app.bot_data["conversation_manager"] = conversation_manager

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bye", bye))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    setup_scheduler(app)
    logger.info(f"Starting bot in {settings.bot_mode} mode...")

    if settings.bot_mode == "webhook":
        app.run_webhook(
            listen="0.0.0.0",
            port=settings.webhook_port,
            url_path=settings.telegram_token,
            webhook_url=f"{settings.webhook_url}/{settings.telegram_token}",
        )
    else:
        app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
