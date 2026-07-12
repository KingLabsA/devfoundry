import pytest

from app.events.bus import EventBus
from app.models.schemas import PipelineEvent, Stage
from app.orchestrator.pipeline import Orchestrator

pytestmark = pytest.mark.anyio


async def test_event_bus_replay_and_live():
    bus = EventBus()
    e1 = PipelineEvent(run_id="r1", stage=Stage.SPEC, kind="log", message="first")
    await bus.publish(e1)

    q, replay = await bus.subscribe("r1")
    assert [e.message for e in replay] == ["first"]

    e2 = PipelineEvent(run_id="r1", stage=Stage.SPEC, kind="log", message="second")
    await bus.publish(e2)
    assert (await q.get()).message == "second"
    await bus.unsubscribe("r1", q)


def test_materialize_blocks_path_traversal(tmp_path):
    Orchestrator._materialize(tmp_path, {
        "safe.txt": "ok",
        "../escape.txt": "evil",
        "nested/dir/file.py": "print('hi')",
    })
    assert (tmp_path / "safe.txt").read_text() == "ok"
    assert (tmp_path / "nested/dir/file.py").exists()
    assert not (tmp_path.parent / "escape.txt").exists()
