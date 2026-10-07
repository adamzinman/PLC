# PLC — EFC Ignition Perspective 8.1 Library

All of the EFC Perspective work from the EFC-Repo zips (`efc-ignition-library.zip`,
`efc-ignition-library_1.zip`, `efc-processvalues-repo.zip`, `EFC_ProcessValues-1.3.0.zip`,
`IO Faceplates.zip`) merged into **one** importable Ignition 8.1 project: `EFC_Library`.

## Import

1. **Project:** Gateway → Config → Projects → **Import**, choose `dist/EFC_Library.zip`.
   Name it `EFC_Library` (or anything you like). It has no parent and is inheritable, so you can
   use it directly or set it as the parent of your HMI project.
2. **Tags:** Designer → Tag Browser → Import Tags (JSON) into the `[default]` provider. Import the
   UDT files before the instance files:

   | Folder | Import order |
   |---|---|
   | `tags/PID_Symbols/` | `PID_ControlValve_UDT.json`, `PID_Motor_UDT.json`, `Valve_Discrete_Demo_UDT.json`, then `PID_Demo_Instances.json` |
   | `tags/PID_Loops/` | `PID_Loop_UDT.json`, then `PID_Loop_Demo_Instances.json` |
   | `tags/ProcessValues/` | `PV_Demo_Tags.json` (UDT + demo instances) |
   | `tags/IO/` | `EFC_IO_UDTs.json`, then `EFC_IO_Demo_Tags.json` |

   The demo views bind to `[default]PID_Demo/...`, `[default]PV_Demo/...` and `[default]IO_Demo/...`.

The advanced stylesheet (`stylesheet.css`) needs Ignition 8.1.22 or newer.

## Layout

```
EFC_Library/                         The Ignition project (zip this folder's contents to import)
  project.json
  com.inductiveautomation.perspective/
    stylesheet/                      Advanced stylesheet (EFC_Styles v5.1)
    style-classes/                   EFC_Styles v5.1 (166 classes) + Process Value classes v1.3.0
    views/
      Styles/_Catalog                Style class catalog
      Templates/Rotating/...         PID symbol templates v5.1 (pumps, compressors, motor, ...)
      Templates/Valves/...           Valve templates v5.1
      Templates/HeatTransfer/...     Heat-transfer templates v5.1
      Templates/_Demo                PID symbol demo screen
      Templates/ProcessValues/...    PV_StatusStrip, PV_RangeBar, _Demo (v1.3.0)
      PID/Templates/Loop_B1..B4      PID loop faceplates
      PID/Popups/LoopConfig          Loop configuration popup
      PID/_Demo_Loops                PID loop demo screen
      IO/Faceplates/BMX...           x80 I/O card faceplates (popups)
      IO/Parts/...                   I/O row / tile parts
      IO/RackOverview, IO/_Demo      Rack overview and demo screen
tags/                                Tag JSON to import in the Tag Browser (not part of the project zip)
symbols/                             Static P&ID SVGs (use as Drawing components) + NavConnectors
docs/                                Style guide, ISA-101 palette/audit, design notes, changelogs
tools/package.py                     Static 8.1 checks + builds dist/EFC_Library.zip
dist/EFC_Library.zip                 Ready-to-import project
```

After editing anything under `EFC_Library/`, rebuild the zip:

```
python3 tools/package.py
```

## What was merged and what was dropped

| Source | Used |
|---|---|
| `efc-ignition-library.zip` (git repo, v5.1) | EFC_Styles, PID symbol templates, `Styles/_Catalog`, PID tags, SVG symbols, docs |
| `efc-ignition-library_1.zip` (git repo) | PID_Loops views + tags, NavConnector SVGs, PV / loop docs |
| `EFC_ProcessValues-1.3.0.zip` / `efc-processvalues-repo.zip` | Process Value style classes + views (the two are identical) |
| `IO Faceplates.zip` | EFC_IOFaceplates views + IO UDT / demo tags |

- `EFC_Styles` and `EFC_ProcessValues` appeared in more than one source; the copies had identical
  content (only `resource.json` timestamps differed), so one copy of each is kept.
- `PID_Symbols` and `EFC_PID_Library` from the v5.1 repo held the same templates; kept once.
- `PID_Compressor_Diaphragm` (`PID/Rotating/Compressor_Diaphragm`) was dropped: its own README marks
  it as a legacy add-on superseded by `Templates/Rotating/Compressor_Diaphragm` (v5.1).
- No style class or view paths collided, so every view path is unchanged and existing
  embedded-view / popup references still resolve (checked by `tools/package.py`).
- The Python generators were not carried over: they write to the old per-project folders. They are
  still in the EFC-Repo zips if you need to regenerate something.
