"""Запуск бота: python -m app.run_bot (нужен BOT_TOKEN). Без токена печатает подсказку и завершается."""
import logging
import os
import sys

from .content import ContentStore
from .crm import LoggingCRM, make_crm
from .dialog import Dialog
from .settings import Settings
from .telegram import TelegramBot


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    s = Settings.from_env()
    if not s.bot_token:
        print("Не задан BOT_TOKEN. Создайте бота у @BotFather и укажите токен в .env")
        return 1
    os.makedirs(s.data_dir, exist_ok=True)
    crm = LoggingCRM(make_crm(s.amo_subdomain, s.amo_token), os.path.join(s.data_dir, "leads.jsonl"))
    TelegramBot(s.bot_token, Dialog(ContentStore(s.data_dir), crm), s.manager_chat_id).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
