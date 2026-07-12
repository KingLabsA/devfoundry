FROM node:20-slim
RUN apt-get update && apt-get install -y git python3 && rm -rf /var/lib/apt/lists/* \
    && npm install -g opencode-ai
WORKDIR /srv
RUN npm init -y && npm install express
COPY adapter.mjs /srv/adapter.mjs
ENV ANTHROPIC_API_KEY="" OPENAI_API_KEY=""
EXPOSE 9103
CMD ["node", "adapter.mjs"]
