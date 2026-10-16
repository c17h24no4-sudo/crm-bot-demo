"""Админ-панель для заказчика: правка текстов бота и услуг, список последних заявок."""
import html
import secrets
from typing import Optional

from fastapi import Depends, FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from .content import ContentError, ContentStore
from .crm import read_leads
from .settings import Settings

LABELS = {
    "welcome": "Приветствие",
    "ask_name": "Вопрос про имя",
    "ask_phone": "Вопрос про телефон",
    "ask_comment": "Вопрос про задачу",
    "thanks": "Сообщение после заявки",
    "cancelled": "Сообщение при отмене",
}


def create_admin(settings: Optional[Settings] = None, content: Optional[ContentStore] = None) -> FastAPI:
    settings = settings or Settings.from_env()
    content = content or ContentStore(settings.data_dir)
    security = HTTPBasic()
    app = FastAPI(title="Админка бота", docs_url=None, redoc_url=None)

    def auth(creds: HTTPBasicCredentials = Depends(security)) -> None:
        ok = secrets.compare_digest(creds.password.encode(), settings.admin_token.encode())
        if not ok:
            raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Basic"})

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse, dependencies=[Depends(auth)])
    def index(saved: int = 0, error: str = ""):
        c = content.load()
        fields = "".join(
            f'<label>{LABELS[k]}<textarea name="{k}" rows="2" maxlength="500">{html.escape(c[k])}</textarea></label>'
            for k in LABELS
        )
        services = html.escape("\n".join(c["services"]))
        import os

        leads = read_leads(os.path.join(settings.data_dir, "leads.jsonl"))
        rows = "".join(
            f"<tr><td>{html.escape(str(l['id']))}</td><td>{html.escape(l['service'])}</td>"
            f"<td>{html.escape(l['name'])}</td><td>{html.escape(l['phone'])}</td><td>{html.escape(l['comment'] or '')}</td></tr>"
            for l in leads
        ) or '<tr><td colspan="5">Заявок пока нет</td></tr>'
        banner = ""
        if saved:
            banner = '<p class="ok">Сохранено. Бот уже отвечает по-новому.</p>'
        if error:
            banner = f'<p class="err">{html.escape(error)}</p>'
        return f"""<!doctype html><html lang="ru"><meta charset="utf-8"><title>Админка бота</title>
<style>body{{font-family:system-ui;max-width:760px;margin:2rem auto;padding:0 1rem}}label{{display:block;margin:.8rem 0;font-weight:600}}
textarea{{width:100%;font:inherit;margin-top:.3rem}}button{{padding:.6rem 1.2rem;font-size:1rem}}table{{border-collapse:collapse;width:100%}}
td,th{{border:1px solid #ccc;padding:.3rem .5rem;text-align:left}}.ok{{color:#0a7a2f}}.err{{color:#b00020}}</style>
<h1>Админка бота</h1>{banner}
<form method="post" action="/save"><h2>Тексты</h2>{fields}
<label>Услуги (по одной в строке, до 8)<textarea name="services" rows="6">{services}</textarea></label>
<button type="submit">Сохранить</button></form>
<h2>Последние заявки</h2><table><tr><th>№</th><th>Услуга</th><th>Имя</th><th>Телефон</th><th>Комментарий</th></tr>{rows}</table></html>"""

    @app.post("/save", dependencies=[Depends(auth)])
    def save(
        welcome: str = Form(...),
        ask_name: str = Form(...),
        ask_phone: str = Form(...),
        ask_comment: str = Form(...),
        thanks: str = Form(...),
        cancelled: str = Form(...),
        services: str = Form(...),
    ):
        try:
            content.save(
                {"welcome": welcome, "ask_name": ask_name, "ask_phone": ask_phone, "ask_comment": ask_comment,
                 "thanks": thanks, "cancelled": cancelled, "services": services}
            )
        except ContentError as exc:
            from urllib.parse import quote

            return RedirectResponse(f"/?error={quote(str(exc))}", status_code=303)
        return RedirectResponse("/?saved=1", status_code=303)

    return app


app = create_admin()
