from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    url: str = Field(default="postgresql+asyncpg://skynet:skynet@localhost:5432/skynet")


class RedisSettings(BaseSettings):
    url: str = Field(default="redis://localhost:6379/0")


class CelerySettings(BaseSettings):
    broker_url: str = Field(default="redis://localhost:6379/0")
    result_backend: str = Field(default="redis://localhost:6379/0")


class LLMSettings(BaseSettings):
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    ollama_base_url: str = Field(default="http://localhost:11434")


class NotificationSettings(BaseSettings):
    feishu_webhook_url: Optional[str] = None
    dingtalk_webhook_url: Optional[str] = None
    wechat_work_webhook_url: Optional[str] = None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__")

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    celery: CelerySettings = Field(default_factory=CelerySettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    notification: NotificationSettings = Field(default_factory=NotificationSettings)


@lru_cache
def get_settings() -> Settings:
    return Settings()
