from __future__ import annotations

import argparse
from pathlib import Path

from .config import ADPConfig
from .gcode import emit_gcode
from .model import PathDocument, load_path_document
from .orca_gcode import extract_outer_loops_from_orca_gcode
from .planner import plan_adp_walls


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="adp-slicer",
        description="Generate Adaptive Detail Printing dual-nozzle wall G-code.",
    )
    parser.add_argument("input", type=Path, help="ADP path JSON, or Orca G-code with --from-orca")
    parser.add_argument("-o", "--output", type=Path, default=Path("build/adp_output.gcode"))
    parser.add_argument("--from-orca", action="store_true", help="extract first-layer outer loops from Orca-style G-code")
    parser.add_argument("--height", type=float, help="override model height in mm")
    parser.add_argument("--fine-tool", default="T0")
    parser.add_argument("--coarse-tool", default="T1")
    parser.add_argument("--fine-layer-height", type=float, default=0.2)
    parser.add_argument("--coarse-layer-height", type=float, default=0.8)
    parser.add_argument("--fine-line-width", type=float, default=0.24)
    parser.add_argument("--coarse-line-width", type=float, default=0.8)
    parser.add_argument("--backing-inset", type=float)
    args = parser.parse_args(argv)

    config = ADPConfig(
        fine_tool=args.fine_tool,
        coarse_tool=args.coarse_tool,
        fine_layer_height_mm=args.fine_layer_height,
        coarse_layer_height_mm=args.coarse_layer_height,
        fine_line_width_mm=args.fine_line_width,
        coarse_line_width_mm=args.coarse_line_width,
        backing_inset_mm=args.backing_inset,
    )

    if args.from_orca:
        extraction = extract_outer_loops_from_orca_gcode(args.input, config)
        if not extraction.outer_loops:
            for warning in extraction.warnings:
                print(f"warning: {warning}")
            return 2
        height_mm = args.height or extraction.max_z_mm or config.coarse_layer_height_mm
        document = PathDocument(
            model_name=args.input.stem,
            height_mm=height_mm,
            outer_loops=extraction.outer_loops,
        )
        for warning in extraction.warnings:
            print(f"warning: {warning}")
    else:
        document = load_path_document(args.input)
        if args.height is not None:
            document = PathDocument(
                model_name=document.model_name,
                height_mm=args.height,
                outer_loops=document.outer_loops,
            )

    passes = plan_adp_walls(document.outer_loops, document.height_mm, config)
    gcode = emit_gcode(passes, config, document.model_name)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(gcode, encoding="utf-8")
    print(f"wrote {args.output} with {len(passes)} ADP tool passes")
    return 0
