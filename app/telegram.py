"""Тонкий слой Telegram Bot API (long polling). Без внешних библиотек, только httpx."""
import logging
import time
from typing import Callable, Optional

import httpx

from .dialog import Dialog


class TelegramBot:
    def __init__(self, token: str, dialog: Dialog, manager_chat_id: Optional[str], client: Optional[httpx.Client] = None):
        self._base = f"https://api.telegram.org/bot{token}"
        self._dialog = dialog
        self._manager = manager_chat_id
        self._client = client or httpx.Client(timeout=40)

    def _call(self, method: str, **params):
        r = self._client.post(f"{self._base}/{method}", json=params)
        r.raise_for_status()
        return r.json()

    def send(self, chat_id, text: str, buttons=None) -> None:
        params = {"chat_id": chat_id, "text": text}
        if buttons:
            params["reply_markup"] = {"keyboard": [[{"text": b}] for b in buttons], "resize_keyboard": True, "one_time_keyboard": True}
        else:
            params["reply_markup"] = {"remove_keyboard": True}
        self._call("sendMessage", **params)

    def process_update(self, update: dict) -> None:
        msg = update.get("message") or {}
        text = msg.get("text")
        if not text:
            return
        chat_id = str(msg["chat"]["id"])
        user = (msg.get("from") or {}).get("username")
        reply = self._dialog.handle(chat_id, text, user)
        self.send(chat_id, reply.text, reply.buttons)
        if reply.notify_manager and self._manager:
            self.send(self._manager, reply.notify_manager)

    def run(self, stop: Callable[[], bool] = lambda: False) -> None:
        offset = 0
        while not stop():
            try:
                data = self._call("getUpdates", offset=offset, timeout=30)
                for upd in data.get("result", []):
                    offset = upd["update_id"] + 1
                    self.process_update(upd)
            except httpx.HTTPError as exc:
                logging.warning("Telegram API: %s; повтор через 3 с", exc)
                time.sleep(3)  # сеть или Telegram недоступны: повторяем, не падаем
