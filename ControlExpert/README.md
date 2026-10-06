# Control Expert code

Target: EcoStruxure Control Expert Classic V16.2 (M340 / M580), Structured Text.
SCADA: Ignition Perspective 8.1.

## Layout
- `DFB/<Name>/Interface.md`: variable tables to enter in the Data Editor (DFB Types)
- `DFB/<Name>/<Name>.st`: code for the DFB's ST section
- `Sections/*.st`: example program sections (MAST task)

## Conventions
- Prefixes: `i_` inputs, `q_` outputs; type letter `x` BOOL, `i` INT, `di` DINT, `r` REAL, `t` TIME.
- Comments `(* *)` only. Outputs bound with `=>` in DFB calls.
- DFBs use no located variables (`%M`, `%MW`); sections bind the I/O.
- Edges use `R_TRIG` (`RE()` needs EBOOL).
- Commands written by Ignition are set TRUE by SCADA and cleared by the PLC after the DFB call, so each press gives a fresh rising edge.

## DFB_Motor behaviour
- Start on a rising edge; stop is dominant.
- **Permissives** (`i_xPermissives`, TRUE = inhibit, non-safety): drop the run command. No reset is needed; a new start is accepted once they clear.
- **Interlock** (`i_xInterlockOk`, FALSE = tripped, fail-safe): drops the run command and latches `q_xIlkTripped`. Needs a reset from SCADA with the interlock healthy, then a new start.
- **Feedback supervision:** command/feedback mismatch longer than `i_tFbkTimeout` latches a fault. Codes: 1 fail to start, 2 feedback lost while running, 3 running without a command.
- `i_xReset` (rising edge) clears both faults and interlock trips. Reset never starts the motor.
- Run hours are accumulated in seconds (DINT) and output as REAL hours.
