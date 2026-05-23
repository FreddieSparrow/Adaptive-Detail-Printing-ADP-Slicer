<div align="center">

<picture>
  <img alt="ADP Slicer logo" src="resources/images/OrcaSlicer.png" width="15%" height="15%">
</picture>

# Adaptive Detail Printing (ADP) Slicer

**An OrcaSlicer fork built for dual-nozzle printers that combine a 0.2 mm fine nozzle with a 0.8 mm coarse nozzle.**

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE.txt)
[![Build all](https://github.com/OrcaSlicer/OrcaSlicer/actions/workflows/build_all.yml/badge.svg?branch=main)](https://github.com/OrcaSlicer/OrcaSlicer/actions/workflows/build_all.yml)

</div>

---

## What is ADP?

Adaptive Detail Printing is a dual-nozzle slicing strategy that prints every outer wall twice — once with a fine nozzle for dimensional accuracy and surface finish, and once with a coarse nozzle for structural backing. The result is a wall that looks and tolerances like a fine print but is mechanically backed like a thick one.

### How it works

```
  Band height = 0.8 mm  (one coarse layer)
  Fine layers per band = 4  (four 0.2 mm layers)

  Z=0.2  →  T0 fine outer wall   (0.2 mm nozzle, 0.24 mm line)
  Z=0.4  →  T0 fine outer wall
  Z=0.6  →  T0 fine outer wall
  Z=0.8  →  T0 fine outer wall
  Z=0.8  →  T1 coarse backing wall  (0.8 mm nozzle, 0.8 mm line, inset behind T0)
             ↑ activates once fine layers reach coarse-band height

  Z=1.0  →  T0 fine outer wall   (next band begins)
  ...
```

The coarse wall is offset inward by `(fine_line_width + coarse_line_width) / 2` so it sits flush behind the fine outer wall without pushing it outward.

> **This fork only generates G-code for printer profiles that have exactly one 0.2 mm nozzle (T0) and one 0.8 mm nozzle (T1).** G-code export refuses any other profile combination.

---

## Repository layout

```
Adaptive-Detail-Printing-ADP-Slicer/
│
├── adp_slicer/               ← Python reference kernel (works today)
│   ├── src/adp_slicer/       ← Core library
│   │   ├── config.py         ← ADPConfig – all tunable parameters
│   │   ├── geometry.py       ← Polygon loops, inward offsetting
│   │   ├── planner.py        ← Band scheduler, ToolPass sequence
│   │   ├── gcode.py          ← G-code emitter, extrusion maths
│   │   ├── orca_gcode.py     ← Outer-loop extractor from Orca G-code
│   │   ├── model.py          ← JSON path-document loader
│   │   └── cli.py            ← Command-line entry point
│   ├── tests/                ← Unit tests (unittest)
│   ├── examples/             ← Demo JSON models
│   ├── build/                ← Generated G-code output
│   └── pyproject.toml
│
├── src/                      ← OrcaSlicer C++ application (fork base)
├── resources/profiles/       ← Printer/material profiles
├── tests/                    ← OrcaSlicer C++ test suites (Catch2)
├── CLAUDE.md                 ← C++ build & architecture reference
├── AGENTS.md                 ← Contribution guidelines
└── README.md                 ← This file
```

---

## Quick start — Python prototype

The Python kernel runs standalone and requires **Python 3.10+** with no extra dependencies.

### Generate the demo G-code

```sh
cd adp_slicer
PYTHONPATH=src python3 -m adp_slicer examples/adp_demo_paths.json -o build/adp_demo.gcode
```

Output is written to `adp_slicer/build/adp_demo.gcode`. Open it in any G-code viewer or OrcaSlicer's preview to inspect the ADP wall sequence.

### Run the tests

```sh
cd adp_slicer
PYTHONPATH=src python3 -m unittest discover -s tests
```

### Extract ADP walls from existing Orca G-code

```sh
cd adp_slicer
PYTHONPATH=src python3 -m adp_slicer --from-orca /path/to/orca_output.gcode \
    -o build/adp_from_orca.gcode
```

This extracts the first-layer outer-wall loops from an Orca/Bambu G-code file (identified by `;TYPE:Outer wall`, `; FEATURE: Outer wall`, or `;TYPE:External perimeter` comments) and re-slices them with the ADP dual-wall strategy.

### Input format

The prototype accepts a simple JSON path document:

```json
{
  "model_name": "demo_box",
  "height_mm": 1.6,
  "outer_loops": [
    [[0, 0], [40, 0], [40, 30], [0, 30]]
  ]
}
```

`outer_loops` is a list of closed polygons in XY (mm). Each loop must have at least three unique vertices. Duplicate closing vertices are stripped automatically.

### CLI options

| Flag | Default | Description |
|------|---------|-------------|
| `--from-orca` | off | Parse loops from Orca-style G-code instead of JSON |
| `--height` | from input | Override model height (mm) |
| `--fine-tool` | `T0` | Tool name for the fine nozzle |
| `--coarse-tool` | `T1` | Tool name for the coarse nozzle |
| `--fine-layer-height` | `0.2` | Fine layer height (mm) |
| `--coarse-layer-height` | `0.8` | Coarse band height (mm) |
| `--fine-line-width` | `0.24` | Fine extrusion line width (mm) |
| `--coarse-line-width` | `0.8` | Coarse extrusion line width (mm) |
| `--backing-inset` | auto | Override inward offset for the backing wall (mm) |

---

## Build the full OrcaSlicer fork (C++)

Build instructions for all platforms are in [CLAUDE.md](CLAUDE.md). The short version:

### macOS

```sh
./build_release_macos.sh
```

### Linux

```sh
./build_linux.sh
```

### Windows

```bat
build_release_vs2022.bat
```

Run the C++ test suite after building:

```sh
cd build && ctest --output-on-failure
```

---

## ADP printer profile requirements

When the full C++ fork is in use, G-code export enforces:

- Exactly **two extruders** defined in the printer profile.
- Extruder 1 (T0) nozzle diameter = **0.2 mm**.
- Extruder 2 (T1) nozzle diameter = **0.8 mm**.

Any other combination is rejected with a clear error message. This is intentional — ADP walls only make physical sense with this specific nozzle pairing.

---

## Security audit

The upstream repository [`FreddieSparrow/Adaptive-Detail-Printing-ADP-Slicer`](https://github.com/FreddieSparrow/Adaptive-Detail-Printing-ADP-Slicer) was audited on **2026-05-22**.

**Findings: clean.** The repository is a direct fork of the official [OrcaSlicer/OrcaSlicer](https://github.com/OrcaSlicer/OrcaSlicer) codebase licensed under AGPL-3.0. No suspicious binaries, obfuscated scripts, unexpected network calls, or credential-harvesting patterns were found. The only additions beyond vanilla OrcaSlicer are:

- `CLAUDE.md` — Claude Code architecture reference (documentation only).
- `AGENTS.md` — Contribution guidelines (documentation only).
- `.cursorignore` — Cursor IDE ignore file (configuration only).
- Modified `README.md` — ADP fork description.
- `adp_slicer/` — The Python reference kernel (this project).

The `.exe` files in `tools/` (`7z.exe`, `xgettext.exe`, `msgfmt.exe`, `msgmerge.exe`) are standard Windows build utilities present in the original OrcaSlicer repository.

---

## Roadmap to production slicer

The Python prototype demonstrates the core ADP scheduling algorithm. These are the remaining milestones for a fully production-ready fork:

| # | Milestone | Status |
|---|-----------|--------|
| 1 | ADP band scheduler + G-code emitter | ✅ Done (Python prototype) |
| 2 | Outer-loop extraction from Orca G-code | ✅ Done (Python prototype) |
| 3 | OrcaSlicer fork base + ADP profile enforcement | ✅ Done (C++ fork) |
| 4 | Per-layer geometry from real STL/3MF slicing | 🔲 Pending |
| 5 | Full UI integration in OrcaSlicer | 🔲 Pending |
| 6 | Collision detection & wipe tower for tool changes | 🔲 Pending |
| 7 | Prime tower, purge, and temperature handling | 🔲 Pending |
| 8 | Retraction & pressure advance per tool | 🔲 Pending |
| 9 | Changing cross-sections (not just repeated outlines) | 🔲 Pending |
| 10 | Printer-specific tool-change macros | 🔲 Pending |

---

## How the backing wall offset is calculated

The inward offset places the centre of the coarse bead directly adjacent to the inner face of the fine bead:

```
offset = (fine_line_width + coarse_line_width) / 2
       = (0.24 + 0.8) / 2
       = 0.52 mm
```

This means the fine outer wall and the coarse backing wall share a face with no gap and no overlap. The value can be overridden with `--backing-inset` or `ADPConfig(backing_inset_mm=…)`.

---

## G-code structure

A typical ADP output looks like this:

```gcode
; generated by Adaptive Detail Printing (ADP) Slicer 0.1.0
; strategy: fine outer wall first, coarse backing wall after each coarse-height band
; fine: T0 nozzle=0.2mm layer=0.2mm
; coarse: T1 nozzle=0.8mm layer=0.8mm
G21 ; millimeters
G90 ; absolute XY
M83 ; relative extrusion

T0 ; select ADP fine tool
G92 E0
; ADP_FINE_OUTER_WALL band=1 z=0.2 nozzle=0.2 line_width=0.24
; ADP_FINE_LAYER index=1
G0 Z0.2 F9000
G0 X0 Y0 F9000
G1 X40 Y0 E0.35437 F1800
...

T1 ; select ADP coarse tool
G92 E0
; ADP_COARSE_BACKING_WALL band=1 z=0.8 nozzle=0.8 line_width=0.8
G0 Z0.8 F9000
G0 X0.52 Y0.52 F9000
G1 X39.48 Y0.52 E1.01234 F1200
...
; ADP_END
G92 E0
```

Feature comments (`ADP_FINE_OUTER_WALL`, `ADP_COARSE_BACKING_WALL`) allow post-processors and future UI preview layers to identify ADP wall segments.

---

## Contributing

See [AGENTS.md](AGENTS.md) for coding style, testing, and PR guidelines. The project follows the same C++ conventions as OrcaSlicer (C++17, snake_case functions, PascalCase classes, `.clang-format` enforced).

Python code follows PEP 8. Run `python3 -m unittest discover -s adp_slicer/tests` before opening a PR that touches the Python kernel.

---

## License

ADP Slicer inherits OrcaSlicer's licence:

- **ADP Slicer / OrcaSlicer** — GNU Affero General Public License v3.
- **Bambu Studio** (upstream) — GNU Affero General Public License v3.
- **PrusaSlicer** (upstream) — GNU Affero General Public License v3.
- **Slic3r** (upstream) — GNU Affero General Public License v3.

The AGPL-3.0 requires that any version of this software, including network-hosted versions, must make their source code available under the same licence.

---

## Acknowledgements

Built on top of [OrcaSlicer](https://github.com/OrcaSlicer/OrcaSlicer) by SoftFever and the OrcaSlicer community. OrcaSlicer itself descends from Bambu Studio → PrusaSlicer → Slic3r. The ADP slicing concept and dual-nozzle scheduling algorithm are original additions by Freddie Sparrow.
