FROM python:3.13-slim

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && useradd --uid 1000 --no-create-home app
COPY app ./app
# Readable by the unprivileged user whatever umask the host checkout used
RUN chmod -R a+rX /srv/app

ENV DB_PATH=/data/jobs.db PYTHONUNBUFFERED=1
USER app
EXPOSE 8080

# checked every 3 s while starting (so an upgrade doesn't wait a minute per workspace), then every minute
HEALTHCHECK --interval=60s --timeout=5s --start-period=40s --start-interval=3s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=4)"

CMD ["uvicorn", "app.web:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]
