from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ADPConfig:
    fine_tool: str = "T0"
    coarse_tool: str = "T1"
    fine_nozzle_mm: float = 0.2
    coarse_nozzle_mm: float = 0.8
    fine_layer_height_mm: float = 0.2
    coarse_layer_height_mm: float = 0.8
    fine_line_width_mm: float = 0.24
    coarse_line_width_mm: float = 0.8
    filament_diameter_mm: float = 1.75
    flow_multiplier: float = 1.0
    travel_feedrate_mm_min: float = 9000.0
    fine_feedrate_mm_min: float = 1800.0
    coarse_feedrate_mm_min: float = 1200.0
    first_layer_z_mm: float = 0.2
    loop_close_tolerance_mm: float = 0.35
    backing_inset_mm: float | None = None

    @property
    def effective_backing_inset_mm(self) -> float:
        if self.backing_inset_mm is not None:
            return self.backing_inset_mm
        return (self.fine_line_width_mm + self.coarse_line_width_mm) / 2.0

    def validate(self) -> None:
        values = {
            "fine_nozzle_mm": self.fine_nozzle_mm,
            "coarse_nozzle_mm": self.coarse_nozzle_mm,
            "fine_layer_height_mm": self.fine_layer_height_mm,
            "coarse_layer_height_mm": self.coarse_layer_height_mm,
            "fine_line_width_mm": self.fine_line_width_mm,
            "coarse_line_width_mm": self.coarse_line_width_mm,
            "filament_diameter_mm": self.filament_diameter_mm,
            "flow_multiplier": self.flow_multiplier,
        }
        for name, value in values.items():
            if value <= 0:
                raise ValueError(f"{name} must be greater than zero")
        if self.coarse_layer_height_mm < self.fine_layer_height_mm:
            raise ValueError("coarse_layer_height_mm must be >= fine_layer_height_mm")
