FROM python:3.11-slim
RUN apt-get update && apt-get install -y docker.io && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir fastapi uvicorn
WORKDIR /srv
COPY server.py /srv/server.py
EXPOSE 9105
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "9105"]
