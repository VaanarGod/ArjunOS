"""Optional desktop backend: Cua Driver (https://cua.ai/docs/cua-driver), driven over MCP.

Why: the app's own driver clicks with the real mouse, so it fights you for the pointer. Cua Driver sends input to ONE window without raising it, so you
keep working in another app, and macOS permissions are granted once to its signed app.

What does NOT change: the plan / execute / verify loop, every safety rule and every approval are the same code. This module only answers the same four
questions the app answers (observe, resolve, act, state) with the same JSON, so the runner cannot tell the two apart. It is also deliberately narrow:

  * only a short list of Cua tools can be called (no kill_app, no clipboard, no scripts, no menus, no foreground-stealing unless switched on);
  * off-limits apps and blocked shortcuts are refused HERE as well, so a bug elsewhere cannot send a Cua call to the terminal or to ArjunOS itself;
  * everything Cua returns is treated as untrusted data and clamped by the same parsers as anything else.

Nothing here has run against a real Cua Driver yet: it follows the published tool reference, and check_contract() compares what this module sends with the
tool schemas of the driver that is actually installed, so a renamed parameter is reported at connect time instead of failing step by step.
"""
from __future__ import annotations
import asyncio, base64, json, re, secrets, time
from typing import Awaitable, Callable
from ..security.redact import redact_text
from .broker import BrokerError
from .safety import BLOCKED_KEYS, app_problem

Call = Callable[[str, dict], Awaitable[dict]]

# Every Cua tool this module may call, and the argument names it sends. Anything else is refused before it leaves the bridge.
TOOLS: dict = {
    "list_apps": {"session"}, "list_windows": {"pid", "on_screen_only", "session"}, "launch_app": {"name", "bundle_id", "session"},
    "get_window_state": {"pid", "window_id", "tree_format", "include_screenshot", "max_dimension", "screenshot_format", "max_elements", "session"},
    "click": {"element_token", "x", "y", "target", "button", "delivery_mode", "session"}, "double_click": {"element_token", "x", "y", "target", "delivery_mode", "session"},
    "right_click": {"element_token", "x", "y", "target", "delivery_mode", "session"}, "type_text": {"text", "element_token", "target", "delivery_mode", "session"},
    "press_key": {"key", "target", "delivery_mode", "session"}, "hotkey": {"keys", "target", "delivery_mode", "session"},
    "scroll": {"direction", "amount", "target", "element_token", "delivery_mode", "session"},
    "drag": {"from_x", "from_y", "to_x", "to_y", "target", "delivery_mode", "session"},
    "check_permissions": set(), "end_session": {"session"},
}
KEY_NAMES = {"enter": "return", "esc": "escape", "backspace": "delete", "opt": "option"}
BLOCKED_NAMES = ("kill_app", "bring_to_front", "invoke_menu", "clipboard_read", "clipboard_write", "run_script", "run_steps", "set_config", "install_extension", "set_value")


class CuaError(Exception):
    def __init__(self, message: str, code: str = ""):
        super().__init__(message); self.code = code


def unpack(res) -> tuple:
    """(structured data, text, first image as base64, is_error) from an MCP tool result, whatever mix of fields the server used."""
    if not isinstance(res, dict): return {}, "", "", True
    content = [c for c in (res.get("content") or []) if isinstance(c, dict)]
    text = "\n".join(str(c.get("text", "")) for c in content if c.get("type") == "text")
    img = next((str(c.get("data", "")) for c in content if c.get("type") == "image"), "")
    sc = res.get("structuredContent")
    if not isinstance(sc, dict):
        try: sc = json.loads(text) if text.strip().startswith("{") else {}
        except ValueError: sc = {}
    return (sc if isinstance(sc, dict) else {}), text, img, bool(res.get("isError"))


def _words(role: str) -> str:
    r = re.sub(r"^AX", "", str(role or ""))
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", r).lower().strip() or "element"


def _frame(f) -> tuple:
    """x, y, w, h from a frame given as {x,y,width,height}, {x,y,w,h} or [x,y,w,h]. Zeros when it is anything else."""
    try:
        if isinstance(f, (list, tuple)) and len(f) == 4: x, y, w, h = f
        elif isinstance(f, dict): x, y, w, h = f.get("x", 0), f.get("y", 0), f.get("width", f.get("w", 0)), f.get("height", f.get("h", 0))
        else: return 0, 0, 0, 0
        return int(round(float(x))), int(round(float(y))), int(round(float(w))), int(round(float(h)))
    except (TypeError, ValueError): return 0, 0, 0, 0


def _norm(s: str) -> str: return " ".join(str(s or "").lower().split())


def best_match(label: str, role: str, els: list):
    """Same ranking as the app's matcher: exact beats prefix beats substring, a matching role breaks ties, then reading order."""
    want, wr = _norm(label), _norm(role)
    if not want: return None
    ranked = []
    for e in els:
        have = _norm(e["label"])
        if not have: continue
        s = 300 if have == want else 200 if have.startswith(want) else 100 if want in have else None
        if s is None: continue
        if wr: s += 50 if wr in _norm(e["role"]) else -50
        ranked.append((s, e))
    if not ranked: return None
    top = max(s for s, _ in ranked)
    return sorted((e for s, e in ranked if s == top), key=lambda e: (e["y"], e["x"]))[0]


def check_contract(tools: list) -> list:
    """Problems between what this module sends and the installed driver's tool list ([] = it matches)."""
    have = {t.get("name"): t for t in tools if isinstance(t, dict)}
    out = []
    for name, args in TOOLS.items():
        t = have.get(name)
        if t is None: out.append(f"the driver has no tool called {name}"); continue
        props = ((t.get("inputSchema") or {}).get("properties"))
        if isinstance(props, dict) and props:
            miss = sorted(a for a in args if a not in props)
            if miss: out.append(f"{name} has no parameter {', '.join(miss)}")
    return out


class CuaBackend:
    """Answers the runner's observe / resolve / act / state requests by calling Cua Driver tools."""

    def __init__(self, call: Call, *, allow_foreground: bool = False, sleep=asyncio.sleep, max_elements: int = 250):
        self._call_raw, self.allow_foreground, self._sleep, self.max_elements = call, allow_foreground, sleep, max_elements
        self._tasks: set = set(); self._stopping: set = set()
        self.session = ""
        self._reset()

    def _reset(self):
        self.target: dict | None = None                # {pid, window_id, app, bundle_id, title}
        self.gen = 0; self.tokens: dict = {}; self.els: list = []; self.shot_ok = False; self._sig = ""; self._bundles: dict = {}; self.perms_ok: bool | None = None

    # -------------------------------------------------------------- the broker interface
    async def request(self, kind: str, payload: dict, emit, timeout: float = 60.0) -> dict:
        task = asyncio.ensure_future(self._answer(kind, payload)); self._tasks.add(task)
        try:
            done, _ = await asyncio.wait({task}, timeout=timeout)
            if task in self._stopping: raise BrokerError("stopped")
            if not done: raise BrokerError("The Cua Driver did not answer in time.")
            try: return task.result()
            except BrokerError: raise
            except Exception as e:                                              # a bug or a surprise in the reply must not take the whole run down
                return {"ok": False, "error": "The Cua Driver sent something unexpected: " + redact_text(f"{type(e).__name__}: {e}")[:160]}
        finally:
            if not task.done(): task.cancel()
            self._tasks.discard(task); self._stopping.discard(task)

    def cancel_all(self) -> int:
        n = 0
        for t in list(self._tasks):
            if not t.done(): self._stopping.add(t); t.cancel(); n += 1
        return n

    async def end(self):
        if self.session:
            try: await self._call("end_session", {})
            except Exception: pass
        self._reset(); self.session = ""

    # -------------------------------------------------------------- guarded calls
    async def _call(self, name: str, args: dict) -> tuple:
        if name not in TOOLS or name in BLOCKED_NAMES: raise CuaError(f"{name} is not something the assistant may use", "blocked")
        if not self.session: self.session = "arjunos-" + secrets.token_hex(4)
        args = {k: v for k, v in args.items() if v is not None}
        if "session" in TOOLS[name]: args.setdefault("session", self.session)
        try: res = await self._call_raw(name, args)
        except BrokerError: raise
        except asyncio.CancelledError: raise
        except Exception as e: raise CuaError(redact_text(str(e))[:300] or "the Cua Driver failed", "driver") from e
        sc, text, img, is_err = unpack(res)
        code = str(sc.get("code") or "")
        if isinstance(sc.get("refusal"), dict): code = code or str(sc["refusal"].get("code") or "")
        if is_err or sc.get("effect") == "refused" or (code and sc.get("ok") is False):
            msg = redact_text(str(sc.get("error") or sc.get("message") or text or "refused"))[:300]
            low = (msg + " " + code).lower()
            raise CuaError(msg, "permission" if any(w in low for w in ("permission", "not granted", "screen recording", "accessibility is")) else (code or "refused"))
        return sc, text, img

    async def _answer(self, kind: str, p: dict) -> dict:
        try:
            if kind == "observe": return await self._observe(p)
            if kind == "state": return {"ok": True, "state": await self._state_only()}
            if kind == "resolve": return await self._resolve(p.get("target") or {})
            if kind == "act": return await self._act(p.get("action") or {}, p.get("gen"))
            return {"ok": False, "error": "Unknown request."}
        except CuaError as e:
            return {"ok": False, "error": str(e), "code": e.code if e.code in ("permission", "stale", "not_found") else ""}

    # -------------------------------------------------------------- seeing
    async def _bundle_of(self, pid: int, name: str) -> str:
        if not self._bundles:
            try:
                sc, _, _ = await self._call("list_apps", {})
                for a in sc.get("apps") or []:
                    if isinstance(a, dict) and a.get("pid"): self._bundles[int(a["pid"])] = str(a.get("bundle_id") or "")
            except CuaError: self._bundles = {-1: ""}
        return self._bundles.get(pid, "")

    async def _pick_window(self, want_pid: int | None = None) -> dict:
        sc, _, _ = await self._call("list_windows", {"pid": want_pid} if want_pid else {"on_screen_only": True})
        wins = [w for w in (sc.get("windows") or []) if isinstance(w, dict) and w.get("window_id") and w.get("pid")]
        if not want_pid: wins = [w for w in wins if int(w.get("layer", 0) or 0) == 0 and app_problem(str(w.get("app_name") or ""), "", False) is None]
        if not wins: raise CuaError("No window to work in. Open an app first.", "not_found")
        wins.sort(key=lambda w: -(w["z_index"] if isinstance(w.get("z_index"), int) else -1))
        w = wins[0]
        return {"pid": int(w["pid"]), "window_id": int(w["window_id"]), "app": str(w.get("app_name") or ""), "title": str(w.get("title") or "")}

    async def _ensure_target(self) -> dict:
        if self.target is None:
            t = await self._pick_window(); t["bundle_id"] = await self._bundle_of(t["pid"], t["app"]); self.target = t
        return self.target

    async def _snapshot(self, *, shot: bool, max_dim: int | None = None, full: bool = True) -> dict:
        t = await self._ensure_target()
        if self.perms_ok is None:
            try:
                sc, _, _ = await self._call("check_permissions", {})
                self.perms_ok = not (sc.get("accessibility") is False or sc.get("screen_recording") is False and shot)
            except CuaError: self.perms_ok = True
            if not self.perms_ok: raise CuaError("Cua Driver needs Accessibility and Screen Recording permission. Grant both to Cua Driver in System Settings → Privacy & Security.", "permission")
        sc, text, img = await self._call("get_window_state", {"pid": t["pid"], "window_id": t["window_id"], "tree_format": "elements", "include_screenshot": shot,
                                                              "max_dimension": max_dim, "screenshot_format": "jpeg" if shot else None, "max_elements": self.max_elements})
        els, tokens = [], {}
        for r in (sc.get("elements") or [])[:200]:
            if not isinstance(r, dict) or r.get("element_index") is None: continue
            i = int(r["element_index"]); x, y, w, h = _frame(r.get("frame")); role_raw = str(r.get("role") or "")
            role = _words(role_raw); low = role_raw.lower()
            label = str(r.get("label") or r.get("title") or r.get("description") or "").strip()
            els.append({"i": i, "role": role, "label": label[:90], "x": x, "y": y, "w": w, "h": h, "secure": "secure" in low, "value": ("" if "secure" in low else str(r.get("value") or "")[:60]),
                        "editable": any(k in low for k in ("textfield", "textarea", "searchfield", "combobox")), "checked": r.get("checked") if isinstance(r.get("checked"), bool) else None})
            if r.get("element_token"): tokens[i] = str(r["element_token"])
        self.gen += 1; self.els, self.tokens = els, tokens
        if shot and img: self.shot_ok = True
        width = int(sc.get("screenshot_width") or sc.get("width") or 0); height = int(sc.get("screenshot_height") or sc.get("height") or 0)
        if shot and img and not width:
            try:
                from PIL import Image; import io
                width, height = Image.open(io.BytesIO(base64.b64decode(img))).size
            except Exception: width = height = 0
        labels = [e["label"].lower() for e in els if e["label"]][:300]
        sig = "|".join(labels) + "|" + t["title"]
        changed = None if not self._sig else sig != self._sig
        self._sig = sig
        title = str(sc.get("title") or sc.get("window_title") or t["title"])
        t["title"] = title
        return {"app": t["app"], "bundle_id": t["bundle_id"], "is_self": any(m in (t["app"] + " " + t["bundle_id"]).lower() for m in ("arjunos", "jarvis", "com.arjun")),
                "title": title, "url": "", "labels": labels, "focused": "", "gen": self.gen, "source": "ax", "changed": changed, "has_secure": any(e["secure"] for e in els),
                "loading": bool(sc.get("degraded") and sc.get("degraded_reason") == "ax_app_launching"), "width": width, "height": height,
                "text": "; ".join(e["label"] for e in els if "text" in e["role"] and not e["editable"] and e["label"])[:3000],
                "elements": els, **({"screenshot_b64": img} if shot and img else {})}

    async def _observe(self, p: dict) -> dict:
        st = await self._snapshot(shot=bool(p.get("images")), max_dim=p.get("max_dim"))
        return {"ok": True, "observation": st}

    async def _state_only(self) -> dict:
        st = await self._snapshot(shot=False); st.pop("elements", None); return st

    async def _resolve(self, tg: dict) -> dict:
        if tg.get("i") is not None:                                        # a number from the screen the model saw: only valid while that screen is still the current one
            if tg.get("gen") != self.gen: raise CuaError("The controls changed since you looked. Look again.", "stale")
            el = next((e for e in self.els if e["i"] == tg["i"]), None)
            if el is None: raise CuaError("No such control.", "not_found")
            return {"ok": True, "element": el, "state": {k: v for k, v in (await self._state_light()).items()}}
        st = await self._snapshot(shot=False)
        el = best_match(str(tg.get("label") or ""), str(tg.get("role") or ""), st["elements"])
        if el is None: raise CuaError("No control with that text.", "not_found")
        st.pop("elements", None)
        return {"ok": True, "element": el, "state": st}

    async def _state_light(self) -> dict:
        t = self.target or {}
        return {"app": t.get("app", ""), "bundle_id": t.get("bundle_id", ""), "title": t.get("title", ""), "gen": self.gen, "source": "ax", "labels": [e["label"].lower() for e in self.els if e["label"]][:300]}

    # -------------------------------------------------------------- doing
    def _tgt(self) -> dict: return {"kind": "window", "pid": self.target["pid"], "window_id": self.target["window_id"]}

    async def _act(self, a: dict, gen) -> dict:
        kind = str(a.get("kind") or "")
        if kind == "wait":
            await self._sleep(min(10.0, max(0.0, float(a.get("seconds") or 1.0)))); return {"ok": True, "state": await self._state_only()}
        if kind == "open_app": return await self._open_app(str(a.get("name") or ""))
        if kind not in ("click", "type", "key", "scroll", "drag"): return {"ok": False, "error": f"“{kind}” is not available on the desktop."}
        await self._ensure_target()
        problem = app_problem(self.target["app"], self.target.get("bundle_id", ""), False)
        if problem: return {"ok": False, "error": f"That app is off limits: {problem}"}
        el_token, el = None, None
        if a.get("element") is not None:
            if gen != self.gen: raise CuaError("The controls changed since you looked. Look again.", "stale")
            el_token = self.tokens.get(int(a["element"])); el = next((e for e in self.els if e["i"] == int(a["element"])), None)
            if not el_token: raise CuaError("That control cannot be addressed any more. Look again.", "stale")
        elif a.get("x") is not None and not self.shot_ok:
            await self._snapshot(shot=True)                                  # Cua only accepts pixel coordinates after a screenshot of the window in this session
        base = {"delivery_mode": "background"}
        if kind == "click":
            tool = "double_click" if a.get("double") else "right_click" if a.get("button") == "right" else "click"
            args = {**base, **({"element_token": el_token} if el_token else {"x": a.get("x"), "y": a.get("y"), "target": self._tgt()})}
            res = await self._do(tool, args)
        elif kind == "type":
            res = await self._do("type_text", {**base, "text": str(a.get("text") or ""), **({"element_token": el_token} if el_token else {"target": self._tgt()})})
            if a.get("submit"): res = await self._do("press_key", {**base, "key": "return", "target": self._tgt()})
        elif kind == "key":
            combo = str(a.get("keys") or "")
            if combo in BLOCKED_KEYS: return {"ok": False, "error": f"{combo} is never sent."}
            parts = [KEY_NAMES.get(x, x) for x in combo.split("+") if x]
            if len(parts) == 1: res = await self._do("press_key", {**base, "key": parts[0], "target": self._tgt()})
            else: res = await self._do("hotkey", {**base, "keys": parts, "target": self._tgt()})
        elif kind == "scroll":
            res = await self._do("scroll", {**base, "direction": a.get("direction") or "down", "amount": int(a.get("amount") or 3), "target": self._tgt(), "element_token": el_token})
        else:
            if None in (a.get("x"), a.get("y"), a.get("x2"), a.get("y2")): return {"ok": False, "error": "drag needs start and end points."}
            res = await self._do("drag", {**base, "from_x": a["x"], "from_y": a["y"], "to_x": a["x2"], "to_y": a["y2"], "target": self._tgt()})
        st = await self._state_only()
        if res.get("effect") == "suspected_noop": st["changed"] = False
        elif res.get("effect") == "confirmed": st["changed"] = True
        return {"ok": True, "state": st, **({"note": "the input may not have landed"} if res.get("effect") == "suspected_noop" else {})}

    async def _do(self, tool: str, args: dict) -> dict:
        sc, _, _ = await self._call(tool, args)
        esc = sc.get("escalation") if isinstance(sc.get("escalation"), dict) else {}
        if sc.get("effect") == "suspected_noop" and esc.get("recommended") == "foreground" and self.allow_foreground:
            sc, _, _ = await self._call(tool, {**args, "delivery_mode": "foreground"})      # only when the person switched this on: it briefly brings the window to the front
        return sc

    async def _open_app(self, name: str) -> dict:
        name = name.strip()
        problem = app_problem(name, "", False)
        if problem: return {"ok": False, "error": f"That app is off limits: {problem}"}
        is_bundle = bool(re.fullmatch(r"[A-Za-z0-9-]+(\.[A-Za-z0-9-]+){2,}", name))
        sc, _, _ = await self._call("launch_app", {"bundle_id": name} if is_bundle else {"name": name})
        pid = int(sc.get("pid") or 0)
        wins = [w for w in (sc.get("windows") or []) if isinstance(w, dict) and w.get("window_id")]
        for _ in range(6):                                                   # a cold start has no window for a moment
            if wins or not pid: break
            await self._sleep(0.4)
            try: wins = [w for w in ((await self._call("list_windows", {"pid": pid}))[0].get("windows") or []) if isinstance(w, dict) and w.get("window_id")]
            except CuaError: break
        if not pid or not wins: return {"ok": False, "error": f"{name} started but has no window yet."}
        w = sorted(wins, key=lambda w: -(w["z_index"] if isinstance(w.get("z_index"), int) else -1))[0]
        bundle = str(sc.get("bundle_id") or "")
        app = str(sc.get("name") or w.get("app_name") or name)
        problem = app_problem(app, bundle, False)
        if problem: return {"ok": False, "error": f"That app is off limits: {problem}"}
        self.target = {"pid": pid, "window_id": int(w["window_id"]), "app": app, "bundle_id": bundle, "title": str(w.get("title") or "")}
        self.shot_ok = False; self._sig = ""
        return {"ok": True, "state": await self._state_only()}


class CuaConnection:
    """Starts `cua-driver mcp` on first use, checks that it matches this module, and hands out the backend. One connection, reused between tasks."""
    ENV = {"CUA_DRIVER_TELEMETRY_ENABLED": "0", "CUA_TELEMETRY_ENABLED": "false"}      # the bridge never opts anyone into Cua's anonymous usage statistics

    def __init__(self, command_for: Callable[[], str], *, foreground_for: Callable[[], bool] = lambda: False, args: list | None = None, client_factory=None, extra_env: dict | None = None):
        self.extra_env = dict(extra_env or {})
        self.command_for, self.foreground_for, self.args, self._factory = command_for, foreground_for, args if args is not None else ["mcp"], client_factory
        self.client = None; self.backend: CuaBackend | None = None; self._lock = asyncio.Lock(); self._command = ""

    async def get(self) -> CuaBackend:
        async with self._lock:
            cmd = self.command_for()
            if self.backend and self.client and self.client.state.value == "ready" and cmd == self._command:
                self.backend.allow_foreground = bool(self.foreground_for()); return self.backend
            await self._close_client()
            from ..mcp.client import MCPClient, MCPError, ServerSpec
            spec = ServerSpec(name="cua-driver", transport="stdio", command=cmd, args=list(self.args), env={**self.extra_env, **self.ENV}, approved=True)     # the person chose this backend and command in Settings
            client = self._factory(spec) if self._factory else MCPClient(spec, request_timeout=45.0)
            try:
                await client.connect()
                problems = check_contract(await client.list_tools())
            except MCPError as e:
                await client.close()
                raise BrokerError(f"Could not start the Cua Driver ({cmd}): {e}. Install it from https://cua.ai/cua-driver or switch the desktop backend back to the built-in one in Settings → Computer use.") from e
            if problems:
                await client.close()
                raise BrokerError("The installed Cua Driver does not match what ArjunOS expects (" + "; ".join(problems[:4]) + "). Update ArjunOS or the driver, or use the built-in backend.")
            self.client, self._command = client, cmd

            async def call(name: str, args: dict) -> dict:
                try: return await client.call_tool(name, args, timeout=45.0)
                except MCPError as e:
                    if type(e).__name__ == "MCPClosed": await self._close_client()
                    raise
            self.backend = CuaBackend(call, allow_foreground=bool(self.foreground_for()))
            return self.backend

    async def _close_client(self):
        c, self.client, self.backend = self.client, None, None
        if c is not None:
            try: await c.close()
            except Exception: pass

    async def close(self):
        async with self._lock: await self._close_client()
