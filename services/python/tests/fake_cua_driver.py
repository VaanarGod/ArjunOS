#!/usr/bin/env python3
"""A fake Cua Driver: a REAL MCP server over stdio that follows the published tool reference (tool names, window-targeted calls, element tokens, snapshots,
structured action results). It is a test double written from the documentation: it proves the bridge's adapter speaks that contract, NOT that the real
driver behaves this way. Every call is appended to the JSON-lines file in FAKE_CUA_LOG so tests can see exactly what was sent.

Flags: --no-click-param-element_token (the schema lacks a parameter)   --missing-tool=hotkey   --noop-first-click   --no-permissions
"""
import json, os, sys

ARGS = sys.argv[1:]
LOG = open(os.environ.get("FAKE_CUA_LOG", os.devnull), "a")
SESSION_LOG = os.environ.get("FAKE_CUA_LOG")

def flag(name): return any(a == name for a in ARGS)
MISSING = next((a.split("=", 1)[1] for a in ARGS if a.startswith("--missing-tool=")), "")

def schema(*props): return {"type": "object", "properties": {p: {} for p in props}}
TOOLS = {
    "list_apps": schema("session"), "list_windows": schema("pid", "on_screen_only", "app", "session"), "launch_app": schema("name", "bundle_id", "urls", "session"),
    "get_window_state": schema("pid", "window_id", "tree_format", "include_screenshot", "max_dimension", "screenshot_format", "max_elements", "query", "since", "session"),
    "click": schema("element_token", "x", "y", "target", "button", "delivery_mode", "session") if not flag("--no-click-param-element_token") else schema("x", "y", "target", "delivery_mode", "button", "session"),
    "double_click": schema("element_token", "x", "y", "target", "delivery_mode", "session"), "right_click": schema("element_token", "x", "y", "target", "delivery_mode", "session"),
    "type_text": schema("text", "element_token", "target", "delivery_mode", "session"), "press_key": schema("key", "target", "delivery_mode", "session"),
    "hotkey": schema("keys", "target", "delivery_mode", "session"), "scroll": schema("direction", "amount", "target", "element_token", "delivery_mode", "session"),
    "drag": schema("from_x", "from_y", "to_x", "to_y", "target", "delivery_mode", "session"), "check_permissions": schema(), "end_session": schema("session"),
    "kill_app": schema("pid"), "clipboard_read": schema(), "run_script": schema("script"), "bring_to_front": schema("pid", "window_id"),
}
if MISSING: TOOLS.pop(MISSING, None)

# ---- a tiny desktop: Finder (pid 501) and Notes (pid 502), Terminal (pid 503)
APPS = {"finder": dict(pid=501, bundle_id="com.apple.finder", name="Finder", window_id=11), "notes": dict(pid=502, bundle_id="com.apple.Notes", name="Notes", window_id=12),
        "terminal": dict(pid=503, bundle_id="com.apple.Terminal", name="Terminal", window_id=13)}
STATE = {"front": "notes", "launched": {"notes"}, "snap": 0, "screen": {"finder": "recents", "notes": "list"}, "first_click_done": False, "typed": ""}
SCREENS = {
    ("finder", "recents"): {"title": "Recents", "els": [("AXTextField", "Search", ""), ("AXButton", "Back", ""), ("AXStaticText", "Recent files", ""), ("AXButton", "Downloads", "")]},
    ("finder", "results"): {"title": "Searching “This Mac”", "els": [("AXTextField", "Search", "xcodeproj"), ("AXRow", "MyApp.xcodeproj", ""), ("AXRow", "Other.xcodeproj", "")]},
    ("finder", "downloads"): {"title": "Downloads", "els": [("AXTextField", "Search", ""), ("AXButton", "Back", ""), ("AXRow", "report.pdf", "")]},
    ("notes", "list"): {"title": "Notes", "els": [("AXButton", "New Note", ""), ("AXSecureTextField", "Lock password", "hunter2")]},
}

def screen(app): return SCREENS.get((app, STATE["screen"].get(app, "")), {"title": app, "els": [("AXButton", "OK", "")]})
def win(app, on_screen=True):
    a = APPS[app]; return {"window_id": a["window_id"], "pid": a["pid"], "app_name": a["name"], "title": screen(app)["title"], "layer": 0, "z_index": 10 if STATE["front"] == app else 1,
                           "is_on_screen": on_screen, "bounds": {"x": 0, "y": 0, "width": 800, "height": 600}}
def app_for(pid): return next((k for k, v in APPS.items() if v["pid"] == pid), None)

def snapshot(app, shot):
    STATE["snap"] += 1; sid = f"s{STATE['snap']}"; els = []
    for i, (role, label, value) in enumerate(screen(app)["els"]):
        els.append({"element_index": i, "element_token": f"{sid}:{i}", "role": role, "label": label, "value": value, "actions": ["AXPress"], "frame": {"x": 20, "y": 30 + 40 * i, "width": 200, "height": 28}, "parent_index": None, "depth": 1})
    sc = {"snapshot_id": sid, "pid": APPS[app]["pid"], "window_id": APPS[app]["window_id"], "title": screen(app)["title"], "elements": els, "tree_format": "elements", "truncated": False}
    content = [{"type": "text", "text": f"snapshot {sid}"}]
    if shot:
        sc.update(screenshot_width=800, screenshot_height=600)
        content.append({"type": "image", "mimeType": "image/jpeg", "data": "/9j/FAKEJPEG"})
    return {"content": content, "structuredContent": sc, "isError": False}

def ok(sc, text="ok"): return {"content": [{"type": "text", "text": text}], "structuredContent": sc, "isError": False}
def fail(code, msg): return {"content": [{"type": "text", "text": msg}], "structuredContent": {"code": code, "effect": "refused", "ok": False, "error": msg}, "isError": True}

def action_result(path="ax", effect="confirmed"): return ok({"path": path, "verified": effect == "confirmed", "effect": effect})

def element(token):
    sid, i = token.split(":"); 
    if sid != f"s{STATE['snap']}": return None, fail("stale_element_token", f"token {token} is stale; the current snapshot is s{STATE['snap']}")
    app = STATE["front_target"]; return screen(app)["els"][int(i)], None

def call(name, a):
    if name == "list_apps": return ok({"apps": [{"name": v["name"], "bundle_id": v["bundle_id"], "pid": v["pid"] if k in STATE["launched"] else 0, "running": k in STATE["launched"]} for k, v in APPS.items()]})
    if name == "list_windows":
        if a.get("pid"):
            k = app_for(a["pid"]); return ok({"windows": [win(k)] if k in STATE["launched"] else []})
        return ok({"windows": [win(k) for k in STATE["launched"]]})
    if name == "launch_app":
        k = next((k for k, v in APPS.items() if a.get("bundle_id") == v["bundle_id"] or str(a.get("name", "")).lower() == v["name"].lower()), None)
        if not k: return fail("app_not_found", f"no app {a.get('name') or a.get('bundle_id')}")
        STATE["launched"].add(k)
        if k == "terminal": STATE["front"] = "terminal"                       # something the person started: it is now the newest, front-most window
        return ok({"pid": APPS[k]["pid"], "bundle_id": APPS[k]["bundle_id"], "name": APPS[k]["name"], "windows": [win(k)], "launch_state": "window_ready"})
    if name == "check_permissions": return ok({"accessibility": not flag("--no-permissions"), "screen_recording": not flag("--no-permissions")})
    if name == "end_session": return ok({"ended": True})
    if name == "get_window_state":
        k = app_for(a.get("pid")); STATE["front_target"] = k
        if k is None or a.get("window_id") != APPS[k]["window_id"]: return fail("window_id_not_found", "window_id_not_found")
        return snapshot(k, a.get("include_screenshot", True))
    if name in ("click", "double_click", "right_click", "type_text", "press_key", "hotkey", "scroll", "drag"):
        if a.get("delivery_mode") == "foreground": return fail("not_allowed_here", "foreground is not available in this fake")
        k = None
        if a.get("element_token"):
            el, err = element(a["element_token"])
            if err: return err
            k = STATE["front_target"]
        elif isinstance(a.get("target"), dict): k = app_for(a["target"].get("pid"))
        if k is None: return fail("window_target_not_found", "no target")
        if name == "click" and a.get("element_token"):
            label = el[1]
            if flag("--noop-first-click") and not STATE["first_click_done"]: STATE["first_click_done"] = True; return ok({"path": "ax", "verified": False, "effect": "suspected_noop", "escalation": {"recommended": "foreground", "reason": "ax press ignored"}})
            if k == "finder" and label == "Downloads": STATE["screen"]["finder"] = "downloads"
        if name == "type_text" and k == "finder" and a.get("element_token"): STATE["typed"] = a.get("text", ""); 
        if name == "press_key" and a.get("key") == "return" and k == "finder" and STATE["typed"]: STATE["screen"]["finder"] = "results"
        if name == "hotkey" and k == "finder" and a.get("keys") == ["cmd", "f"]: STATE["screen"]["finder"] = "recents"
        return action_result()
    if name in ("kill_app", "clipboard_read", "run_script", "bring_to_front"): return ok({"done": True, "note": "this fake would have done it"})
    return fail("unknown_tool", f"unknown tool {name}")

for line in sys.stdin:
    try: m = json.loads(line)
    except Exception: continue
    method, rid, p = m.get("method"), m.get("id"), m.get("params") or {}
    if method == "initialize":
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": rid, "result": {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}}, "serverInfo": {"name": "fake-cua-driver", "version": "0.0-test"}}}) + "\n"); sys.stdout.flush()
    elif method == "tools/list":
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": rid, "result": {"tools": [{"name": n, "description": n, "inputSchema": s} for n, s in TOOLS.items()]}}) + "\n"); sys.stdout.flush()
    elif method == "tools/call":
        n, a = p.get("name"), p.get("arguments") or {}
        LOG.write(json.dumps({"tool": n, "args": a, "env_telemetry": os.environ.get("CUA_DRIVER_TELEMETRY_ENABLED")}) + "\n"); LOG.flush()
        if n not in TOOLS: out = {"content": [{"type": "text", "text": f"unknown tool {n}"}], "isError": True}
        else:
            if n in ("click", "type_text", "press_key", "hotkey") and "front_target" not in STATE: STATE["front_target"] = "finder"
            out = call(n, a)
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": rid, "result": out}) + "\n"); sys.stdout.flush()
    elif method == "ping": sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": rid, "result": {}}) + "\n"); sys.stdout.flush()
