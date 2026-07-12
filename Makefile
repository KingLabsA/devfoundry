.PHONY: dev backend frontend services test

dev: services backend

backend:
	cd backend && uvicorn app.main:app --host 0.0.0.0 --port 9100 --reload

frontend:
	cd frontend && npm run tauri dev

services:
	docker compose up -d metagpt boltdiy opencode orc superpowers

test:
	cd backend && python -m pytest -q
