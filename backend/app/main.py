from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.llm_routes import router as llm_router
from app.api.mcp_routes import router as mcp_router
from app.api.project_routes import router as project_router
from app.api.routes import router as api_router
from app.api.ws import router as ws_router
from app.logging_conf import configure_logging

configure_logging()

app = FastAPI(title="DevFoundry Backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1430", "tauri://localhost"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)
app.include_router(project_router)
app.include_router(llm_router)
app.include_router(mcp_router)
app.include_router(ws_router)


@app.on_event("startup")
async def _load_history() -> None:
    from app.orchestrator.pipeline import orchestrator
    orchestrator.load_history()
