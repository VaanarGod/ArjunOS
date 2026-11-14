"""Rule-based detection of 'do this on my computer' requests, so a small local model does not have to invent a tag to start a task.
Deliberately conservative: questions about how to do things are not tasks. A detected task still asks for the user's approval before it starts."""
from __future__ import annotations
import re

APPS = ("finder|safari|notes|mail|calendar|messages|preview|textedit|xcode|music|photos|reminders|maps|pages|numbers|keynote|chrome|firefox|slack|"
        "vs ?code|visual studio code|spotify|zoom|word|excel|powerpoint|obsidian|system settings|terminal|contacts|facetime|books|podcasts|calculator")
_LEAD = re.compile(r"^\s*(?:hey\s+)?(?:please\s+|pls\s+)?(?:(?:can|could|would|will)\s+you\s+)?(?:please\s+)?", re.I)
_EXPLAIN = re.compile(r"^(?:how|what|why|when|where|who|which|explain|describe|tell me|is|are|does|do|did|should|shall|whats|what's)\b", re.I)
_DESKTOP = [
    re.compile(rf"^(?:open|launch|start|switch to|bring up|go to)\s+(?:the\s+)?(?:{APPS})\b", re.I),
    re.compile(rf"\b(?:open|launch|switch to)\s+(?:the\s+)?(?:{APPS})\b.*\b(?:and|then)\b", re.I),
    re.compile(rf"\b(?:in|using|with)\s+(?:the\s+)?(?:{APPS})\b.*\b(?:find|locate|search|show|create|click|type|write|add|move|rename)\b", re.I),
    re.compile(r"\b(?:find|locate|search for|show me)\b.*\b(?:on|in) my (?:mac|computer|desktop|laptop|disk|drive)\b", re.I),
    re.compile(r"^(?:click|press|type|scroll)\b.*\b(?:on my screen|on screen|in the app|the button)\b", re.I),
    re.compile(r"\b(?:take control|control my (?:mac|computer)|operate my (?:mac|computer))\b", re.I),
]
_BROWSER = [
    re.compile(r"\b(?:in|using|with|on)\s+(?:the\s+)?(?:built-in |integrated |ArjunOS )?browser\b.*\b(?:go|open|search|find|click|fill|log|navigate|add|book|check)\b", re.I),
    re.compile(r"^(?:browse to|go to|navigate to|visit)\s+\S+.*\b(?:and|then)\b", re.I),
    re.compile(r"\b(?:fill (?:in|out)|click|add to cart)\b.*\b(?:on|in) (?:this|the) (?:page|site|website)\b", re.I),
]


def computer_intent(text: str, *, desktop_ok: bool, browser_ok: bool) -> str | None:
    t = (text or "").strip()
    if not t or len(t) > 600 or t.count("\n") > 3: return None
    body = _LEAD.sub("", t, count=1)
    if _EXPLAIN.match(body) or t.endswith("?") and not re.match(r"^(?:can|could|would|will)\s+you\b", t, re.I): return None
    if desktop_ok and any(p.search(body) for p in _DESKTOP): return "desktop"
    if browser_ok and any(p.search(body) for p in _BROWSER): return "browser"
    return None
