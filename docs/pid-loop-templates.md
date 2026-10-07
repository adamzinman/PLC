# PID Loop Templates — Perspective 8.1 (2026-10-05)

Chosen design: Option B (bar-graph card) plus three variations, modern flat ISA-101 style (grays, blue SP, color only for alarms). Shipped as `PID_Loop_Templates_Perspective81.zip` (project `PID_Loops.zip`, tags, README, `generate_loops.py`). Not yet test-imported on a gateway.

| View | Size @1080p | Notes |
|---|---|---|
| `PID/Templates/Loop_B1_Bar` | 150×156 | Vertical PV bar + SP pointer + alarm ticks; SP and OUT values enlarged to 16 px (user request) |
| `PID/Templates/Loop_B2_Horizontal` | 260×92 | Horizontal bar with normal-range band between AlmLo/AlmHi |
| `PID/Templates/Loop_B3_Sparkline` | 172×184 | B1 + 1-min PV/SP sparkline (queryTagHistory) + deviation chip (orange past AlmDev) |
| `PID/Templates/Loop_B4_Column` | 104×196 | Twin vertical bars PV + OUT |
| `PID/Popups/LoopConfig` | 440×480 | Tabs Operate / Tuning / Limits & Alarms |
| `PID/_Demo_Loops` | — | All four × 3 demo loops |

- Template params: `tagPath` (PID_Loop UDT instance), `label` (optional). Whole card is the click target → `openPopup("loopcfg_<tagPath>", "PID/Popups/LoopConfig")`.
- Graphics are Drawing components with bound element geometry; fonts/padding in vh (1080p px / 10.8).
- UDT `PID_Loop`: PV (EngUnit/EngLow/EngHigh drive units + scaling; PV_High/PV_Low alarms bound to AlmHi/AlmLo), SP, OUT, Mode (0 MAN/1 AUTO/2 CAS), Kp, Ti, Td, Action (0 Rev/1 Dir), SP_Lo/Hi, OUT_Lo/Hi, AlmHi, AlmLo, AlmDev, Description. Memory tags in export; map to M580 PID block.
- Popup: mode buttons + SP/OUT write immediately (OUT only in MAN, SP locked in CAS); tuning/limits read on open, written on Apply, editable only with role `view.custom.engineerRole` (default `Engineer`).
- History must be enabled on PV/SP/OUT for the B3 sparkline and popup trend.
- Card alarm state = PV ≥ AlmHi or ≤ AlmLo (not real alarm priority yet).
- Output is labeled "OUT" on cards; user calls it CV (offered to relabel).
