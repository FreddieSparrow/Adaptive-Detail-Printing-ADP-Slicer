# Adaptive Detail Printing (ADP) Slicer

ADP Slicer is a first working prototype for a dual-nozzle slicing strategy inspired by Orca Slicer workflows.

The idea:

- `T0` uses a `0.2 mm` nozzle for the detailed outside wall.
- `T1` uses a `0.8 mm` nozzle for a thick backing wall.
- The fine nozzle prints enough `0.2 mm` layers to reach the height of one coarse `0.8 mm` layer.
- Once that height is reached, the coarse nozzle activates and lays a `0.8 mm` wall behind the fine outside wall.

The full OrcaSlicer-based fork is now cloned in `Adaptive-Detail-Printing-ADP-Slicer/`. The original Python prototype remains here as a small reference kernel and test harness.

The Orca integration is experimental and only supports dual-nozzle printers with exactly one `0.2 mm` nozzle and one `0.8 mm` nozzle. G-code export rejects other printer profiles and generated G-code explains the ADP nozzle requirement.

## Quick Start

Generate the demo G-code:

```sh
PYTHONPATH=src python3 -m adp_slicer examples/adp_demo_paths.json -o build/adp_demo.gcode
```

Run tests:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

## Example Input

The prototype accepts a simple path document:

```json
{
  "model_name": "demo_box",
  "height_mm": 1.6,
  "outer_loops": [
    [[0, 0], [40, 0], [40, 30], [0, 30]]
  ]
}
```

The slicer offsets each outside loop inward by half the fine wall width plus half the coarse wall width, so the `0.8 mm` wall sits directly behind the `0.2 mm` wall.

## Orca Slicer Path

There is also an experimental Orca-style G-code extractor:

```sh
PYTHONPATH=src python3 -m adp_slicer --from-orca input_from_orca.gcode -o build/adp_from_orca.gcode
```

That mode extracts first-layer outer-wall loops from Orca/Bambu-style feature comments such as `;TYPE:Outer wall`, `; FEATURE: Outer wall`, or `;TYPE:External perimeter`, then generates ADP wall G-code from those loops. It is intentionally conservative and is meant as a bridge toward a real Orca fork.

## Current Scope

Implemented:

- ADP band scheduling.
- Fine outside wall passes with `T0`.
- Coarse backing wall passes with `T1`.
- Simple polygon inward offsetting.
- G-code emission with relative extrusion.
- Demo model and unit tests.
- Experimental outer-wall extraction from Orca-style G-code.

Still needed for a production slicer:

- Full Orca Slicer fork and UI integration.
- Per-layer geometry from real STL/3MF slicing.
- Collision, wipe, prime tower, purge, and temperature handling.
- Retraction and pressure advance tuning per tool.
- Support for changing cross-sections instead of one repeated outline.
- Printer-specific tool-change macros.
