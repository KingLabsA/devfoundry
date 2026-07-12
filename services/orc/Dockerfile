FROM python:3.11-slim
RUN pip install --no-cache-dir fastapi uvicorn httpx
WORKDIR /srv
COPY server.py /srv/server.py
ENV ANTHROPIC_API_KEY=""
EXPOSE 9104
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "9104"]
