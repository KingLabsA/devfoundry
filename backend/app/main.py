from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.extra_routes import router as extra_router
from app.api.hardware_routes import router as hardware_router
from app.api.llm_routes import router as llm_router
from app.api.mcp_routes import router as mcp_router
from app.api.project_routes import router as project_router
from app.api.routes import router as api_router
from app.api.ws import router as ws_router
from app.logging_conf import configure_logging

configure_logging()

app = FastAPI(
    title="DevFoundry",
    version="0.2.4",
    description="The local-first AI software factory — created by King3Djbl of KingLabs.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1430", "tauri://localhost", "http://localhost:9100"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)
app.include_router(project_router)
app.include_router(llm_router)
app.include_router(mcp_router)
app.include_router(extra_router)
app.include_router(hardware_router)
app.include_router(ws_router)

# Web-app surface: serve the built frontend at /app (same UI as the desktop app,
# minus Tauri-only features). Build it with: cd frontend && npm run build
_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _dist.is_dir():
    app.mount("/app", StaticFiles(directory=str(_dist), html=True), name="webapp")

    @app.get("/", include_in_schema=False)
    async def _root() -> RedirectResponse:
        return RedirectResponse("/app/")


@app.on_event("startup")
async def _load_history() -> None:
    from app.orchestrator.pipeline import orchestrator
    orchestrator.load_history()
    # Native embedded services (no Docker): start Qdrant if installed.
    import asyncio

    from app import embedded_services
    asyncio.get_event_loop().create_task(embedded_services.autostart())
