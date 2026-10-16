import httpx

from app.crm import AmoCRM, FakeCRM, Lead, LoggingCRM, read_leads
from app.content import ContentStore
from app.dialog import Dialog
from app.telegram import TelegramBot


def test_amocrm_requests_are_built_correctly():
    seen = []

    def handler(request: httpx.Request):
        seen.append((request.method, request.url.path, request.headers["authorization"], request.content.decode()))
        if request.url.path.endswith("/leads/complex"):
            return httpx.Response(200, json=[{"id": 777}])
        return httpx.Response(200, json={})

    crm = AmoCRM("demo", "tok", httpx.Client(transport=httpx.MockTransport(handler)))
    lead_id = crm.create_lead(Lead("Иван", "+79991234567", "Сайт", "лендинг", "@ivan"))
    assert lead_id == "777"
    assert seen[0][1] == "/api/v4/leads/complex" and seen[0][2] == "Bearer tok"
    assert "Иван" in seen[0][3] and "+79991234567" in seen[0][3]
    assert seen[1][1] == "/api/v4/leads/777/notes" and "лендинг" in seen[1][3]


def test_amocrm_error_is_raised_not_swallowed():
    import pytest

    crm = AmoCRM("demo", "bad", httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(401))))
    with pytest.raises(httpx.HTTPStatusError):
        crm.create_lead(Lead("A", "1", "S", ""))


def test_logging_crm_writes_leads(tmp_path):
    path = str(tmp_path / "leads.jsonl")
    crm = LoggingCRM(FakeCRM(), path)
    crm.create_lead(Lead("Анна", "+79000000000", "Бот", "тест"))
    rows = read_leads(path)
    assert rows[0]["name"] == "Анна" and rows[0]["id"] == "demo-1"


def test_telegram_bot_sends_reply_and_manager_notification(tmp_path):
    sent = []

    def handler(request: httpx.Request):
        import json

        sent.append((request.url.path.split("/")[-1], json.loads(request.content)))
        return httpx.Response(200, json={"ok": True, "result": []})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    dialog = Dialog(ContentStore(str(tmp_path)), FakeCRM())
    bot = TelegramBot("TOKEN", dialog, "999", client)

    def msg(text):
        return {"update_id": 1, "message": {"chat": {"id": 5}, "from": {"username": "u"}, "text": text}}

    for t in ["/start", "Сайт", "Иван", "+7 999 123-45-67", "-"]:
        bot.process_update(msg(t))
    methods = [m for m, _ in sent]
    assert methods.count("sendMessage") == 6  # пять ответов клиенту + уведомление менеджеру
    assert sent[0][1]["reply_markup"]["keyboard"][0][0]["text"] == "Сайт"  # меню услуг
    assert sent[-1][1]["chat_id"] == "999" and "Новая заявка" in sent[-1][1]["text"]


def test_telegram_ignores_non_text_updates(tmp_path):
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"ok": True})))
    bot = TelegramBot("T", Dialog(ContentStore(str(tmp_path)), FakeCRM()), None, client)
    bot.process_update({"update_id": 2, "message": {"chat": {"id": 1}, "photo": []}})  # не падает
