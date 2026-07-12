FROM node:20-slim
RUN apt-get update && apt-get install -y git python3 && rm -rf /var/lib/apt/lists/*
# opencode CLI is optional — the adapter falls back to direct LLM edits if absent
RUN npm install -g opencode-ai || echo "opencode CLI unavailable; adapter will use LLM fallback"
WORKDIR /srv
RUN npm init -y >/dev/null && npm install express
COPY adapter.mjs /srv/adapter.mjs
EXPOSE 9103
CMD ["node", "adapter.mjs"]
