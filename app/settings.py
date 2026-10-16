"""Конфигурация из переменных окружения."""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Settings:
    data_dir: str
    bot_token: Optional[str]
    manager_chat_id: Optional[str]
    admin_token: str
    amo_subdomain: Optional[str]
    amo_token: Optional[str]

    @staticmethod
    def from_env() -> "Settings":
        return Settings(
            data_dir=os.getenv("DATA_DIR", "./data"),
            bot_token=os.getenv("BOT_TOKEN") or None,
            manager_chat_id=os.getenv("MANAGER_CHAT_ID") or None,
            admin_token=os.getenv("ADMIN_TOKEN", "change-me"),
            amo_subdomain=os.getenv("AMO_SUBDOMAIN") or None,
            amo_token=os.getenv("AMO_TOKEN") or None,
        )
