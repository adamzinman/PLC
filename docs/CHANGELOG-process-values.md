# Changelog

## 1.3.0 (2026-10-07)
- Cards are now 100 × 50 at 1080p, and the views are 104 × 54 including the shadow margin. Resize any instances already placed.
- At most 2 letters show. Any further letters collapse into a `+N` box, whose tooltip lists the hidden letters and which blinks if any of them is unacknowledged.
- New style classes: `PV/Tag`, `PV/Value`, `PV/ValueSmall`, `PV/Units`, `PV/Chip/More`. Letters are now 9 px text on 12 px boxes.
- PV_RangeBar: the range end labels were removed; hover the bar to see the range. `Bar/RangeLabel` was deleted.

## 1.2.0 (2026-10-06)
- New card style: white background, 6 px corners, a 1 px #B3B3B3 border with a darker bottom edge, and a soft shadow (`PV/Card`).
- New `PV/Shell` wrapper so the embedding container doesn't clip the shadow.

## 1.1.0 (2026-10-06)
- Alarm states now come from one `system.alarm.queryStatus` call per template per second, in a script transform on `custom.alm`. This replaces `isAlarmActiveFiltered`, whose bindings showed errors in the Designer and never updated in Perspective.

## 1.0.0 (2026-10-06)
- First release: PV_StatusStrip (A1), PV_RangeBar (B2), the _Demo view and demo tags.
