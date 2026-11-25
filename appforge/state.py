"""Atomic, journaled configuration and wizard checkpoints with writer exclusion."""
import copy
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from .config import check
from .schema import Invalid, validate_file


def now():
    return datetime.now(timezone.utc).isoformat()


def atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    try:
        with temp.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


class Workspace:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.config_path = self.path / "project.config.json"
        self.state_path = self.path / "wizard-state.json"

    @contextmanager
    def lock(self):
        self.path.mkdir(parents=True, exist_ok=True)
        marker = self.path / ".appforge.lock"
        try:
            fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as error:
            raise Invalid(f"Workspace locked: {marker}. See docs/recovery.md for stale-lock recovery.") from error
        try:
            os.write(fd, f"pid={os.getpid()}\n".encode())
            os.close(fd)
            yield
        finally:
            marker.unlink(missing_ok=True)

    def _recover(self):
        journal = self.path / ".transaction.json"
        if journal.exists():
            payload = json.loads(journal.read_text(encoding="utf-8"))
            check(payload["config"])
            validate_file(payload["state"], "wizard-state.schema.json")
            atomic(self.config_path, payload["config"])
            atomic(self.state_path, payload["state"])
            journal.unlink()

    def _load(self):
        self._recover()
        if not self.config_path.exists():
            raise Invalid("No saved project. Run: python -m appforge init")
        config = json.loads(self.config_path.read_text(encoding="utf-8"))
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        check(config)
        validate_file(state, "wizard-state.schema.json")
        return config, state

    def load(self):
        with self.lock():
            return self._load()

    def _commit(self, config, state, reason, snapshot=True):
        check(config)
        state = copy.deepcopy(state)
        state["updatedAt"] = now()
        state["events"].append({"at": now(), "action": reason})
        if snapshot and self.config_path.exists():
            previous_config, previous_state = self._load()
            checkpoint = uuid4().hex + ".json"
            atomic(self.path / ".history" / checkpoint, {"config": previous_config, "state": previous_state})
            state["checkpoints"].append(checkpoint)
        validate_file(state, "wizard-state.schema.json")
        atomic(self.path / ".transaction.json", {"config": config, "state": state})
        self._recover()

    def initialize(self, config):
        with self.lock():
            if self.config_path.exists():
                raise Invalid("A project already exists; use wizard, set, or a different --workspace")
            state = {"schemaVersion": 1, "stage": "discovery", "answers": {}, "approval": None,
                     "planHash": None, "updatedAt": now(), "events": [], "checkpoints": [], "validations": []}
            self._commit(config, state, "Initialized project", snapshot=False)

    def update(self, transform, reason):
        with self.lock():
            config, state = self._load()
            next_config, next_state = transform(copy.deepcopy(config), copy.deepcopy(state))
            self._commit(next_config, next_state, reason)
            return next_config, next_state

    def undo(self):
        def restore(config, state):
            if not state["checkpoints"]:
                raise Invalid("No checkpoint to restore")
            name = state["checkpoints"][-1]
            if Path(name).name != name or not name.endswith(".json"):
                raise Invalid("Invalid checkpoint path")
            previous = json.loads((self.path / ".history" / name).read_text(encoding="utf-8"))
            previous["state"]["approval"] = None
            previous["state"]["planHash"] = None
            previous["state"]["stage"] = "discovery"
            return previous["config"], previous["state"]
        with self.lock():
            config, state = self._load()
            config, state = restore(config, state)
            self._commit(config, state, "Restored checkpoint; plan requires renewal", snapshot=False)
