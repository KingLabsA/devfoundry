FROM python:3.11-slim
RUN pip install --no-cache-dir fastapi uvicorn httpx pydantic
WORKDIR /srv
COPY llm.py server.py /srv/
EXPOSE 9102
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "9102"]
