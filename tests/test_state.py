import json
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_lab.state import RunState


class TestRunState:
    def test_defaults(self) -> None:
        state = RunState(brief="Build a CLI tool")
        assert state.brief == "Build a CLI tool"
        assert state.artifacts == []
        assert state.transcript == []
        assert state.status == "running"

    def test_append_artifact(self) -> None:
        state = RunState(brief="test")
        state.artifacts.append({"stage": "orchestrator", "result": "ok"})
        assert len(state.artifacts) == 1

    def test_save_and_load_roundtrip(self) -> None:
        state = RunState(brief="Build a web app")
        state.artifacts.append({"stage": "test", "value": 42})
        state.transcript.append("[test] done")
        state.status = "complete"

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "runs" / "test_run.json"
            state.save(path)

            loaded = RunState.load(path)
            assert loaded.brief == state.brief
            assert loaded.artifacts == state.artifacts
            assert loaded.transcript == state.transcript
            assert loaded.status == state.status

    def test_load_missing_optional_fields(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "minimal.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"brief": "minimal"}), encoding="utf-8")

            loaded = RunState.load(path)
            assert loaded.brief == "minimal"
            assert loaded.artifacts == []
            assert loaded.transcript == []
            assert loaded.status == "running"

    def test_save_creates_parent_directories(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "deep" / "nested" / "run.json"
            state = RunState(brief="x")
            state.save(path)
            assert path.exists()
            data = json.loads(path.read_text(encoding="utf-8"))
            assert data["brief"] == "x"
