(* MAST section: Pumps - example DFB_Motor instance *)
(* Declare in Data Editor -> Variables:                         *)
(*   P101       : DFB_Motor                                     *)
(*   P101_Start, P101_Stop, P101_Fbk, P101_Reset, P101_Run,     *)
(*   P101_Fault, P101_IlkTrip                                   *)
(*              : EBOOL  (map to %I / %Q / %M as required)      *)
(*   P101_Perm  : BOOL   (non-safety inhibit, TRUE = inhibit)   *)
(*   LT101_HiHi : BOOL   (dry-run / level interlock)            *)

P101(i_xStartCmd    := P101_Start,
     i_xStopCmd     := P101_Stop,
     i_xRunFbk      := P101_Fbk,
     i_xPermissives := P101_Perm,
     i_xInterlockOk := NOT LT101_HiHi,
     i_xReset       := P101_Reset,
     i_tFbkTimeout  := t#3s,
     q_xRunCmd      => P101_Run,
     q_xFault       => P101_Fault,
     q_xIlkTripped  => P101_IlkTrip);

(* Reset is written TRUE by Ignition; the PLC clears it so the next *)
(* press gives a fresh rising edge.                                 *)
P101_Reset := FALSE;
