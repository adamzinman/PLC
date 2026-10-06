#!/usr/bin/env python3
"""Generate the Ignition Perspective 8.1 scale-station faceplate views.

Writes Perspective view resources under ignition/project/ and a Designer
importable zip under dist/. Re-run after editing this file:

    python3 tools/build_faceplates.py

Every faceplate takes the same view params and reads a ScaleStation UDT
instance (see ignition/tags/ScaleStation_tags.json):

    tagPath        e.g. "[default]Scales/Station1"
    stationNum     1..6
    weightUnits    "lb"
    pressureUnits  "psi"
"""

import json
import os
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_DIR = os.path.join(ROOT, "ignition", "project")
VIEWS_DIR = os.path.join(PROJECT_DIR, "com.inductiveautomation.perspective", "views")
DIST_ZIP = os.path.join(ROOT, "dist", "ScaleStationFaceplates.zip")
VIEW_FOLDER = "ScaleStation"

# UDT member names, keyed by the view.custom property that mirrors them.
MEMBERS = {
    "target": ("TargetWeight", True),
    "maxPressure": ("MaxPressure", True),
    "prefill": ("PrefillPressure", True),
    "sample": ("SampleWeight", True),
    "net": ("NetWeight", False),
    "tare": ("TareWeight", False),
    "total": ("TotalWeight", False),
    "message": ("Message", False),
    "selected": ("Selected", True),
}

SELECT_SCRIPT = (
    "\tpath = \"%s/Selected\" % self.view.params.tagPath\n"
    "\tcurrent = system.tag.readBlocking([path])[0].value\n"
    "\tsystem.tag.writeBlocking([path], [not bool(current)])"
)


# ---------------------------------------------------------------- helpers

def tag_binding(member, bidirectional=False):
    config = {
        "fallbackDelay": 2.5,
        "mode": "indirect",
        "references": {"station": "{view.params.tagPath}"},
        "tagPath": "{station}/" + member,
    }
    if bidirectional:
        config["bidirectional"] = True
    return {"binding": {"type": "tag", "config": config}}


def expr(expression):
    return {"binding": {"type": "expr", "config": {"expression": expression}}}


def prop(path, bidirectional=False):
    config = {"path": path}
    if bidirectional:
        config["bidirectional"] = True
    return {"binding": {"type": "property", "config": config}}


def fmt(key, pattern="#,##0.0"):
    """Expression that formats a view.custom number, showing -- when null."""
    ref = "{view.custom.%s}" % key
    return 'if(isNull(%s), "--", numberFormat(%s, "%s"))' % (ref, ref, pattern)


def sel(when_selected, when_not):
    """Expression choosing a value from the station's Selected state."""
    return 'if({view.custom.selected}, "%s", "%s")' % (when_selected, when_not)


def pos(basis="auto", grow=0, shrink=0):
    return {"basis": basis, "grow": grow, "shrink": shrink}


def comp(type_, name, props=None, position=None, prop_config=None,
         children=None, events=None):
    c = {"type": type_, "meta": {"name": name}}
    if position is not None:
        c["position"] = position
    if props is not None:
        c["props"] = props
    if prop_config:
        c["propConfig"] = prop_config
    if children is not None:
        c["children"] = children
    if events:
        c["events"] = events
    return c


def flex(name, children, direction="column", style=None, position=None,
         prop_config=None, **extra):
    props = {"direction": direction}
    props.update(extra)
    if style:
        props["style"] = style
    return comp("ia.container.flex", name, props, position, prop_config, children)


def label(name, text="", style=None, position=None, prop_config=None):
    props = {"text": text}
    if style:
        props["style"] = style
    return comp("ia.display.label", name, props, position, prop_config)


def numeric_field(name, key, style=None, position=None, pattern="0,0.0"):
    props = {"format": pattern}
    if style:
        props["style"] = style
    return comp("ia.input.numeric-entry-field", name, props, position,
                {"props.value": prop("view.custom." + key, True)})


def select_button(name, text_expr, style, position, bound_style):
    prop_config = {"props.text": expr(text_expr)}
    for key, expression in bound_style.items():
        prop_config["props.style." + key] = expr(expression)
    events = {"component": {"onActionPerformed": {
        "config": {"script": SELECT_SCRIPT}, "scope": "G", "type": "script"}}}
    return comp("ia.input.button", name, {"text": "", "style": style},
                position, prop_config, events=events)


def spacer(name, basis="auto", grow=1):
    return flex(name, [], position=pos(basis, grow, 1))


def make_view(root, width, height, extra_custom=None):
    custom = {key: None for key in MEMBERS}
    prop_config = {
        "params.tagPath": {"paramDirection": "input", "persistent": True},
        "params.stationNum": {"paramDirection": "input", "persistent": True},
        "params.weightUnits": {"paramDirection": "input", "persistent": True},
        "params.pressureUnits": {"paramDirection": "input", "persistent": True},
    }
    for key, (member, bidirectional) in MEMBERS.items():
        prop_config["custom." + key] = tag_binding(member, bidirectional)
    for key, expression in (extra_custom or {}).items():
        custom[key] = None
        prop_config["custom." + key] = expr(expression)
    return {
        "custom": custom,
        "params": {
            "tagPath": "[default]Scales/Station1",
            "stationNum": 1,
            "weightUnits": "lb",
            "pressureUnits": "psi",
        },
        "propConfig": prop_config,
        "props": {"defaultSize": {"width": width, "height": height}},
        "root": root,
    }


W_UNITS = "{view.params.weightUnits}"
P_UNITS = "{view.params.pressureUnits}"
STATION_TITLE = '"STATION " + toStr({view.params.stationNum})'
HAS_MSG = "len(trim(coalesce({view.custom.message}, \"\"))) > 0"
MSG_TEXT = 'if(%s, {view.custom.message}, "No message")' % HAS_MSG

SETPOINTS = [
    ("Target Weight", "target", W_UNITS),
    ("Sample Weight", "sample", W_UNITS),
    ("Max Pressure", "maxPressure", P_UNITS),
    ("Prefill Pressure", "prefill", P_UNITS),
]
WEIGHTS = [("Net", "net"), ("Tare", "tare"), ("Total", "total")]


# ------------------------------------------------- Option A: ISA-101 HP

def option_a():
    c = {"bg": "#DCDCDC", "panel": "#E9E9E9", "text": "#1A1A1A", "muted": "#555555",
         "edge": "#8C8C8C", "field": "#FFFFFF", "readout": "#CDCDCD", "sel": "#1F5FA8"}
    font = "Arial, Helvetica, sans-serif"

    def section(name, text):
        return label(name, text, position=pos("20px"), style={
            "fontSize": "11px", "fontWeight": "bold", "letterSpacing": "1px",
            "color": c["muted"], "borderBottom": "1px solid " + c["edge"],
            "marginTop": "6px"})

    def unit(name, unit_expr):
        return label(name, position=pos("38px"), style={"fontSize": "12px", "color": c["muted"], "paddingLeft": "6px"},
                     prop_config={"props.text": expr(unit_expr)})

    rows = [section("SetpointsHeader", "SETPOINTS")]
    for text, key, units in SETPOINTS:
        rows.append(flex(key + "Row", [
            label("Label", text, position=pos("auto", 1, 1), style={"fontSize": "13px", "color": c["text"]}),
            numeric_field("Field", key, position=pos("104px"), style={
                "backgroundColor": c["field"], "border": "1px solid " + c["edge"],
                "fontSize": "14px", "textAlign": "right"}),
            unit("Units", units),
        ], direction="row", alignItems="center", position=pos("30px")))

    rows.append(section("WeightsHeader", "WEIGHTS"))
    for text, key in WEIGHTS:
        bold = key == "total"
        rows.append(flex(key + "Row", [
            label("Label", text, position=pos("auto", 1, 1), style={
                "fontSize": "13px", "color": c["text"], "fontWeight": "bold" if bold else "normal"}),
            label("Value", position=pos("104px"), style={
                "backgroundColor": c["readout"], "border": "1px solid " + c["edge"],
                "fontSize": "15px", "fontWeight": "bold", "textAlign": "right",
                "justifyContent": "flex-end", "padding": "2px 6px", "color": c["text"],
                "fontVariantNumeric": "tabular-nums"},
                prop_config={"props.text": expr(fmt(key))}),
            unit("Units", W_UNITS),
        ], direction="row", alignItems="center", position=pos("30px")))

    rows.append(section("MessageHeader", "PLC MESSAGE"))
    rows.append(label("Message", position=pos("54px"), style={
        "backgroundColor": c["panel"], "border": "1px solid " + c["edge"],
        "padding": "4px 8px", "fontSize": "13px", "whiteSpace": "normal",
        "overflowY": "auto", "alignItems": "flex-start"},
        prop_config={"props.text": expr(MSG_TEXT),
                     "props.style.color": expr('if(%s, "%s", "%s")' % (HAS_MSG, c["text"], "#7A7A7A"))}))

    header = flex("Header", [
        flex("SelectedBar", [], position=pos("6px"),
             prop_config={"props.style.backgroundColor": expr(sel(c["sel"], c["edge"]))}),
        label("Title", position=pos("auto", 1, 1), style={
            "fontSize": "15px", "fontWeight": "bold", "paddingLeft": "10px", "color": c["text"]},
            prop_config={"props.text": expr(STATION_TITLE)}),
        flex("StateIndicator", [], position=pos("12px"), style={"height": "12px", "border": "1px solid #333333"},
             prop_config={"props.style.backgroundColor": expr(sel(c["sel"], c["bg"]))}),
        label("State", position=pos("104px"), style={
            "fontSize": "11px", "fontWeight": "bold", "paddingLeft": "6px"},
            prop_config={"props.text": expr(sel("SELECTED", "NOT SELECTED")),
                         "props.style.color": expr(sel(c["sel"], c["muted"]))}),
    ], direction="row", alignItems="center", position=pos("40px"),
        style={"backgroundColor": c["panel"], "borderBottom": "1px solid " + c["edge"], "paddingRight": "8px"})

    body = flex("Body", rows, position=pos("auto", 1, 1),
                style={"padding": "6px 12px", "gap": "4px", "overflowY": "auto"})

    footer = flex("Footer", [
        select_button("SelectButton", sel("DESELECT STATION", "SELECT STATION"),
                      {"fontSize": "13px", "fontWeight": "bold", "borderRadius": "2px",
                       "border": "1px solid #333333"},
                      pos("auto", 1, 1),
                      {"backgroundColor": sel(c["sel"], c["readout"]),
                       "color": sel("#FFFFFF", c["text"])}),
    ], direction="row", position=pos("52px"), style={"padding": "8px 12px"})

    root = flex("root", [header, body, footer], style={
        "backgroundColor": c["bg"], "fontFamily": font,
        "border": "1px solid " + c["edge"]})
    return make_view(root, 320, 480)


# ------------------------------------------- Option B: Dark control room

def option_b():
    c = {"bg": "#0E141B", "panel": "#151E28", "edge": "#253241", "text": "#E6EDF3",
         "muted": "#8B9BAD", "accent": "#38BDF8", "sel": "#22C55E", "idle": "#475569",
         "console": "#0A0F14", "consoleText": "#4ADE80"}
    mono = "Consolas, 'Roboto Mono', 'Courier New', monospace"
    font = "'Segoe UI', Roboto, Arial, sans-serif"
    panel = {"backgroundColor": c["panel"], "border": "1px solid " + c["edge"], "borderRadius": "6px"}

    def caption(name, text=None, text_expr=None, basis="16px"):
        return label(name, text or "", position=pos(basis), style={
            "fontSize": "10px", "letterSpacing": "1.2px", "color": c["muted"]},
            prop_config={"props.text": expr(text_expr)} if text_expr else None)

    def small_tile(name, title, key):
        return flex(name, [
            caption("Caption", title),
            flex("ValueRow", [
                label("Value", position=pos("auto", 1, 1), style={
                    "fontFamily": mono, "fontSize": "20px", "color": c["text"]},
                    prop_config={"props.text": expr(fmt(key))}),
                label("Units", position=pos("auto"), style={"fontSize": "11px", "color": c["muted"]},
                      prop_config={"props.text": expr(W_UNITS)}),
            ], direction="row", alignItems="baseline", position=pos("auto", 1, 1)),
        ], position=pos("0px", 1, 1), style=dict(panel, padding="8px 10px"))

    def setpoint_cell(text, key, units):
        return flex(key + "Cell", [
            caption("Caption", text_expr='"%s (" + %s + ")"' % (text.upper().replace("PRESSURE", "PRESS."), units)),
            numeric_field("Field", key, position=pos("32px"), style={
                "backgroundColor": c["console"], "color": c["text"], "border": "1px solid " + c["edge"],
                "borderRadius": "4px", "fontFamily": mono, "fontSize": "15px"}),
        ], position=pos("0px", 1, 1), style={"gap": "4px"})

    header = flex("Header", [
        flex("Led", [], position=pos("12px"), style={"height": "12px", "borderRadius": "50%"},
             prop_config={"props.style.backgroundColor": expr(sel(c["sel"], c["idle"])),
                          "props.style.boxShadow": expr(sel("0 0 8px " + c["sel"], "none"))}),
        label("Title", position=pos("auto", 1, 1), style={
            "fontSize": "16px", "fontWeight": "600", "letterSpacing": "1px",
            "color": c["text"], "paddingLeft": "10px"},
            prop_config={"props.text": expr(STATION_TITLE)}),
        label("StatePill", position=pos("90px"), style={
            "fontSize": "10px", "fontWeight": "bold", "letterSpacing": "1px", "color": "#0E141B",
            "borderRadius": "10px", "padding": "3px 0", "textAlign": "center", "justifyContent": "center"},
            prop_config={"props.text": expr(sel("SELECTED", "STANDBY")),
                         "props.style.backgroundColor": expr(sel(c["sel"], c["idle"]))}),
    ], direction="row", alignItems="center", position=pos("36px"))

    hero = flex("NetPanel", [
        caption("Caption", "NET WEIGHT"),
        flex("ValueRow", [
            label("Value", position=pos("auto", 1, 1), style={
                "fontFamily": mono, "fontSize": "44px", "color": c["accent"], "lineHeight": "1"},
                prop_config={"props.text": expr(fmt(key="net"))}),
            label("Units", position=pos("auto"), style={"fontSize": "16px", "color": c["muted"]},
                  prop_config={"props.text": expr(W_UNITS)}),
        ], direction="row", alignItems="baseline", position=pos("auto", 1, 1)),
    ], position=pos("96px"), style=dict(panel, padding="10px 12px"))

    weights = flex("TareTotal", [small_tile("Tare", "TARE", "tare"), small_tile("Total", "TOTAL", "total")],
                   direction="row", position=pos("66px"), style={"gap": "8px"})

    setpoints = flex("Setpoints", [
        caption("Caption", "SETPOINTS", basis="14px"),
        flex("Row1", [setpoint_cell(*SETPOINTS[0]), setpoint_cell(*SETPOINTS[1])],
             direction="row", position=pos("auto"), style={"gap": "10px"}),
        flex("Row2", [setpoint_cell(*SETPOINTS[2]), setpoint_cell(*SETPOINTS[3])],
             direction="row", position=pos("auto"), style={"gap": "10px"}),
    ], position=pos("auto"), style=dict(panel, padding="10px 12px", gap="8px"))

    console = flex("Console", [
        caption("Caption", "PLC MESSAGE", basis="14px"),
        label("Message", position=pos("auto", 1, 1), style={
            "fontFamily": mono, "fontSize": "13px", "whiteSpace": "normal",
            "alignItems": "flex-start", "overflowY": "auto"},
            prop_config={"props.text": expr('"> " + ' + MSG_TEXT),
                         "props.style.color": expr('if(%s, "%s", "%s")' % (HAS_MSG, c["consoleText"], c["muted"]))}),
    ], position=pos("64px"), style={"backgroundColor": c["console"], "border": "1px solid " + c["edge"],
                                     "borderRadius": "6px", "padding": "6px 10px", "gap": "2px"})

    footer = flex("Footer", [
        label("Label", position=pos("auto", 1, 1), style={"fontSize": "13px", "color": c["text"]},
              prop_config={"props.text": expr(sel("Station selected", "Station not selected"))}),
        comp("ia.input.toggle-switch", "SelectToggle", {"selected": False}, pos("60px"),
             {"props.selected": prop("view.custom.selected", True)}),
    ], direction="row", alignItems="center", position=pos("44px"),
        style=dict(panel, padding="0 12px"))

    root = flex("root", [header, hero, weights, setpoints, console, footer], style={
        "backgroundColor": c["bg"], "fontFamily": font, "padding": "10px 12px", "gap": "8px",
        "borderWidth": "2px", "borderStyle": "solid"},
        prop_config={"props.style.borderColor": expr(sel(c["sel"], c["edge"]))})
    return make_view(root, 340, 540)


# -------------------------------------------- Option C: Touch-friendly cards

def option_c():
    c = {"bg": "#EEF2F7", "card": "#FFFFFF", "edge": "#D5DDE8", "text": "#1B2733",
         "muted": "#5B6B7F", "primary": "#1D5FD1", "primaryTint": "#E6EEFC",
         "good": "#15803D", "goodTint": "#DCFCE7", "warn": "#B45309", "warnTint": "#FEF3C7"}
    font = "'Segoe UI', Roboto, Arial, sans-serif"
    card = {"backgroundColor": c["card"], "border": "1px solid " + c["edge"],
            "borderRadius": "12px", "boxShadow": "0 1px 3px rgba(27,39,51,0.08)"}

    def weight_tile(title, key):
        net = key == "net"
        style = dict(card, padding="10px 12px", gap="2px")
        if net:
            style.update(backgroundColor=c["primaryTint"], border="1px solid " + c["primary"])
        return flex(key + "Tile", [
            label("Caption", title, position=pos("16px"), style={
                "fontSize": "12px", "fontWeight": "600", "color": c["primary"] if net else c["muted"]}),
            label("Value", position=pos("auto", 1, 1), style={
                "fontSize": "26px" if net else "22px", "fontWeight": "600", "color": c["text"],
                "fontVariantNumeric": "tabular-nums"},
                prop_config={"props.text": expr(fmt(key))}),
            label("Units", position=pos("14px"), style={"fontSize": "11px", "color": c["muted"]},
                  prop_config={"props.text": expr(W_UNITS)}),
        ], position=pos("0px", 1.3 if net else 1, 1), style=style)

    def setpoint_cell(text, key, units):
        return flex(key + "Cell", [
            label("Caption", position=pos("16px"), style={"fontSize": "12px", "color": c["muted"]},
                  prop_config={"props.text": expr('"%s (" + %s + ")"' % (text, units))}),
            numeric_field("Field", key, position=pos("44px"), style={
                "fontSize": "18px", "borderRadius": "8px", "border": "1px solid " + c["edge"],
                "backgroundColor": "#F8FAFC", "color": c["text"]}),
        ], position=pos("0px", 1, 1), style={"gap": "4px"})

    header = flex("Header", [
        flex("Titles", [
            label("Title", position=pos("26px"), style={"fontSize": "20px", "fontWeight": "700", "color": c["text"]},
                  prop_config={"props.text": expr('"Station " + toStr({view.params.stationNum})')}),
            label("Path", position=pos("16px"), style={"fontSize": "11px", "color": c["muted"]},
                  prop_config={"props.text": expr("{view.params.tagPath}")}),
        ], position=pos("auto", 1, 1)),
        label("Chip", position=pos("104px"), style={
            "fontSize": "12px", "fontWeight": "600", "borderRadius": "14px", "padding": "5px 0",
            "textAlign": "center", "justifyContent": "center"},
            prop_config={"props.text": expr(sel("Selected", "Not selected")),
                         "props.style.backgroundColor": expr(sel(c["goodTint"], "#E2E8F0")),
                         "props.style.color": expr(sel(c["good"], c["muted"]))}),
    ], direction="row", alignItems="center", position=pos("64px"), style=dict(card, padding="8px 14px"))

    weights = flex("Weights", [weight_tile("Net", "net"), weight_tile("Tare", "tare"), weight_tile("Total", "total")],
                   direction="row", position=pos("96px"), style={"gap": "8px"})

    setpoints = flex("Setpoints", [
        label("Caption", "Setpoints", position=pos("20px"),
              style={"fontSize": "14px", "fontWeight": "700", "color": c["text"]}),
        flex("Row1", [setpoint_cell(*SETPOINTS[0]), setpoint_cell(*SETPOINTS[1])],
             direction="row", position=pos("auto"), style={"gap": "12px"}),
        flex("Row2", [setpoint_cell(*SETPOINTS[2]), setpoint_cell(*SETPOINTS[3])],
             direction="row", position=pos("auto"), style={"gap": "12px"}),
    ], position=pos("auto"), style=dict(card, padding="12px 14px", gap="10px"))

    banner = flex("MessageBanner", [
        comp("ia.display.icon", "Icon", {"path": "material/info_outline"}, pos("24px"),
             {"props.color": expr('if(%s, "%s", "%s")' % (HAS_MSG, c["warn"], c["muted"]))}),
        label("Message", position=pos("auto", 1, 1), style={
            "fontSize": "14px", "whiteSpace": "normal", "paddingLeft": "8px", "overflowY": "auto"},
            prop_config={"props.text": expr(MSG_TEXT),
                         "props.style.color": expr('if(%s, "%s", "%s")' % (HAS_MSG, c["text"], c["muted"]))}),
    ], direction="row", alignItems="center", position=pos("60px"),
        style={"borderRadius": "12px", "padding": "8px 14px", "borderWidth": "1px", "borderStyle": "solid"},
        prop_config={"props.style.backgroundColor": expr('if(%s, "%s", "%s")' % (HAS_MSG, c["warnTint"], c["card"])),
                     "props.style.borderColor": expr('if(%s, "#F59E0B", "%s")' % (HAS_MSG, c["edge"]))})

    button = select_button("SelectButton", sel("✓  Selected  (tap to deselect)", "Select Station"),
                           {"fontSize": "16px", "fontWeight": "600", "borderRadius": "12px",
                            "borderWidth": "2px", "borderStyle": "solid", "borderColor": c["primary"]},
                           pos("56px"),
                           {"backgroundColor": sel(c["primary"], c["card"]),
                            "color": sel("#FFFFFF", c["primary"])})

    root = flex("root", [header, weights, setpoints, banner, button], style={
        "backgroundColor": c["bg"], "fontFamily": font, "padding": "12px", "gap": "10px",
        "borderWidth": "3px", "borderStyle": "solid", "borderRadius": "14px"},
        prop_config={"props.style.borderColor": expr(sel(c["primary"], "transparent"))})
    return make_view(root, 380, 580)


# ---------------------------------------------- Option D: Compact fill tile

def option_d():
    c = {"bg": "#F7F8FA", "edge": "#CBD2DC", "text": "#1F2933", "muted": "#64707D",
         "head": "#3A4655", "sel": "#0F7B4F", "fill": "#2563EB", "done": "#16A34A",
         "track": "#E2E8F0", "warn": "#D97706"}
    font = "'Segoe UI', Roboto, Arial, sans-serif"
    pct = "{view.custom.pctOfTarget}"

    header = flex("Header", [
        label("Number", position=pos("34px"), style={
            "height": "34px", "borderRadius": "50%", "backgroundColor": "rgba(255,255,255,0.18)",
            "color": "#FFFFFF", "fontSize": "18px", "fontWeight": "700",
            "textAlign": "center", "justifyContent": "center"},
            prop_config={"props.text": expr("toStr({view.params.stationNum})")}),
        flex("Titles", [
            label("Title", "STATION", position=pos("16px"), style={
                "fontSize": "11px", "letterSpacing": "1.5px", "color": "rgba(255,255,255,0.75)"}),
            label("State", position=pos("18px"), style={"fontSize": "13px", "fontWeight": "700", "color": "#FFFFFF"},
                  prop_config={"props.text": expr(sel("SELECTED", "IDLE"))}),
        ], position=pos("auto", 1, 1), style={"paddingLeft": "8px"}),
        select_button("SelectButton", sel("DESELECT", "SELECT"),
                      {"fontSize": "11px", "fontWeight": "700", "borderRadius": "4px",
                       "border": "1px solid rgba(255,255,255,0.6)", "padding": "0 6px"},
                      pos("74px"),
                      {"backgroundColor": sel("#FFFFFF", "transparent"),
                       "color": sel(c["sel"], "#FFFFFF")}),
    ], direction="row", alignItems="center", position=pos("54px"),
        style={"padding": "0 10px", "height": "54px"},
        prop_config={"props.style.backgroundColor": expr(sel(c["sel"], c["head"]))})

    net = flex("Net", [
        label("Caption", "NET", position=pos("14px"), style={
            "fontSize": "11px", "letterSpacing": "1.5px", "color": c["muted"], "justifyContent": "center"}),
        label("Value", position=pos("40px"), style={
            "fontSize": "34px", "fontWeight": "700", "color": c["text"], "justifyContent": "center",
            "fontVariantNumeric": "tabular-nums"},
            prop_config={"props.text": expr(fmt("net"))}),
        label("Units", position=pos("14px"), style={"fontSize": "11px", "color": c["muted"], "justifyContent": "center"},
              prop_config={"props.text": expr(W_UNITS)}),
    ], position=pos("auto"), style={"padding": "8px 10px 4px"})

    fill = flex("FillBar", [
        flex("Track", [
            flex("Fill", [], position=pos("0%"),
                 prop_config={"position.basis": expr('toStr(round(%s, 1)) + "%%"' % pct),
                              "props.style.backgroundColor": expr('if(%s >= 100, "%s", "%s")' % (pct, c["done"], c["fill"]))}),
        ], direction="row", position=pos("10px"),
            style={"backgroundColor": c["track"], "borderRadius": "5px", "overflow": "hidden"}),
        label("Caption", position=pos("16px"), style={"fontSize": "11px", "color": c["muted"], "justifyContent": "center"},
              prop_config={"props.text": expr(
                  'numberFormat(%s, "0") + "%% of target  (" + %s + " " + %s + ")"' % (pct, fmt("target"), W_UNITS))}),
    ], position=pos("auto"), style={"padding": "0 12px", "gap": "4px"})

    def mini(title, key):
        return flex(key + "Mini", [
            label("Caption", title, position=pos("14px"), style={
                "fontSize": "10px", "letterSpacing": "1px", "color": c["muted"], "justifyContent": "center"}),
            label("Value", position=pos("20px"), style={
                "fontSize": "15px", "fontWeight": "600", "color": c["text"], "justifyContent": "center",
                "fontVariantNumeric": "tabular-nums"},
                prop_config={"props.text": expr(fmt(key))}),
        ], position=pos("0px", 1, 1))

    minis = flex("TareTotal", [mini("TARE", "tare"), mini("TOTAL", "total")], direction="row",
                 position=pos("auto"), style={"margin": "8px 10px", "padding": "6px 0",
                                              "borderTop": "1px solid " + c["edge"],
                                              "borderBottom": "1px solid " + c["edge"]})

    short = {"target": "Target", "sample": "Sample", "maxPressure": "Max press.", "prefill": "Prefill"}
    rows = []
    for _, key, units in SETPOINTS:
        rows.append(flex(key + "Row", [
            label("Label", position=pos("auto", 1, 1), style={"fontSize": "12px", "color": c["text"]},
                  prop_config={"props.text": expr('"%s (" + %s + ")"' % (short[key], units))}),
            numeric_field("Field", key, position=pos("84px"), style={
                "fontSize": "13px", "border": "1px solid " + c["edge"], "borderRadius": "3px",
                "backgroundColor": "#FFFFFF"}),
        ], direction="row", alignItems="center", position=pos("28px")))
    setpoints = flex("Setpoints", rows, position=pos("auto"), style={"padding": "0 10px", "gap": "4px"})

    message = label("Message", position=pos("auto", 1, 1), style={
        "margin": "8px 10px 10px", "padding": "6px 8px", "fontSize": "12px", "whiteSpace": "normal",
        "alignItems": "flex-start", "overflowY": "auto", "backgroundColor": "#FFFFFF",
        "borderLeftWidth": "4px", "borderLeftStyle": "solid", "minHeight": "40px"},
        prop_config={"props.text": expr(MSG_TEXT),
                     "props.style.borderLeftColor": expr('if(%s, "%s", "%s")' % (HAS_MSG, c["warn"], c["edge"])),
                     "props.style.color": expr('if(%s, "%s", "%s")' % (HAS_MSG, c["text"], c["muted"]))})

    root = flex("root", [header, net, fill, minis, setpoints, message], style={
        "backgroundColor": c["bg"], "fontFamily": font, "border": "1px solid " + c["edge"],
        "borderRadius": "6px", "overflow": "hidden"})
    pct_expr = ("if(coalesce({view.custom.target}, 0) <= 0, 0, "
                "min(100, max(0, 100.0 * coalesce({view.custom.net}, 0) / {view.custom.target})))")
    return make_view(root, 230, 480, extra_custom={"pctOfTarget": pct_expr})


# ------------------------------------------------ Overview (all 6 stations)

OPTIONS = [
    ("OptionA_HighPerformance", "A - ISA-101 High Performance", option_a),
    ("OptionB_DarkControlRoom", "B - Dark Control Room", option_b),
    ("OptionC_TouchCards", "C - Touch Cards", option_c),
    ("OptionD_CompactTile", "D - Compact Fill Tile", option_d),
]


def overview():
    options = [{"value": "%s/%s" % (VIEW_FOLDER, name), "label": text} for name, text, _ in OPTIONS]
    instances = [{"tagPath": "[default]Scales/Station%d" % n, "stationNum": n,
                  "weightUnits": "lb", "pressureUnits": "psi"} for n in range(1, 7)]
    header = flex("Header", [
        label("Title", "Scale Stations", position=pos("auto", 1, 1),
              style={"fontSize": "20px", "fontWeight": "700", "color": "#1F2933"}),
        label("PickerLabel", "Faceplate", position=pos("80px"), style={"fontSize": "13px", "color": "#64707D"}),
        comp("ia.input.dropdown", "FaceplatePicker", {"options": options, "value": options[0]["value"]},
             pos("260px"), {"props.value": prop("view.custom.faceplate", True)}),
    ], direction="row", alignItems="center", position=pos("48px"), style={"padding": "0 16px"})
    repeater = comp("ia.display.flex-repeater", "Stations", {
        "path": options[0]["value"],
        "instances": instances,
        "direction": "row",
        "wrap": "wrap",
        "alignContent": "flex-start",
        "useDefaultViewWidth": True,
        "useDefaultViewHeight": True,
        "style": {"gap": "12px", "padding": "0 16px 16px", "overflowY": "auto"},
    }, pos("auto", 1, 1), {"props.path": prop("view.custom.faceplate")})
    root = flex("root", [header, repeater], style={
        "backgroundColor": "#E9ECEF", "fontFamily": "'Segoe UI', Roboto, Arial, sans-serif"})
    return {
        "custom": {"faceplate": options[0]["value"]},
        "params": {},
        "props": {"defaultSize": {"width": 1400, "height": 1100}},
        "root": root,
    }


# ------------------------------------------------------------------ output

RESOURCE = {"scope": "G", "version": 1, "restricted": False, "overridable": True,
            "files": ["view.json"], "attributes": {}}


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, sort_keys=False)
        f.write("\n")


def main():
    views = [(name, builder()) for name, _, builder in OPTIONS]
    views.append(("Overview", overview()))
    for name, view in views:
        folder = os.path.join(VIEWS_DIR, VIEW_FOLDER, name)
        write_json(os.path.join(folder, "view.json"), view)
        write_json(os.path.join(folder, "resource.json"), RESOURCE)

    write_json(os.path.join(PROJECT_DIR, "project.json"), {
        "title": "ScaleStationFaceplates",
        "description": "Scale station faceplate options (generated by tools/build_faceplates.py)",
        "parent": "", "enabled": True, "inheritable": False})

    os.makedirs(os.path.dirname(DIST_ZIP), exist_ok=True)
    with zipfile.ZipFile(DIST_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for base, _, files in os.walk(PROJECT_DIR):
            for fname in sorted(files):
                full = os.path.join(base, fname)
                zf.write(full, os.path.relpath(full, PROJECT_DIR))
    print("Wrote %d views and %s" % (len(views), os.path.relpath(DIST_ZIP, ROOT)))


if __name__ == "__main__":
    main()
