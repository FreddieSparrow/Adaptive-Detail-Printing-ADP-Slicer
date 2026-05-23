from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .geometry import Loop, parse_loop


@dataclass(frozen=True)
class PathDocument:
    model_name: str
    height_mm: float
    outer_loops: list[Loop]


def load_path_document(path: Path) -> PathDocument:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("path document must be a JSON object")
    return path_document_from_mapping(data, default_name=path.stem)


def path_document_from_mapping(data: dict[str, Any], default_name: str = "adp_model") -> PathDocument:
    model_name = str(data.get("model_name") or default_name)
    try:
        height_mm = float(data["height_mm"])
    except KeyError as exc:
        raise ValueError("path document needs height_mm") from exc

    raw_loops = data.get("outer_loops")
    if not isinstance(raw_loops, list) or not raw_loops:
        raise ValueError("path document needs at least one outer loop")

    outer_loops = [parse_loop(raw_loop) for raw_loop in raw_loops]
    return PathDocument(model_name=model_name, height_mm=height_mm, outer_loops=outer_loops)
