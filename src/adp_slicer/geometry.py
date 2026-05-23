from __future__ import annotations

from math import hypot, isclose
from typing import Iterable, Sequence

Point = tuple[float, float]
Loop = list[Point]


def distance(a: Point, b: Point) -> float:
    return hypot(b[0] - a[0], b[1] - a[1])


def signed_area(loop: Sequence[Point]) -> float:
    points = normalize_loop(loop)
    area = 0.0
    for index, current in enumerate(points):
        nxt = points[(index + 1) % len(points)]
        area += current[0] * nxt[1] - nxt[0] * current[1]
    return area / 2.0


def normalize_loop(loop: Sequence[Point]) -> Loop:
    points = [(float(x), float(y)) for x, y in loop]
    if len(points) > 1 and distance(points[0], points[-1]) <= 1e-9:
        points = points[:-1]
    if len(points) < 3:
        raise ValueError("a loop needs at least three unique points")
    return points


def close_loop(loop: Sequence[Point]) -> Loop:
    points = normalize_loop(loop)
    return points + [points[0]]


def bbox(loop: Sequence[Point]) -> tuple[float, float, float, float]:
    points = normalize_loop(loop)
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def loop_length(loop: Sequence[Point]) -> float:
    points = close_loop(loop)
    return sum(distance(points[index], points[index + 1]) for index in range(len(points) - 1))


def offset_polygon_inward(loop: Sequence[Point], inset_mm: float) -> Loop:
    """Offset a simple polygon inward using mitered line intersections.

    This deliberately stays dependency-free for the prototype. It works well
    for convex and mildly concave walls, which is enough for the first ADP
    planner tests. A production Orca fork should use the slicer's clipping
    library instead.
    """
    if inset_mm < 0:
        raise ValueError("inset_mm must be non-negative")

    points = normalize_loop(loop)
    area = signed_area(points)
    if isclose(area, 0.0, abs_tol=1e-9):
        raise ValueError("cannot offset a zero-area loop")
    inward_side = 1.0 if area > 0 else -1.0

    shifted_edges: list[tuple[Point, Point]] = []
    for index, start in enumerate(points):
        end = points[(index + 1) % len(points)]
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = hypot(dx, dy)
        if length <= 1e-9:
            raise ValueError("loop contains a zero-length edge")
        left_normal = (-dy / length, dx / length)
        normal = (left_normal[0] * inward_side, left_normal[1] * inward_side)
        shift = (normal[0] * inset_mm, normal[1] * inset_mm)
        shifted_edges.append(
            (
                (start[0] + shift[0], start[1] + shift[1]),
                (end[0] + shift[0], end[1] + shift[1]),
            )
        )

    offset_points: Loop = []
    for index in range(len(points)):
        prev_edge = shifted_edges[index - 1]
        current_edge = shifted_edges[index]
        intersection = line_intersection(
            prev_edge[0], prev_edge[1], current_edge[0], current_edge[1]
        )
        if intersection is None:
            # Parallel adjacent edges are rare for clean polygons. Keep the
            # current shifted vertex so the caller still gets a usable loop.
            intersection = current_edge[0]
        offset_points.append(intersection)

    if abs(signed_area(offset_points)) >= abs(area):
        raise ValueError("offset loop did not move inward; check polygon winding")
    return offset_points


def line_intersection(a1: Point, a2: Point, b1: Point, b2: Point) -> Point | None:
    dax = a2[0] - a1[0]
    day = a2[1] - a1[1]
    dbx = b2[0] - b1[0]
    dby = b2[1] - b1[1]
    denominator = dax * dby - day * dbx
    if isclose(denominator, 0.0, abs_tol=1e-12):
        return None
    bax = b1[0] - a1[0]
    bay = b1[1] - a1[1]
    t = (bax * dby - bay * dbx) / denominator
    return (a1[0] + t * dax, a1[1] + t * day)


def parse_loop(raw_loop: Iterable[Iterable[float]]) -> Loop:
    points: Loop = []
    for raw_point in raw_loop:
        values = list(raw_point)
        if len(values) != 2:
            raise ValueError(f"expected [x, y] point, got {values!r}")
        points.append((float(values[0]), float(values[1])))
    return normalize_loop(points)
