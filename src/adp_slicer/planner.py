from __future__ import annotations

from dataclasses import dataclass
from math import ceil, isclose
from typing import Literal, Sequence

from .config import ADPConfig
from .geometry import Loop, offset_polygon_inward

PassKind = Literal["fine_outer_wall", "coarse_backing_wall"]


@dataclass(frozen=True)
class ToolPass:
    kind: PassKind
    tool: str
    z_mm: float
    layer_height_mm: float
    line_width_mm: float
    nozzle_mm: float
    feedrate_mm_min: float
    loops: list[Loop]
    band_index: int
    fine_layer_index: int | None = None


def plan_adp_walls(
    outer_loops: Sequence[Loop], height_mm: float, config: ADPConfig
) -> list[ToolPass]:
    config.validate()
    if height_mm <= 0:
        raise ValueError("height_mm must be greater than zero")
    if not outer_loops:
        raise ValueError("at least one outer loop is required")

    passes: list[ToolPass] = []
    band_count = ceil(height_mm / config.coarse_layer_height_mm)
    fine_layers_per_full_band = max(
        1, round(config.coarse_layer_height_mm / config.fine_layer_height_mm)
    )

    previous_band_top = 0.0
    backing_loops = [
        offset_polygon_inward(loop, config.effective_backing_inset_mm)
        for loop in outer_loops
    ]

    for band_index in range(band_count):
        band_top = min(height_mm, (band_index + 1) * config.coarse_layer_height_mm)
        band_height = band_top - previous_band_top
        fine_layer_count = max(
            1, ceil((band_height - 1e-9) / config.fine_layer_height_mm)
        )

        for layer_in_band in range(fine_layer_count):
            z = previous_band_top + (layer_in_band + 1) * config.fine_layer_height_mm
            if z > band_top or isclose(z, band_top, abs_tol=1e-6):
                z = band_top
            passes.append(
                ToolPass(
                    kind="fine_outer_wall",
                    tool=config.fine_tool,
                    z_mm=round(z, 6),
                    layer_height_mm=min(config.fine_layer_height_mm, band_height),
                    line_width_mm=config.fine_line_width_mm,
                    nozzle_mm=config.fine_nozzle_mm,
                    feedrate_mm_min=config.fine_feedrate_mm_min,
                    loops=list(outer_loops),
                    band_index=band_index,
                    fine_layer_index=band_index * fine_layers_per_full_band
                    + layer_in_band
                    + 1,
                )
            )

        passes.append(
            ToolPass(
                kind="coarse_backing_wall",
                tool=config.coarse_tool,
                z_mm=round(band_top, 6),
                layer_height_mm=round(band_height, 6),
                line_width_mm=config.coarse_line_width_mm,
                nozzle_mm=config.coarse_nozzle_mm,
                feedrate_mm_min=config.coarse_feedrate_mm_min,
                loops=backing_loops,
                band_index=band_index,
            )
        )
        previous_band_top = band_top

    return passes
