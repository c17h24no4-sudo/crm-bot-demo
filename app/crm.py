"""CRM: amoCRM (REST API v4) и «заглушка» для демо и тестов."""
from dataclasses import dataclass
from typing import List, Optional, Protocol

import httpx


@dataclass
class Lead:
    name: str
    phone: str
    service: str
    comment: str
    telegram_user: Optional[str] = None


class CRM(Protocol):
    def create_lead(self, lead: Lead) -> str: ...


class FakeCRM:
    """Хранит заявки в памяти: позволяет показать демо без реальной CRM."""

    def __init__(self) -> None:
        self.leads: List[Lead] = []

    def create_lead(self, lead: Lead) -> str:
        self.leads.append(lead)
        return f"demo-{len(self.leads)}"


class AmoCRM:
    """Создаёт сделку и контакт одним запросом: POST /api/v4/leads/complex.

    Нужны поддомен аккаунта и долгосрочный токен (раздел «Интеграции» в amoCRM).
    """

    def __init__(self, subdomain: str, token: str, client: Optional[httpx.Client] = None) -> None:
        self._base = f"https://{subdomain}.amocrm.ru"
        self._token = token
        self._client = client or httpx.Client(timeout=30)

    def create_lead(self, lead: Lead) -> str:
        payload = [
            {
                "name": f"Заявка из Telegram: {lead.service}",
                "_embedded": {
                    "contacts": [
                        {
                            "first_name": lead.name,
                            "custom_fields_values": [
                                {"field_code": "PHONE", "values": [{"value": lead.phone, "enum_code": "WORK"}]}
                            ],
                        }
                    ]
                },
            }
        ]
        resp = self._client.post(
            f"{self._base}/api/v4/leads/complex",
            headers={"Authorization": f"Bearer {self._token}"},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        lead_id = str(data[0]["id"])
        # комментарий (примечание) к сделке
        note = f"Услуга: {lead.service}\nКомментарий: {lead.comment}\nTelegram: {lead.telegram_user or '-'}"
        self._client.post(
            f"{self._base}/api/v4/leads/{lead_id}/notes",
            headers={"Authorization": f"Bearer {self._token}"},
            json=[{"note_type": "common", "params": {"text": note}}],
        ).raise_for_status()
        return lead_id


def make_crm(subdomain: Optional[str], token: Optional[str]):
    return AmoCRM(subdomain, token) if subdomain and token else FakeCRM()


class LoggingCRM:
    """Оборачивает любую CRM и пишет заявки в leads.jsonl (их показывает админка)."""

    def __init__(self, inner, path: str) -> None:
        self._inner = inner
        self._path = path

    def create_lead(self, lead: Lead) -> str:
        import json
        import time

        lead_id = self._inner.create_lead(lead)
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"id": lead_id, "time": int(time.time()), **lead.__dict__}, ensure_ascii=False) + "\n")
        return lead_id


def read_leads(path: str, limit: int = 20):
    import json
    import os

    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    return rows[-limit:][::-1]
