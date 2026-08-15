from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from trust_intake.answers import empty_answers


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "untitled"


def new_run_id(title: str, now: datetime | None = None) -> str:
    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{slugify(title)}"


def run_dir(run_id: str, runs_dir: Path) -> Path:
    return runs_dir / run_id


def write_json(run_id: str, name: str, data: dict, runs_dir: Path) -> Path:
    path = run_dir(run_id, runs_dir) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def read_json(run_id: str, name: str, runs_dir: Path) -> dict:
    path = run_dir(run_id, runs_dir) / name
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def init_run(title: str, runs_dir: Path, now: datetime | None = None) -> Path:
    run_id = new_run_id(title, now=now)
    dest = run_dir(run_id, runs_dir)
    dest.mkdir(parents=True, exist_ok=False)
    write_json(run_id, "answers.json", empty_answers(run_id, title), runs_dir)
    return dest
