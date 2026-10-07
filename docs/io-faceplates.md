# EFC x80 I/O Card Faceplates (Ignition Perspective 8.1, 8.3-safe)

These are faceplates for the eight standard X80 I/O cards in Controls Standard rev H, Table 6.1:
- Discrete inputs: BMXDDI1602, BMXDDI3202K
- Discrete outputs: BMXDDO1602, BMXDDO3202K, BMXDDO6402K
- Analog: BMXAMI0810 (inputs), BMXAMO0802 (outputs)
- Temperature: BMXART0814

Each card has one UDT and one faceplate, both tied to the Control Expert IODDTs the card uses. Data comes over OPC UA through the BMENUA0100.

## Files
| File | What it is | Import |
|---|---|---|
| `EFC_IOFaceplates.zip` | Perspective project (parent `EFC_Styles`). It contains the 8 faceplates, the parts they repeat, `IO/RackOverview` and `IO/_Demo`. | Gateway → Config → Projects → Import |
| `EFC_IO_UDTs.json` | Card UDTs under `_types_/IO/<card>`, using OPC tags | Designer Tag Browser → Import, at the provider root |
| `EFC_IO_Demo_Tags.json` | Demo setup that needs no PLC: memory-tag copies of the UDTs (`_types_/IO_Demo`) and a demo rack (`IO_Demo/Rack0`) | Same as above |
| `build_io.py` | The generator. Edit the `IODDT` table or `CARDS`, run it, then re-import. | — |

Project chain: `EFC_Styles → EFC_IOFaceplates → … → HMI`. Alternatively, copy the `IO` view folder into the HMI project. The views use EFC_Styles classes only and add no new classes.

## UDT structure (example: one BMXAMI0810)
```
R0S5                      instance of IO/BMXAMI0810
  CardModel, CardDesc, Rack, Slot
  Module/                 T_GEN_MOD     -> {Prefix}{ModSuffix}       e.g. R0S5_MOD
    MOD_ERROR  EXCH_STS  EXCH_RPT  MOD_FLT  MOD_FAIL  CH_FLT  BLK  CONF_FLT  NO_MOD
    HMI/DiagText
  CH00 … CH07/            T_ANA_IN_BMX  -> {Prefix}{ChSuffix}n       e.g. R0S5_CH3
    VALUE  CH_ERROR  EXCH_STS  EXCH_RPT  LOWER_LIMIT  UPPER_LIMIT  SENSOR_FLT  RANGE_FLT
    INTERNAL_FLT  CONF_FLT  COM_FLT  APPLI_FLT
    Doc/  LoopTag  Description  Spare  Units  RawMin  RawMax  EngMin  EngMax    (memory, kept in Ignition)
    HMI/  Scaled  DiagText                                                       (expressions)
```

Each instance takes these parameters:

| Parameter | Default | Meaning |
|---|---|---|
| `Prefix` | (blank) | The card's variable prefix in the PLC, e.g. `R0S5` |
| `Rack` | 0 | Rack number, shown on the faceplate |
| `Slot` | 0 | Slot number, shown on the faceplate |
| `OPCServer` | `BMENUA0100` | Name of the Ignition OPC UA connection |
| `NodePrefix` | `ns=2;s=` | Start of the OPC UA node ID |
| `ChSuffix` | `_CH` | Text between the prefix and the channel number |
| `ModSuffix` | `_MOD` | Text between the prefix and the module variable |

The OPC item path is built as `{NodePrefix}{Prefix}{ChSuffix}n.ELEMENT`.

In normal use you set only `Prefix`, `Rack` and `Slot`. The rest keep their defaults.

Fill in the `Doc` tags (loop tag, description, scaling, spare) for each channel. These are the values the faceplate shows.

## PLC side (Control Expert)
1. **Declare one IODDT variable per channel and one T_GEN_MOD per card.** Use this naming pattern:
   - `R0S5_CH0 … R0S5_CH7 : T_ANA_IN_BMX` (at `%CH0.5.0` …)
   - `R0S5_MOD : T_GEN_MOD` (at `%CH0.5.MOD`)
2. **Set the HMI attribute on those variables.** The BMENUA0100 only exposes HMI variables (Controls Standard 8.2).
3. **Refresh the status words with READ_STS.** `VALUE`, `CH_ERROR` and `MOD_ERROR` update every scan. The status words and their bits (`TRIP`, `SENSOR_FLT`, `MOD_FAIL` …) only refresh when the program calls `READ_STS` on that channel or module. Call it on a slow round-robin, or those diagnostics will stay at their last value.

## Verify on the first import (not tested on a gateway yet)
- [ ] **Node ID format.** Browse the BMENUA0100 in the Designer OPC browser and confirm the namespace index and path, e.g. `ns=2;s=R0S5_CH3.VALUE`. If they differ, change the `NodePrefix` default.
- [ ] **IODDT element names.** Check the `IODDT` table at the top of `build_io.py` against the Control Expert data editor. The output names `ACT_WIRE_FLT`, and the bit sets of `T_DIS_*_STD` and `T_GEN_MOD`, are the least certain. Rebuild after any change.
- [ ] **Analog raw ranges.** The defaults are:
  - AMI/AMO: raw 0–10000 maps to 0–100 %.
  - ART: `VALUE / 10` gives degrees, displayed as °C.

  Set the `Doc` scaling per channel to match the channel configuration.
- [ ] **Rack overview and faceplates.** Open `IO/_Demo` in a browser session, not the Designer, since vh text sizes only render correctly in a browser. Then click every card.

## Behaviour
- **Opening a faceplate.** `IO/RackOverview` (param `rackPath`, e.g. `[default]Plant/Rack0`) browses every UDT instance in that folder, sorts them by `Slot`, and draws one tile per card. Clicking a tile opens `IO/Faceplates/<CardModel>` as a draggable popup with `cardPath`. To open a faceplate from anywhere else, call:
  `system.perspective.openPopup(id, "IO/Faceplates/BMXAMI0810", params={"cardPath": path})`.
- **Module health chip.** It reads HEALTHY, MODULE FAULT (`MOD_ERROR`), or COMMS? when the OPC quality is bad (shown magenta).
- **Discrete cards.** Channels show as tiles in groups of 16 (one per terminal connector):
  - White lamp = ON, gray lamp = OFF.
  - A dark tile is a channel fault (`CH_ERROR`).
  - A dashed tile is a spare.
  - Hovering a tile shows its loop tag, description and active diagnostic bits.
- **Analog and temperature cards.** These show a table with these columns: channel, loop tag, description, raw value, scaled value, units, range bar (AI/AO), UNDER/OVER (from `LOWER_LIMIT`/`UPPER_LIMIT`), and health. The health chip's tooltip lists the diagnostic bits.
- **Outputs are read-only.** The faceplates show what the PLC is writing; they never write to the card.

## 8.3 notes
- The suite uses only views, UDTs and existing style classes, with no gateway event scripts.
- The rack overview's script transform uses `system.tag.browse` and `system.tag.readBlocking`, which are unchanged in 8.3.
- Popup sizes are view default sizes in px (800–1620 wide at 1080p), while text scales in vh. On 4K screens the text grows faster than the popup. If anything clips, pass a larger `position` to `openPopup`.
