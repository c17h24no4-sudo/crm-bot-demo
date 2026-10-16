"""Логика диалога сбора заявки. Не зависит от Telegram: на вход событие, на выход ответ.

Шаги: услуга → имя → телефон → комментарий → заявка в CRM.
Состояние диалога хранится по chat_id в памяти процесса.
"""
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .crm import CRM, Lead
from .content import ContentStore

PHONE_RE = re.compile(r"^\+?\d[\d\s\-()]{8,17}$")


@dataclass
class Reply:
    text: str
    buttons: List[str] = field(default_factory=list)  # подписи кнопок (по одной в ряд)
    notify_manager: Optional[str] = None  # текст уведомления менеджеру


@dataclass
class Session:
    step: str = "service"
    service: str = ""
    name: str = ""
    phone: str = ""


class Dialog:
    def __init__(self, content: ContentStore, crm: CRM) -> None:
        self._content = content
        self._crm = crm
        self._sessions: Dict[str, Session] = {}

    def handle(self, chat_id: str, text: str, username: Optional[str] = None) -> Reply:
        c = self._content.load()
        text = (text or "").strip()
        if text in ("/start", "/cancel"):
            self._sessions[chat_id] = Session()
            if text == "/cancel":
                return Reply(c["cancelled"])
            return Reply(c["welcome"], c["services"])
        s = self._sessions.get(chat_id)
        if s is None:
            self._sessions[chat_id] = Session()
            return Reply(c["welcome"], c["services"])
        if s.step == "service":
            if text not in c["services"]:
                return Reply(c["welcome"], c["services"])
            s.service, s.step = text, "name"
            return Reply(c["ask_name"])
        if s.step == "name":
            if len(text) < 2:
                return Reply(c["ask_name"])
            s.name, s.step = text[:60], "phone"
            return Reply(c["ask_phone"])
        if s.step == "phone":
            if not PHONE_RE.match(text):
                return Reply("Не похоже на номер. Пример: +7 999 123-45-67")
            s.phone, s.step = text, "comment"
            return Reply(c["ask_comment"])
        # step == "comment": заявка готова
        comment = "" if text == "-" else text[:500]
        lead = Lead(s.name, s.phone, s.service, comment, f"@{username}" if username else None)
        lead_id = self._crm.create_lead(lead)
        self._sessions[chat_id] = Session()
        note = f"Новая заявка №{lead_id}\n{lead.service}\n{lead.name}, {lead.phone}\n{lead.comment or '—'}"
        return Reply(c["thanks"], notify_manager=note)
