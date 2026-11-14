"""Keeps the screen text given to the model small. On a local model the time to the first answer is mostly spent reading the prompt, so the control
list and page text are fitted into a character budget instead of always being sent whole.

Dropping a control from the LIST never makes it unusable: a plan step names a control by its text and the machine looks it up in the full list when the
step runs. The model just does not spend time reading rows it is unlikely to need. The kept controls keep their original numbers.
"""
from __future__ import annotations

_HIGH = ("text field", "search", "combo", "text area", "textfield", "secure")
_MID = ("button", "link", "menu", "tab", "check", "radio", "pop", "toggle", "switch", "slider", "stepper", "disclosure", "segment", "item")
_LOW = ("row", "cell", "outline", "list", "image", "icon")


def priority(e) -> int:
    """3 = where you type, 2 = what you press, 1 = things you pick from, 0 = anything else."""
    r = (e.role or "").lower()
    if e.editable or e.secure or any(k in r for k in _HIGH): return 3
    if any(k in r for k in _MID): return 2
    if any(k in r for k in _LOW): return 1
    return 0


def fit_controls(elements: list, budget_chars: int) -> tuple:
    """(kept controls in their original order, how many were left out). Everything is kept when it fits."""
    if sum(len(e.line()) + 1 for e in elements) <= budget_chars: return list(elements), 0
    seen, cand = set(), []
    for pos, e in enumerate(elements):                                    # a repeated control (same role and label) adds nothing the first one does not say
        key = (e.role.lower(), e.label.lower())
        if e.label and key in seen: continue
        seen.add(key)
        cand.append((pos, e))
    ranked = sorted(cand, key=lambda pe: (-(priority(pe[1]) if pe[1].label or pe[1].editable else -1), pe[0]))
    kept, used = [], 0
    for pos, e in ranked:
        cost = len(e.line()) + 1
        if used + cost > budget_chars: continue                            # a long line may not fit while a shorter one still does
        kept.append((pos, e)); used += cost
    kept.sort(key=lambda pe: pe[0])
    return [e for _, e in kept], len(elements) - len(kept)


def text_allowance(budget_chars: int, controls_chars: int, cap: int = 3000, floor: int = 600) -> int:
    """What is left of the budget for the page text: never more than the old fixed cap, never less than a short floor."""
    return max(floor, min(cap, budget_chars - controls_chars))
