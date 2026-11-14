"""The optional Cua Driver backend. The driver is replaced by tests/fake_cua_driver.py, a real MCP server over stdio written from Cua's published tool
reference. These tests prove the bridge sends the calls that reference describes, keeps every safety rule, and fails clearly when the driver does not match.
They do NOT prove the real Cua Driver behaves like the fake: that needs a Mac with Cua Driver installed."""
import asyncio, json, sys
from pathlib import Path
import pytest
from test_computer import Env, Model, done, plan, PUBLIC
from jarvis_bridge.computer import cua as cua_mod
from jarvis_bridge.computer.agent import ComputerRunner
from jarvis_bridge.computer.broker import BrokerError, ComputerBroker
from jarvis_bridge.computer.cua import CuaBackend, CuaConnection, CuaError, best_match, check_contract, unpack, _frame
from jarvis_bridge.computer.routing import RoutingBroker
from jarvis_bridge.security.audit import AuditLog
from jarvis_bridge.security.policy import PolicyEngine
from jarvis_bridge.settings import SettingsStore

FAKE = str(Path(__file__).parent / "fake_cua_driver.py")


class CuaEnv:
    """The real runner with the real routing broker, pointed at the fake Cua Driver process."""
    def __init__(self, tmp_path, *flags, backend="cua", foreground=False):
        self.log = tmp_path / "cua.jsonl"; self.log.write_text("")
        self.settings = SettingsStore(tmp_path / "s.json")
        self.settings.update(computer_consented=True, computer_desktop_enabled=True, computer_desktop_backend=backend)
        self.audit = AuditLog(); self.policy = PolicyEngine(self.audit); self.app_broker = ComputerBroker()
        self.conn = CuaConnection(lambda: sys.executable, args=[FAKE, *flags], extra_env={"FAKE_CUA_LOG": str(self.log)}, foreground_for=lambda: foreground)
        self.router = RoutingBroker(self.app_broker, self.conn, self.settings)
        self.runner = ComputerRunner(self.settings, self.policy, self.audit, self.router, resolver=PUBLIC)
        self.runner.APPROVAL_WAIT, self.runner.VERIFY_GAP = 5.0, 0.01
        self.events, self.approvals = [], []

    def calls(self): return [json.loads(l) for l in self.log.read_text().splitlines() if l.strip()]
    def tools(self): return [c["tool"] for c in self.calls()]

    async def run(self, model, goal="open Finder", **kw):
        def emit(ev): self.events.append(ev)
        async def approver():
            while True:
                for p in self.policy.pending(): self.approvals.append(p.request.args.get("do")); self.policy.resolve(p.approval_id, True)
                await asyncio.sleep(0.01)
        t = asyncio.create_task(approver())
        try: return await self.runner.run(goal, "desktop", emit, 1, stream=model, model="m", vision=kw.pop("vision", None), **kw)
        finally: t.cancel(); await self.conn.close()


# ====================================================================== the contract with the installed driver
def test_the_expected_tools_match_a_driver_that_has_them_and_report_one_that_does_not():
    tools = [{"name": n, "inputSchema": {"type": "object", "properties": {a: {} for a in args}}} for n, args in cua_mod.TOOLS.items()]
    assert check_contract(tools) == []
    renamed = [dict(t, inputSchema={"type": "object", "properties": {("keys_list" if p == "keys" else p): {} for p in t["inputSchema"]["properties"]}}) if t["name"] == "hotkey" else t for t in tools]
    assert any("hotkey has no parameter keys" in p for p in check_contract(renamed))
    assert any("no tool called drag" in p for p in check_contract([t for t in tools if t["name"] != "drag"]))
    assert check_contract([{"name": n, "inputSchema": {"type": "object"}} for n in cua_mod.TOOLS]) == []          # a schema that lists no parameters is not held against the driver

async def test_a_driver_with_a_missing_tool_or_parameter_is_refused_at_connect_with_a_clear_message(tmp_path):
    for flag, word in (("--missing-tool=hotkey", "hotkey"), ("--no-click-param-element_token", "element_token")):
        e = CuaEnv(tmp_path, flag)
        with pytest.raises(BrokerError, match=word): await e.conn.get()
        await e.conn.close()

async def test_a_missing_driver_program_gives_install_help_not_a_traceback(tmp_path):
    e = CuaEnv(tmp_path); e.conn.command_for = lambda: "/nonexistent/cua-driver"
    with pytest.raises(BrokerError, match="Could not start the Cua Driver"): await e.conn.get()

async def test_the_driver_is_started_with_telemetry_switched_off(tmp_path):
    e = CuaEnv(tmp_path); b = await e.conn.get()
    await b._call("list_apps", {}); await e.conn.close()
    assert e.calls()[0]["env_telemetry"] == "0"


# ====================================================================== a whole task through the real runner
async def test_a_finder_task_runs_through_cua_with_background_input_and_one_session(tmp_path):
    e = CuaEnv(tmp_path)
    m = Model(plan({"action": "open_app", "name": "Finder"}, {"action": "key", "keys": "cmd+f", "expect": {"app": "finder"}},
                   {"action": "type", "target": "Search", "text": "xcodeproj", "submit": True, "expect": {"label": "MyApp.xcodeproj"}}), done("Found MyApp.xcodeproj."))
    out = await e.run(m, "Open Finder, locate my Xcode projects, and show me the results")
    assert out.status == "done" and out.steps == 3, out.text
    calls = e.calls(); t = e.tools()
    assert "launch_app" in t and "hotkey" in t and "type_text" in t and "press_key" in t and t[-1] == "end_session"
    assert next(c for c in calls if c["tool"] == "launch_app")["args"]["name"] == "Finder"
    hot = next(c for c in calls if c["tool"] == "hotkey")["args"]
    assert hot["keys"] == ["cmd", "f"] and hot["target"] == {"kind": "window", "pid": 501, "window_id": 11}
    typ = next(c for c in calls if c["tool"] == "type_text")["args"]
    assert typ["text"] == "xcodeproj" and typ["element_token"].count(":") == 1                 # typed into a control found by its text, addressed by its token
    assert all(c["args"].get("delivery_mode") == "background" for c in calls if c["tool"] in ("hotkey", "type_text", "press_key", "click"))
    sessions = {c["args"]["session"] for c in calls if "session" in c["args"]}; assert len(sessions) == 1 and next(iter(sessions)).startswith("arjunos-")
    assert not any(c["tool"] in ("kill_app", "bring_to_front", "clipboard_read", "run_script") for c in calls)
    assert e.approvals                                                                          # the first use of Finder still asked the person
    assert out.stats["actions"] == 3

async def test_a_click_by_text_uses_the_element_token_of_a_fresh_snapshot(tmp_path):
    e = CuaEnv(tmp_path)
    m = Model(plan({"action": "open_app", "name": "Finder"}, {"action": "click", "target": "Downloads", "expect": {"title": "downloads"}}), done("Opened Downloads."))
    out = await e.run(m, "open Finder and open Downloads")
    assert out.status == "done", out.text
    c = [x for x in e.calls() if x["tool"] == "click"]
    assert len(c) == 1 and c[0]["args"]["element_token"].startswith("s") and "x" not in c[0]["args"]

async def test_the_agent_sees_roles_in_plain_words_and_never_the_value_of_a_password_field(tmp_path):
    e = CuaEnv(tmp_path); b = await e.conn.get()
    r = await b.request("observe", {"mode": "desktop", "images": False}, lambda ev: None, 20)
    await e.conn.close()
    els = r["observation"]["elements"]
    assert [x["role"] for x in els] == ["button", "secure text field"] and els[1]["secure"] is True and els[1]["value"] == ""
    assert r["observation"]["app"] == "Notes" and r["observation"]["bundle_id"] == "com.apple.Notes" and "hunter2" not in json.dumps(r)


# ====================================================================== safety, again, inside the backend
async def test_only_the_listed_cua_tools_can_be_called_at_all(tmp_path):
    e = CuaEnv(tmp_path); b = await e.conn.get()
    for name in ("kill_app", "clipboard_read", "run_script", "bring_to_front", "invoke_menu", "set_value", "something_new"):
        with pytest.raises(CuaError) as ei: await b._call(name, {"pid": 1})
        assert ei.value.code == "blocked"
    await e.conn.close(); assert e.calls() == []                                               # nothing reached the driver

async def test_an_off_limits_app_is_refused_before_it_is_launched(tmp_path):
    e = CuaEnv(tmp_path); b = await e.conn.get()
    r = await b.request("act", {"action": {"kind": "open_app", "name": "Terminal"}}, lambda ev: None, 20)
    await e.conn.close()
    assert r["ok"] is False and "off limits" in r["error"] and "launch_app" not in e.tools()

async def test_a_blocked_shortcut_is_never_sent_even_if_the_runner_were_fooled(tmp_path):
    e = CuaEnv(tmp_path); b = await e.conn.get()
    r = await b.request("act", {"action": {"kind": "key", "keys": "cmd+q"}}, lambda ev: None, 20)
    await e.conn.close(); assert r["ok"] is False and "never sent" in r["error"] and "hotkey" not in e.tools()

async def test_the_front_window_is_never_an_off_limits_app(tmp_path):
    e = CuaEnv(tmp_path); b = await e.conn.get()
    await b._call("launch_app", {"name": "Terminal"})                                          # Terminal is now the front-most window on the desktop
    wins = (await b._call("list_windows", {"on_screen_only": True}))[0]["windows"]
    assert max(wins, key=lambda w: w["z_index"])["app_name"] == "Terminal"                    # (the fake really did put it in front)
    picked = await b._pick_window()
    assert picked["app"] != "Terminal"                                                         # the picker skips it and takes the next window
    obs = (await b.request("observe", {"mode": "desktop"}, lambda ev: None, 20))["observation"]
    await e.conn.close(); assert obs["app"] != "Terminal" and obs["bundle_id"] != "com.apple.Terminal"


async def test_numbers_from_an_old_screen_are_refused_not_clicked(tmp_path):
    e = CuaEnv(tmp_path); b = await e.conn.get()
    obs = (await b.request("observe", {"mode": "desktop"}, lambda ev: None, 20))["observation"]
    await b.request("state", {"mode": "desktop"}, lambda ev: None, 20)                         # the screen was read again: the numbers of `obs` are now stale
    r = await b.request("act", {"action": {"kind": "click", "element": 0}, "gen": obs["gen"]}, lambda ev: None, 20)
    await e.conn.close(); assert r["ok"] is False and r["code"] == "stale" and "click" not in e.tools()


# ====================================================================== failures and limits
async def test_missing_macos_permissions_end_the_task_with_instructions(tmp_path):
    e = CuaEnv(tmp_path, "--no-permissions"); m = Model(done("x"))
    out = await e.run(m, "look at the screen")
    assert out.status == "failed" and "Accessibility" in out.text and "System Settings" in out.text and m.calls == []

async def test_background_input_that_did_not_land_is_reported_and_never_escalated_to_foreground_unless_switched_on(tmp_path):
    e = CuaEnv(tmp_path, "--noop-first-click"); b = await e.conn.get()
    await b.request("act", {"action": {"kind": "open_app", "name": "Finder"}}, lambda ev: None, 20)
    obs = (await b.request("observe", {"mode": "desktop"}, lambda ev: None, 20))["observation"]
    r = await b.request("act", {"action": {"kind": "click", "element": 3}, "gen": obs["gen"]}, lambda ev: None, 20)
    await e.conn.close()
    assert r["ok"] and r["state"]["changed"] is False and "may not have landed" in r["note"]
    assert not any(c["args"].get("delivery_mode") == "foreground" for c in e.calls())

async def test_foreground_retry_happens_only_when_the_person_allowed_it(tmp_path):
    e = CuaEnv(tmp_path, "--noop-first-click", foreground=True); b = await e.conn.get()
    await b.request("act", {"action": {"kind": "open_app", "name": "Finder"}}, lambda ev: None, 20)
    obs = (await b.request("observe", {"mode": "desktop"}, lambda ev: None, 20))["observation"]
    r = await b.request("act", {"action": {"kind": "click", "element": 3}, "gen": obs["gen"]}, lambda ev: None, 20)
    await e.conn.close()
    assert any(c["args"].get("delivery_mode") == "foreground" for c in e.calls())              # tried once in the foreground (this fake refuses it)
    assert r["ok"] is False

async def test_stop_cancels_a_call_that_is_in_flight():
    gate = asyncio.Event()
    async def slow(name, args): await gate.wait(); return {}
    b = CuaBackend(slow)
    t = asyncio.create_task(b.request("observe", {"mode": "desktop"}, lambda ev: None, 30)); await asyncio.sleep(0.05)
    assert b.cancel_all() == 1
    with pytest.raises(BrokerError, match="stopped"): await t

async def test_an_unexpected_reply_becomes_an_error_answer_not_a_crash():
    async def weird(name, args): return {"structuredContent": {"elements": ["not a dict", 5, None]}, "content": []}
    async def listing(name, args):
        if name == "list_windows": return {"structuredContent": {"windows": [{"window_id": 1, "pid": 9, "app_name": "Notes", "z_index": 1}]}}
        if name == "list_apps": return {"structuredContent": {"apps": []}}
        return await weird(name, args)
    b = CuaBackend(listing)
    r = await b.request("observe", {"mode": "desktop"}, lambda ev: None, 5)
    assert r["ok"] is True and r["observation"]["elements"] == []
    async def explode(name, args): raise ValueError("boom " * 100)
    r2 = await CuaBackend(explode).request("observe", {"mode": "desktop"}, lambda ev: None, 5)
    assert r2["ok"] is False and len(r2["error"]) < 400


# ====================================================================== routing
async def test_the_builtin_backend_is_the_default_and_the_browser_never_goes_to_cua(tmp_path):
    e = CuaEnv(tmp_path, backend="builtin")
    seen = []
    async def fake_request(kind, payload, emit, timeout=60.0): seen.append(payload["mode"]); return {"ok": True}
    e.app_broker.request = fake_request
    await e.router.request("observe", {"mode": "desktop"}, lambda ev: None)
    e.settings.update(computer_desktop_backend="cua")
    await e.router.request("observe", {"mode": "browser"}, lambda ev: None)
    assert seen == ["desktop", "browser"] and e.conn.backend is None                           # Cua was never even started

async def test_with_cua_selected_desktop_requests_go_to_cua_and_stop_reaches_both(tmp_path):
    e = CuaEnv(tmp_path)
    r = await e.router.request("observe", {"mode": "desktop", "images": True}, lambda ev: None)
    assert r["ok"] and r["observation"]["screenshot_b64"] and e.conn.backend is not None
    assert e.router.cancel_all() == 0
    await e.router.end("desktop"); assert e.tools()[-1] == "end_session"; await e.conn.close()


# ====================================================================== small pure pieces
def test_unpack_reads_structured_text_json_and_images():
    assert unpack({"structuredContent": {"a": 1}, "content": [{"type": "text", "text": "t"}, {"type": "image", "data": "IMG"}]}) == ({"a": 1}, "t", "IMG", False)
    assert unpack({"content": [{"type": "text", "text": '{"b": 2}'}]})[0] == {"b": 2}
    assert unpack("garbage")[3] is True and unpack({"isError": True, "content": []})[3] is True

def test_frames_are_read_in_every_shape_the_driver_might_use():
    assert _frame({"x": 1, "y": 2, "width": 3, "height": 4}) == (1, 2, 3, 4) == _frame({"x": 1, "y": 2, "w": 3, "h": 4}) == _frame([1, 2, 3, 4])
    assert _frame(None) == _frame("x") == _frame({"x": "a"}) == (0, 0, 0, 0)

def test_the_matcher_prefers_exact_then_prefix_then_substring_then_role_then_reading_order():
    els = [{"i": 0, "role": "button", "label": "Search results", "x": 0, "y": 50}, {"i": 1, "role": "text field", "label": "Search", "x": 0, "y": 90},
           {"i": 2, "role": "button", "label": "Search", "x": 0, "y": 10}, {"i": 3, "role": "button", "label": "Search", "x": 0, "y": 5}]
    assert best_match("search", "", els)["i"] == 3                                             # exact, and first in reading order
    assert best_match("search", "text field", els)["i"] == 1                                   # the role breaks the tie
    assert best_match("search res", "", els)["i"] == 0 and best_match("zzz", "", els) is None and best_match("", "", els) is None
