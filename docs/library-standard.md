# Process Device Library – Design Standard (DRAFT v0.1)

**Status:** Draft for review. Nothing in this repo has been built yet. This spec defines the shape of every object
first, so we can agree on it once before writing the DFBs, DDTs, UDTs and faceplates.

| Item | Target |
|---|---|
| PLC | Modicon M580, EcoStruxure Control Expert **16.2** |
| PLC languages | DFB bodies in ST; call sites in any language (FBD recommended for readability) |
| HMI | Ignition **8.1** Perspective, with **8.3** as the target in roughly 6 months |
| PLC ↔ HMI | OPC UA, symbolic (BMENUA0100, OFS, or Kepware). No located `%MW` blocks |

Open questions are collected in [§14](#14-open-questions-for-review). Please answer those before Phase 1 starts.

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
   mode, state, status, alarms, interlocks, permissives and bypass. A single shared Ignition base UDT and the common
   faceplate parts (mode bar, interlock list and so on) work for every device type.
4. **Operator commands use a single integer command register, not bits.** The HMI writes a command code, and the PLC
   executes it, writes a response code and clears the register. That avoids read-modify-write races on packed words
   and "stuck-on" command bits when a write is lost.
5. **Signals are named for their true meaning.** `Ovld = TRUE` means overloaded. Any wiring inversion (NC contacts)
   is done at the call site, never inside the DFB.
6. **The library contains no safety functions.** Interlocks here are process/equipment interlocks. SIS / safety
   functions stay hardwired or in a safety PLC. The library may *monitor* them.
7. **Every device is simulation-capable.** Each DFB can simulate its own feedback, so code and HMI can be FAT-tested
   with no I/O.
8. **Standards alignment.** Alarms follow ISA-18.2 practice (PLC-side delays and deadbands, rationalized priorities,
   suppression by design). The HMI follows ISA-101 (low-colour normal state, colour reserved for abnormal).

---

## 2. Object list

### 2.1 Phase 1–4 (this library)

| Object | DFB type | HMI DDT | Ignition UDT | Purpose |
|---|---|---|---|---|
| Common core | `PL_Core` (internal) | `PL_Base` | `PL_Base` (abstract parent) | Mode, command decode, interlock/permissive, first-out, bypass, reset, sim gating |
| Analog input | `PL_Ain` | `PL_Ain_HMI` | `PL_Ain` | Scaling, filter, HH/H/L/LL, NAMUR bad-signal, sim |
| Discrete input | `PL_Din` | `PL_Din_HMI` | `PL_Din` | Debounce, alarm state, sim |
| Discrete valve | `PL_DVlv` | `PL_DVlv_HMI` | `PL_DVlv` | On/off air-operated valve, 0/1/2 limit switches, single or double solenoid |
| Motor (fixed speed) | `PL_Mtr` | `PL_Mtr_HMI` | `PL_Mtr` | Across-the-line or soft starter. Maintained or 3-wire pulse outputs |
| VFD motor | `PL_Vfd` | `PL_Vfd_HMI` | `PL_Vfd` | Drive-agnostic speed-controlled motor |
| Altivar adapter | `PL_ATV_Adp` | – | – | Maps `PL_Vfd` ⇄ Altivar CMD/ETA/LFR/RFR (DRIVECOM) |
| Analog valve | `PL_AVlv` | `PL_AVlv_HMI` | `PL_AVlv` | Positioned control valve, 4–20 mA output, optional position feedback |
| PID loop | `PL_Pid` | `PL_Pid_HMI` | `PL_Pid` | Wraps the Control Expert `PIDFF` block. Adds Man/Auto/Cas, SP limits/ramp, bumpless transfer, alarms |
| Global | – | `PL_Global` | `PL_Global` | Site sim permit, PLC↔HMI heartbeat |
| Helper | `PL_Pack16` | – | – | 16 BOOL → WORD, inputs default TRUE. Used to build interlock and permissive words in FBD |

### 2.2 Later candidates (not in v1)

Motor-operated valve (open/close/stop with torque switches), 2-speed and reversing starters, duty/standby/rotation,
totalizer, analog output, sequence/phase interface (ISA-88-style), dosing pump, and a valve-bank/manifold adapter.

> **Build vs. buy check:** Schneider's EcoStruxure Process Expert library and the Modicon Libraries cover similar
> ground. They are tied to their own HMI and tooling, so a lean in-house library that matches Ignition is usually the
> better fit here. It is still worth a look before we freeze this spec.

---

## 3. Naming conventions

| Thing | Convention | Example |
|---|---|---|
| Library prefix | `PL_` (placeholder, see Q1) | |
| DFB type | `PL_<Type>` | `PL_DVlv` |
| HMI DDT type | `PL_<Type>_HMI` | `PL_DVlv_HMI` |
| Sub-structure DDTs | `PL_<Type>_Cfg`, `PL_<Type>_Val` | `PL_DVlv_Cfg` |
| DFB instance | Device tag, ISA-5.1 | `XV_1001`, `P_2001`, `FIC_3001` |
| HMI variable | `<Instance>_HMI` | `XV_1001_HMI` |
| Ignition UDT instance | `<Area>/<Instance>` | `[default]Area100/XV_1001` |
| Members | PascalCase, units suffix when not obvious | `TravelTmo_s`, `SpdRef`, `RunHrs` |

Control Expert names are case-insensitive. OPC UA and Ignition paths are case-sensitive, so case must be kept
consistent everywhere. Names may be at most 32 characters.

---

## 4. Architecture

```
 Field I/O (X80 / eX80 / drives on EIP)
        │  (topological I/O variables or device DDTs from DTMs)
        ▼
 ┌────────────────────────────────────────────┐
 │ MAST task (periodic, 50–100 ms)            │
 │                                            │
 │  PL_Pack16 ──Intlk/Perm WORDs──┐           │
 │  program logic ──PCmd/PCV──────┤           │
 │                                ▼           │
 │                     ┌──────────────────┐   │
 │  field inputs ─────►│  PL_DVlv XV_1001 │──►│ outputs to I/O
 │                     │  (PL_Core nested)│   │
 │                     └──────┬───────────┘   │
 │                     IN_OUT │               │
 │                  XV_1001_HMI : PL_DVlv_HMI │ ◄── only this is exposed (data dictionary / HMI flag)
 └────────────────────────────┬───────────────┘
                              │ OPC UA (symbolic)
                              ▼
 Ignition: UDT PL_DVlv (inherits PL_Base)
   ├─ OPC tags  → XV_1001_HMI.*
   ├─ Expression tags (bit unpacking, text)
   ├─ Memory tags (interlock/permissive text dataset)
   └─ Alarms (Bit-State on Base.Alm)
        │
        ▼
 Perspective: Library/DVlv/Icon (on P&IDs) ──click──► Library/DVlv/Faceplate (popup)
```

### 4.1 Execution rules

- Call every library DFB **unconditionally, every scan**. Never call one inside an `IF` or in a section that is
  conditionally executed, because timers and edge detection depend on it.
- Use **MAST, periodic**, 50 ms or 100 ms. PID loops must run in a periodic task.
- Make each device's DFB call the **only** writer of its `_HMI` variable. Program logic reads `_HMI` members if
  needed, but drives the device only through DFB inputs.
- Set **I/O fallback** in the X80 module configuration so that the outputs' fallback state on PLC STOP or comms loss
  matches each device's configured fail state.

### 4.2 OPC UA exposure

- Enable the **data dictionary** in Project Settings. It is required for symbolic access by BMENUA0100, OFS and
  Kepware.
- Expose only the `*_HMI` variables and `PL_Global`. If the project uses the "HMI variable" filter, set that flag on
  `_HMI` instances only. This keeps the address space small and keeps DFB internals private. *(Verify the exact
  CE 16.2 setting name during Phase 1.)*
- On the server side, use security policy `Basic256Sha256` with Sign & Encrypt, and trust Ignition's client
  certificate explicitly.
- **Sizing:** subscriptions are counted per monitored item. The packed status and alarm words in §5 keep a typical
  device at about 10–15 monitored items (with config on a leased tag group) instead of 40+. Check the chosen server's
  published item and session limits against the device count (see Q4).

### 4.3 Known Control Expert gotchas this design addresses

| Gotcha | Mitigation |
|---|---|
| A full download overwrites values written from the HMI with the project's **initial values** | §10 config persistence: run *Update Init Values with Current Values* before a download, and keep an Ignition-side config backup that can push config back |
| Changing a DDT or DFB interface used by running instances may not be possible online | Keep HMI DDTs stable and version DFBs (§11). Interface changes are planned as stop-and-download events *(confirm online-modification limits on CE 16.2 + M580 in Phase 1)* |
| Bit access on unlocated `WORD` (`MyWord.3`) needs a project setting | Enable "bit extraction of INT/WORD" in Project Settings, **or** use `PL_Pack16` and shift/mask code inside the DFBs |
| Passing an element of an `IN_OUT` (`Hmi.Base`) on to a nested DFB's `IN_OUT` | *Verify in Phase 1.* Fallback: `PL_Core` takes the base by copy-in/copy-out inside the parent DFB |
| `TIME` members appear as raw Int32 ms over OPC UA | HMI-facing durations are `REAL` seconds (`_s` suffix) and are converted inside the DFB |
| `EBOOL` is not allowed or not sensible in DDTs | DDT members use `BOOL`. `EBOOL` is used only for located I/O |

---

## 5. Common base (`PL_Base` DDT + `PL_Core` DFB)

Every `PL_<Type>_HMI` has `Base : PL_Base` as its **first** member. Ignition path example: `XV_1001_HMI.Base.Mode`.

### 5.1 `PL_Base` members

| Member | Type | Dir | Description |
|---|---|---|---|
| `Cmd` | INT | HMI→PLC | Operator command register (§5.3). The PLC clears it to 0 after processing |
| `CmdRsp` | INT | PLC→HMI | Result of the last command (§5.4) |
| `Mode` | INT | PLC→HMI | Current mode (§5.2) |
| `State` | INT | PLC→HMI | Device state enum, device-specific (e.g. valve: 1 Closed, 2 Opening, 3 Open, 4 Closing, 9 Travel fault) |
| `Sts` | WORD | PLC→HMI | Common status bits (§5.5) |
| `StsX` | WORD | PLC→HMI | Device-specific status bits |
| `Alm` | WORD | PLC→HMI | Alarm condition bits. Bit 0 = I/O fault, bit 1 = interlock trip, bits 2–15 device-specific |
| `IntlkSts` | WORD | PLC→HMI | Live interlock word, **1 = OK** |
| `IntlkFO` | WORD | PLC→HMI | First-out capture: the bit that dropped first. Cleared on reset |
| `PermSts` | WORD | PLC→HMI | Live permissive word, **1 = OK** |
| `BypSts` | WORD | PLC→HMI | Interlocks currently bypassed |
| `BypRemain_s` | REAL | PLC→HMI | Time left before the bypass auto-expires |
| `PCmdSts` | INT | PLC→HMI | What the program is requesting right now (e.g. 1 = open/run, 2 = close/stop). Shown on the faceplate so the operator knows what *Auto* will do before selecting it |

### 5.2 Modes (`Mode`)

| Value | Mode | Who drives the device | Notes |
|---|---|---|---|
| 1 | **Out of Service** | Nobody. Outputs at fail state | Commands rejected except "→ Manual". Ignition suppresses the device's alarms. Supervisor role |
| 2 | **Maintenance** | Operator (faceplate) | Same as Manual for the PLC, but Ignition suppresses process alarms (not I/O faults) and shows an "M" badge. The program cannot force it to Auto. Supervisor role |
| 3 | **Manual** | Operator (faceplate) | |
| 4 | **Auto** | Program (DFB `PCmd*` / `PCV` / `PSpdRef` inputs) | |
| 5 | **Cascade** | Remote SP from another loop | `PL_Pid` only |
| 6 | **Local** | Field (HOA in Hand, local control station) | Entered automatically when the `Local` input is TRUE. The PLC tracks the device and does not drive it. On exit, goes to `Cfg.LocalExitMode` (default **Manual**, so the device never bumps into Auto) |

Transitions:

- Auto ↔ Manual: Operator, unless the `ModeLock` input is TRUE (program holds Auto, e.g. during a sequence).
- Manual → Maintenance / Out of Service: Supervisor.
- Back to Manual: Supervisor.
- **Bumpless transfer.** Going Auto→Manual, the device holds its current state or output. Going Manual→Auto, the
  device follows the program immediately, which is why the faceplate shows `PCmdSts` before the operator presses
  Auto.
- On first scan or cold start, a device starts in `Cfg.InitMode`. The default is Manual for motors and Auto for
  valves (see Q3).

### 5.3 Command codes (`Cmd`), shared by all objects

| Code | Command | Code | Command |
|---|---|---|---|
| 0 | none | 20 | Interlock bypass ON (uses `Cfg.BypMask` ∧ DFB `IntlkBypMask` input) |
| 1 | Open / Start / Run fwd | 21 | Interlock bypass OFF |
| 2 | Close / Stop | 30 | Simulation ON (only if `PL_Global.SimPermit`) |
| 3 | Reset (trips, first-out, latched alarms) | 31 | Simulation OFF |
| 4 | Run reverse (VFD) | 40 | Reset counters (cycles, starts, run hours) |
| 10 | Mode → Auto | 50 | Update the DFB's stored reference (e.g. accept stroke time as baseline) |
| 11 | Mode → Manual | | |
| 12 | Mode → Maintenance | | |
| 13 | Mode → Out of Service | | |
| 14 | Mode → Cascade | | |

Analog operator values are written directly to their own REAL members, e.g. `Val.OCV` (operator CV %), `Val.OSpd`,
`Val.OSP`, `Val.OOut`. The DFB uses them only in the appropriate mode and clamps them to limits.

Roles are enforced in Ignition. The PLC enforces the *state* rules (mode, interlock, permissive), not who is logged in.

### 5.4 Command response (`CmdRsp`)

`0` OK · `1` rejected: wrong mode · `2` rejected: interlock · `3` rejected: permissive · `4` rejected: fault latched,
reset first · `5` rejected: not allowed by config · `6` unknown code

The faceplate shows a short toast when `CmdRsp ≠ 0` after a write.

### 5.5 Common status bits (`Sts`)

| Bit | Meaning | Bit | Meaning |
|---|---|---|---|
| 0 | Ready (no interlock, permissives OK, no fault, available) | 8 | Simulation active |
| 1 | Active (open / running / output > 0) | 9 | Bypass active |
| 2 | Inactive (closed / stopped) | 10 | Local (field control) |
| 3 | Transitioning | 11 | Mode locked by program |
| 4 | Interlocked (any interlock not OK) | 12 | Program command active (PCmd) |
| 5 | Permissive not OK | 13 | Command response ≠ 0 (latched 5 s) |
| 6 | Tripped / fault latched (needs reset) | 14 | spare |
| 7 | Any alarm condition active | 15 | spare |

### 5.6 Interlocks vs. permissives

| | Permissive (`Perm`) | Interlock (`Intlk`) |
|---|---|---|
| When checked | Only to **start / open / move away from fail state** | **Always** |
| On loss | Nothing happens if already running | Drive to fail state; set `Alm` bit 1 and first-out |
| Bypass | Allowed in Maintenance (`Cmd 20`), Supervisor | Only bits enabled in the DFB input `IntlkBypMask` (decided in code, not from the HMI), Supervisor, auto-expires after `Cfg.BypTime_s` |
| After clearing | – | `Cfg.IntlkLatch` TRUE: needs Reset (default for motors). FALSE: in Auto, the device resumes following the program (default for valves) |

- Each is a `WORD`, **1 = OK**, with 16 conditions per device. The DFB input default is `16#FFFF`, so unused bits are
  OK.
- Build the words in FBD with `PL_Pack16` (16 BOOL pins, all defaulting to TRUE), or in ST with bit access.
- The **text** for each bit lives in Ignition (§8.3), so the faceplate can list "Bit 3: LSHH-2001 Tank high-high —
  NOT OK (first out)".

### 5.7 Failure handling

Failure alarms (fail-to-open, fail-to-start, and so on) take an action set by `Cfg.FailAction`:
`0` = alarm only, `1` = drive to fail state and latch (needs reset). Defaults: valves `0`, motors and VFDs `1`.

### 5.8 Simulation

- `Cmd 30` is accepted only when `PL_Global.SimPermit = TRUE`. That is a site-wide key, off in production.
- In sim, the DFB ignores field feedback and generates it:
  - Valves stroke over `Cfg.SimTravel_s`.
  - Motors confirm after 1 s.
  - VFD speed ramps.
  - AIN takes `Val.SimPV`.
- Physical outputs are still written unless `Cfg.SimOutputsOff = TRUE`.
- `Sts` bit 8 and a large "SIM" badge appear on the icon and faceplate.

---

## 6. Device specifications

Each object lists: DFB pins, then the HMI DDT members beyond `Base`, and alarm bit allocation. Pin names in
**bold** are required, the rest are optional with safe defaults.

### 6.1 Discrete valve – `PL_DVlv`

Covers spring-return single solenoid (fail closed or fail open), double solenoid (maintained), and 0, 1 or 2 limit
switches.

**DFB inputs:** **`ZSO`** BOOL, **`ZSC`** BOOL, `IOFlt` BOOL, `Intlk` WORD(FFFF), `Perm` WORD(FFFF),
`IntlkBypMask` WORD(0), `PCmdOpen` BOOL (Auto: TRUE = open, level), `ModeLock` BOOL, `Local` BOOL, `Reset` BOOL
(program reset, edge)
**DFB outputs:** `OutOpen` BOOL (single solenoid, or open coil), `OutClose` BOOL (close coil, double-acting only),
`IsOpen`, `IsClosed`, `Ready`, `Fault`
**IN_OUT:** **`Hmi`** : `PL_DVlv_HMI`

`PL_DVlv_HMI`:

| Member | Type | Notes |
|---|---|---|
| `Base` | PL_Base | `State`: 0 Unknown, 1 Closed, 2 Opening, 3 Open, 4 Closing, 5 Travel fault, 6 Limit conflict |
| `Cfg.HasZSO` / `Cfg.HasZSC` | BOOL | Feedback present. If absent, the position is inferred after `TravelTmo_s` |
| `Cfg.FailOpen` | BOOL | Spring opens on de-energise. Output logic inverts |
| `Cfg.DoubleSol` | BOOL | Use `OutOpen` / `OutClose` as maintained coils |
| `Cfg.TravelTmo_s` | REAL | Fail-to-open/close timeout |
| `Cfg.FailAction` | INT | §5.7 |
| `Cfg.IntlkLatch` | BOOL | §5.6 |
| `Cfg.InitMode`, `Cfg.LocalExitMode` | INT | §5.2 |
| `Cfg.BypMask`, `Cfg.BypTime_s` | WORD, REAL | §5.6 |
| `Cfg.SimTravel_s`, `Cfg.SimOutputsOff` | REAL, BOOL | §5.8 |
| `Val.StrokeOpen_s` / `Val.StrokeClose_s` | REAL | Last measured stroke time. Trend these for valve health |
| `Val.StrokeRef_s` | REAL | Baseline stroke time (Cmd 50). Alarm bit 6 if `last > ref × Cfg.StrokeDegr` |
| `Val.Cycles` | DINT | Open cycles since reset |

`StsX`: 0 ZSO, 1 ZSC, 2 OutOpen, 3 OutClose, 4 Cmd open (resolved), 5 Opening, 6 Closing
`Alm`: 0 I/O fault, 1 Interlock trip, 2 Fail to open, 3 Fail to close, 4 Position lost (left position without
command), 5 Limit conflict (both ZSO and ZSC), 6 Stroke time degraded

### 6.2 Motor – `PL_Mtr`

**DFB inputs:** **`RunFbk`** BOOL (aux contact), `Ovld` BOOL, `Avail` BOOL(TRUE) (disconnect / MCC bucket
ready), `Local` BOOL (HOA not in Auto), `IOFlt`, `Intlk`, `Perm`, `IntlkBypMask`, `PRun` BOOL (Auto, level),
`ModeLock`, `Reset`
**DFB outputs:** `RunOut` (maintained), `StartPls`, `StopPls` (3-wire), `Running`, `Ready`, `Fault`

`PL_Mtr_HMI`:

| Member | Type | Notes |
|---|---|---|
| `Base` | PL_Base | `State`: 1 Stopped, 2 Starting, 3 Running, 4 Stopping, 5 Tripped |
| `Cfg.FbkPresent` | BOOL | If FALSE, Running = RunOut |
| `Cfg.StartTmo_s` / `Cfg.StopTmo_s` | REAL | Fail-to-start/stop |
| `Cfg.PulseOut`, `Cfg.Pulse_s` | BOOL, REAL | 3-wire control |
| `Cfg.MaxStartsHr` | INT | 0 = off. Start rejected (`CmdRsp 5`) and alarm 7 when exceeded |
| `Cfg.RestartDly_s` | REAL | Minimum off-time before restart (anti-backspin / thermal) |
| `Cfg.FailAction`, `IntlkLatch`, `InitMode`, `LocalExitMode`, `BypMask`, `BypTime_s`, `SimOutputsOff` | | Common |
| `Val.RunHrs` | REAL | Accumulated in DINT seconds internally |
| `Val.Starts` | DINT | |
| `Val.StartsLastHr` | INT | Rolling |
| `Val.RestartRemain_s` | REAL | Shown on faceplate as "Restart available in …" |

`StsX`: 0 RunFbk, 1 RunOut, 2 Ovld, 3 Avail, 4 Restart inhibited, 5 Starts limit reached
`Alm`: 0 I/O fault, 1 Interlock trip, 2 Fail to start, 3 Fail to stop, 4 Unexpected stop, 5 Overload,
6 Not available, 7 Starts/hr exceeded, 8 Not in remote while demanded (low priority)

### 6.3 VFD motor – `PL_Vfd` (+ `PL_ATV_Adp`)

`PL_Vfd` is **drive-agnostic**: it works in engineering units and simple BOOLs. A thin adapter per drive family
translates to the drive's I/O. For Altivar (ATV320/340/630/930 over EtherNet/IP or Modbus TCP via the DTM-generated
device DDT) that is `PL_ATV_Adp`, which runs the DRIVECOM / CiA-402 state machine on CMD/ETA and scales LFR/RFR.
Other brands get their own adapter, so `PL_Vfd`, its DDT, the UDT and the faceplate never change.

**`PL_Vfd` inputs:** everything in `PL_Mtr` except `RunFbk`/`Ovld`, plus **`DrvRunning`**, **`DrvFault`**,
`DrvReady`, `DrvFaultCode` INT, `AtSpeed`, **`SpdFbk`** REAL (EU), `Current` REAL (A), `Power` REAL (kW),
`CommFlt` BOOL, `PSpdRef` REAL (Auto speed, EU), `PRev` BOOL
**Outputs:** `RunFwd`, `RunRev`, `SpdRef` REAL (EU, clamped and ramped), `FltResetOut` (pulse), `Running`,
`Ready`, `Fault`

`PL_Vfd_HMI` = everything in `PL_Mtr_HMI`, plus:

| Member | Type | Notes |
|---|---|---|
| `Cfg.SpdMin` / `Cfg.SpdMax` | REAL | EU clamp on the reference |
| `Cfg.SpdEUFull` | REAL | e.g. 60.0 (Hz) or 1780 (rpm). EU text lives in Ignition |
| `Cfg.Ramp_EUs` | REAL | PLC-side reference ramp, 0 = off (normally leave ramping to the drive) |
| `Cfg.RevAllowed` | BOOL | |
| `Cfg.SpdDevLim`, `Cfg.SpdDevDly_s` | REAL | Speed deviation alarm |
| `Val.OSpd` | REAL | Operator speed, HMI-writable, used in Manual. Tracks `SpdRef` in Auto for bumpless transfer |
| `Val.SpdRef`, `Val.SpdFbk`, `Val.Current`, `Val.Power` | REAL | |
| `Val.FaultCode` | INT | Ignition maps it to text with a per-drive-family dataset |

`Alm`: `PL_Mtr` set, with 5 = Drive fault (in place of Overload), plus 9 Comm fault, 10 Speed deviation.

`PL_ATV_Adp`: inputs `RunFwd, RunRev, SpdRef, FltReset`, the drive's `ETA, RFR, LCR, LFT`, and `Hz_per_EU`.
Outputs `CMD, LFR` and the `Drv*` signals for `PL_Vfd`. *The CMD/ETA bit patterns will be verified against the
specific ATV programming manual during Phase 3.*

### 6.4 Analog (positioned) valve – `PL_AVlv`

**DFB inputs:** `PCV` REAL (Auto position, 0–100 %, e.g. from `PL_Pid.Out`), `PosFbk` REAL (%), `PosFbkFlt`
BOOL, `IOFlt`, `Intlk`, `IntlkBypMask`, `Local`, `ModeLock`, `Reset`
**DFB outputs:** `CV` REAL (% after limits, ramp and cutoff), `OutRaw` INT (scaled for the X80 AO channel),
`Ready`, `Fault`

`PL_AVlv_HMI`:

| Member | Type | Notes |
|---|---|---|
| `Base` | PL_Base | `State`: 1 Closed (≤ cutoff), 2 Throttling, 3 Full open, 5 Fail position |
| `Cfg.OutMin` / `Cfg.OutMax` | REAL | % travel limits (not applied in Out of Service or interlock) |
| `Cfg.Rate_pcts` | REAL | Rate limit, %/s, 0 = off |
| `Cfg.FailPos` | REAL | Position on interlock or Out of Service, normally 0 or 100 |
| `Cfg.Cutoff` | REAL | Tight shut-off: CV < Cutoff → 0 % |
| `Cfg.Reverse` | BOOL | Output inverted (4 mA = 100 % open) |
| `Cfg.RawMin` / `Cfg.RawMax` | INT | AO raw range (X80 default 0–10000) |
| `Cfg.FbkPresent`, `Cfg.DevLim`, `Cfg.DevDly_s` | | Position-deviation alarm |
| `Val.OCV` | REAL | Operator position, HMI-writable. Tracks CV in Auto for bumpless transfer |
| `Val.CV`, `Val.PosFbk`, `Val.Dev` | REAL | |

`Alm`: 0 I/O fault, 1 Interlock trip, 2 Position deviation, 3 Feedback bad

### 6.5 PID loop – `PL_Pid`

Wraps the Control Expert **`PIDFF`** EFB (CONT_CTL library) rather than reinventing the algorithm. `PL_Pid` adds
the mode model, SP handling, cascade initialization, alarms and the HMI DDT. *Exact PIDFF parameter names and
`PARA_PIDFF` fields are confirmed in Phase 4.*

**DFB inputs:** **`PV`** REAL (EU, normally `PL_Ain.PV`), `PVBad` BOOL, `CasSP` REAL (remote SP from a primary loop
or program), `FF` REAL, `OutRbk` REAL (actual downstream value, e.g. `PL_AVlv.CV`, for anti-windup and
initialization), `DownstreamNotAuto` BOOL (e.g. the valve was put in Manual, so this loop tracks `OutRbk`), `TrkEn`
BOOL + `TrkVal` REAL (override tracking), `Intlk`, `ModeLock`
**DFB outputs:** `Out` REAL (0–100 %), `InitPri` BOOL + `InitVal` REAL (tells a primary loop to track while this
secondary is not in Cascade), `Ready`

`PL_Pid_HMI`:

| Member | Type | Notes |
|---|---|---|
| `Base` | PL_Base | Modes used: Out of Service, Manual, Auto, Cascade. `State`: 1 Manual, 2 Auto, 3 Cascade, 4 Tracking, 5 Initializing, 6 PV bad |
| `Cfg.Kp`, `Cfg.Ti_s`, `Cfg.Td_s` | REAL | Tuning |
| `Cfg.Reverse` | BOOL | Action. Reverse = PV↑ → Out↓ (heating, level-by-inflow) |
| `Cfg.PVMin` / `Cfg.PVMax` | REAL | PV range, for normalization |
| `Cfg.OutMin` / `Cfg.OutMax` | REAL | |
| `Cfg.SPMin` / `Cfg.SPMax` | REAL | Clamp on operator, cascade and program SP |
| `Cfg.SPRamp_EUs` | REAL | 0 = step |
| `Cfg.SPTrackPV` | BOOL | In Manual, SP follows PV so the switch to Auto is bumpless |
| `Cfg.Dband` | REAL | Error deadband |
| `Cfg.DevLim`, `Cfg.DevDly_s` | REAL | Deviation alarm |
| `Cfg.PVBadAction` | INT | 0 hold output in Auto, 1 force Manual (hold), 2 drive to `Cfg.FailOut` |
| `Cfg.FailOut` | REAL | |
| `Val.PV`, `Val.SP`, `Val.Out`, `Val.Err` | REAL | Active values |
| `Val.OSP` | REAL | Operator SP, HMI-writable (Auto) |
| `Val.OOut` | REAL | Operator output, HMI-writable (Manual). Tracks Out otherwise |
| `Val.CasSP` | REAL | Read-only display |

`Alm`: 0 I/O fault (PV bad), 1 Interlock, 2 Deviation high, 3 Deviation low, 4 Output at limit (diagnostic
priority), 5 Not in normal mode (`Cfg.NormMode`, ISA-18.2 "off-normal")

**Linking pattern (loop → valve):**

```
AIN FT_3001 ──PV──► PL_Pid FIC_3001 ──Out──► PL_AVlv FCV_3001.PCV
                       ▲  OutRbk ◄──────────── FCV_3001.CV
                       └─ DownstreamNotAuto ◄─ FCV_3001_HMI.Base.Mode <> 4
```

If an operator takes the valve into Manual, the loop initializes to the valve position, so there is no windup and
no bump on return. Cascade uses the same pattern via `InitPri`/`InitVal`.

### 6.6 Analog input – `PL_Ain`

**Inputs:** **`Raw`** INT, `ChFlt` BOOL (channel health)
**Outputs:** `PV` REAL, `Bad`, `HH`, `H`, `L`, `LL` BOOL. Use these in interlocks, and note that they are delayed
and deadbanded.
**Cfg:** `RawMin/Max`, `EUMin/Max`, `Filt_s` (first-order), `HHLim/HLim/LLim/LLLim` + `AlmEn` WORD (enable bits),
`AlmDB` (deadband EU), `AlmDly_s`, `BadLoRaw/BadHiRaw` (NAMUR NE43, default 3.6/21.0 mA equivalent),
`BadAction` (0 hold last, 1 substitute `Cfg.BadPV`), `RocLim_EUs`
**Val:** `PV`, `RawEcho`, `SimPV`
`Alm`: 0 Bad signal, 2 HH, 3 H, 4 L, 5 LL, 6 Rate of change. (`Mode` uses only Manual/Auto/Out of Service.
"Manual" means a substituted value, which ISA calls *Override*.)

### 6.7 Discrete input – `PL_Din`

**Inputs:** **`In`** BOOL, `ChFlt` · **Outputs:** `Out` (debounced), `Alarm`
**Cfg:** `AlmState` BOOL, `AlmEn` BOOL, `Dly_s`, `Debounce_s` · `Alm`: 0 I/O fault, 2 Alarm

### 6.8 Global – `PL_Global`

`SimPermit` BOOL (HMI-writable, Engineer), `PlcHeartbeat` INT (PLC increments every second), `HmiHeartbeat` INT
(written by an Ignition gateway timer script), `HmiOK` BOOL (PLC: the HMI heartbeat changed within 10 s), `LibVer`
INT.

---

## 7. Call-site examples

FBD is the recommended language at call sites. The equivalent ST is shown here:

```iecst
(* Interlocks: 1 = OK *)
XV_1001_Ilk(In1 := NOT LSHH_2001.HH,      (* Tank 2001 high-high      *)
            In2 := NOT ESD_Active,         (* Area ESD                 *)
            In3 := P_2001.Running);        (* Pump must run to open    *)
                                           (* In4..In16 default TRUE   *)

XV_1001(ZSO          := DI_ZSO_1001,
        ZSC          := DI_ZSC_1001,
        IOFlt        := NOT DI_Slot3_Health,
        Intlk        := XV_1001_Ilk.Out,
        IntlkBypMask := 16#0004,            (* only bit 2 may be bypassed *)
        PCmdOpen     := Seq100.FillStep,
        Hmi          := XV_1001_HMI);

DO_XY_1001 := XV_1001.OutOpen;
```

---

## 8. Ignition UDTs

### 8.1 Structure

```
PL_Base                       (parent, all device UDTs inherit; Ignition 8.1 UDT inheritance)
├─ Parameters:  OpcServer, PlcVar (e.g. "XV_1001_HMI"), OpcNsPrefix, Area, Desc, HistProvider, EU
├─ Base/        OPC tags → {OpcNsPrefix}{PlcVar}.Base.*
│   Cmd, CmdRsp, Mode, State, Sts, StsX, Alm, IntlkSts, IntlkFO, PermSts, BypSts, BypRemain_s, PCmdSts
├─ Derived/     expression tags: Ready, Active, Interlocked, Tripped, Sim, Bypassed, Local, ModeText, StateText
│               e.g.  getBit({[.]../Base/Sts}, 4)
├─ Text/        memory tags: IntlkDesc (Dataset[16]: Bit, Desc), PermDesc (Dataset[16]), StateMap (Dataset)
└─ Alarms       defined on Base/Alm, mode "Bit State", one alarm per bit

PL_DVlv  (parent = PL_Base)
├─ Cfg/   OPC tags, tag group "Leased" (polled only while a faceplate is open)
└─ Val/   OPC tags, Default group. History on stroke times and cycles
```

- **OPC item path:** the parameterized `OpcNsPrefix` + `PlcVar` absorbs node-ID format differences between
  BMENUA0100, OFS and Kepware. Browse one variable once, then set the prefix gateway-wide.
- **Tag groups:**
  - `PL_Fast` (500 ms) for `Base/*` and the main `Val/*`.
  - `PL_Leased` (leased, 1 s when needed, 0 otherwise) for `Cfg/*` and diagnostics.
- **History:** stored on PVs, SP/Out, speed, current and stroke times only. `HistProvider` is a UDT parameter, so
  the 8.3 historian change (§12) is a single edit.
- **Bulk creation:** UDT instances come from a CSV (tag, type, area, desc, PlcVar, interlock text) through a small
  import script in the repo. That way the instrument list is the source of truth.

### 8.2 Alarm definitions (example: `PL_DVlv`)

| Bit | Name | Default priority | Delay | Notes |
|---|---|---|---|---|
| 0 | IOFault | High | 0 (PLC filters) | Not suppressed in Maintenance |
| 1 | InterlockTrip | Medium | 0 | Text includes the first-out description |
| 2 | FailToOpen | Medium | 0 | |
| 3 | FailToClose | Medium | 0 | |
| 4 | PositionLost | High | 0 | |
| 5 | LimitConflict | Low | 0 | |
| 6 | StrokeDegraded | Diagnostic | 0 | Maintenance notification, not an operator alarm |

- **Enabled expression** (suppression by design):
  `{[.]../Base/Mode} != 1 && ({[.]../Base/Mode} != 2 || <bit is IOFault>)`
- **Display path:** `{Area}/{InstanceName}`.
- **Label:** `{Desc} – Fail to open`.
- **Priorities** follow the site alarm philosophy (Q6). The table above shows defaults only, and each instance can
  override them.

### 8.3 Interlock and permissive text

`Text/IntlkDesc` is a 16-row dataset, editable from the Engineer tab of the faceplate or loaded by CSV. The
faceplate joins it with `IntlkSts`, `IntlkFO` and `BypSts` to show one table: *bit · description · OK/NOT OK ·
first-out · bypassed*.

---

## 9. Perspective faceplates

### 9.1 View organization

```
Library/
  Common/
    StatusHeader      tag, desc, mode badge, state text, alarm/SIM/BYP/LOCAL badges
    ModeBar           mode buttons, role-gated, shows PCmdSts "Program wants: OPEN"
    IntlkTable        §8.3 table. Bypass buttons (Supervisor)
    AlarmPanel        alarm status table filtered to this instance's path
    CmdResponseToast
    NumericEntry      confirm-on-enter numeric write with limits and units
  DVlv/   Icon, Faceplate
  Mtr/    Icon, Faceplate
  Vfd/    Icon, Faceplate
  AVlv/   Icon, Faceplate
  Pid/    Icon, Faceplate (incl. Power Chart trend tab)
  Ain/    Icon (value + bar), Faceplate
  Din/    Icon, Faceplate
```

- Every view takes a single parameter, **`tagPath`** (the UDT instance path), and binds indirectly
  (`{view.params.tagPath}/Base/Mode`).
- **One popup function** for all types: the script `pl.faceplate.open(tagPath)` reads the instance's
  `typeId`, maps it to `Library/<Type>/Faceplate`, and opens a popup with id = `tagPath`, so the same device never
  opens twice. Icons call it on click.
- **Icons** support `orientation` and `size` parameters, and show state by shape and fill per ISA-101. Abnormal
  conditions show a coloured alarm indicator (priority colour), plus SIM, BYP, M and L badges.

### 9.2 Faceplate layout (discrete valve)

```
┌───────────────────────────────────────────────┐
│ XV-1001   Tank 2001 inlet valve        [x]    │
│ ● OPEN      MANUAL         ⚠ 1 alarm  SIM BYP │  ← StatusHeader
├───────────────────────────────────────────────┤
│ [Operate] [Interlocks 1] [Alarms] [Maint] [Eng]│
├───────────────────────────────────────────────┤
│ Mode:  [AUTO] [MANUAL]        Program: CLOSE   │  ← ModeBar
│                                               │
│        [  OPEN  ]      [ CLOSE ]      [RESET] │
│                                               │
│  ZSO ■   ZSC □    Output ■                    │
│  Last stroke: open 3.2 s / close 2.9 s        │
└───────────────────────────────────────────────┘
```

| Tab | Content | Role |
|---|---|---|
| Operate | Mode, commands, key values, operator setpoints | Operator |
| Interlocks | IntlkTable + PermTable, first-out, bypass | View: all. Bypass: Supervisor |
| Alarms | Active and recent alarms for this device, shelve | Operator (shelve: Supervisor) |
| Trend | Power Chart of the device's historized tags (AIN, AVlv, Vfd, Pid) | All |
| Maint | Counters, run hours, stroke times, Maintenance/Out of Service modes, counter reset | Supervisor |
| Eng | All `Cfg/*` with limits and units, SIM, interlock text editing, config backup/restore | Engineer |

### 9.3 Security

| Action | Operator | Supervisor | Engineer |
|---|:-:|:-:|:-:|
| Open/close/start/stop, setpoints, Auto/Manual, Reset | ✔ | ✔ | ✔ |
| Maintenance, Out of Service, bypass, shelve, counter reset | | ✔ | ✔ |
| Cfg edits, SIM, interlock text | | | ✔ |

- Roles are checked in the component's `enabled` binding *and* again in the write script. The script uses
  `pl.cmd.send(tagPath, code)` to check the role, write, wait for `CmdRsp`, and record an audit entry.
- Map roles to the IdP / AD groups (Q12).
- Commands that start equipment or remove protection (bypass, Out of Service) need a confirmation dialog.

### 9.4 Look and feel

- All colours come from **Perspective style classes** (`PL/State/Active`, `PL/Alarm/High`, …) and theme variables,
  never hard-coded. Switching between ISA-101 grey and traditional red/green (Q7) is then a theme change.
- Faceplates have a fixed popup size (around 420 × 520) and must work on a 1080p operator screen and a tablet.

---

## 10. Configuration persistence

Problem: `Cfg.*` values are tuned from the HMI at runtime, but a full download writes the project's initial values
back over them.

1. **Engineering procedure:** before any download, run **PLC → Update Init Values with Current Values** (or the
   equivalent online command) and save the project. This goes in the change-management checklist.
2. **Safety net:** a Gateway script snapshots every instance's `Cfg/*` to a database table:
   - nightly
   - on every Engineer edit (via `pl.cmd`)

   The Eng tab offers "Compare PLC vs. last snapshot" and "Restore" (Engineer only, with confirmation).
3. **Optional:** `PL_Global.CfgCRC`. The PLC computes a cheap checksum over config and Ignition alarms on an
   unexpected change, which catches a download that reverted values.

---

## 11. Versioning, source control and testing

### 11.1 Versioning

- Each DFB type carries its Control Expert type version. The library also has `LibVer` (in `PL_Global` and in the
  Ignition `PL_Base` UDT) using semver.
- **Breaking** (major): any change to an HMI DDT member name or type, or to a DFB pin. These require a matching
  Ignition UDT release.
- **Minor:** added DFB pins with safe defaults, or added DDT members at the end of a sub-structure.
- **Patch:** body-only changes.
- Library DFBs and DDTs are distributed through a Control Expert **Types Library** (`.dtx`, Types Library Manager)
  so projects pull a known version.

### 11.2 Repository layout (planned)

```
docs/                     this standard, alarm defaults, CSV templates
plc/
  ddt/                    *.xdd exports (DDT types)
  dfb/                    *.xdb exports (DFB types), the import source of truth
  src/                    *.st, readable DFB bodies + interface tables for review and diffs
  test/                   test project (.zef) + animation tables / test procedures
ignition/
  udts/                   *.json UDT definitions (8.1 tag export format)
  perspective/Library/    view.json resources
  scripts/pl/             project library scripts (faceplate, cmd, cfg backup, csv import)
  styles/                 style classes
tools/
  csv_to_udt_instances.py
```

The workflow is to author in Control Expert and Designer, then export into the repo. Only exported, importable files
are the source of truth. The `.st` copies are for review.

### 11.3 Testing

- **PLC unit tests:** a test project instantiates every DFB with sim ON and runs scripted scenarios for each object:
  mode transitions, each `Cmd`/`CmdRsp`, interlock trip and latch, first-out, bypass expiry, each failure alarm,
  Local entry/exit and bumpless transfer.
- **Integration:** to connect Ignition to the Control Expert **simulator**, use OFS. BMENUA0100 cannot attach to the
  simulator. Alternatively, test on a bench M580 with BMENUA0100.
- **Acceptance:** a per-object checklist in `plc/test/` is signed off before an object is released.

---

## 12. Ignition 8.1 → 8.3 readiness

To make the upgrade a non-event, the 8.1 work will follow these rules:

- **Structure the files for source control now.** 8.3 stores gateway and tag configuration as files, which suits
  git. Keeping the UDTs and views in `ignition/` from day one means the 8.3 migration can switch to direct file-based
  resources.
- **Make history a parameter.** 8.3 introduces new historian options. The `HistProvider` UDT parameter means
  re-targeting history is one change per gateway, not per tag.
- **No deprecated APIs.** Use `system.tag.readBlocking/writeBlocking`, not `read`/`write`. Use
  `system.perspective.*` only, and avoid undocumented internal classes.
- **No gateway-wide dependencies in views.** Views use only their params, the project script library and style
  classes.
- **Do a trial upgrade early.** Before go-live on 8.1, restore a gateway backup to an 8.3 test gateway and run the
  same faceplate checklist.

*Exact 8.3 behaviour (historian, resource layout, upgrade path for 8.1 tag exports) will be confirmed against the
8.3 upgrade guide during Phase 1. These items are planning assumptions.*

---

## 13. Delivery plan

| Phase | Content | Exit criteria |
|---|---|---|
| **0** | This spec + answers to §14 | Spec approved (v1.0) |
| **1** | `PL_Base`/`PL_Core`, `PL_Pack16`, `PL_Global`, `PL_Ain`, `PL_Din`. Ignition base UDT, Common views, `pl.*` scripts, style classes. Verify the CE and OPC UA assumptions flagged in §4.3 | AIN/DIN pass the test checklist on a bench or simulator through OPC UA |
| **2** | `PL_DVlv` end to end. This is the template for the rest | Reviewed by you, then pattern frozen |
| **3** | `PL_Mtr`, `PL_Vfd`, `PL_ATV_Adp` | Checklist pass |
| **4** | `PL_AVlv`, `PL_Pid` incl. cascade and the loop↔valve linking | Checklist pass, loop tuned on a sim plant model |
| **5** | CSV import tool, config backup/restore, documentation, `.dtx` library release | v1.0 release tag |

---

## 14. Open questions for review

1. **Prefix and naming.** Is `PL_` right, or do you use a company or site prefix? Do you prefer the instance and
   HMI-variable naming `XV_1001` / `XV_1001_HMI`?
2. **Packed vs. individual BOOLs.** This spec packs status and alarms into WORDs for OPC UA efficiency and uses
   Ignition Bit-State alarms. Individual BOOLs are easier to read in animation tables but cost about 3× more
   monitored items. Are packed words OK?
3. **Mode set.** Do you want both *Maintenance* and *Out of Service*? Are the initial-mode defaults right (motors
   Manual, valves Auto)?
4. **OPC UA server and size.** BMENUA0100, OFS or Kepware? Roughly how many devices per PLC, and how many PLCs?
5. **I/O health.** Where should `IOFlt`/`ChFlt` come from: X80 channel/module error bits from topological
   addressing, or IODDTs? Do you use remote racks or eX80 drops?
6. **Alarm philosophy.** Is there a site alarm philosophy document (priorities, colours, response times)?
7. **Colour standard.** ISA-101 grey-scale (with state shown by shape and fill), or traditional red = running /
   green = stopped (or the reverse)?
8. **Drives.** Which VFD makes and models, and on which network (EtherNet/IP DTM, Modbus TCP, hardwired)?
9. **Valve variants.** Do you also need 3-way/diverter valves, motor-operated valves (open/close/stop with torque
   switches), or valves with a mid-position?
10. **Config persistence.** Is the §10 approach acceptable, and is there an Ignition database available for the
    snapshot table?
11. **Existing standards.** Is there an existing plant or corporate PLC/HMI standard (or a previous project) whose
    look or behaviour this must match?
12. **Security.** Which identity provider (Ignition internal, AD/LDAP, SAML/OIDC)? Are the role names Operator /
    Supervisor / Engineer OK?
13. **Motors.** Are starts-per-hour and restart-delay protection wanted in the PLC, or are they handled in the
    motor protection relay?
