"""Check the EFC_Library project folder and package it for Ignition 8.1.

    python3 tools/package.py

Checks (static; no gateway needed)
  - project.json at the project root with title, parent, enabled, inheritable
  - every .json file parses
  - every resource.json is scope G / version 1 and lists files that exist
  - every view.json / style.json folder has a resource.json
  - style.json has base.style; variants have pseudo + style
  - every embedded view path points at a view in the project
  - Drawing (ia.shapes.svg) preserveAspectRatio is a bare 8.1 enum value
  - event scripts and script transforms compile as Python
  - expressions have balanced parentheses
  - every tag export under tags/ parses

Writes dist/EFC_Library.zip with project.json at the zip root, which is what
Gateway > Config > Projects > Import expects. Exit code 1 if any check fails.
"""
import json, os, sys, zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PROJECT = os.path.join(ROOT, "EFC_Library")
VIEWS = os.path.join(PROJECT, "com.inductiveautomation.perspective", "views")
ASPECT = {"none"} | {f"x{x}Y{y}" for x in ("Min", "Mid", "Max") for y in ("Min", "Mid", "Max")}
errors = []


def check_py(src, f):
    try:
        compile(src + "\n", f, "exec")
    except SyntaxError as e:
        errors.append(f"{f}: script syntax error line {e.lineno}: {e.msg}")


def walk(o, f, view_paths):
    if isinstance(o, dict):
        t = o.get("type")
        if t == "ia.shapes.svg":
            par = o.get("props", {}).get("preserveAspectRatio")
            if par is not None and par not in ASPECT:
                errors.append(f"{f}: preserveAspectRatio '{par}' is not a bare 8.1 value")
        if t in ("ia.display.view", "ia.display.flex-repeater"):
            p = o.get("props", {}).get("path")
            if isinstance(p, str) and p and p not in view_paths:
                errors.append(f"{f}: embedded view path '{p}' not in project")
        if t == "script" and isinstance(o.get("code"), str):
            check_py("def transform(self, value, quality, timestamp):\n" + o["code"], f)
        if t == "script" and isinstance(o.get("config"), dict) and "script" in o["config"]:
            check_py("def runAction(self, event):\n" + o["config"]["script"], f)
        if t == "expr" and isinstance(o.get("config"), dict):
            e = o["config"].get("expression", "")
            if e.count("(") != e.count(")"):
                errors.append(f"{f}: unbalanced parentheses in expression: {e[:80]}")
        for v in o.values():
            walk(v, f, view_paths)
    elif isinstance(o, list):
        for v in o:
            walk(v, f, view_paths)


def check():
    pj_path = os.path.join(PROJECT, "project.json")
    if not os.path.isfile(pj_path):
        errors.append("EFC_Library/project.json missing")
    else:
        pj = json.load(open(pj_path, encoding="utf-8"))
        for k in ("title", "parent", "enabled", "inheritable"):
            if k not in pj:
                errors.append(f"project.json lacks {k}")

    view_paths = set()
    for dp, _, files in os.walk(VIEWS):
        if "view.json" in files:
            view_paths.add(os.path.relpath(dp, VIEWS).replace(os.sep, "/"))

    n = 0
    for dp, _, files in os.walk(PROJECT):
        rel_dir = os.path.relpath(dp, ROOT)
        if ("view.json" in files or "style.json" in files or "stylesheet.css" in files) and "resource.json" not in files:
            errors.append(f"{rel_dir}: resource.json missing")
        for fn in files:
            if not fn.endswith(".json"):
                continue
            path = os.path.join(dp, fn)
            rel = os.path.relpath(path, ROOT)
            try:
                data = json.load(open(path, encoding="utf-8"))
            except Exception as e:
                errors.append(f"{rel}: invalid JSON ({e})")
                continue
            n += 1
            if fn == "resource.json":
                if data.get("scope") != "G" or data.get("version") != 1:
                    errors.append(f"{rel}: scope/version is not G/1")
                for f in data.get("files", []):
                    if not os.path.isfile(os.path.join(dp, f)):
                        errors.append(f"{rel}: lists missing file {f}")
            elif fn == "style.json":
                if "style" not in data.get("base", {}):
                    errors.append(f"{rel}: base.style missing")
                for v in data.get("variants", []):
                    if "pseudo" not in v or "style" not in v:
                        errors.append(f"{rel}: bad variant")
            elif fn == "view.json":
                walk(data, rel, view_paths)
    print(f"EFC_Library: {n} JSON files, {len(view_paths)} views checked")

    t = 0
    for dp, _, files in os.walk(os.path.join(ROOT, "tags")):
        for fn in files:
            if fn.endswith(".json"):
                t += 1
                try:
                    json.load(open(os.path.join(dp, fn), encoding="utf-8"))
                except Exception as e:
                    errors.append(f"tags/{fn}: invalid JSON ({e})")
    print(f"tags: {t} files checked")


def package():
    out_dir = os.path.join(ROOT, "dist")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "EFC_Library.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for dp, dirs, files in os.walk(PROJECT):
            dirs.sort()
            for fn in sorted(files):
                path = os.path.join(dp, fn)
                arc = os.path.relpath(path, PROJECT).replace(os.sep, "/")
                info = zipfile.ZipInfo(arc, date_time=(2026, 10, 7, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                with open(path, "rb") as fh:
                    z.writestr(info, fh.read())
    print(f"wrote {os.path.relpath(out, ROOT)}")


if __name__ == "__main__":
    check()
    if errors:
        for e in errors:
            print("FAIL", e)
        sys.exit(1)
    package()
    print("PASS")
