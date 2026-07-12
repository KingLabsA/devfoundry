FROM node:20-slim
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
WORKDIR /srv
RUN git clone --depth 1 https://github.com/stackblitz-labs/bolt.diy . && npm ci && npm install express
COPY adapter.mjs /srv/adapter.mjs
ENV OPENAI_API_KEY="" ANTHROPIC_API_KEY=""
EXPOSE 9102
CMD ["node", "adapter.mjs"]
