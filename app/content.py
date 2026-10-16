"""Тексты, кнопки и услуги бота. Хранятся в JSON-файле, который правит заказчик в админке.

Бот читает файл при каждом сообщении, поэтому изменения применяются сразу, без перезапуска.
"""
import json
import os
import threading
from typing import Any, Dict, List

DEFAULT_CONTENT: Dict[str, Any] = {
    "welcome": "Здравствуйте! Выберите услугу, и мы оформим заявку.",
    "ask_name": "Как к вам обращаться?",
    "ask_phone": "Оставьте номер телефона для связи.",
    "ask_comment": "Коротко опишите задачу (или напишите «-», если нечего добавить).",
    "thanks": "Спасибо! Заявка принята, менеджер свяжется с вами.",
    "cancelled": "Хорошо, заявку отменили. Напишите /start, чтобы начать заново.",
    "services": ["Сайт", "Telegram-бот", "Интеграция с CRM"],
}

_lock = threading.Lock()


class ContentError(ValueError):
    pass


def validate(data: Dict[str, Any]) -> Dict[str, Any]:
    """Проверка того, что приходит из админки: нужные ключи, строки, 1–8 услуг."""
    out: Dict[str, Any] = {}
    for key, default in DEFAULT_CONTENT.items():
        value = data.get(key, default)
        if key == "services":
            if isinstance(value, str):
                value = [line.strip() for line in value.splitlines() if line.strip()]
            if not isinstance(value, list) or not (1 <= len(value) <= 8):
                raise ContentError("Услуг должно быть от 1 до 8")
            if any((not isinstance(s, str)) or not s.strip() or len(s) > 40 for s in value):
                raise ContentError("Название услуги: от 1 до 40 символов")
            out[key] = [s.strip() for s in value]
        else:
            if not isinstance(value, str) or not value.strip():
                raise ContentError(f"Поле «{key}» не может быть пустым")
            if len(value) > 500:
                raise ContentError(f"Поле «{key}» слишком длинное (до 500 символов)")
            out[key] = value.strip()
    return out


class ContentStore:
    def __init__(self, data_dir: str) -> None:
        self._path = os.path.join(data_dir, "content.json")
        os.makedirs(data_dir, exist_ok=True)

    def load(self) -> Dict[str, Any]:
        with _lock:
            if not os.path.exists(self._path):
                return dict(DEFAULT_CONTENT)
            try:
                with open(self._path, encoding="utf-8") as f:
                    return validate(json.load(f))
            except (ValueError, OSError):
                return dict(DEFAULT_CONTENT)  # битый файл не должен ронять бота

    def save(self, data: Dict[str, Any]) -> Dict[str, Any]:
        clean = validate(data)
        with _lock:
            tmp = self._path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(clean, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self._path)  # запись целиком или никак
        return clean
