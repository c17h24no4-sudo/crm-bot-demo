from app.content import ContentStore
from app.crm import FakeCRM
from app.dialog import Dialog


def make(tmp_path):
    crm = FakeCRM()
    return Dialog(ContentStore(str(tmp_path)), crm), crm


def test_full_flow_creates_lead_and_notifies_manager(tmp_path):
    d, crm = make(tmp_path)
    r = d.handle("1", "/start")
    assert "Сайт" in r.buttons
    assert d.handle("1", "Сайт").text.startswith("Как к вам")
    d.handle("1", "Иван")
    d.handle("1", "+7 999 123-45-67")
    r = d.handle("1", "Нужен лендинг", username="ivan")
    assert len(crm.leads) == 1
    lead = crm.leads[0]
    assert (lead.name, lead.service, lead.telegram_user) == ("Иван", "Сайт", "@ivan")
    assert r.notify_manager and "Иван" in r.notify_manager


def test_bad_phone_is_rejected_and_step_repeats(tmp_path):
    d, crm = make(tmp_path)
    d.handle("1", "/start"); d.handle("1", "Сайт"); d.handle("1", "Иван")
    assert "Не похоже на номер" in d.handle("1", "abc").text
    assert crm.leads == []


def test_unknown_service_shows_menu_again(tmp_path):
    d, _ = make(tmp_path)
    d.handle("1", "/start")
    assert d.handle("1", "что-то другое").buttons


def test_cancel_resets_dialog_to_beginning(tmp_path):
    d, crm = make(tmp_path)
    d.handle("1", "/start"); d.handle("1", "Сайт"); d.handle("1", "Иван")  # дошли до телефона
    r = d.handle("1", "/cancel")
    assert "заново" in r.text
    # после отмены диалог начинается с выбора услуги, а не с телефона
    assert "Как к вам обращаться" in d.handle("1", "Сайт").text
    assert crm.leads == []


def test_users_do_not_mix(tmp_path):
    d, crm = make(tmp_path)
    d.handle("a", "/start"); d.handle("a", "Сайт"); d.handle("a", "Анна")
    d.handle("b", "/start"); d.handle("b", "Telegram-бот"); d.handle("b", "Борис")
    d.handle("a", "+7 900 000-00-01"); d.handle("a", "-")
    assert len(crm.leads) == 1 and crm.leads[0].name == "Анна"


def test_changed_texts_apply_without_restart(tmp_path):
    store = ContentStore(str(tmp_path))
    d = Dialog(store, FakeCRM())
    assert "Выберите услугу" in d.handle("1", "/start").text
    c = store.load(); c["welcome"] = "Добро пожаловать в студию!"; c["services"] = ["Логотип"]
    store.save(c)
    r = d.handle("1", "/start")
    assert r.text == "Добро пожаловать в студию!" and r.buttons == ["Логотип"]
