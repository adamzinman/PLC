# DFB_Motor: interface

Target: EcoStruxure Control Expert Classic V16.2 (M340 / M580).
Enter these in **Data Editor → DFB Types → DFB_Motor**. Then create one ST section
inside the DFB and paste `DFB_Motor.st` into it.

## Inputs
| Name             | Type | Initial | Comment                                         |
|------------------|------|---------|-------------------------------------------------|
| i_xStartCmd      | BOOL | FALSE   | Start request (rising edge)                     |
| i_xStopCmd       | BOOL | FALSE   | Stop request (level, stop dominant)             |
| i_xRunFbk        | BOOL | FALSE   | Contactor / drive running feedback              |
| i_xPermissives   | BOOL | FALSE   | Non-safety inhibit; TRUE removes run command, no reset needed |
| i_xInterlockOk   | BOOL | TRUE    | FALSE trips and latches; needs reset before a new start |
| i_xReset         | BOOL | FALSE   | Fault / interlock reset from SCADA (rising edge) |
| i_tFbkTimeout    | TIME | t#3s    | Max command/feedback mismatch before faulting   |

## Outputs
| Name             | Type | Initial | Comment                                         |
|------------------|------|---------|-------------------------------------------------|
| q_xRunCmd        | BOOL | FALSE   | Run command to contactor / drive                |
| q_xRunning       | BOOL | FALSE   | Commanded AND feedback present                  |
| q_xFault         | BOOL | FALSE   | Latched fault                                   |
| q_xIlkTripped    | BOOL | FALSE   | Latched interlock trip, awaiting reset          |
| q_iFaultCode     | INT  | 0       | 0 none, 1 fail to start, 2 feedback lost, 3 uncommanded run |
| q_rRunHours      | REAL | 0.0     | Accumulated run hours                           |

## Private variables
| Name             | Type   | Initial | Comment                                       |
|------------------|--------|---------|-----------------------------------------------|
| rtStart          | R_TRIG |         | Start edge                                    |
| rtReset          | R_TRIG |         | Reset edge                                    |
| tonFbk           | TON    |         | Command/feedback mismatch timer               |
| tonSec           | TON    |         | 1 s run-time tick                             |
| xRunLatch        | BOOL   | FALSE   | Internal run latch                            |
| xFbkSeen         | BOOL   | FALSE   | Feedback has been seen during this run        |
| xFault           | BOOL   | FALSE   | Internal fault latch                          |
| xIlkLatch        | BOOL   | FALSE   | Interlock trip latch                          |
| iFaultCode       | INT    | 0       | Internal fault code                           |
| diRunSeconds     | DINT   | 0       | Run-time counter (retained on warm restart)   |
