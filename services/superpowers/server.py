"""Superpowers adapter: packages the generated app into a container and runs it."""
import logging
import subprocess
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level="INFO")
app = FastAPI()


class DeployReq(BaseModel):
    project_dir: str
    target: str = "container"


DEFAULT_DOCKERFILE = """FROM node:20-slim
WORKDIR /app
COPY . .
RUN [ -f package.json ] && npm install --omit=dev || true
EXPOSE 3000
CMD ["sh", "-c", "npm start || node index.js || python3 -m http.server 3000"]
"""


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/api/deploy")
def deploy(req: DeployReq):
    project = Path(req.project_dir)
    if not project.is_dir():
        raise HTTPException(400, f"project_dir not found: {req.project_dir}")
    tag = f"devfoundry-app:{uuid.uuid4().hex[:8]}"
    dockerfile = project / "Dockerfile"
    if not dockerfile.exists():
        dockerfile.write_text(DEFAULT_DOCKERFILE)
    try:
        build = subprocess.run(["docker", "build", "-t", tag, str(project)],
                               capture_output=True, text=True, timeout=600)
        if build.returncode != 0:
            raise HTTPException(500, f"build failed:\n{build.stderr[-3000:]}")
        run = subprocess.run(["docker", "run", "-d", "-P", tag],
                             capture_output=True, text=True, timeout=60)
        if run.returncode != 0:
            raise HTTPException(500, f"run failed:\n{run.stderr[-2000:]}")
        container = run.stdout.strip()
        port = subprocess.run(["docker", "port", container], capture_output=True, text=True).stdout
        return {"image": tag, "container": container, "url": port.strip(),
                "logs": build.stdout[-3000:]}
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "deployment timed out")
