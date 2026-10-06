(* DFB_Motor - single-direction motor with feedback supervision *)
(* Control Expert Classic V16.2. Declarations: see Interface.md  *)

(* ---- Edge detection ---- *)
rtStart(CLK := i_xStartCmd);
rtReset(CLK := i_xReset);

(* ---- Fault reset ---- *)
IF rtReset.Q THEN
    xFault := FALSE;
    iFaultCode := 0;
END_IF;

(* ---- Interlock latch ---- *)
(* Trip latches; reset only clears it once the interlock is healthy. *)
IF NOT i_xInterlockOk THEN
    xIlkLatch := TRUE;
ELSIF rtReset.Q THEN
    xIlkLatch := FALSE;
END_IF;

(* ---- Feedback supervision ---- *)
(* Mismatch between command and feedback for longer than the timeout. *)
(* Evaluated before the latch so the code reflects the previous scan.  *)
tonFbk(IN := xRunLatch XOR i_xRunFbk, PT := i_tFbkTimeout);

IF xRunLatch AND i_xRunFbk THEN
    xFbkSeen := TRUE;
END_IF;

IF tonFbk.Q AND NOT xFault THEN
    xFault := TRUE;
    IF NOT xRunLatch THEN
        iFaultCode := 3;            (* running without command *)
    ELSIF xFbkSeen THEN
        iFaultCode := 2;            (* feedback lost while running *)
    ELSE
        iFaultCode := 1;            (* failed to start *)
    END_IF;
END_IF;

(* ---- Run latch (stop dominant) ---- *)
(* Permissives (TRUE = inhibit) drop the command; a new start edge *)
(* is accepted as soon as they clear. Interlock trips need a reset. *)
IF i_xStopCmd OR i_xPermissives OR xIlkLatch OR xFault THEN
    xRunLatch := FALSE;
ELSIF rtStart.Q THEN
    xRunLatch := TRUE;
END_IF;

IF NOT xRunLatch THEN
    xFbkSeen := FALSE;
END_IF;

(* ---- Run hours ---- *)
(* Self-resetting 1 s tick; loses one scan per second (~0.1 % at 1 ms). *)
tonSec(IN := i_xRunFbk AND NOT tonSec.Q, PT := t#1s);
IF tonSec.Q THEN
    diRunSeconds := diRunSeconds + 1;
END_IF;

(* ---- Outputs ---- *)
q_xRunCmd    := xRunLatch;
q_xRunning   := xRunLatch AND i_xRunFbk;
q_xFault     := xFault;
q_xIlkTripped := xIlkLatch;
q_iFaultCode := iFaultCode;
q_rRunHours  := DINT_TO_REAL(diRunSeconds) / 3600.0;
