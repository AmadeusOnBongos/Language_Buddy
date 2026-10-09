import logging
import random
from datetime import datetime

from telegram.ext import ContextTypes

from config import settings
from conversation import ConversationManager

logger = logging.getLogger(__name__)


def load_chat_id() -> int | None:
    try:
        with open("chat_id.txt") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return None


def save_chat_id(chat_id: int):
    with open("chat_id.txt", "w") as f:
        f.write(str(chat_id))


async def send_proactive_message(context: ContextTypes.DEFAULT_TYPE):
    chat_id = load_chat_id()
    if not chat_id:
        logger.info("No chat_id saved — skipping proactive message")
        schedule_next(context.application)
        return

    conversation_manager: ConversationManager | None = context.bot_data.get(
        "conversation_manager"
    )
    if not conversation_manager:
        logger.warning("No conversation_manager in bot_data")
        return

    now = datetime.now()
    if not (settings.schedule_start_hour <= now.hour < settings.schedule_end_hour):
        logger.info(f"Outside waking hours ({now.hour}), rescheduling in 30min")
        schedule_next(context.application, delay_minutes=30)
        return

    try:
        topic = await conversation_manager.generate_topic()
        await context.bot.send_message(chat_id=chat_id, text=topic)
        logger.info(f"Proactive message sent: {topic[:100]}")
    except Exception as e:
        logger.error(f"Failed to send proactive message: {e}", exc_info=True)

    schedule_next(context.application)


def schedule_next(
    app, delay_minutes: int | None = None, start_immediate: bool = False
):
    if start_immediate:
        delay_seconds = 5
    elif delay_minutes is not None:
        delay_seconds = delay_minutes * 60
    else:
        delay_seconds = random.randint(
            settings.schedule_min_interval_minutes,
            settings.schedule_max_interval_minutes,
        ) * 60

    app.job_queue.run_once(
        send_proactive_message,
        delay_seconds,
        name="proactive_message",
    )


def setup_scheduler(app):
    schedule_next(app, start_immediate=True)
    logger.info("Scheduler setup complete — first message in 5 seconds")
