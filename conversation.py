import json
import logging

from config import settings
from llm_client import LLMClient
from memory_store import MemoryStore
from prompts import build_converser_prompt, build_reviewer_prompt, build_topic_prompt

logger = logging.getLogger(__name__)


class ConversationManager:
    def __init__(self, llm: LLMClient, memory: MemoryStore):
        self.llm = llm
        self.memory = memory
        self._histories: dict[int, list[dict]] = {}

    async def process_message(self, chat_id: int, user_message: str) -> str:
        if chat_id not in self._histories:
            self._histories[chat_id] = []

        similar = self.memory.search_similar(user_message)
        context_docs = [s["document"] for s in similar]

        reviewer_msgs = build_reviewer_prompt(
            user_message=user_message,
            conversation_history=self._histories[chat_id],
        )
        logger.info("Calling reviewer...")
        review_response = await self.llm.async_chat(
            reviewer_msgs,
            temperature=settings.reviewer_temperature,
            model=settings.reviewer_model or settings.llm_model,
        )
        review_result = review_response.content
        logger.info(f"Review result: {review_result[:300]}")

        topic = None
        has_errors = False
        try:
            review_json = json.loads(review_result)
            topic = review_json.get("topic")
            has_errors = review_json.get("has_errors", False)
        except (json.JSONDecodeError, KeyError):
            pass

        recent_from_store = []
        if not self._histories[chat_id]:
            recent_from_store = [
                r["document"]
                for r in self.memory.get_recent_exchanges(limit=3)
            ]

        all_context = context_docs + recent_from_store
        converser_msgs = build_converser_prompt(
            user_message=user_message,
            review_result=review_result if has_errors else None,
            conversation_history=self._histories[chat_id],
            retrieved_context=all_context,
        )

        logger.info("Calling converser...")
        converser_response = await self.llm.async_chat(
            converser_msgs,
            temperature=settings.converser_temperature,
        )
        bot_reply = converser_response.content
        logger.info(f"Bot reply: {bot_reply[:300]}")

        self.memory.add_exchange(user_message, bot_reply, topic=topic)

        self._histories[chat_id].append({"role": "user", "content": user_message})
        self._histories[chat_id].append({"role": "assistant", "content": bot_reply})
        self._histories[chat_id] = self._histories[chat_id][-20:]

        return bot_reply

    async def generate_topic(self) -> str:
        recent = self.memory.get_recent_exchanges(limit=10)
        recent_topics = [
            e["metadata"].get("topic", "")
            for e in recent
            if e.get("metadata")
        ]
        recent_topics = [t for t in recent_topics if t]

        topic_prompt = build_topic_prompt(recent_topics)
        response = await self.llm.async_chat(
            [{"role": "user", "content": topic_prompt}],
            temperature=0.8,
        )
        return response.content

    def clear_history(self, chat_id: int) -> None:
        self._histories.pop(chat_id, None)
