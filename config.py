from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    telegram_token: str
    llm_provider: str = "groq"
    llm_model: str = "gemma2-9b-it"
    llm_api_key: str
    llm_base_url: Optional[str] = "https://api.groq.com/openai/v1"
    german_level: str = "A1-A2"
    rag_top_k: int = 5
    rag_collection_name: str = "conversations"
    embedding_model: str = "all-MiniLM-L6-v2"
    schedule_start_hour: int = 9
    schedule_end_hour: int = 22
    schedule_min_interval_minutes: int = 60
    schedule_max_interval_minutes: int = 240
    bot_mode: str = "polling"
    webhook_url: Optional[str] = None
    webhook_port: int = 8443
    reviewer_model: Optional[str] = None
    reviewer_temperature: float = 0.3
    converser_temperature: float = 0.7


settings = Settings()
