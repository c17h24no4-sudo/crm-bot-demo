FROM python:3.12-slim
WORKDIR /srv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
RUN useradd --create-home appuser && mkdir /data && chown appuser /data
USER appuser
ENV DATA_DIR=/data
EXPOSE 8001
CMD ["uvicorn", "app.admin:app", "--host", "0.0.0.0", "--port", "8001"]
