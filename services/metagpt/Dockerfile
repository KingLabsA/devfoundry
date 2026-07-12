FROM python:3.11-slim
RUN pip install --no-cache-dir metagpt fastapi uvicorn
WORKDIR /srv
COPY server.py /srv/server.py
ENV OPENAI_API_KEY=""
EXPOSE 9101
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "9101"]
