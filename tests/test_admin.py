import base64

import pytest
from fastapi.testclient import TestClient

from app.admin import create_admin
from app.content import ContentStore
from app.settings import Settings


def settings(tmp_path):
    return Settings(str(tmp_path), None, None, "secret", None, None)


@pytest.fixture()
def env(tmp_path):
    s = settings(tmp_path)
    store = ContentStore(s.data_dir)
    return TestClient(create_admin(s, store), follow_redirects=False), store


def auth(password="secret"):
    return {"Authorization": "Basic " + base64.b64encode(f"admin:{password}".encode()).decode()}


FORM = {"welcome": "Привет!", "ask_name": "Имя?", "ask_phone": "Телефон?", "ask_comment": "Что нужно?",
        "thanks": "Спасибо!", "cancelled": "Отмена", "services": "Сайт\nБот"}


def test_requires_password(env):
    client, _ = env
    assert client.get("/").status_code == 401
    assert client.get("/", headers=auth("wrong")).status_code == 401
    assert client.get("/", headers=auth()).status_code == 200


def test_save_changes_content(env):
    client, store = env
    r = client.post("/save", data=FORM, headers=auth())
    assert r.status_code == 303 and "saved=1" in r.headers["location"]
    assert store.load()["welcome"] == "Привет!"
    assert store.load()["services"] == ["Сайт", "Бот"]


def test_invalid_form_is_rejected_and_old_content_stays(env):
    client, store = env
    before = store.load()
    bad = dict(FORM, services="   ")
    r = client.post("/save", data=bad, headers=auth())
    assert r.status_code == 303 and "error=" in r.headers["location"]
    assert store.load() == before


def test_html_is_escaped(env):
    client, store = env
    client.post("/save", data=dict(FORM, welcome="<script>alert(1)</script>"), headers=auth())
    page = client.get("/", headers=auth()).text
    assert "<script>alert(1)</script>" not in page and "&lt;script&gt;" in page


def test_corrupted_content_file_falls_back_to_defaults(tmp_path):
    store = ContentStore(str(tmp_path))
    (tmp_path / "content.json").write_text("{не json", encoding="utf-8")
    assert store.load()["services"]
