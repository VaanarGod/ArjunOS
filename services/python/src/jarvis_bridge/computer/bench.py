"""Latency benchmark for computer use on a REAL local model, with no Mac involved.

It runs the real ComputerRunner (the same prompts, schema, budget, marks and timing code the app uses) against a synthetic Finder-like screen, so the
only thing being measured is the model and the bridge. The task is always "open the Downloads folder": one click on a control that is somewhere in a
list of N controls. Different screen sizes and prompt budgets show where time goes and where a small model starts to miss.

    python -m jarvis_bridge.computer.bench --model qwen2.5:7b
    python -m jarvis_bridge.computer.bench --model qwen2.5vl:7b --vision --controls 30,120 --budgets 3000,6000,9000 --runs 3

Every approval is granted automatically: the machine is simulated, nothing real can happen. Do not reuse this runner for anything else.
"""
from __future__ import annotations
import argparse, asyncio, base64, io, json, statistics, sys, tempfile
from pathlib import Path
from ..inference.ollama import DEFAULT_URL, OllamaProvider
from ..security.audit import AuditLog
from ..security.policy import PolicyEngine
from ..settings import SettingsStore
from .agent import ComputerRunner, stream_options
from .broker import ComputerBroker

SIDEBAR = ["Recents", "Applications", "Desktop", "Documents", "Downloads", "Movies", "Music", "Pictures"]
TOOLBAR = [("Back", "button"), ("Forward", "button"), ("Search", "text field")]


class SimMac:
    """A tiny simulated Finder window. Clicking "Downloads" moves to the Downloads screen; anything else changes nothing."""
    def __init__(self, broker: ComputerBroker, controls: int, *, text_chars: int = 1200, with_image: bool = False):
        self.broker, self.controls, self.text_chars, self.with_image = broker, controls, text_chars, with_image
        self.screen, self.gen, self.acts = "recents", 0, []

    def elements(self) -> list:
        els = [(t, r) for t, r in TOOLBAR] + [(s, "button") for s in SIDEBAR]
        els += [(f"File {i:03d}.txt", "row") for i in range(max(0, self.controls - len(els)))]
        out = []
        for i, (label, role) in enumerate(els[:160]):                     # a grid of up to 160 controls inside a 1000x700 window
            out.append({"i": i, "role": role, "label": label, "x": 10 + 160 * (i // 28), "y": 10 + 24 * (i % 28), "w": 150, "h": 20, "editable": role == "text field"})
        return out

    def _png(self, els: list) -> str:
        try: from PIL import Image, ImageDraw
        except Exception: return ""
        img = Image.new("RGB", (1000, 700), (245, 245, 247)); d = ImageDraw.Draw(img)
        for e in els:
            d.rectangle((e["x"], e["y"], e["x"] + e["w"], e["y"] + e["h"]), fill=(255, 255, 255), outline=(200, 200, 205)); d.text((e["x"] + 6, e["y"] + 4), e["label"], fill=(20, 20, 20))
        buf = io.BytesIO(); img.save(buf, "PNG"); return base64.b64encode(buf.getvalue()).decode()

    def state(self, full: bool) -> dict:
        self.gen += 1
        els = self.elements()
        title = "Downloads" if self.screen == "downloads" else "Recents"
        d = {"app": "Finder", "bundle_id": "com.apple.finder", "title": title, "url": "", "gen": self.gen, "source": "ax", "changed": True, "width": 1000, "height": 700,
             "labels": [e["label"].lower() for e in els] + [title.lower()], "text": ("Folder contents. " * 80)[: self.text_chars]}
        if full:
            d["elements"] = els
            if self.with_image: d["screenshot_b64"] = self._png(els)
        return d

    def answer(self, req: dict):
        k, res = req["kind"], None
        if k == "observe": res = {"ok": True, "observation": self.state(True)}
        elif k == "state": res = {"ok": True, "state": self.state(False)}
        elif k == "resolve":
            want = (req["target"].get("label") or "").lower(); hit = None
            for e in self.elements():
                if want and (want == e["label"].lower() or want in e["label"].lower()) or ("i" in req["target"] and req["target"]["i"] == e["i"]): hit = e; break
            res = {"ok": True, "element": hit, "state": self.state(False)} if hit else {"ok": False, "error": "no such control", "code": "not_found"}
        elif k == "act":
            a = req["action"]; self.acts.append(a)
            label = (a.get("label") or "").lower()
            if a["kind"] == "click" and (label == "downloads" or (a.get("element") is not None and self.elements()[a["element"]]["label"] == "Downloads")): self.screen = "downloads"
            res = {"ok": True, "state": self.state(False)}
        if res is not None: self.broker.resolve(req["id"], res)

    def emit(self, ev: dict):
        req = ev.get("computer_request")
        if req and req.get("kind") != "end": asyncio.get_running_loop().call_soon(self.answer, req)


async def run_case(stream_for, model: str, *, controls: int, budget: int, vision: bool, marks: bool, num_ctx: int, text_chars: int = 1200) -> dict:
    """One run of the task. `stream_for(cfg)` returns the model stream the runner calls."""
    with tempfile.TemporaryDirectory() as d:
        settings = SettingsStore(Path(d) / "s.json")
        settings.update(computer_consented=True, computer_desktop_enabled=True, computer_prompt_chars=budget, computer_marks=marks, computer_num_ctx=num_ctx, computer_max_steps=12)
        audit = AuditLog(); policy = PolicyEngine(audit); broker = ComputerBroker()
        runner = ComputerRunner(settings, policy, audit, broker)
        runner.APPROVAL_WAIT, runner.VERIFY_GAP = 60.0, 0.05
        mac = SimMac(broker, controls, text_chars=text_chars, with_image=vision)
        stop = asyncio.Event()

        async def approver():
            while not stop.is_set():
                for p in policy.pending(): policy.resolve(p.approval_id, True)
                await asyncio.sleep(0.02)
        t = asyncio.create_task(approver())
        try: out = await runner.run("Open the Downloads folder", "desktop", mac.emit, 1, stream=stream_for(settings.value), model=model, vision=vision)
        finally: stop.set(); t.cancel()
    s = out.stats or {}
    return {"controls": controls, "budget": budget, "vision": vision, "marks": marks, "status": out.status, "reached_goal": mac.screen == "downloads", "steps": out.steps, **s}


def summarise(rows: list) -> dict:
    """Median over repeated runs of the same case. A case 'passes' when the task was finished on screen."""
    def med(k): xs = [r[k] for r in rows if r.get(k) is not None]; return int(statistics.median(xs)) if xs else None
    r0 = rows[0]
    return {"controls": r0["controls"], "budget": r0["budget"], "vision": r0["vision"], "marks": r0["marks"], "runs": len(rows), "passed": sum(1 for r in rows if r["reached_goal"] and r["status"] == "done"),
            "first_action_ms": med("first_action_ms"), "wall_ms": med("wall_ms"), "model_calls": med("model_calls"), "model_ms_avg": med("model_ms_avg"), "prompt_tokens_avg": med("prompt_tokens_avg"),
            "prompt_chars_max": med("prompt_chars_max"), "context_full_calls": max((r.get("context_full_calls") or 0) for r in rows)}


def table(cases: list) -> str:
    head = ["controls", "budget", "vision", "marks", "pass", "first action", "total", "model calls", "model avg", "prompt tok", "ctx full"]
    out = [head]
    f = lambda v, u="": "n/a" if v is None else f"{v}{u}"
    for c in cases:
        out.append([str(c["controls"]), str(c["budget"]), "yes" if c["vision"] else "no", "yes" if c["marks"] else "no", f"{c['passed']}/{c['runs']}", f(c["first_action_ms"], " ms"), f(c["wall_ms"], " ms"),
                    f(c["model_calls"]), f(c["model_ms_avg"], " ms"), f(c["prompt_tokens_avg"]), "YES" if c["context_full_calls"] else "no"])
    w = [max(len(r[i]) for r in out) for i in range(len(head))]
    return "\n".join("  ".join(c.ljust(w[i]) for i, c in enumerate(r)) for r in out)


async def bench(stream_for, model: str, *, controls: list, budgets: list, vision: bool, marks: bool, runs: int, num_ctx: int, progress=None) -> list:
    cases = []
    for n in controls:
        for b in budgets:
            rows = []
            for r in range(runs):
                if progress: progress(f"{n} controls, budget {b}, run {r + 1}/{runs} ...")
                rows.append(await run_case(stream_for, model, controls=n, budget=b, vision=vision, marks=marks, num_ctx=num_ctx))
            cases.append(summarise(rows))
    return cases


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True); ap.add_argument("--endpoint", default=DEFAULT_URL)
    ap.add_argument("--controls", default="30,120", help="comma list: how many controls the synthetic screen has")
    ap.add_argument("--budgets", default="3000,6000,9000", help="comma list: computer_prompt_chars values to compare")
    ap.add_argument("--runs", type=int, default=2); ap.add_argument("--vision", action="store_true", help="send screenshots (use a vision model)")
    ap.add_argument("--no-marks", action="store_true"); ap.add_argument("--num-ctx", type=int, default=8192); ap.add_argument("--json", help="also write the results to this file")
    a = ap.parse_args(argv)
    prov = OllamaProvider(a.endpoint)

    def stream_for(cfg):
        opts = stream_options(cfg)
        return lambda model, messages, **extra: prov.chat_stream(model, messages, **{**opts, **extra})

    async def go():
        try:
            h = await prov.health()
            if not h.ok: print(f"Cannot reach Ollama at {a.endpoint}: {h.detail}", file=sys.stderr); return None
            await prov.load_model(a.model)                                  # the first call must not include loading the model from disk
            return await bench(stream_for, a.model, controls=[int(x) for x in a.controls.split(",")], budgets=[int(x) for x in a.budgets.split(",")], vision=a.vision,
                               marks=not a.no_marks, runs=a.runs, num_ctx=a.num_ctx, progress=lambda m: print(m, file=sys.stderr))
        finally: await prov.aclose()
    cases = asyncio.run(go())
    if cases is None: return 2
    print(); print(table(cases)); print("\nTarget: first action in 2-5 s. 'ctx full' means the prompt filled the context window (raise --num-ctx or lower the budget).")
    if a.json: Path(a.json).write_text(json.dumps(cases, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
