"""Did the action do what the plan expected? Answered from Accessibility / DOM facts the app reports after the action (app, window title, URL,
the labels on screen). No model is involved, which is what lets a plan of several steps run without asking the LLM between them."""
from __future__ import annotations
from .protocol import Action, Observation


def expectations(action: Action) -> dict:
    ex = dict(action.expect)
    if action.kind == "open_app" and "app" not in ex: ex["app"] = action.name.strip().lower()
    return ex


def check(action: Action, state: Observation) -> str | None:
    """None when every expectation holds; otherwise one sentence for the model (it is shown on the next planning turn)."""
    ex = expectations(action)
    app, title, url = state.app.lower(), state.title.lower(), state.url.lower()
    if "app" in ex and ex["app"] not in app and ex["app"] not in state.bundle_id.lower():
        return f"expected the front app to be \"{ex['app']}\" but it is \"{state.app or 'unknown'}\""
    if "title" in ex and ex["title"] not in title:
        return f"expected the window title to contain \"{ex['title']}\" but it is \"{state.title or 'empty'}\""
    if "url" in ex and ex["url"] not in url:
        return f"expected the address to contain \"{ex['url']}\" but it is \"{state.url or 'empty'}\""
    pool = [*state.labels, state.focused.lower()]
    if "label" in ex and not any(ex["label"] in l for l in pool if l):
        return f"expected to see \"{ex['label']}\" on screen, but it is not there"
    if "gone" in ex and any(ex["gone"] in l for l in pool if l):
        return f"expected \"{ex['gone']}\" to disappear, but it is still on screen"
    return None
