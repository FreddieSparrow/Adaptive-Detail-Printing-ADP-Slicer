from __future__ import annotations

import unittest

from adp_slicer.config import ADPConfig
from adp_slicer.gcode import emit_gcode
from adp_slicer.geometry import bbox, offset_polygon_inward
from adp_slicer.orca_gcode import extract_outer_loops_from_text
from adp_slicer.planner import plan_adp_walls


class ADPSlicerTests(unittest.TestCase):
    def test_offsets_square_inward_for_backing_wall(self) -> None:
        square = [(0, 0), (10, 0), (10, 10), (0, 10)]
        inset = 0.52

        offset = offset_polygon_inward(square, inset)

        for actual, expected in zip(bbox(offset), (inset, inset, 10 - inset, 10 - inset)):
            self.assertAlmostEqual(actual, expected)

    def test_scheduler_places_coarse_wall_after_four_fine_layers(self) -> None:
        config = ADPConfig()
        outer = [[(0, 0), (40, 0), (40, 30), (0, 30)]]

        passes = plan_adp_walls(outer, height_mm=0.8, config=config)

        self.assertEqual([tool_pass.kind for tool_pass in passes], [
            "fine_outer_wall",
            "fine_outer_wall",
            "fine_outer_wall",
            "fine_outer_wall",
            "coarse_backing_wall",
        ])
        self.assertEqual([tool_pass.z_mm for tool_pass in passes], [0.2, 0.4, 0.6, 0.8, 0.8])
        self.assertEqual(passes[-1].tool, "T1")
        self.assertEqual(passes[-1].line_width_mm, 0.8)

    def test_gcode_switches_from_fine_tool_to_coarse_tool(self) -> None:
        config = ADPConfig()
        outer = [[(0, 0), (10, 0), (10, 10), (0, 10)]]
        passes = plan_adp_walls(outer, height_mm=0.8, config=config)

        gcode = emit_gcode(passes, config, "test_box")

        self.assertIn("T0 ; select ADP fine tool", gcode)
        self.assertIn("T1 ; select ADP coarse tool", gcode)
        self.assertIn("; ADP_COARSE_BACKING_WALL", gcode)
        self.assertLess(gcode.index("T0 ; select ADP fine tool"), gcode.index("T1 ; select ADP coarse tool"))

    def test_extracts_orca_style_outer_loop(self) -> None:
        config = ADPConfig()
        text = """
G90
M83
G0 X0 Y0 Z0.2
;TYPE:Outer wall
G1 X10 Y0 E1
G1 X10 Y10 E1
G1 X0 Y10 E1
G1 X0 Y0 E1
;TYPE:Inner wall
G1 X5 Y5 E1
"""

        extraction = extract_outer_loops_from_text(text, config)

        self.assertEqual(len(extraction.outer_loops), 1)
        self.assertEqual(extraction.outer_loops[0], [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)])

    def test_orca_extractor_ends_path_on_travel_without_extrusion(self) -> None:
        config = ADPConfig()
        text = """
G90
M83
G0 X0 Y0 Z0.2
; FEATURE: Outer wall
G1 X10 Y0 E1
G1 X10 Y10 E1
G0 X20 Y20
G1 X30 Y20 E1
G1 X30 Y30 E1
G1 X20 Y30 E1
G1 X20 Y20 E1
"""

        extraction = extract_outer_loops_from_text(text, config)

        self.assertEqual(len(extraction.outer_loops), 1)
        self.assertEqual(extraction.outer_loops[0][0], (20.0, 20.0))


if __name__ == "__main__":
    unittest.main()
