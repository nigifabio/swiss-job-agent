# One image for the two platform services (gateway, provisioner); see docker-compose.yml.
FROM python:3.13-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 1000 --no-create-home app
COPY jobplatform ./jobplatform
RUN chmod -R a+rX /srv/jobplatform && mkdir -p /state /archives && chown 1000:1000 /state && chmod 700 /archives
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
EXPOSE 8090
