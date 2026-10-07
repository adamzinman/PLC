# EFC ISA-101 Color Palette

Light-gray HMI color palette for Ignition Perspective screens, as implemented in the EFC_Styles style class library.

## About ISA-101

ANSI/ISA-101.01-2015 does not specify hex codes. It requires a neutral, low-contrast gray background, muted grays for normal equipment states, and saturated color reserved for abnormal conditions and alarms. Exact values are left to each site's HMI style guide. This file is that guide for EFC.

**Screen background: `#D9D9D9`** (RGB 217, 217, 217).

## Rules

- Use alarm colors only for alarms. Never use them for decoration or normal states.
- Show normal equipment states in grayscale.
- Show faults in dark gray (`#3A3A3A`); the alarm outline carries the priority color.
- Exception: the manual-mode **M** marker shares `#FFD200` with Medium alarms.

## Backgrounds and structure

| Use | Key | Hex | RGB |
|---|---|---|---|
| Screen / process area (page background) | `screen` | `#D9D9D9` | 217, 217, 217 |
| Header bar | `header` | `#C4C4C4` | 196, 196, 196 |
| Left menu | `menu` | `#CCCCCC` | 204, 204, 204 |
| Right trend panel | `trend` | `#E0E0E0` | 224, 224, 224 |
| Bottom alarm bar | `alarmBar` | `#BDBDBD` | 189, 189, 189 |
| Panel | `panel` | `#E6E6E6` | 230, 230, 230 |
| Card | `card` | `#F0F0F0` | 240, 240, 240 |
| Inset | `inset` | `#CFCFCF` | 207, 207, 207 |
| Editable entry field | `field` | `#FFFFFF` | 255, 255, 255 |
| Read-only field | `readonly` | `#EDEDED` | 237, 237, 237 |
| Border | `border` | `#A6A6A6` | 166, 166, 166 |
| Border, dark | `borderDark` | `#7F7F7F` | 127, 127, 127 |
| Border, extra dark | `borderXDark` | `#595959` | 89, 89, 89 |

## Text and interaction

| Use | Key | Hex | RGB |
|---|---|---|---|
| Primary text | `text` | `#1F1F1F` | 31, 31, 31 |
| Muted text | `textMuted` | `#4D4D4D` | 77, 77, 77 |
| Faint text | `textFaint` | `#5A5A5A` | 90, 90, 90 |
| Disabled text | `textDisabled` | `#9A9A9A` | 154, 154, 154 |
| Inverse text | `textInverse` | `#FFFFFF` | 255, 255, 255 |
| Accent (primary button / active nav) | `accent` | `#4D4D4D` | 77, 77, 77 |
| Editable values (setpoints, operator entry) | `editable` | `#1F4E99` | 31, 78, 153 |
| Link | `link` | `#1F4E99` | 31, 78, 153 |
| Hover | `hover` | `#F5F5F5` | 245, 245, 245 |
| Pressed | `pressed` | `#BFBFBF` | 191, 191, 191 |
| Highlight / search hit | `highlight` | `#DCE3EC` | 220, 227, 236 |

## Equipment states

| Use | Key | Hex | RGB |
|---|---|---|---|
| Running | `running` | `#FFFFFF` | 255, 255, 255 |
| Stopped | `stopped` | `#9E9E9E` | 158, 158, 158 |
| Transitioning (opening/closing/starting/stopping) | `transition` | `#C4C4C4` | 196, 196, 196 |
| Fault (dark gray; red is reserved for Critical alarms) | `fault` | `#3A3A3A` | 58, 58, 58 |
| Manual | `manual` | `#595959` | 89, 89, 89 |
| Manual-mode M marker | `manualM` | `#FFD200` | 255, 210, 0 |
| Simulated / forced (fill) | `simulated` | `#D7EEEB` | 215, 238, 235 |
| Simulated / forced (text) | `simulatedText` | `#00695C` | 0, 105, 92 |
| Bad quality | `badQuality` | `#B000B0` | 176, 0, 176 |
| Permissive P badge | `permissiveBadge` | `#F08000` | 240, 128, 0 |
| Interlock I badge | `interlock` | `#C00000` | 192, 0, 0 |

## Alarm priorities (the only saturated colors)

| Use | Key | Hex | RGB |
|---|---|---|---|
| Critical | `alarmCritical` | `#D50000` | 213, 0, 0 |
| High | `alarmHigh` | `#FF7A00` | 255, 122, 0 |
| Medium | `alarmMedium` | `#FFD200` | 255, 210, 0 |
| Low | `alarmLow` | `#00A3E0` | 0, 163, 224 |
| Diagnostic | `alarmDiag` | `#7A7A7A` | 122, 122, 122 |

## Source

Values come from the palette in `style-library-generator.py` (EFC_Styles). If the two disagree, the generator is the source of truth; update this file to match.
