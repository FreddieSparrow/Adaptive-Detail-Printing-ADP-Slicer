from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .config import ADPConfig
from .geometry import Loop, distance, normalize_loop


@dataclass(frozen=True)
class OrcaExtraction:
    outer_loops: list[Loop]
    max_z_mm: float | None
    warnings: list[str] = field(default_factory=list)


def extract_outer_loops_from_orca_gcode(
    path: Path, config: ADPConfig
) -> OrcaExtraction:
    return extract_outer_loops_from_text(path.read_text(encoding="utf-8", errors="replace"), config)


def extract_outer_loops_from_text(text: str, config: ADPConfig) -> OrcaExtraction:
    x: float | None = None
    y: float | None = None
    z: float | None = None
    e: float | None = None
    absolute_xy = True
    absolute_e = True
    active_outer_feature = False
    current_path: Loop = []
    loops: list[Loop] = []
    warnings: list[str] = []
    extraction_z: float | None = None
    max_z: float | None = None

    def finish_path() -> None:
        nonlocal current_path
        if len(current_path) < 3:
            current_path = []
            return
        if distance(current_path[0], current_path[-1]) <= config.loop_close_tolerance_mm:
            current_path[-1] = current_path[0]
            try:
                loops.append(normalize_loop(current_path))
            except ValueError as exc:
                warnings.append(str(exc))
        current_path = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        comment = ""
        command = line
        if ";" in line:
            command, comment = line.split(";", 1)
            comment = comment.strip().lower()
            if _comment_selects_outer_wall(comment):
                finish_path()
                active_outer_feature = True
            elif _comment_selects_non_outer_feature(comment):
                finish_path()
                active_outer_feature = False
            if "layer_change" in comment or comment.startswith("layer:"):
                finish_path()

        command = command.strip()
        if not command:
            continue

        parts = command.split()
        op = parts[0].upper()
        params = _parse_params(parts[1:])

        if op == "G90":
            absolute_xy = True
            continue
        if op == "G91":
            absolute_xy = False
            continue
        if op == "M82":
            absolute_e = True
            continue
        if op == "M83":
            absolute_e = False
            continue

        if op not in {"G0", "G1", "G00", "G01"}:
            continue

        old_x, old_y, old_e = x, y, e
        new_x = _next_axis_value("X", params, x, absolute_xy)
        new_y = _next_axis_value("Y", params, y, absolute_xy)
        new_z = _next_axis_value("Z", params, z, absolute_xy)
        new_e = _next_axis_value("E", params, e, absolute_e)

        if new_z is not None:
            z = new_z
            max_z = z if max_z is None else max(max_z, z)

        if not active_outer_feature:
            x, y, e = new_x, new_y, new_e
            continue

        if old_x is None or old_y is None or new_x is None or new_y is None:
            x, y, e = new_x, new_y, new_e
            continue

        e_delta = _extrusion_delta(old_e, new_e, "E" in params)
        is_xy_move = distance((old_x, old_y), (new_x, new_y)) > 1e-9
        is_extruding = e_delta > 0 and is_xy_move

        if is_extruding:
            if extraction_z is None:
                extraction_z = z
            elif z is not None and extraction_z is not None and z > extraction_z + config.fine_layer_height_mm / 2.0:
                finish_path()
                break

            if not current_path:
                current_path.append((old_x, old_y))
            current_path.append((new_x, new_y))
        else:
            finish_path()

        x, y, e = new_x, new_y, new_e

    finish_path()
    if not loops:
        warnings.append("no closed outer-wall loops were extracted")
    return OrcaExtraction(outer_loops=loops, max_z_mm=max_z, warnings=warnings)


def _comment_selects_outer_wall(comment: str) -> bool:
    return (
        "outer wall" in comment
        or "external perimeter" in comment
        or "type:external" in comment
    )


def _comment_selects_non_outer_feature(comment: str) -> bool:
    feature_markers = ("type:", "feature:", "feature ")
    if not any(marker in comment for marker in feature_markers):
        return False
    return not _comment_selects_outer_wall(comment)


def _parse_params(parts: list[str]) -> dict[str, float]:
    params: dict[str, float] = {}
    for part in parts:
        key = part[:1].upper()
        if key in {"X", "Y", "Z", "E", "F"}:
            try:
                params[key] = float(part[1:])
            except ValueError:
                continue
    return params


def _next_axis_value(
    axis: str, params: dict[str, float], previous: float | None, absolute: bool
) -> float | None:
    if axis not in params:
        return previous
    value = params[axis]
    if absolute or previous is None:
        return value
    return previous + value


def _extrusion_delta(
    old_e: float | None, new_e: float | None, has_e_param: bool
) -> float:
    if not has_e_param or new_e is None:
        return 0.0
    if old_e is None:
        return max(new_e, 0.0)
    return new_e - old_e
