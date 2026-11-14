"""The rules that stand between a model and your computer. All of them are deterministic code that looks at what is really on the
screen (labels, URLs, app names reported by the macOS app), never at what the model claims it is doing.

  block    : never runs, no matter what anyone approves (secrets, password fields, other people's logins, the terminal, quitting, ...)
  approve  : the user sees exactly what is about to happen and must say yes (one action, single use)
  ok       : harmless on its own (scrolling, reading, typing ordinary text into an ordinary field, clicking an ordinary link)
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit
from ..security.netguard import EndpointRejected, NetPolicy, validate_endpoint
from ..security.redact import redact_text
from .protocol import Action, Element, Observation, OBSERVING

# --- apps the agent may never operate. The terminal would bypass the shell sandbox, a password manager holds your secrets, and
# --- ArjunOS itself holds the Approve buttons.
BLOCKED_APP_WORDS = ("terminal", "iterm", "keychain", "system settings", "system preferences", "script editor", "automator", "activity monitor",
                     "1password", "bitwarden", "lastpass", "dashlane", "keeper", "enpass", "arjunos", "jarvis", "disk utility", "shortcuts", "passwords")
BLOCKED_BUNDLE_PREFIXES = ("com.apple.terminal", "com.googlecode.iterm2", "com.apple.keychainaccess", "com.apple.systempreferences", "com.apple.scripteditor2",
                           "com.apple.automator", "com.apple.activitymonitor", "com.apple.passwords", "com.apple.shortcuts", "com.apple.diskutility",
                           "com.agilebits.", "com.1password.", "com.bitwarden.", "com.lastpass.", "com.dashlane.", "com.jarvis", "com.arjun")

# --- keyboard shortcuts
BLOCKED_KEYS = frozenset({"cmd+q", "cmd+opt+q", "cmd+shift+q", "cmd+ctrl+q", "cmd+opt+esc", "ctrl+opt+esc", "cmd+shift+delete", "cmd+opt+shift+delete",
                          "cmd+space", "ctrl+cmd+power", "cmd+opt+shift+esc"})
APPROVE_KEYS = frozenset({"cmd+w", "cmd+delete", "cmd+v", "cmd+shift+v", "cmd+opt+v", "cmd+shift+w", "cmd+opt+w"})

_SENSITIVE_LABEL = re.compile(
    r"\b(buy|purchase|pay|payment|place (?:your |my )?order|order now|checkout|check out|confirm|send|post|publish|tweet|reply|submit|delete|remove|erase|"
    r"empty|format|transfer|wire|withdraw|subscribe|unsubscribe|donate|install|uninstall|authori[sz]e|allow|grant|accept|agree|sign in|log in|login|"
    r"sign up|register|download|upload|share|invite|book|reserve|apply|empty trash|move to trash|reset|deactivate|close account|cancel (?:subscription|order|plan))\b", re.I)
_CREDENTIAL_FIELD = re.compile(r"\b(password|passcode|passphrase|pin|cvv|cvc|security code|card number|credit card|debit card|ssn|social security|"
                               r"routing number|account number|one[- ]time|otp|2fa|verification code|recovery code|seed phrase|private key)\b", re.I)
_SENSITIVE_URL = re.compile(r"(checkout|/pay\b|payment|billing|purchase|place[-_]?order|order/confirm|wallet|/bank|transfer|/cart/confirm)", re.I)
_CARD_DIGITS = re.compile(r"(?:\d[ -]?){13,19}")


@dataclass(frozen=True)
class Gate:
    level: str                       # ok | approve | block
    reason: str = ""
    flags: frozenset = frozenset()


@dataclass
class RunState:
    goal: str
    mode: str                        # browser | desktop
    approval_mode: str = "risky"     # risky | every
    offline: bool = False
    visited_hosts: set = field(default_factory=set)
    granted_apps: set = field(default_factory=set)


def host_of(url: str) -> str:
    try: return (urlsplit(url).hostname or "").lower()
    except ValueError: return ""


def goal_hosts(goal: str) -> set:
    """Hosts the USER wrote in their own request: those are pre-trusted for navigation."""
    out = set()
    for m in re.finditer(r"https?://[^\s<>\"')]+", goal or ""):
        h = host_of(m.group(0))
        if h: out.add(h)
    for m in re.finditer(r"\b((?:[a-z0-9-]+\.)+(?:com|org|net|io|dev|app|edu|gov|co|ai|me|tv|uk|de|fr|in|ca|au))\b", (goal or "").lower()):
        out.add(m.group(1))
    return out


def first_goal_url(goal: str) -> str | None:
    """The first web address the USER wrote in their request (https assumed for a bare domain), or None."""
    m = re.search(r"https?://[^\s<>\"')]+", goal or "")
    if m: return m.group(0).rstrip(".,;:!?")
    m = re.search(r"\b((?:[a-z0-9-]+\.)+(?:com|org|net|io|dev|app|edu|gov|co|ai|me|tv|uk|de|fr|in|ca|au))\b(/[^\s<>\"')]*)?", (goal or "").lower())
    return ("https://" + m.group(1) + (m.group(2) or "").rstrip(".,;:!?")) if m else None


_URLISH = re.compile(r"^\s*(https?://\S+|(?:(?:[a-z0-9-]+\.)+[a-z]{2,}|(?:\d{1,3}\.){3}\d{1,3}|localhost)(?::\d+)?(?:/\S*)?)\s*$", re.I)


def looks_like_url(text: str) -> str | None:
    """Text that is nothing but a web address (as typed into a browser's address bar), normalised to https://..., else None."""
    m = _URLISH.match(text or "")
    if not m: return None
    u = m.group(1)
    return u if re.match(r"https?://", u, re.I) else "https://" + u


def url_problem(url: str, offline: bool, *, resolver=None) -> str | None:
    """None when the agent may be on / go to this URL; otherwise a sentence for the user."""
    try:
        kw = {"resolver": resolver} if resolver else {}
        validate_endpoint(url, NetPolicy(allow_remote=True, offline_mode=offline), **kw)
    except EndpointRejected as e:
        return str(e)
    return None


def app_problem(app: str, bundle_id: str, is_self: bool) -> str | None:
    a, b = (app or "").strip().lower(), (bundle_id or "").strip().lower()
    if is_self: return "That is ArjunOS itself. I never click inside it, because that is where your approvals live."
    if any(w in a for w in BLOCKED_APP_WORDS) or any(b.startswith(p) for p in BLOCKED_BUNDLE_PREFIXES):
        return f"{app or bundle_id} is off limits for computer control (terminals, password managers and system settings can never be driven by an AI)."
    return None


def luhn_card(text: str) -> bool:
    for m in _CARD_DIGITS.finditer(text or ""):
        d = [int(c) for c in m.group(0) if c.isdigit()]
        if 13 <= len(d) <= 19 and sum(x if i % 2 == 0 else (x * 2 - 9 if x * 2 > 9 else x * 2) for i, x in enumerate(reversed(d))) % 10 == 0:
            return True
    return False


def target_element(action: Action, obs: Observation) -> Element | None:
    """The element an action lands on: the one it names, else the smallest one under its x,y."""
    if action.element is not None: return obs.by_index.get(action.element)
    if action.x is None or action.y is None: return None
    hit = [e for e in obs.elements if e.x <= action.x <= e.x + e.w and e.y <= action.y <= e.y + e.h and e.w > 0 and e.h > 0]
    return min(hit, key=lambda e: e.w * e.h) if hit else None


def describe(action: Action, obs: Observation | None = None) -> str:
    """One human sentence for the activity log and the approval card."""
    el = target_element(action, obs) if obs else None
    what = f"“{el.label}”" if el and el.label else (f"{el.role}" if el else (f"point ({action.x}, {action.y})" if action.x is not None else "the focused control"))
    k = action.kind
    if k == "click": return f"{'Double-click' if action.double else ('Right-click' if action.button == 'right' else 'Click')} {what}"
    if k == "type":
        shown = action.text if len(action.text) <= 80 else action.text[:77] + "…"
        return f"Type “{shown}” into {what}" + (" and press Enter" if action.submit else "")
    if k == "key": return f"Press {action.keys}"
    if k == "scroll": return f"Scroll {action.direction}"
    if k == "drag": return f"Drag from ({action.x}, {action.y}) to ({action.x2}, {action.y2})"
    if k == "navigate": return f"Go to {action.url}"
    if k == "open_app": return f"Open the app {action.name}"
    if k == "wait": return "Wait"
    if k in ("back", "forward"): return f"Go {k}"
    return k


def assess(action: Action, obs: Observation, st: RunState, *, injected: bool = False, url_issue: str | None = None) -> Gate:
    k = action.kind
    if k in OBSERVING: return Gate("ok")
    every = st.approval_mode == "every" or injected
    why_every = "this page contains text that tries to give me orders" if injected else "you asked to approve every action"

    # ---- hard blocks ----
    if st.mode == "desktop":
        p = app_problem(obs.app, obs.bundle_id, obs.is_self)
        if p and not (k == "open_app" or (k == "key" and action.keys == "cmd+tab")):     # the only way out of an off-limits app
            return Gate("block", p)
    if k == "open_app":
        p = app_problem(action.name, "", False)
        if p: return Gate("block", p)
        return Gate("approve", f"open {action.name}", frozenset({"privileged"}))
    if k == "key":
        if action.keys in BLOCKED_KEYS: return Gate("block", f"{action.keys} could quit apps, lock the Mac or open launchers, so I will not press it.")
    if k == "navigate":
        if url_issue: return Gate("block", url_issue)
    el = target_element(action, obs)
    typed_url = looks_like_url(action.text) if (k == "type" and st.mode == "desktop") else None
    if typed_url and url_issue: return Gate("block", url_issue)
    if k == "type":
        if el is not None and el.secure:
            return Gate("block", "That is a password field. I never type passwords: ask the user to enter it themselves.")
        if el is not None and _CREDENTIAL_FIELD.search(el.label or ""):
            return Gate("block", f"“{el.label}” asks for a credential or payment detail. Ask the user to type it themselves.")
        if redact_text(action.text) != action.text:
            return Gate("block", "That text looks like a secret (key, token or password), so I will not type it anywhere.")
        if luhn_card(action.text):
            return Gate("block", "That looks like a payment card number, so I will not type it anywhere.")

    # ---- approvals ----
    if st.mode == "desktop":
        app = (obs.app or "").strip().lower()
        if app and app not in st.granted_apps:
            return Gate("approve", f"control {obs.app}", frozenset({"privileged"}))
    flags = set()
    if typed_url and host_of(typed_url) not in st.visited_hosts:
        return Gate("approve", f"visit {host_of(typed_url)} (a site this task has not used yet)")
    if k == "navigate":
        h = host_of(action.url)
        if h not in st.visited_hosts: return Gate("approve", f"visit {h or action.url} (a site this task has not used yet)")
    if k == "drag": return Gate("approve", "drag and drop can move or delete things")
    if k == "key" and action.keys in APPROVE_KEYS: return Gate("approve", f"{action.keys} can close things or paste your clipboard")
    labelled = f"{el.role} “{el.label}”" if el and el.label else ""
    if k == "click" and el is not None and (_SENSITIVE_LABEL.search(el.label or "")):
        flags.add("purchase" if re.search(r"buy|purchase|pay|order|checkout|check out|donate", el.label, re.I) else "external_communication")
        if re.search(r"delete|remove|erase|empty|format|uninstall|trash|close account", el.label, re.I): flags = {"destructive"}
        return Gate("approve", f"the {labelled} button looks like it makes a real change", frozenset(flags))
    on_sensitive_page = bool(_SENSITIVE_URL.search(obs.url or "")) and k in ("click", "type", "key")
    if on_sensitive_page and (k == "click" or (k == "type" and action.submit) or (k == "key" and action.keys == "enter")):
        return Gate("approve", "this looks like a checkout, payment or banking page", frozenset({"purchase"}))
    if k == "type" and el is None and (obs.has_secure or any(e.secure for e in obs.elements)):
        return Gate("approve", "a password field is on screen and I am not sure where this text will go")
    if every: return Gate("approve", why_every)
    return Gate("ok")
