import pytest

pytestmark = pytest.mark.anyio


async def test_create_run_rejects_short_idea(client):
    resp = await client.post("/api/runs", json={"idea": "too short"})
    assert resp.status_code == 422


async def test_create_run_returns_run_id(client, monkeypatch):
    from app.orchestrator import pipeline

    async def noop(self, state):
        state.stage = "done"

    monkeypatch.setattr(pipeline.Orchestrator, "_execute", noop)
    resp = await client.post("/api/runs", json={"idea": "Build a Slack bot for OKR tracking"})
    assert resp.status_code == 202
    run_id = resp.json()["run_id"]

    resp = await client.get(f"/api/runs/{run_id}")
    assert resp.status_code == 200
    assert resp.json()["idea"].startswith("Build a Slack bot")


async def test_get_unknown_run_404(client):
    resp = await client.get("/api/runs/deadbeef")
    assert resp.status_code == 404
