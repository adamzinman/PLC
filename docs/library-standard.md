# Process Device Library – Design Standard (DRAFT v0.3)

**Status:** Draft for review. Nothing in this repo has been built yet. This spec defines the shape of every object
first, so we can agree on it once before writing the DFBs, DDTs, UDTs and faceplates.

| Item | Target |
|---|---|
| PLC | Modicon M580, EcoStruxure Control Expert **16.2** |
| PLC languages | DFB bodies in ST; call sites in any language (FBD recommended for readability) |
| HMI | Ignition **8.1** Perspective, with **8.3** as the target in roughly 6 months |
| PLC ↔ HMI | OPC UA, symbolic, **one BMENUA0100 per system**. No located `%MW` blocks |
| Field devices | Valves on **SMC SY3000 manifolds with an SMC EX260 SI unit**: **EtherNet/IP** first, **Modbus TCP** as the fallback. Limit switches are optional per valve (most valves have none). VFDs are **Allen-Bradley PowerFlex 525** on EtherNet/IP |
| System size | Small system 1–10 devices, large 5–20 (one M580 + BMENUA0100 per system) |
| HMI style | **ISA-101 grey scale** |

Open questions are in [§14](#14-open-questions-for-review).

### Change log

| Ver | Change |
|---|---|
| 0.1 | First draft |
| 0.2 | Prefix `PL_` confirmed. **Status and alarms are now individual BOOLs** (packed words removed). One BMENUA0100 per system. ISA-101 grey scale chosen. Added **valve bank object `PL_VBank`** for SMC SI units (EtherNet/IP or Modbus TCP). Double-solenoid / 3-position valve behaviour added. All Ethernet devices are now handled transport-independently |
| 0.3 | SMC **EX260** confirmed. **Limit switches are optional** (`Cfg.HasZSO/HasZSC`, default none) and the no-switch behaviour is defined. VFD built around the **PowerFlex 525** (`PL_PF525_Adp`), with its comms constraint noted (no native Modbus TCP). Sizing simplified for 1–20 devices per system. Unanswered questions now have stated defaults |

---

## 1. Design principles

1. **The DFB owns behaviour and Ignition owns presentation.** Interlocks, modes, failure detection, timers and alarm
   *conditions* run in the PLC, so the plant stays safe and consistent when Ignition is down. Ignition handles alarm
   acknowledgement, shelving, journaling, text, security and history.
2. **There is one HMI interface structure per device.** Each device instance gets a global DDT variable
   (`XV_1001_HMI`) that is passed to its DFB as `IN_OUT`. Ignition binds only to that variable. DFB internals, private
   variables and pins are never read by the HMI. This means we can change and re-version a DFB without breaking any
   Ignition tag paths.
3. **Every device uses the same base.** All device DDTs begin with the same `Base` sub-structure: command register,
   mode, state, summary status, interlocks, permissives and bypass. Every alarm structure begins with the same two
   alarms. A single shared Ignition base UDT and the common faceplate parts work for every device type.
4. **Status and alarms are individual, named BOOLs.** `XV_1001_HMI.Alm.FailOpen` is readable in an animation table,
   in an OPC UA browse and in Ignition with no bit masks. The cost is more OPC UA monitored items, which is managed in
   §4.2.
5. **Operator commands use a single integer command register.** The HMI writes a command code, and the PLC executes
   it, writes a response code and clears the register. This is kept even though status is now BOOLs. A lost or
   duplicated write can't leave a command bit stuck on, two commands can't be active at once, and every command gets
   a response code.
6. **Signals are named for their true meaning.** `Ovld = TRUE` means overloaded. Any wiring inversion (NC contacts)
   is done at the call site, never inside the DFB.
7. **The comms transport stays at the edge.** Device DFBs never see EtherNet/IP or Modbus. Valve banks and drives go
   through a thin adapter DFB that maps the device's process image, so switching a bank or drive from EtherNet/IP to
   Modbus TCP (stock shortage) changes only the hardware configuration and one adapter call.
8. **The library contains no safety functions.** Interlocks here are process/equipment interlocks. SIS / safety
   functions stay hardwired or in a safety PLC. The library may *monitor* them.
9. **Every device is simulation-capable.** Each DFB can simulate its own feedback, so code and HMI can be FAT-tested
   with no I/O.
10. **Standards alignment.** Alarms follow ISA-18.2 practice (PLC-side delays and deadbands, rationalized
    priorities, suppression by design). The HMI follows ISA-101 (grey-scale normal state, colour reserved for
    abnormal).

---

## 2. Object list

### 2.1 Phase 1–4 (this library)

| Object | DFB type | HMI DDT | Ignition UDT | Purpose |
|---|---|---|---|---|
| Common core | `PL_Core` (internal) | `PL_Base` | `PL_Base` (abstract parent) | Mode, command decode, interlock/permissive, first-out, bypass, reset, sim gating |
| Analog input | `PL_Ain` | `PL_Ain_HMI` | `PL_Ain` | Scaling, filter, HH/H/L/LL, NAMUR bad-signal, sim |
| Discrete input | `PL_Din` | `PL_Din_HMI` | `PL_Din` | Debounce, alarm state, sim |
| Discrete valve | `PL_DVlv` | `PL_DVlv_HMI` | `PL_DVlv` | On/off air-operated valve. SY3000 single solenoid, double solenoid or 3-position. Limit switches optional: none (default), open only, closed only, or both |
| **Valve bank** | `PL_VBank` | `PL_VBank_HMI` | `PL_VBank` | SMC SI unit + SY3000 manifold. Coil image packing, comm/air/power health, station map. EtherNet/IP or Modbus TCP |
| Motor (fixed speed) | `PL_Mtr` | `PL_Mtr_HMI` | `PL_Mtr` | Across-the-line or soft starter. Maintained or 3-wire pulse outputs |
| VFD motor | `PL_Vfd` | `PL_Vfd_HMI` | `PL_Vfd` | Drive-agnostic speed-controlled motor |
| PowerFlex 525 adapter | `PL_PF525_Adp` | – | – | Maps `PL_Vfd` ⇄ the PF525 EtherNet/IP I/O (Logic Command/Status, speed ref/feedback, Datalinks). Other drive families can get their own adapter later |
| Analog valve | `PL_AVlv` | `PL_AVlv_HMI` | `PL_AVlv` | Positioned control valve, 4–20 mA output, optional position feedback |
| PID loop | `PL_Pid` | `PL_Pid_HMI` | `PL_Pid` | Wraps the Control Expert `PIDFF` block. Adds Man/Auto/Cas, SP limits/ramp, bumpless transfer, alarms |
| Global | – | `PL_Global` | `PL_Global` | Site sim permit, PLC↔HMI heartbeat |
| Helper | `PL_Pack16` | – | – | 16 BOOL → WORD, inputs default TRUE. Used to build interlock and permissive words in FBD |

### 2.2 Later candidates (not in v1)

Motor-operated valve (open/close/stop with torque switches), 2-speed and reversing starters, duty/standby/rotation,
totalizer, analog output, sequence/phase interface (ISA-88-style), dosing pump.

---

## 3. Naming conventions

| Thing | Convention | Example |
|---|---|---|
| Library prefix | `PL_` (may change later, see below) | |
| DFB type | `PL_<Type>` | `PL_DVlv` |
| HMI DDT type | `PL_<Type>_HMI` | `PL_DVlv_HMI` |
| Sub-structure DDTs | `PL_<Type>_Cfg`, `_Val`, `_Sts`, `_Alm` | `PL_DVlv_Alm` |
| DFB instance | Device tag, ISA-5.1 | `XV_1001`, `P_2001`, `FIC_3001` |
| HMI variable | `<Instance>_HMI` | `XV_1001_HMI` |
| Valve bank instance | `VB_<n>` | `VB_101`, `VB_101_HMI` |
| Ignition UDT instance | `<System>/<Area>/<Instance>` | `[default]Sys1/Area100/XV_1001` |
| Members | PascalCase, units suffix when not obvious | `TravelTmo_s`, `SpdRef`, `RunHrs` |

**Keeping the prefix changeable:** the prefix appears **only in type names**, never in member names, variable
instance names, OPC paths or Ignition tag paths. Renaming it later is then a mechanical find/replace across the
`.xdb`/`.xdd` exports, the UDT JSON and the view resources, with zero change to live tag paths. A
`tools/rename_prefix` script will be part of Phase 5.

Control Expert names are case-insensitive. OPC UA and Ignition paths are case-sensitive, so case must be kept
consistent everywhere. Names may be at most 32 characters.

---

## 4. Architecture

```
 Field                        M580 (one system)                                   Ignition
 ─────                        ─────────────────                                   ────────
 X80 DI/AI (limit sw,  ──►  ┌────────────────────────────────────────────┐
 transmitters, aux)         │ MAST task (periodic, 50–100 ms)            │
                            │                                            │
                            │  PL_Pack16 ──Intlk/Perm WORDs──┐           │
                            │  program logic ─PCmd/PCV/PSpd──┤           │
                            │                                ▼           │
                            │   PL_DVlv XV_1001 ──OutA/OutB──► VB_101    │
                            │     │IN_OUT                     │PL_VBank  │──► SMC SI unit (EIP or Modbus TCP)
                            │   XV_1001_HMI          Healthy ◄┘          │
                            │                                            │
                            │   PL_Vfd P_2001 ◄─► PL_PF525_Adp           │◄─► PowerFlex 525 (EtherNet/IP)
                            │     │IN_OUT                                │
                            │   P_2001_HMI                               │
                            │                                            │
                            │  only *_HMI + PL_Global exposed ───────────┼──► BMENUA0100 ──OPC UA──► UDTs
                            └────────────────────────────────────────────┘                           │
                                                                                     Perspective icons + faceplates
```

### 4.1 Execution rules

- Call every library DFB **unconditionally, every scan**. Never call one inside an `IF` or in a section that is
  conditionally executed, because timers and edge detection depend on it.
- Use **MAST, periodic**, 50 ms or 100 ms. PID loops must run in a periodic task.
- **Order matters for Ethernet I/O:**
  1. Drive and bank adapters' *input* side.
  2. Device DFBs.
  3. Bank and drive adapters' *output* side, last.

  That way a command reaches the network in the same scan. Each adapter is split into an `…_In` call and an `…_Out`
  call, or called once at the end with the previous scan's status (to be decided in Phase 2; one scan of latency is
  usually acceptable).
- Make each device's DFB call the **only** writer of its `_HMI` variable.
- Set **I/O fallback** to match each device's fail state:
  - X80 modules: fallback configuration.
  - SMC SI units: the *output on comm error* setting (§6.2.2).
  - Drives: the comm-loss fault response.

### 4.2 OPC UA exposure and sizing (one BMENUA0100 per system)

- Enable the **data dictionary** in Project Settings.
- Expose only the `*_HMI` variables and `PL_Global` (use the HMI-variable filter if used). *(Verify the exact
  CE 16.2 setting name in Phase 1.)*
- Use security policy `Basic256Sha256` with Sign & Encrypt. Trust Ignition's client certificate explicitly.
- In Ignition, create **one OPC UA connection per system**. The UDT parameter `OpcServer` selects it.
- **Sizing:** systems have 1–20 devices. Even at about 50 members per device, that is ~1,000 monitored items per
  BMENUA0100, which is well within what an embedded OPC UA server is designed for. *(Phase 1: still confirm against
  the BMENUA0100 user guide limits.)* No leased-group tricks are needed, so it's kept simple with two tag groups:

| Tag group | Mode | Members |
|---|---|---|
| `PL_Fast` | Direct, 500 ms | Everything except `Cfg.*` |
| `PL_Slow` | Direct, 2 s | `Cfg.*` |

  A third *leased* group can be added later if a system ever grows well beyond 20 devices.

- Interlock, permissive and bypass status are **BOOL arrays** (`ARRAY[0..15] OF BOOL`). Each array is one OPC UA
  item and one Ignition array tag, and is still readable element by element in an animation table. *(Verify
  BMENUA0100 publishes arrays inside DDTs. The fallback is 16 named BOOLs.)*
- *(Phase 1: confirm whether BMENUA0100 must sit in the main local rack.)*

### 4.3 Known Control Expert gotchas this design addresses

| Gotcha | Mitigation |
|---|---|
| A full download overwrites values written from the HMI with the project's **initial values** | §10 config persistence |
| Changing a DDT or DFB interface used by running instances may not be possible online | Keep HMI DDTs stable and version DFBs (§11). Interface changes are planned as stop-and-download events *(confirm online-modification limits in Phase 1)* |
| Bit access on unlocated `WORD` (`MyWord.3`) needs a project setting | Enable "bit extraction of INT/WORD" in Project Settings, or use shift/mask code inside the DFBs. Only `PL_Pack16`, the Intlk/Perm pins and the adapters touch words now |
| Passing an element of an `IN_OUT` (`Hmi.Base`) on to a nested DFB's `IN_OUT` | *Verify in Phase 1.* Fallback: copy-in/copy-out inside the parent DFB |
| `TIME` members appear as raw Int32 ms over OPC UA | HMI-facing durations are `REAL` seconds (`_s` suffix) |
| `EBOOL` in DDTs | DDT members use `BOOL` |
| Modbus TCP word byte order differs from the EtherNet/IP byte image | Adapters have a `Cfg.SwapBytes` / mapping option so the coil or bit order is the same for both transports (§6.2.2) |

---

## 5. Common base (`PL_Base` DDT + `PL_Core` DFB)

Every `PL_<Type>_HMI` has these members, in this order:

1. `Base : PL_Base`
2. `Sts`-like device status, `DevSts : PL_<Type>_Sts`
3. `Alm : PL_<Type>_Alm`
4. `Val : PL_<Type>_Val`
5. `Cfg : PL_<Type>_Cfg`

Every `PL_<Type>_Alm` starts with `IOFlt` and `IntlkTrip`, so the base UDT can define those two alarms once.

### 5.1 `PL_Base` members

| Member | Type | Dir | Description |
|---|---|---|---|
| `Cmd` | INT | HMI→PLC | Operator command register (§5.3). The PLC clears it to 0 after processing |
| `CmdRsp` | INT | PLC→HMI | Result of the last command (§5.4) |
| `Mode` | INT | PLC→HMI | Current mode (§5.2) |
| `State` | INT | PLC→HMI | Device state enum, device-specific. Drives the icon |
| `PCmdSts` | INT | PLC→HMI | What the program is requesting right now (1 = open/run, 2 = close/stop, 0 = none). Shown on the faceplate before the operator selects Auto |
| `Sts` | PL_Sts | PLC→HMI | Summary status BOOLs (§5.5) |
| `IntlkOK` | ARRAY[0..15] OF BOOL | PLC→HMI | Live interlock conditions, **TRUE = OK** |
| `IntlkFO` | INT | PLC→HMI | First-out: the index of the first interlock to drop, −1 = none. Cleared on reset |
| `PermOK` | ARRAY[0..15] OF BOOL | PLC→HMI | Live permissives, TRUE = OK |
| `Byp` | ARRAY[0..15] OF BOOL | PLC→HMI | Interlocks currently bypassed |
| `BypRemain_s` | REAL | PLC→HMI | Time left before the bypass auto-expires |

### 5.2 Modes (`Mode`)

| Value | Mode | Who drives the device | Notes |
|---|---|---|---|
| 1 | **Out of Service** | Nobody. Outputs at fail state | Commands rejected except "→ Manual". Ignition suppresses the device's alarms. Supervisor role |
| 2 | **Maintenance** | Operator | Same as Manual for the PLC. Ignition suppresses process alarms (not `IOFlt`) and shows an "M" badge. The program cannot force it to Auto. Supervisor role |
| 3 | **Manual** | Operator | |
| 4 | **Auto** | Program (`PCmd*` / `PCV` / `PSpdRef` inputs) | |
| 5 | **Cascade** | Remote SP | `PL_Pid` only |
| 6 | **Local** | Field (HOA in Hand, local station) | Entered automatically when the `Local` input is TRUE. The PLC tracks the device and does not drive it. On exit, goes to `Cfg.LocalExitMode` (default **Manual**) |

- Auto ↔ Manual: Operator, unless the `ModeLock` input is TRUE.
- Manual → Maintenance / Out of Service and back: Supervisor.
- **Bumpless transfer.** Going Auto→Manual, the device holds its state or output. Going Manual→Auto, it follows the
  program immediately, which is why the faceplate shows `PCmdSts`.
- First scan / cold start: the device starts in `Cfg.InitMode`. Defaults are Manual for motors and Auto for valves
  (Q3).

### 5.3 Command codes (`Cmd`), shared by all objects

| Code | Command | Code | Command |
|---|---|---|---|
| 0 | none | 20 | Interlock bypass ON (`Cfg.BypMask` ∧ DFB `IntlkBypMask`) |
| 1 | Open / Start / Run fwd | 21 | Interlock bypass OFF |
| 2 | Close / Stop | 30 | Simulation ON (only if `PL_Global.SimPermit`) |
| 3 | Reset (trips, first-out, latched alarms) | 31 | Simulation OFF |
| 4 | Run reverse (VFD) / Hold mid-position (3-position valve) | 40 | Reset counters |
| 10 | Mode → Auto | 50 | Capture stroke-time baseline |
| 11 | Mode → Manual | | |
| 12 | Mode → Maintenance | | |
| 13 | Mode → Out of Service | | |
| 14 | Mode → Cascade | | |

Analog operator values are written directly to their own REAL members (`Val.OCV`, `Val.OSpd`, `Val.OSP`,
`Val.OOut`). The DFB uses them only in the appropriate mode and clamps them to limits. Roles are enforced in
Ignition. The PLC enforces state rules (mode, interlock, permissive).

### 5.4 Command response (`CmdRsp`)

`0` OK · `1` rejected: wrong mode · `2` rejected: interlock · `3` rejected: permissive · `4` rejected: fault latched,
reset first · `5` rejected: not allowed by config · `6` unknown code

### 5.5 Summary status (`Base.Sts : PL_Sts`)

| Member | Meaning | Member | Meaning |
|---|---|---|---|
| `Ready` | No interlock, permissives OK, no fault, available | `Sim` | Simulation active |
| `Active` | Open / running / output > 0 | `Byp` | Any bypass active |
| `Inactive` | Closed / stopped | `Local` | Field control |
| `Transit` | Moving / starting / stopping | `ModeLocked` | Program holds mode |
| `Intlkd` | Any interlock not OK | `PCmdOn` | Program command active |
| `PermNOK` | Any permissive not OK | `CmdRej` | Last command rejected (held 5 s) |
| `Tripped` | Fault latched, needs reset | `AnyAlm` | Any `Alm.*` TRUE |

### 5.6 Interlocks vs. permissives

| | Permissive (`Perm`) | Interlock (`Intlk`) |
|---|---|---|
| When checked | Only to **start / open / move away from fail state** | **Always** |
| On loss | Nothing happens if already running | Drive to fail state. Set `Alm.IntlkTrip` and first-out |
| Bypass | Allowed in Maintenance (`Cmd 20`), Supervisor | Only bits enabled in the DFB input `IntlkBypMask` (decided in code), Supervisor, auto-expires after `Cfg.BypTime_s` |
| After clearing | – | `Cfg.IntlkLatch` TRUE: needs Reset (default for motors). FALSE: in Auto, the device resumes following the program (default for valves) |

- **DFB pins** are `WORD`, 1 = OK, default `16#FFFF`. A WORD keeps the block to one pin instead of 16, and
  `PL_Pack16` builds it in FBD.
- **HMI members** are BOOL arrays (§5.1).
- The **text** for each condition lives in Ignition (§8.3).

### 5.7 Failure handling

`Cfg.FailAction`: `0` = alarm only, `1` = drive to fail state and latch. Defaults: valves `0`, motors and VFDs `1`.

### 5.8 Simulation

- `Cmd 30` is accepted only when `PL_Global.SimPermit = TRUE`.
- In sim, the DFB ignores field feedback and generates it:
  - Valves stroke over `Cfg.SimTravel_s`.
  - Motors confirm after 1 s.
  - VFD speed ramps.
  - AIN takes `Val.SimPV`.
- Physical outputs are still written unless `Cfg.SimOutputsOff = TRUE`.
- `Base.Sts.Sim` is set, and a "SIM" badge appears on the icon and faceplate.

---

## 6. Device specifications

**Bold** pins are required. The rest are optional with safe defaults. DDT tables list members beyond `Base`.

### 6.1 Discrete valve – `PL_DVlv`

The valve covers the SY3000 functions:

| `Cfg.ValveType` | SY3000 function | Coils | Fail state (loss of power or comm) |
|---|---|---|---|
| 1 | 2-position **single solenoid** | A | Spring return: closed (`Cfg.FailOpen = FALSE`) or open (`TRUE`) |
| 2 | 2-position **double solenoid** | A (open), B (close) | **Holds last position** (detented spool). Fail-in-place |
| 3 | 3-position **closed / exhaust / pressure center** | A (open), B (close) | Spring-centred → mid position (actuator held, exhausted or pressurized depending on center type) |

- **Double and 3-position valves** never energize both coils; the DFB enforces this. `Cfg.CoilPulse_s` = 0 keeps the
  active coil maintained (recommended for SY3000 against vibration). A value > 0 pulses the coil and then drops it.
- With 3-position valves, `Cmd 4` = Hold (both coils off → centre). Interlock action for 3-position valves is
  `Cfg.IntlkAction`: 0 = centre, 1 = close, 2 = open.
- Fail-in-place valves (type 2) **cannot be driven to a safe state by loss of comm.** The faceplate shows this, and
  the I/O-fault alarm text says so. If a valve must go to a defined position on comm loss, it must be type 1 or 3.
  This is an engineering choice made in the valve selection (see the note in §6.2.2).

#### Limit switches are optional

Most valves have no limit switches, but any valve can get them later with **no code or HMI change**: wire the
input, set `Cfg.HasZSO` and/or `Cfg.HasZSC`, done. The pins default to FALSE, and the default config is no switches.

| `HasZSO` / `HasZSC` | Position shown | Opening/Closing state | Fail-to-open/close, position-lost, stroke time |
|---|---|---|---|
| none / none (default) | **Commanded** position. `DevSts.PosConfirmed = FALSE` | Shown for `Cfg.TravelTime_s` (nominal stroke) after a command, so the icon animates the same way | Not available. These alarms are never raised, and the Maint tab hides stroke data |
| one switch | Confirmed at the switched end, inferred at the other end after `TravelTime_s` | Ends when the switch makes (or the timer expires at the unswitched end) | Fail-to-reach only for the switched end. Position-lost only for the switched end |
| both | Confirmed at both ends | Ends when the switch makes | All available. `TravelTmo_s` is the fail timeout |

- An unconfirmed position is drawn the same as a confirmed one, but with a small neutral "≈" marker on the icon and
  "Open (cmd)" text on the faceplate. That way the operator always knows whether the plant or the PLC is the source.
- `Alm.IOFlt` still works without switches, because it comes from the bank (comm/air/power).
- Interlocks that need a *proven* valve position (e.g. "XV-1001 proven closed") should use `XV_1001.IsClosed`
  **and** `XV_1001_HMI.DevSts.PosConfirmed`. The `IsClosedPrv` output combines both.

**DFB inputs:** `ZSO` BOOL(FALSE), `ZSC` BOOL(FALSE), `IOFlt` BOOL (normally `NOT VB_xxx.Healthy` OR the
limit-switch channel fault), `Intlk` WORD(FFFF), `Perm` WORD(FFFF), `IntlkBypMask` WORD(0), `PCmdOpen` BOOL (Auto: TRUE = open,
level), `PCmdHold` BOOL (3-position only), `ModeLock`, `Local`, `Reset`
**DFB outputs:** `CoilA` BOOL, `CoilB` BOOL (wired to the valve bank's coil image), `IsOpen`, `IsClosed` (confirmed
or commanded), `IsOpenPrv`, `IsClosedPrv` (proven by a switch only), `Ready`, `Fault`
**IN_OUT:** **`Hmi`** : `PL_DVlv_HMI`

`PL_DVlv_HMI`:

| Member | Type | Notes |
|---|---|---|
| `Base` | PL_Base | `State`: 0 Unknown, 1 Closed, 2 Opening, 3 Open, 4 Closing, 5 Mid (3-pos hold), 8 Travel fault, 9 Limit conflict |
| `DevSts.ZSO`, `.ZSC` | BOOL | Limit switches (after sim substitution). FALSE when not configured |
| `DevSts.PosConfirmed` | BOOL | Current position is proven by a switch |
| `DevSts.CoilA`, `.CoilB` | BOOL | Outputs |
| `DevSts.CmdOpen` | BOOL | Resolved open command (any mode) |
| `DevSts.Opening`, `.Closing` | BOOL | |
| `DevSts.FailInPlace` | BOOL | Type 2. Faceplate warning |
| `Alm.IOFlt` | BOOL | Bank comm / air / power fault, or limit-switch channel fault |
| `Alm.IntlkTrip` | BOOL | |
| `Alm.FailOpen` / `Alm.FailClose` | BOOL | Travel timeout |
| `Alm.PosLost` | BOOL | Left position without a command |
| `Alm.LimitConflict` | BOOL | ZSO and ZSC both on |
| `Alm.StrokeDegr` | BOOL | Last stroke > `StrokeRef_s × Cfg.StrokeDegr` (diagnostic priority) |
| `Cfg.ValveType` | INT | 1/2/3 above |
| `Cfg.HasZSO`, `Cfg.HasZSC` | BOOL | Default FALSE. See "Limit switches are optional" above |
| `Cfg.TravelTime_s` | REAL | Nominal stroke, used for the Opening/Closing display and to infer position without a switch |
| `Cfg.FailOpen` | BOOL | Type 1 only |
| `Cfg.CoilPulse_s`, `Cfg.IntlkAction` | REAL, INT | Types 2/3 |
| `Cfg.TravelTmo_s`, `Cfg.StrokeDegr` | REAL | Only used with switches |
| `Cfg.FailAction`, `IntlkLatch`, `InitMode`, `LocalExitMode`, `BypMask`, `BypTime_s`, `SimTravel_s`, `SimOutputsOff` | | Common |
| `Val.StrokeOpen_s`, `Val.StrokeClose_s`, `Val.StrokeRef_s` | REAL | Trend for valve health. Only valid with both switches |
| `Val.Cycles` | DINT | |

### 6.2 Valve bank – `PL_VBank`

#### 6.2.1 Purpose

Each SY3000 manifold with its SMC Ethernet SI unit is one `PL_VBank` instance. It:

- collects the coil commands from all `PL_DVlv` instances on the bank and packs them into the SI unit's output image
  in station/coil order;
- normalizes the image between EtherNet/IP and Modbus TCP, so swapping transport doesn't change any valve code;
- derives `Healthy` from comm freshness, the SI unit's diagnostics, and an optional bank air-pressure switch. Every
  valve on the bank uses it for `IOFlt`;
- publishes a bank faceplate showing which station or coil belongs to which valve tag.

**DFB inputs:** **`Coil`** : `ARRAY[0..31] OF BOOL` (written by the valve calls), **`CommOK`** BOOL (EtherNet/IP
connection *freshness* or Modbus scanner health from the DTM device DDT), `DiagIn` WORD (SI unit status/diagnostic
input data, if the unit/transport provides it), `AirOK` BOOL(TRUE) (optional manifold supply pressure switch,
wired to X80 DI), `PwrOK` BOOL(TRUE) (valve power supply monitor, if available)
**DFB outputs:** `OutImg` : `ARRAY[0..1] OF WORD` (map onto the device DDT output area), `Healthy` BOOL
**IN_OUT:** **`Hmi`** : `PL_VBank_HMI`

`PL_VBank_HMI` (no `Base`: banks have no modes or commands, apart from the faceplate reading them):

| Member | Type | Notes |
|---|---|---|
| `Sts.Healthy`, `.CommOK`, `.AirOK`, `.PwrOK` | BOOL | |
| `Sts.Coil` | ARRAY[0..31] OF BOOL | Live coil image |
| `Alm.CommFlt` | BOOL | High priority. One alarm per bank, not per valve, to avoid floods |
| `Alm.AirLow`, `Alm.PwrFlt`, `Alm.Diag` | BOOL | |
| `Cfg.Transport` | INT | 1 EtherNet/IP, 2 Modbus TCP (informational and selects the default mapping) |
| `Cfg.SwapBytes` | BOOL | Normalizes Modbus register byte order to the EtherNet/IP coil order |
| `Cfg.Stations` | INT | |
| `Cfg.DoubleWiring` | BOOL | Manifold wiring spec: double wiring = 2 coils per station regardless of valve type |

Valves on a bank have their **`IOFlt` alarm suppressed while the bank's `CommFlt` is active**. The operator gets one
bank alarm, and each valve still shows the I/O-fault state on its icon. In Ignition this is the valve alarm's enabled
expression.

#### 6.2.2 SMC specifics to confirm in Phase 2

- **SI unit:** SMC **EX260**, an output-only SI unit (16 or 32 outputs depending on variant).
  - EtherNet/IP variant: added in the Control Expert DTM browser from SMC's EDS.
  - Modbus TCP variant: added as a Modbus TCP device with I/O scanning.

  *Phase 2:* get the EDS and Modbus register map for the exact variants used (`docs/vendor/`). Then confirm:
  - output image size and coil order;
  - whether any status/diagnostic input data exists for `DiagIn` (if not, `DiagIn` stays 0 and `Alm.Diag` is unused);
  - the Modbus register byte order that `Cfg.SwapBytes` corrects.
- **Output behaviour on comm error:** SMC SI units have a HOLD/CLEAR setting. The library standard is **CLEAR (all
  outputs off)**, so single-solenoid and 3-position valves go to their spring state. This must be set on every unit,
  and it goes in the commissioning checklist.
- **Coil/bit mapping:**
  - On a *double-wiring* manifold, station *n* uses bits 2n (A) and 2n+1 (B).
  - On *single wiring*, each station uses one bit.

  `PL_VBank` encapsulates this. Valve calls write `Coil[]` by station and coil letter using a small helper
  convention: `VB_101_Coil[2*Stn+0]` for A and `[2*Stn+1]` for B.
- **Limit switches:** the EX260 is output-only. When a valve does get switches, they come from X80 DI (or another
  input device). The valve DFB doesn't care where; their channel fault goes into the valve's `IOFlt`.

#### 6.2.3 Call pattern

```iecst
(* --- valves on bank VB_101 --- *)
XV_1001(IOFlt := NOT VB_101.Healthy,          (* no limit switches: ZSO/ZSC left unconnected *)
        Intlk := XV_1001_Ilk.Out, PCmdOpen := Seq100.Fill,
        Hmi := XV_1001_HMI);
VB_101_Coil[0] := XV_1001.CoilA;             (* station 0 *)
VB_101_Coil[1] := XV_1001.CoilB;

(* --- bank, called after all its valves --- *)
VB_101(Coil := VB_101_Coil,
       CommOK := VB_101_EIP.Freshness,        (* name from the DTM device DDT *)
       AirOK  := DI_PSL_VB101,
       Hmi    := VB_101_HMI);
VB_101_EIP.Outputs := VB_101.OutImg;          (* exact member/area per device DDT, Phase 2 *)
```

### 6.3 Motor – `PL_Mtr`

**DFB inputs:** **`RunFbk`** BOOL, `Ovld` BOOL, `Avail` BOOL(TRUE), `Local` BOOL, `IOFlt`, `Intlk`, `Perm`,
`IntlkBypMask`, `PRun` BOOL (Auto, level), `ModeLock`, `Reset`
**DFB outputs:** `RunOut` (maintained), `StartPls`, `StopPls` (3-wire), `Running`, `Ready`, `Fault`

`PL_Mtr_HMI`:

| Member | Type | Notes |
|---|---|---|
| `Base` | PL_Base | `State`: 1 Stopped, 2 Starting, 3 Running, 4 Stopping, 5 Tripped |
| `DevSts.RunFbk`, `.RunOut`, `.Ovld`, `.Avail`, `.RestartInh`, `.StartsLim` | BOOL | |
| `Alm.IOFlt`, `.IntlkTrip` | BOOL | Common |
| `Alm.FailStart`, `.FailStop`, `.UnexpStop`, `.Ovld`, `.NotAvail`, `.StartsExceeded`, `.NotRemote` | BOOL | `NotRemote` = in Auto with demand but HOA not in Auto (low priority) |
| `Cfg.FbkPresent`, `StartTmo_s`, `StopTmo_s`, `PulseOut`, `Pulse_s`, `MaxStartsHr`, `RestartDly_s` | | |
| `Cfg.FailAction`, `IntlkLatch`, `InitMode`, `LocalExitMode`, `BypMask`, `BypTime_s`, `SimOutputsOff` | | Common |
| `Val.RunHrs` (REAL), `Val.Starts` (DINT), `Val.StartsLastHr` (INT), `Val.RestartRemain_s` (REAL) | | |

### 6.4 VFD motor – `PL_Vfd` + drive adapter

`PL_Vfd` stays **drive-agnostic**: it works in engineering units and plain BOOLs. The **PowerFlex 525** specifics live
in `PL_PF525_Adp`, so a different drive family later only needs a new adapter. The DDT, UDT and faceplate stay the
same.

**`PL_Vfd` inputs:** everything in `PL_Mtr` except `RunFbk`/`Ovld`, plus **`DrvRunning`**, **`DrvFault`**,
`DrvReady`, `DrvFaultCode` INT, `AtSpeed`, **`SpdFbk`** REAL (EU), `Current` REAL, `Power` REAL, **`CommFlt`**,
`PSpdRef` REAL, `PRev` BOOL
**Outputs:** `RunFwd`, `RunRev`, `SpdRef` REAL (EU, clamped and ramped), `FltResetOut` (pulse), `Running`,
`Ready`, `Fault`

`PL_Vfd_HMI` = everything in `PL_Mtr_HMI` (the `Alm.Ovld` alarm is replaced by `Alm.DrvFault`), plus:

| Member | Type | Notes |
|---|---|---|
| `DevSts.DrvReady`, `.DrvRunning`, `.AtSpeed`, `.Rev`, `.STOActive` | BOOL | |
| `Alm.CommFlt`, `Alm.SpdDev` | BOOL | |
| `Cfg.SpdMin`, `SpdMax`, `SpdEUFull`, `Ramp_EUs`, `RevAllowed`, `SpdDevLim`, `SpdDevDly_s` | | Speed is in Hz (PF525 native). `SpdEUFull` default 60.0 |
| `Cfg.HasDiag` | BOOL | TRUE on EtherNet/IP (current, power and fault code available). FALSE when hardwired |
| `Val.OSpd` | REAL | Operator speed, used in Manual. Tracks `SpdRef` in Auto for bumpless transfer |
| `Val.SpdRef`, `SpdFbk`, `Current`, `Power` (REAL), `FaultCode` (INT) | | `FaultCode` → text via a per-family dataset in Ignition |

#### 6.4.1 PowerFlex 525 – what the library uses

| PF525 capability | Used for |
|---|---|
| Embedded EtherNet/IP port, implicit I/O (EDS added in the Control Expert DTM browser) | Control and status every RPI. `CommFlt` = NOT connection freshness from the device DDT |
| **Logic Command** word | Stop, Start, Clear Faults, Forward/Reverse. Built by the adapter |
| **Speed Reference** (Hz × 100) | `SpdRef` EU → INT in the adapter |
| **Logic Status** word | Ready, Active (running), Faulted, At Reference, actual direction, and (where provided) local/network control |
| **Output Frequency** feedback (Hz × 100) | `SpdFbk` |
| **Datalinks** (4 in / 4 out, configured by drive parameters) | Default input Datalink assignment: **Output Current**, **Output Power**, **Fault 1 Code**, **DC Bus Voltage**. Output Datalinks are unused by default |
| Embedded **Safe Torque Off** | STO state is shown on the faceplate (via a Datalink or a hardwired DI). It is never controlled by the library |
| Comm-loss and PLC-idle fault actions (EN Comm Flt Actn / EN Idle Flt Actn) | Library standard: **Fault** (drive stops) on both. This goes in the commissioning checklist |
| Start Source / Speed Reference parameters | Set to EtherNet/IP. The keypad or terminal block as a start source counts as **Local** (`Local` input / Local mode) |

*Phase 3:* confirm bit positions, Datalink parameter numbers and fault-action parameter names against the PF525 user
manual and the EDS revision in use. These are design-level assumptions.

**`PL_PF525_Adp`**

- **Inputs:** `RunFwd`, `RunRev`, `SpdRef` (Hz), `FltReset` (from `PL_Vfd`); the device DDT input assembly (Logic
  Status, Output Freq, Datalinks); `Freshness`.
- **Outputs:** Logic Command and Speed Reference (written to the device DDT output assembly); `DrvReady`,
  `DrvRunning`, `DrvFault`, `AtSpeed`, `SpdFbk`, `Current`, `Power`, `DrvFaultCode`, `CommFlt`, `STOActive` (into
  `PL_Vfd`).
- It drives a stop when `RunFwd` = `RunRev` = FALSE, never sets both directions, and pulses Clear Faults for 500 ms.
- **Fault text:** Ignition dataset `PF525_FaultCodes` (code → text), shared by every PF525 instance.

#### 6.4.2 Comms fallback for the PF525

The PF525 has no native **Modbus TCP**. Its embedded network port is EtherNet/IP, and its other built-in port is
RS-485 Modbus **RTU**. If EtherNet/IP isn't available, the supported fallbacks are:

1. **Dual-port EtherNet/IP option card (25-COMM-E2P).** This is still EtherNet/IP, so the adapter is unchanged.
   *Recommended* if the issue is network topology rather than protocol.
2. **Hardwired.** Run, direction and fault reset go to X80 DO, speed reference to X80 AO, and Running / Faulted / At
   speed come back on DI, with speed feedback on AI. `PL_Vfd` is used **without an adapter**, and its pins are mapped
   directly to I/O. `Current`, `Power` and the fault code are then unavailable, and the faceplate hides them
   (`Cfg.HasDiag = FALSE`).
3. **Modbus RTU** through an RS-485 serial module or gateway. This is possible but not planned for v1; it would be a
   second adapter `PL_PF525_RTU_Adp`.

Please confirm option 1 or 2 is acceptable (Q8b).

### 6.5 Analog (positioned) valve – `PL_AVlv`

**DFB inputs:** `PCV` REAL (Auto %, e.g. `PL_Pid.Out`), `PosFbk` REAL, `PosFbkFlt` BOOL, `IOFlt`, `Intlk`,
`IntlkBypMask`, `Local`, `ModeLock`, `Reset`
**DFB outputs:** `CV` REAL (%), `OutRaw` INT (X80 AO), `Ready`, `Fault`

| Member | Type | Notes |
|---|---|---|
| `Base` | PL_Base | `State`: 1 Closed (≤ cutoff), 2 Throttling, 3 Full open, 5 Fail position |
| `DevSts.AtMin`, `.AtMax`, `.RateLimited`, `.CutoffActive` | BOOL | |
| `Alm.IOFlt`, `.IntlkTrip`, `.PosDev`, `.FbkBad` | BOOL | |
| `Cfg.OutMin`, `OutMax`, `Rate_pcts`, `FailPos`, `Cutoff`, `Reverse`, `RawMin`, `RawMax`, `FbkPresent`, `DevLim`, `DevDly_s` | | |
| `Val.OCV` | REAL | Operator %, tracks CV in Auto |
| `Val.CV`, `PosFbk`, `Dev` | REAL | |

### 6.6 PID loop – `PL_Pid`

Wraps the Control Expert **`PIDFF`** EFB (CONT_CTL library). *Exact parameter names are confirmed in Phase 4.*

**DFB inputs:** **`PV`** REAL, `PVBad` BOOL, `CasSP` REAL, `FF` REAL, `OutRbk` REAL, `DownstreamNotAuto` BOOL,
`TrkEn` BOOL + `TrkVal` REAL, `Intlk`, `ModeLock`
**DFB outputs:** `Out` REAL, `InitPri` BOOL + `InitVal` REAL (cascade initialization), `Ready`

| Member | Type | Notes |
|---|---|---|
| `Base` | PL_Base | Modes: Out of Service, Manual, Auto, Cascade. `State`: 1 Man, 2 Auto, 3 Cas, 4 Tracking, 5 Initializing, 6 PV bad |
| `DevSts.Tracking`, `.Initializing`, `.OutHiLim`, `.OutLoLim`, `.SPRamping` | BOOL | |
| `Alm.IOFlt` (PV bad), `.IntlkTrip`, `.DevHi`, `.DevLo`, `.OutSat` (diagnostic), `.OffNormal` | BOOL | `OffNormal` = mode ≠ `Cfg.NormMode` (ISA-18.2) |
| `Cfg.Kp`, `Ti_s`, `Td_s`, `Reverse`, `PVMin`, `PVMax`, `OutMin`, `OutMax`, `SPMin`, `SPMax`, `SPRamp_EUs`, `SPTrackPV`, `Dband`, `DevLim`, `DevDly_s`, `PVBadAction`, `FailOut`, `NormMode` | | |
| `Val.PV`, `SP`, `Out`, `Err`, `CasSP` | REAL | |
| `Val.OSP`, `Val.OOut` | REAL | Operator SP (Auto) / output (Manual) |

**Linking pattern (loop → valve):**

```
AIN FT_3001 ──PV──► PL_Pid FIC_3001 ──Out──► PL_AVlv FCV_3001.PCV
                       ▲  OutRbk ◄──────────── FCV_3001.CV
                       └─ DownstreamNotAuto ◄─ FCV_3001_HMI.Base.Mode <> 4
```

### 6.7 Analog input – `PL_Ain`

**Inputs:** **`Raw`** INT, `ChFlt` BOOL · **Outputs:** `PV` REAL, `Bad`, `HH`, `H`, `L`, `LL` BOOL (delayed and
deadbanded, for interlocks)

| Member | Notes |
|---|---|
| `DevSts.Substituted`, `.Clamped` | |
| `Alm.IOFlt` (bad signal / channel fault), `.HH`, `.H`, `.L`, `.LL`, `.Roc` | (`IntlkTrip` present but unused) |
| `Cfg.RawMin/Max`, `EUMin/Max`, `Filt_s`, `HHLim`, `HLim`, `LLim`, `LLLim`, `HHEn`, `HEn`, `LEn`, `LLEn`, `AlmDB`, `AlmDly_s`, `BadLoRaw`, `BadHiRaw`, `BadAction`, `BadPV`, `RocLim_EUs` | NAMUR NE43 defaults |
| `Val.PV`, `RawEcho`, `SimPV` | |

### 6.8 Discrete input – `PL_Din`

**Inputs:** **`In`**, `ChFlt` · **Outputs:** `Out`, `Alarm` · `Alm.IOFlt`, `Alm.Active` ·
`Cfg.AlmState`, `AlmEn`, `Dly_s`, `Debounce_s`

### 6.9 Global – `PL_Global`

`SimPermit` BOOL (Engineer), `PlcHeartbeat` INT, `HmiHeartbeat` INT (gateway timer script), `HmiOK` BOOL,
`LibVer` INT. There is one per system.

---

## 7. Call-site example (interlocks)

```iecst
XV_1001_Ilk(In1 := NOT LT_2001.HH,     (* 0: Tank 2001 high-high   *)
            In2 := NOT ESD_Active,      (* 1: Area ESD              *)
            In3 := P_2001.Running);     (* 2: Pump must run         *)
                                        (* In4..In16 default TRUE   *)
```

The matching text rows in Ignition (`Text/IntlkDesc`) are 0: "LT-2001 Tank 2001 high-high", 1: "Area ESD active",
2: "P-2001 not running".

---

## 8. Ignition UDTs

### 8.1 Structure

```
PL_Base                       (parent, all commandable device UDTs inherit)
├─ Parameters:  OpcServer (per system), PlcVar ("XV_1001_HMI"), OpcNsPrefix, System, Area, Desc, HistProvider, EU
├─ Base/        OPC tags → {OpcNsPrefix}{PlcVar}.Base.*
│   Cmd, CmdRsp, Mode, State, PCmdSts, IntlkFO, BypRemain_s
│   IntlkOK, PermOK, Byp           (Boolean[] array tags)
│   Sts/  Ready, Active, Inactive, Transit, Intlkd, PermNOK, Tripped, Sim, Byp, Local, ModeLocked, PCmdOn, CmdRej, AnyAlm
├─ Alm/         IOFlt, IntlkTrip   (OPC BOOL tags, each with one alarm)
├─ Derived/     ModeText, StateText (expression + dataset lookup)
└─ Text/        IntlkDesc, PermDesc (Dataset[16]: Idx, Desc), StateMap

PL_DVlv  (parent = PL_Base)
├─ DevSts/  ZSO, ZSC, CoilA, CoilB, PosConfirmed, …
├─ Alm/     + FailOpen, FailClose, PosLost, LimitConflict, StrokeDegr
├─ Val/     StrokeOpen_s, StrokeClose_s, StrokeRef_s, Cycles  (history on strokes)
├─ Cfg/     … (PL_Slow)
└─ Params:  + Bank ("VB_101"), Station, used for the bank alarm suppression and faceplate link

PL_VBank (standalone)
└─ Sts/, Alm/, Cfg/, Text/StationMap (Dataset: Station, Coil, ValveTagPath)
```

- **OPC item path:** `OpcNsPrefix` + `PlcVar` absorbs the BMENUA0100 node-ID format. Browse one variable in each
  system once to confirm it.
- **Tag groups:** `PL_Fast`, `PL_Slow` (§4.2).
- **History:** on PVs, SP/Out, speed, current and stroke times. `HistProvider` is a parameter.
- **Bulk creation:** UDT instances come from a CSV instrument list (tag, type, system, area, desc, bank, station,
  interlock text) through `tools/csv_to_udt_instances`.

### 8.2 Alarm definitions

Each `Alm/*` member is an OPC BOOL tag with **one alarm, mode "Equal", setpoint 1**. Example for `PL_DVlv`:

| Tag | Default priority | Notes |
|---|---|---|
| `Alm/IOFlt` | High | Enabled only when the bank is healthy (see below). Not suppressed in Maintenance |
| `Alm/IntlkTrip` | Medium | Label includes the first-out description |
| `Alm/FailOpen`, `Alm/FailClose` | Medium | |
| `Alm/PosLost` | High | |
| `Alm/LimitConflict` | Low | |
| `Alm/StrokeDegr` | Diagnostic | Maintenance notification |

- **Enabled expression** (suppression by design):
  - All process alarms: `{[.]../Base/Mode} > 2` (not in Out of Service or Maintenance).
  - Valve `IOFlt`: `{[.]../Base/Mode} != 1 && !{[~]{System}/Banks/{Bank}/Alm/CommFlt}`.
- **Display path:** `{System}/{Area}/{InstanceName}`.
- **Label:** `{Desc} – Fail to open`.
- Priorities follow the site alarm philosophy (Q6). The values above are defaults that each instance can override.

### 8.3 Interlock and permissive text

`Text/IntlkDesc` is a 16-row dataset, editable on the Eng tab or loaded from the CSV. The faceplate builds one table
from `IntlkDesc` + `IntlkOK[]` + `IntlkFO` + `Byp[]`, with columns *index · description · OK / NOT OK · first-out ·
bypassed*.

---

## 9. Perspective faceplates

### 9.1 View organization

```
Library/
  Common/  StatusHeader, ModeBar, IntlkTable, AlarmPanel, CmdResponseToast, NumericEntry, QualityOverlay
  DVlv/    Icon, Faceplate
  VBank/   Icon (bank health), Faceplate (station map: click a station → valve faceplate)
  Mtr/ Vfd/ AVlv/ Pid/ Ain/ Din/   Icon, Faceplate
```

- Every view takes a single parameter, **`tagPath`**, and binds indirectly.
- **One popup function** for all types: `pl.faceplate.open(tagPath)` reads the instance `typeId` and opens
  `Library/<Type>/Faceplate` with popup id = `tagPath`.

### 9.2 Faceplate layout (discrete valve)

```
┌───────────────────────────────────────────────┐
│ XV-1001   Tank 2001 inlet valve        [x]    │
│ OPEN      MANUAL               ◆2 1 alarm     │  ← StatusHeader (◆2 = priority-2 shape + colour)
├───────────────────────────────────────────────┤
│ [Operate] [Interlocks] [Alarms] [Maint] [Eng] │
├───────────────────────────────────────────────┤
│ Mode:  [AUTO] [MANUAL]        Program: CLOSE   │
│                                               │
│        [  OPEN  ]      [ CLOSE ]      [RESET] │
│                                               │
│  ZSO ■   ZSC □    Coil A ■  Coil B □          │
│  Bank VB-101 / stn 3   Healthy                │
│  Last stroke: open 3.2 s / close 2.9 s        │
└───────────────────────────────────────────────┘
```

| Tab | Content | Role |
|---|---|---|
| Operate | Mode, commands, key values, setpoints | Operator |
| Interlocks | Interlock + permissive tables, first-out, bypass | View: all. Bypass: Supervisor |
| Alarms | This device's alarms, shelve | Operator (shelve: Supervisor) |
| Trend | Power Chart (AIN, AVlv, Vfd, Pid) | All |
| Maint | Counters, run hours, stroke times, Maintenance/Out of Service, counter reset | Supervisor |
| Eng | `Cfg/*`, SIM, interlock text, config backup/restore | Engineer |

### 9.3 Security

| Action | Operator | Supervisor | Engineer |
|---|:-:|:-:|:-:|
| Open/close/start/stop, setpoints, Auto/Manual, Reset | ✔ | ✔ | ✔ |
| Maintenance, Out of Service, bypass, shelve, counter reset | | ✔ | ✔ |
| Cfg edits, SIM, interlock text | | | ✔ |

- Roles are checked in the `enabled` binding and again in `pl.cmd.send()`, which writes, waits for `CmdRsp` and
  audits.
- Starting equipment, bypass and Out of Service need a confirmation dialog.

### 9.4 ISA-101 grey-scale style (decided)

All colours are defined once as theme variables and style classes under `PL/…`. No view hard-codes a colour.

| Element | Treatment |
|---|---|
| Background | Light neutral grey |
| Equipment outline | Dark grey |
| Normal state, active (open / running) | **Solid dark-grey fill** |
| Normal state, inactive (closed / stopped) | **Hollow / background fill**, dark outline |
| Transitioning | Half fill or dashed outline. Blink is never used for normal transitions |
| Process values | Dark text on grey. No colour when normal |
| Alarm, by priority | The **only saturated colours**: Critical/High red, Medium amber, Low yellow, Diagnostic blue/violet. Always paired with a **priority shape + number** next to the object, so colour is never the only cue. Unacknowledged = blinking indicator only, never the whole object |
| Interlocked / permissive not OK | Small neutral "I" / "P" glyph next to the icon. The faceplate gives details |
| Mode, Local, SIM, Bypass, Maintenance | Neutral text badges (`A`/`M`/`L`/`SIM`/`BYP`/`MNT`). `BYP` and `SIM` are outlined to stand out without alarm colours |
| Bad tag quality / comm loss | Dedicated *quality overlay* (light cross-hatch + "?"), distinct from alarm colours |

The exact hex values will be chosen in Phase 1 against the plant's control-room monitors and checked for
colour-blind contrast.

---

## 10. Configuration persistence

1. **Engineering procedure:** before any download, run **Update Init Values with Current Values** and save. This goes
   in the change checklist.
2. **Safety net:** a Gateway script snapshots every instance's `Cfg/*` to a database table, nightly and on every
   Engineer edit. The Eng tab offers "Compare PLC vs. snapshot" and "Restore".
3. **Optional:** a config checksum in `PL_Global`, with an Ignition alarm on an unexpected change.

---

## 11. Versioning, source control and testing

### 11.1 Versioning

- Semver `LibVer` (in `PL_Global` and the Ignition base UDT).
  - **Major:** any HMI DDT member or DFB pin rename or type change.
  - **Minor:** added members or pins with safe defaults.
  - **Patch:** body-only changes.
- Distributed through a Control Expert **Types Library** (`.dtx`).

### 11.2 Repository layout (planned)

```
docs/                     this standard, alarm defaults, CSV templates, commissioning checklists (incl. SMC HOLD/CLEAR)
plc/
  ddt/                    *.xdd exports
  dfb/                    *.xdb exports (source of truth)
  src/                    *.st readable copies for review
  test/                   test project + procedures
ignition/
  udts/                   *.json UDT definitions
  perspective/Library/    view resources
  scripts/pl/             faceplate, cmd, cfg backup, csv import
  styles/                 PL/* style classes + theme variables
tools/                    csv_to_udt_instances, rename_prefix
```

### 11.3 Testing

- **PLC unit tests:** every DFB with sim ON, run through scripted scenarios: modes, every `Cmd`/`CmdRsp`, interlock
  trip and latch, first-out, bypass expiry, failure alarms, Local and bumpless transfer. For `PL_VBank`: coil
  packing for single- and double-wiring manifolds, byte swap, and comm-loss propagation to valves.
- **Integration:** use OFS against the Control Expert simulator, or a bench M580 + BMENUA0100 + one EX260 bank on
  EtherNet/IP *and* on Modbus TCP (to prove a transport swap needs no valve code change) + one PF525 on EtherNet/IP
  (including comm-loss and PLC-stop behaviour).
- **Acceptance:** a per-object checklist, signed before release.

---

## 12. Ignition 8.1 → 8.3 readiness

- UDTs and views are kept in `ignition/` from day one. 8.3 stores configuration as files, so the migration can go
  file-based.
- `HistProvider` is a parameter, so a historian change in 8.3 is one edit.
- Only `system.tag.readBlocking/writeBlocking` and `system.perspective.*`. No deprecated or internal APIs.
- Views depend only on their params, the project script library and style classes.
- Do a trial upgrade of a gateway backup on an 8.3 test gateway before go-live.

*8.3 specifics are planning assumptions and will be confirmed against the 8.3 upgrade guide in Phase 1.*

---

## 13. Delivery plan

| Phase | Content | Exit criteria |
|---|---|---|
| **0** | This spec + remaining answers in §14 | Spec approved (v1.0) |
| **1** | `PL_Base`/`PL_Core`, `PL_Pack16`, `PL_Global`, `PL_Ain`, `PL_Din`. Ignition base UDT, tag groups, Common views, `pl.*` scripts, ISA-101 style classes. Verify the CE and BMENUA0100 items in §4 | AIN/DIN pass the checklist through BMENUA0100 |
| **2** | `PL_DVlv` + `PL_VBank` end to end, on an EX260 bank over EtherNet/IP and Modbus TCP, valves with and without limit switches | Reviewed by you, then pattern frozen |
| **3** | `PL_Mtr`, `PL_Vfd`, `PL_PF525_Adp` | Checklist pass on a bench PF525 |
| **4** | `PL_AVlv`, `PL_Pid` incl. cascade and the loop↔valve linking | Checklist pass |
| **5** | CSV import, config backup/restore, rename-prefix tool, docs, `.dtx` release | v1.0 tag |

---

## 14. Open questions for review

**Answered:**

| # | Question | Answer |
|---|---|---|
| Q1 | Prefix | `PL_`. May change later, so it's kept rename-friendly (§3) |
| Q2 | Packed or BOOLs | Individual BOOLs |
| Q4 | OPC UA server / size | One BMENUA0100 per system. Systems have 1–10 (small) or 5–20 (large) devices |
| Q7 | Colours | ISA-101 grey scale |
| Q8 | Drives | Allen-Bradley PowerFlex 525, EtherNet/IP |
| Q14 | SI unit | SMC EX260, EtherNet/IP first, Modbus TCP fallback |
| Q15 | Limit switches | Mostly none. Must be a configurable option (§6.1) |

**Still open. The default shown is what I'll build if you don't say otherwise:**

| # | Question | Default if unanswered |
|---|---|---|
| Q3 | Mode set and initial modes | All 6 modes. Motors/VFDs start in Manual, valves in Auto |
| Q5 | I/O health source for X80 points | X80 channel/module error bits via topological addressing |
| Q6 | Alarm philosophy / priorities | The default priorities in §8.2 |
| Q8b | PF525 fallback when EtherNet/IP isn't available | Hardwired (option 2 in §6.4.2) |
| Q9 | SY3000 functions in use. Any valves not on SMC banks? | Library supports single, double and 3-position. Hardwired X80 DO solenoids also work, since `CoilA`/`CoilB` are just BOOLs |
| Q10 | Config persistence (§10), database on gateway? | Procedure + snapshot to the gateway's existing DB connection, if one exists |
| Q11 | Existing plant standard to match? | None |
| Q12 | Identity provider and role names | Ignition internal user source. Roles `Operator`, `Supervisor`, `Engineer` |
| Q13 | Starts/hr and restart delay in PLC? | In the PLC, disabled by default (`MaxStartsHr = 0`, `RestartDly_s = 0`) |
| Q16 | Bank air pressure / valve power monitoring | Optional `AirOK`/`PwrOK` pins, default TRUE (not monitored) |
