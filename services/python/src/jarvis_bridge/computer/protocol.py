"""What the model may ask for (the action vocabulary) and what the app sends back (an observation). Everything is clamped:
the model's JSON and the app's JSON are both treated as untrusted input."""
from __future__ import annotations
import json, re
from dataclasses import dataclass, field

BROWSER_ACTIONS = frozenset({"click", "type", "key", "scroll", "navigate", "back", "forward", "wait", "done", "ask_user", "fail"})
DESKTOP_ACTIONS = frozenset({"click", "type", "key", "scroll", "drag", "open_app", "wait", "done", "ask_user", "fail"})
TERMINAL = frozenset({"done", "ask_user", "fail"})
OBSERVING = frozenset({"wait", "done", "ask_user", "fail"})          # actions that change nothing on the machine

MODIFIERS = {"cmd": "cmd", "command": "cmd", "meta": "cmd", "super": "cmd", "ctrl": "ctrl", "control": "ctrl",
             "alt": "opt", "opt": "opt", "option": "opt", "shift": "shift"}
NAMED_KEYS = {"enter": "enter", "return": "enter", "tab": "tab", "esc": "esc", "escape": "esc", "space": "space", "backspace": "backspace",
              "delete": "delete", "up": "up", "down": "down", "left": "left", "right": "right", "home": "home", "end": "end",
              "pageup": "pageup", "pagedown": "pagedown", **{f"f{i}": f"f{i}" for i in range(1, 13)}}
DIRECTIONS = ("up", "down", "left", "right")
MAX_TEXT = 2000
MAX_ELEMENTS = 120
_CTRL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f\u202a-\u202e\u2066-\u2069]")      # control and bidi-override characters


class ProtocolError(ValueError):
    """The model's reply was not a usable action. The message is shown to the model so it can correct itself."""


def clean(s, limit: int) -> str:
    return _CTRL.sub("", str(s if s is not None else "")).replace("\r", " ")[:limit]


@dataclass(frozen=True)
class Action:
    kind: str
    element: int | None = None
    x: int | None = None
    y: int | None = None
    x2: int | None = None
    y2: int | None = None
    text: str = ""
    keys: str = ""                 # normalised: "cmd+shift+t"
    direction: str = "down"
    amount: int = 3
    url: str = ""
    name: str = ""
    seconds: float = 1.0
    button: str = "left"
    double: bool = False
    submit: bool = False           # press Enter after typing
    trusted: bool = False          # browser clicks only: send a real OS-level mouse event instead of a DOM event (set by the bridge on a retry, never by the model)
    note: str = ""                 # done: summary / ask_user: question / fail: reason
    label: str = ""                # a control named by its text ("Search"): resolved on the Mac at the moment of the action
    role: str = ""                 # optional: "button", "text field", ...
    expect: dict = field(default_factory=dict)   # what must be true afterwards (checked with Accessibility / DOM data, not another model call)

    def wire(self) -> dict:
        """What is sent to the app: only the fields that matter for this action."""
        d: dict = {"kind": self.kind}
        for k in ("element", "x", "y", "x2", "y2"):
            if getattr(self, k) is not None: d[k] = getattr(self, k)
        if self.label: d["label"] = self.label
        if self.role: d["role"] = self.role
        if self.kind == "type": d.update(text=self.text, submit=self.submit)
        if self.kind == "key": d["keys"] = self.keys
        if self.kind == "scroll": d.update(direction=self.direction, amount=self.amount)
        if self.kind in ("navigate",): d["url"] = self.url
        if self.kind == "open_app": d["name"] = self.name
        if self.kind == "wait": d["seconds"] = self.seconds
        if self.kind == "click":
            d.update(button=self.button, double=self.double)
            if self.trusted: d["trusted"] = True
        return d


def first_json_object(text: str) -> dict:
    """The first complete {...} in the reply (models add prose, code fences, or <think> blocks around it)."""
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S | re.I)
    start = text.find("{")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            c = text[i]
            if in_str:
                if esc: esc = False
                elif c == "\\": esc = True
                elif c == '"': in_str = False
                continue
            if c == '"': in_str = True
            elif c == "{": depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[start:i + 1])
                        if isinstance(obj, dict): return obj
                    except json.JSONDecodeError:
                        pass
                    break
        start = text.find("{", start + 1)
    raise ProtocolError("Reply with ONLY one JSON object such as {\"action\": \"click\", \"element\": 3}.")


def normalize_keys(raw: str) -> str:
    parts = [p.strip().lower() for p in str(raw).replace(" ", "+").split("+") if p.strip()]
    if not parts: raise ProtocolError("\"keys\" is empty.")
    mods, main = [], None
    for p in parts:
        if p in MODIFIERS:
            m = MODIFIERS[p]
            if m not in mods: mods.append(m)
        elif main is None and (p in NAMED_KEYS or (len(p) == 1 and p.isprintable())):
            main = NAMED_KEYS.get(p, p)
        else:
            raise ProtocolError(f"\"{clean(p, 20)}\" is not a key I can press. Use names like enter, tab, esc, cmd+l, down.")
    if main is None: raise ProtocolError("A key combination needs one non-modifier key, for example cmd+l.")
    order = {"cmd": 0, "ctrl": 1, "opt": 2, "shift": 3}
    return "+".join([*sorted(mods, key=order.get), main])


def _int(d: dict, k: str, lo: int, hi: int) -> int | None:
    v = d.get(k)
    if v is None or isinstance(v, bool): return None
    try: n = int(round(float(v)))
    except (TypeError, ValueError): raise ProtocolError(f"\"{k}\" must be a number.")
    if not lo <= n <= hi: raise ProtocolError(f"\"{k}\" is out of range ({lo} to {hi}).")
    return n


EXPECT_KEYS = ("app", "title", "url", "label", "gone")
MAX_PLAN = 8


def _expect(raw) -> dict:
    if not isinstance(raw, dict): return {}
    return {k: clean(raw[k], 80).strip().lower() for k in EXPECT_KEYS if isinstance(raw.get(k), (str, int, float)) and clean(raw[k], 80).strip()}


def _target(d: dict) -> tuple[str, str]:
    t = d.get("target")
    if isinstance(t, dict): return clean(t.get("label") or t.get("text") or t.get("name"), 90).strip(), clean(t.get("role"), 24).strip().lower()
    if isinstance(t, str): return clean(t, 90).strip(), clean(d.get("role"), 24).strip().lower()
    return clean(d.get("label"), 90).strip(), clean(d.get("role"), 24).strip().lower()


def action_from_dict(d: dict, mode: str, *, first: bool = True, screen_w: int = 4096, screen_h: int = 4096, n_elements: int = 0) -> Action:
    kind = str(d.get("action") or "").strip().lower().replace("-", "_")
    if not kind: raise ProtocolError("A plan step has no \"action\". Every step is {\"action\": ...}; put \"expect\" INSIDE the step it checks, never as a step of its own.")
    kind = {"press": "key", "hotkey": "key", "goto": "navigate", "open_url": "navigate", "finish": "done", "scroll_down": "scroll", "launch": "open_app", "open": "open_app"}.get(kind, kind)
    allowed = BROWSER_ACTIONS if mode == "browser" else DESKTOP_ACTIONS
    if kind not in allowed:
        raise ProtocolError(f"\"{clean(kind, 30)}\" is not an action here. Use one of: {', '.join(sorted(allowed))}.")
    label, role = _target(d)
    el = _int(d, "element", 0, 100_000)
    x, y = _int(d, "x", 0, screen_w), _int(d, "y", 0, screen_h)
    if (x is None) != (y is None): raise ProtocolError("Give both \"x\" and \"y\", or name the control.")
    if kind in ("click", "type", "scroll") and not first and (el is not None or x is not None):
        raise ProtocolError("After the first action of a plan, name controls by their text (\"target\": \"Search\"): numbers and coordinates change as soon as something happens.")
    if el is not None and first and el >= n_elements and kind in ("click", "type", "scroll"):
        raise ProtocolError(f"There is no control [{el}] on this screen. Pick a number from the list, or name it with \"target\".")
    note = clean(d.get("summary") or d.get("question") or d.get("reason") or d.get("note") or "", 1500)
    ex = _expect(d.get("expect"))
    if mode == "browser": ex.pop("app", None)                      # in the browser there is no other app to expect: models put the site name here by mistake
    common = dict(label=label if el is None and x is None else "", role=role if el is None and x is None else "", expect=ex)
    if kind == "click":
        if el is None and x is None and not label: raise ProtocolError("click needs a control: \"element\" number, \"target\" text, or x and y.")
        btn = str(d.get("button", "left")).lower()
        return Action("click", element=el, x=x if el is None else None, y=y if el is None else None,
                      button=btn if btn in ("left", "right") else "left", double=bool(d.get("double")), **common)
    if kind == "type":
        text = clean(d.get("text"), MAX_TEXT)
        if not text: raise ProtocolError("type needs non-empty \"text\".")
        return Action("type", element=el, x=x if el is None else None, y=y if el is None else None, text=text, submit=bool(d.get("submit")), **common)
    if kind == "key": return Action("key", keys=normalize_keys(d.get("keys") or d.get("key") or ""), expect=ex)
    if kind == "scroll":
        direction = str(d.get("direction", "down")).lower()
        if direction not in DIRECTIONS: raise ProtocolError("direction must be up, down, left or right.")
        return Action("scroll", element=el, direction=direction, amount=_int(d, "amount", 1, 20) or 3, **common)
    if kind == "drag":
        x2, y2 = _int(d, "x2", 0, screen_w), _int(d, "y2", 0, screen_h)
        if None in (x, y, x2, y2): raise ProtocolError("drag needs x, y (start) and x2, y2 (end).")
        if not first: raise ProtocolError("drag uses coordinates, so it can only be the first action of a plan.")
        return Action("drag", x=x, y=y, x2=x2, y2=y2, expect=ex)
    if kind == "navigate":
        url = clean(d.get("url"), 2048).strip()
        if not url: raise ProtocolError("navigate needs a \"url\".")
        return Action("navigate", url=url, expect=ex)
    if kind == "open_app":
        name = clean(d.get("name") or d.get("app"), 80).strip()
        if not name: raise ProtocolError("open_app needs the app's \"name\".")
        return Action("open_app", name=name, expect=ex)
    if kind == "wait":
        try: sec = float(d.get("seconds", 1))
        except (TypeError, ValueError): sec = 1.0
        return Action("wait", seconds=min(10.0, max(0.2, sec)), expect=ex)
    if kind in ("back", "forward"): return Action(kind, expect=ex)
    return Action(kind, note=note)


@dataclass
class Plan:
    actions: list
    final: Action | None = None        # done / ask_user / fail, when the model ended the task
    say: str = ""
    notes: list = field(default_factory=list)


def parse_plan(reply: str, mode: str, *, screen_w: int = 4096, screen_h: int = 4096, n_elements: int = 0) -> Plan:
    """The reply is either {"plan": [action, ...]} or one action object. Up to 8 actions run back to back without asking the model again."""
    d = first_json_object(reply)
    raw = d.get("plan") if isinstance(d.get("plan"), list) else d.get("actions") if isinstance(d.get("actions"), list) else [d]
    if not raw: raise ProtocolError("The plan is empty. Give at least one action, or finish with done.")
    items: list = []
    for r in raw:
        if not isinstance(r, dict): continue
        if "action" not in r and isinstance(r.get("expect"), dict) and items and "action" in items[-1]:      # a stray {"expect": ...} step belongs to the step before it
            items[-1] = {**items[-1], "expect": {**(items[-1].get("expect") or {}), **r["expect"]}}
            continue
        items.append(r)
    if not items: raise ProtocolError("Each plan step must be a JSON object with an \"action\".")
    acts, notes, final = [], [], None
    for i, r in enumerate(items):
        a = action_from_dict(r, mode, first=(i == 0), screen_w=screen_w, screen_h=screen_h, n_elements=n_elements)
        if a.kind in TERMINAL:
            if a.kind == "done" and acts:
                notes.append("You can only finish with done on its own, after you have SEEN the result. The steps before it will run first; I will show you the screen.")
                break                                           # a model cannot know the outcome of steps it has not run yet
            final = a
            break
        acts.append(a)
        if len(acts) >= MAX_PLAN:
            if i + 1 < len(items): notes.append(f"Only the first {MAX_PLAN} steps run at a time.")
            break
    say = clean(d.get("say") or d.get("thought") or "", 200)
    return Plan(acts, final, say, notes)


# ------------------------------------------------------------------ what the app sends back
@dataclass(frozen=True)
class Element:
    i: int
    role: str
    label: str
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0
    secure: bool = False
    editable: bool = False
    value: str = ""
    checked: bool | None = None

    def line(self) -> str:
        bits = [f"[{self.i}] {self.role}"]
        if self.label: bits.append(f"\"{self.label}\"")
        if self.value and not self.secure: bits.append(f"value=\"{self.value}\"")
        if self.secure: bits.append("(password field)")
        if self.checked is not None: bits.append("checked" if self.checked else "unchecked")
        bits.append(f"@({self.x + self.w // 2},{self.y + self.h // 2})")
        return " ".join(bits)


@dataclass
class Observation:
    screenshot_b64: str = ""
    width: int = 0
    height: int = 0
    url: str = ""
    title: str = ""
    app: str = ""
    bundle_id: str = ""
    is_self: bool = False
    text: str = ""
    loading: bool = False
    elements: list = field(default_factory=list)
    error: str = ""
    error_code: str = ""
    gen: int = 0                   # which numbered list this is: an action must name it, so stale numbers are never clicked
    labels: list = field(default_factory=list)   # lower-case labels of everything on screen (cheap evidence for "did it work?")
    focused: str = ""
    changed: bool | None = None    # did this action change what is on screen? (None = unknown)
    has_secure: bool = False       # a password field is on screen
    source: str = ""               # ax | dom | ocr | ax+ocr : where the control list came from

    @property
    def by_index(self) -> dict:
        return {e.i: e for e in self.elements}

    def signature(self) -> str:
        """Cheap fingerprint of 'what the screen looks like', used to notice that an action changed nothing."""
        import hashlib
        h = hashlib.sha1()
        h.update(f"{self.url}|{self.title}|{self.app}|".encode("utf-8", "ignore"))
        h.update(self.screenshot_b64[:200_000].encode() if self.screenshot_b64 else "|".join(e.line() for e in self.elements).encode("utf-8", "ignore"))
        return h.hexdigest()


def _element(raw) -> Element | None:
    if not isinstance(raw, dict): return None
    try:
        return Element(int(raw["i"]), clean(raw.get("role"), 24) or "element", clean(raw.get("label"), 90).strip(),
                       int(raw.get("x", 0)), int(raw.get("y", 0)), int(raw.get("w", 0)), int(raw.get("h", 0)),
                       bool(raw.get("secure")), bool(raw.get("editable")), clean(raw.get("value"), 60),
                       raw.get("checked") if isinstance(raw.get("checked"), bool) else None)
    except (KeyError, TypeError, ValueError):
        return None


def parse_observation(res: dict, key: str = "observation") -> Observation:
    """Builds an Observation (or, for an action's result, a small 'state') from the app's JSON. Never raises on odd input."""
    if not isinstance(res, dict): return Observation(error="The app sent an unreadable screen.", error_code="bad")
    if not res.get("ok", True):
        return Observation(error=clean(res.get("error") or "The screen could not be read.", 400), error_code=clean(res.get("code") or "", 30))
    o = res.get(key) if isinstance(res.get(key), dict) else {}
    els = [e for e in (_element(r) for r in (o.get("elements") or [])[:MAX_ELEMENTS]) if e is not None]
    shot = o.get("screenshot_b64") if isinstance(o.get("screenshot_b64"), str) else ""
    labels = [clean(l, 90).lower() for l in (o.get("labels") or [])[:300] if isinstance(l, str)]
    return Observation(shot if len(shot) <= 6_000_000 else "", int(o.get("width") or 0), int(o.get("height") or 0), clean(o.get("url"), 2048), clean(o.get("title"), 200),
                       clean(o.get("app"), 120), clean(o.get("bundle_id"), 120), bool(o.get("is_self")), clean(o.get("text"), 6000), bool(o.get("loading")), els,
                       gen=int(o.get("gen") or 0), labels=labels, focused=clean(o.get("focused"), 90),
                       changed=o.get("changed") if isinstance(o.get("changed"), bool) else None,
                       has_secure=bool(o.get("has_secure")) or any(e.secure for e in els), source=clean(o.get("source"), 12))
