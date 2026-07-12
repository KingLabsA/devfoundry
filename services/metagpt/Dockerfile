FROM python:3.11-slim
RUN pip install --no-cache-dir fastapi uvicorn httpx pydantic
# Optional heavyweight engine — uncomment to use the real MetaGPT simulation:
# RUN pip install --no-cache-dir metagpt
WORKDIR /srv
COPY llm.py server.py /srv/
EXPOSE 9101
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "9101"]
