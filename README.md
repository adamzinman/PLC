# PLC

## Scale station faceplates (Ignition Perspective 8.1)

Four design options for a scale station faceplate. Each one shows the operator
setpoints (target weight, sample weight, max pressure, prefill pressure), the
PLC weights (net, tare, total), a PLC message string, and a select/deselect
control. There are 6 stations.

| Option | View | Size | Idea |
|---|---|---|---|
| A | `ScaleStation/OptionA_HighPerformance` | 320 × 480 | ISA-101 gray, label/value/unit rows |
| B | `ScaleStation/OptionB_DarkControlRoom` | 340 × 540 | Dark, large net readout, console message, toggle switch |
| C | `ScaleStation/OptionC_TouchCards` | 380 × 580 | Light cards, large touch targets, message banner |
| D | `ScaleStation/OptionD_CompactTile` | 230 × 480 | Narrow tile with net-vs-target fill bar, fits 6 across |
| – | `ScaleStation/Overview` | 1400 × 1100 | All 6 stations in a flex repeater, with a dropdown to switch options |

An interactive browser mock of all four is in `preview/scale_faceplate_options.html`.

### Files

- `ignition/tags/ScaleStation_tags.json`: `ScaleStation` UDT (memory tags for testing) and `Scales/Station1..6` instances.
- `ignition/project/`: the Perspective view resources.
- `dist/ScaleStationFaceplates.zip`: the same views as a project export for Designer import.
- `tools/build_faceplates.py`: generates the views and zip. Edit it and run `python3 tools/build_faceplates.py`.

### Import into Ignition

1. **Tags:** in the Designer Tag Browser, select the `[default]` provider root, click Import Tags, and choose `ignition/tags/ScaleStation_tags.json`.
2. **Views:** in the Designer, use File > Import and pick `dist/ScaleStationFaceplates.zip`. Alternatively copy the `ScaleStation` folder from `ignition/project/com.inductiveautomation.perspective/views/` into `<ignition>/data/projects/<YourProject>/com.inductiveautomation.perspective/views/` and run a project scan.
3. Open `ScaleStation/Overview` in a session to see all 6 stations.

### UDT members

| Member | Type | Direction |
|---|---|---|
| `TargetWeight`, `SampleWeight` | Float4 | HMI writes |
| `MaxPressure`, `PrefillPressure` | Float4 | HMI writes |
| `NetWeight`, `TareWeight`, `TotalWeight` | Float4 | PLC writes |
| `Message` | String | PLC writes |
| `Selected` | Boolean | HMI toggles |

The UDT members are memory tags so the views work without a PLC. To go live,
change each member to an OPC tag pointing at the station's PLC tags.

### View parameters

| Param | Default |
|---|---|
| `tagPath` | `[default]Scales/Station1` |
| `stationNum` | `1` |
| `weightUnits` | `lb` |
| `pressureUnits` | `psi` |

Each view binds the UDT members once, into `view.custom.*` (indirect tag
bindings on `{view.params.tagPath}`). The components bind to those custom
properties, so renaming a UDT member only touches the `MEMBERS` table in the
generator. The select buttons run a script that reads `Selected` and writes
the inverse value.
