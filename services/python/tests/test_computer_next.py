"""Computer use, second round: user takeover, trusted clicks, marked screenshots, prompt budget and timings, the optional Cua Driver backend.
As in test_computer.py the Mac is simulated: these tests prove what the bridge asks for and enforces, not that any Swift or Cua code works."""
import asyncio, json
import pytest
from test_computer import Env, FakeMac, Model, done, finder_world, plan
from jarvis_bridge.computer.agent import RISKY_TOOL, SAFE_TOOL


def takeover_when(env, pred):
    """From the moment pred(env) is true, every answer from the simulated Mac says the person touched the mouse or keyboard."""
    orig = env.broker.resolve
    def resolve(rid, res):
        if isinstance(res, dict) and pred(env): res = {**res, "takeover": True}
        return orig(rid, res)
    env.broker.resolve = resolve


# ====================================================================== user takeover
async def test_touching_the_mouse_or_keyboard_mid_plan_stops_the_task_and_nothing_else_runs(tmp_path):
    screens, moves = finder_world(); e = Env(tmp_path, screens, "notes", moves)
    takeover_when(e, lambda env: len(env.mac.acts) >= 1)                                  # the person grabs the mouse after the first action
    m = Model(plan({"action": "open_app", "name": "Finder"}, {"action": "key", "keys": "cmd+f"}, {"action": "type", "target": "Search", "text": "x"}), done())
    out = await e.run(m, "Open Finder and search")
    assert out.status == "stopped" and "mouse or keyboard" in out.text
    assert len(e.mac.acts) == 1                                                           # the second and third steps never ran
    assert len(m.calls) == 1                                                              # and the model was not asked what to do next
    assert any(d["decision"] == "user_takeover" for d in e.audit.query(tool_id="computer:run"))
    assert any("notice" in ev and "took over" in ev["notice"] for ev in e.events)
    assert {"computer_request": {"id": "end", "kind": "end"}} in e.mac.events            # the overlay is still told to go away

async def test_takeover_reported_while_looking_at_the_screen_also_stops_before_the_model_is_called(tmp_path):
    screens, moves = finder_world(); e = Env(tmp_path, screens, "notes", moves)
    takeover_when(e, lambda env: True)
    m = Model(done())
    out = await e.run(m, "Open Finder")
    assert out.status == "stopped" and m.calls == [] and e.mac.acts == []

async def test_takeover_can_also_arrive_as_an_error_code(tmp_path):
    screens, moves = finder_world(); e = Env(tmp_path, screens, "notes", moves)
    e.mac.fail_next = None
    orig = e.broker.resolve
    e.broker.resolve = lambda rid, res: orig(rid, {"ok": False, "error": "input detected", "code": "takeover"} if (isinstance(res, dict) and len(e.mac.acts) >= 1) else res)
    m = Model(plan({"action": "open_app", "name": "Finder"}, {"action": "key", "keys": "tab"}), done())
    out = await e.run(m, "Open Finder")
    assert out.status == "stopped" and "mouse or keyboard" in out.text

async def test_a_normal_stop_is_still_just_stopped(tmp_path):
    screens, moves = finder_world(); e = Env(tmp_path, screens, "notes", moves)
    m = Model(plan({"action": "open_app", "name": "Finder"}), done())
    async def stopper():
        while not e.mac.acts: await asyncio.sleep(0.005)
        e.runner.stop_all()
    t = asyncio.create_task(stopper())
    out = await e.run(m, "Open Finder"); t.cancel()
    assert out.status in ("stopped", "done")                                              # a stop that lands after the last step is allowed to lose the race
    assert not any(d["decision"] == "user_takeover" for d in e.audit.query(tool_id="computer:run"))

def test_the_api_accepts_the_takeover_flag_from_the_app():
    from jarvis_bridge.api.server import ComputerResultReq
    r = ComputerResultReq(ok=True, takeover=True)
    assert r.model_dump(exclude_none=True)["takeover"] is True
    assert "takeover" not in ComputerResultReq(ok=True).model_dump(exclude_none=True)


# ====================================================================== trusted (OS-level) clicks in web pages
def browser_world():
    screens = {"shop": {"app": "ArjunOS browser", "bundle_id": "browser", "title": "Shop", "url": "https://shop.example/", "elements": [{"label": "Show details"}, {"label": "Buy now"}]},
               "open": {"app": "ArjunOS browser", "bundle_id": "browser", "title": "Details", "url": "https://shop.example/", "elements": [{"label": "Hide details"}, {"label": "Buy now"}]}}
    return screens


def picky_page(env, *, ignores_dom_clicks):
    """A page whose scripts only react to trusted clicks: the DOM click lands but changes nothing."""
    orig = env.mac._answer
    def answer(req):
        if req["kind"] == "act" and req["action"]["kind"] == "click":
            trusted = bool(req["action"].get("trusted"))
            env.mac.acts.append(req["action"]); env.mac.requests.append(req)
            if trusted or not ignores_dom_clicks: env.mac.cur = "open"
            st = env.mac._state(); st["changed"] = env.mac.cur == "open"
            env.mac.act_gens = getattr(env.mac, "act_gens", []) + [st["gen"]]
            env.broker.resolve(req["id"], {"ok": True, "state": st})
        else: orig(req)
    env.mac._answer = answer


async def test_a_dom_click_the_page_ignored_is_retried_once_as_a_real_click(tmp_path):
    e = Env(tmp_path, browser_world(), "shop"); picky_page(e, ignores_dom_clicks=True)
    m = Model(plan({"action": "click", "target": "Show details"}), done("Details are showing."))
    out = await e.run(m, "show the details", mode="browser")
    assert out.status == "done"
    clicks = [a for a in e.mac.acts if a["kind"] == "click"]
    assert [bool(a.get("trusted")) for a in clicks] == [False, True]                      # first a DOM click, then one real click
    acts = [r for r in e.mac.requests if r["kind"] == "act"]
    assert acts[1]["gen"] == e.mac.act_gens[0]                                            # the retry names the page generation the first click reported, not the older one it was planned on
    assert len(m.calls) == 2                                                              # the model was never asked to deal with it
    assert any(d["detail"].get("trusted") for d in e.audit.query(tool_id=SAFE_TOOL) if d.get("detail"))

async def test_a_click_that_worked_is_never_repeated(tmp_path):
    e = Env(tmp_path, browser_world(), "shop"); picky_page(e, ignores_dom_clicks=False)
    m = Model(plan({"action": "click", "target": "Show details"}), done())
    await e.run(m, "show the details", mode="browser")
    assert [bool(a.get("trusted")) for a in e.mac.acts if a["kind"] == "click"] == [False]

async def test_a_consequential_click_is_never_retried_automatically(tmp_path):
    e = Env(tmp_path, browser_world(), "shop"); picky_page(e, ignores_dom_clicks=True)
    m = Model(plan({"action": "click", "target": "Buy now"}), done())
    out = await e.run(m, "buy it", mode="browser", decide=lambda p: True)
    clicks = [a for a in e.mac.acts if a["kind"] == "click"]
    assert len(clicks) == 1 and not clicks[0].get("trusted")                              # approved once, performed once: no second purchase
    assert e.seen_approvals                                                               # and it did ask first

async def test_the_model_cannot_ask_for_a_trusted_click_itself():
    from jarvis_bridge.computer.protocol import parse_plan
    a = parse_plan(plan({"action": "click", "target": "Go", "trusted": True}), "browser").actions[0]
    assert a.trusted is False and "trusted" not in a.wire()


# ====================================================================== marked screenshots
import base64, io
from jarvis_bridge.computer import marks as marks_mod
from jarvis_bridge.computer.marks import mark_screenshot
from jarvis_bridge.computer.protocol import Element

PIL = pytest.importorskip("PIL.Image")
from PIL import Image


def png_b64(w=400, h=300, colour=(250, 250, 250), fmt="PNG"):
    buf = io.BytesIO(); Image.new("RGB", (w, h), colour).save(buf, fmt)
    return base64.b64encode(buf.getvalue()).decode()

def decode(b64): return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")

def els(*boxes): return [Element(i, "button", f"b{i}", *b) for i, b in enumerate(boxes)]


def test_boxes_and_numbers_are_drawn_where_the_controls_are_and_nowhere_else():
    src = png_b64()
    out = mark_screenshot(src, els((50, 60, 120, 40), (200, 150, 100, 50)), width=400, height=300)
    assert out.changed and out.marked == (0, 1) and out.b64 != src
    a, b = decode(src), decode(out.b64)
    assert a.size == b.size == (400, 300)
    assert b.getpixel((50, 80)) != a.getpixel((50, 80))                                   # the left edge of box 0 is coloured
    assert b.getpixel((200, 175)) != a.getpixel((200, 175))                               # and of box 1
    assert b.getpixel((10, 10)) == a.getpixel((10, 10)) and b.getpixel((390, 290)) == a.getpixel((390, 290))   # empty areas untouched
    badge = [(x, y) for x in range(50, 62) for y in range(60 - 20, 60) if b.getpixel((x, y)) != a.getpixel((x, y))]
    assert badge                                                                          # a numbered badge sits just above box 0

def test_boxes_are_scaled_when_the_picture_is_not_the_size_the_coordinates_refer_to():
    src = png_b64(800, 600)                                                              # a picture twice the size of the coordinate space
    out = mark_screenshot(src, els((50, 60, 120, 40)), width=400, height=300)
    a, b = decode(src), decode(out.b64)
    assert b.getpixel((100, 160)) != a.getpixel((100, 160)) and b.getpixel((50, 80)) == a.getpixel((50, 80))     # the box is at (100,120) in this picture

def test_controls_that_cannot_be_placed_are_skipped_and_the_count_is_capped():
    out = mark_screenshot(png_b64(), els((10, 10, 0, 0), (900, 900, 50, 50), (-80, -80, 20, 20), (30, 30, 60, 30)), width=400, height=300)
    assert out.marked == (3,)                                                            # zero-size, off-screen and negative boxes get no number
    many = els(*[(5 + (i % 10) * 38, 5 + (i // 10) * 28, 30, 20) for i in range(80)])
    assert len(mark_screenshot(png_b64(), many, width=400, height=300, max_marks=25).marked) == 25

def test_nothing_is_drawn_for_bad_input_and_the_original_comes_back():
    good = png_b64()
    for bad in ("", "!!!notbase64!!!", base64.b64encode(b"not an image at all").decode(), good[:60]):
        r = mark_screenshot(bad, els((10, 10, 50, 50)), width=400, height=300)
        assert r.b64 == bad and not r.changed and r.marked == ()
    assert mark_screenshot(good, [], width=400, height=300).b64 == good

def test_a_huge_picture_is_refused_before_it_is_decoded():
    big = png_b64(5000, 4000)                                                            # 20 million pixels
    r = mark_screenshot(big, els((10, 10, 50, 50)), width=5000, height=4000)
    assert not r.changed and r.b64 == big

def test_without_pillow_the_original_screenshot_is_used(monkeypatch):
    monkeypatch.setattr(marks_mod, "HAVE_PIL", False)
    src = png_b64(); assert mark_screenshot(src, els((10, 10, 50, 50)), width=400, height=300).b64 == src

def test_only_numbers_are_drawn_never_labels(monkeypatch):
    from PIL import ImageDraw
    drawn = []; orig = ImageDraw.ImageDraw.text
    monkeypatch.setattr(ImageDraw.ImageDraw, "text", lambda self, xy, text, *a, **k: (drawn.append(text), orig(self, xy, text, *a, **k))[1])
    e = [Element(0, "text field", "Card number 4111 1111 1111 1111", 20, 20, 200, 30, editable=True, value="secret"), Element(7, "button", "Pay now", 20, 100, 80, 30)]
    out = mark_screenshot(png_b64(), e, width=400, height=300)
    assert out.marked == (0, 7) and drawn == ["0", "7"]                                   # the only text that ever touches the picture is the index

async def test_a_vision_model_gets_the_marked_picture_and_is_told_what_the_boxes_mean(tmp_path):
    screens = {"s": {"app": "Notes", "bundle_id": "com.apple.Notes", "title": "Notes", "elements": [{"label": "New Note"}, {"label": "Search"}]}}
    e = Env(tmp_path, screens, "s"); orig = e.mac._answer; src = png_b64(1000, 700)
    def shot(req):
        if req["kind"] == "observe": e.mac.requests.append(req); e.broker.resolve(req["id"], {"ok": True, "observation": {**e.mac._state(True), "screenshot_b64": src}})
        else: orig(req)
    e.mac._answer = shot
    m = Model(plan({"action": "ask_user", "question": "which one?"}))
    await e.run(m, "open notes", vision=True)
    sent = m.calls[0][-1].images_b64[0]
    assert sent != src and decode(sent).size == (1000, 700)                                # a marked copy went to the model
    assert "numbered boxes" in m.prompt(0) and "control [N]" in m.prompt(0)

async def test_marks_can_be_switched_off(tmp_path):
    screens = {"s": {"app": "Notes", "bundle_id": "com.apple.Notes", "title": "Notes", "elements": [{"label": "New Note"}]}}
    e = Env(tmp_path, screens, "s", computer_marks=False); orig = e.mac._answer; src = png_b64(1000, 700)
    def shot(req):
        if req["kind"] == "observe": e.mac.requests.append(req); e.broker.resolve(req["id"], {"ok": True, "observation": {**e.mac._state(True), "screenshot_b64": src}})
        else: orig(req)
    e.mac._answer = shot
    m = Model(plan({"action": "ask_user", "question": "which one?"}))
    await e.run(m, "open notes", vision=True)
    assert m.calls[0][-1].images_b64 == (src,) and "numbered boxes" not in m.prompt(0)


# ====================================================================== prompt budget
from jarvis_bridge.computer.budget import fit_controls, priority, text_allowance
from jarvis_bridge.inference.base import ChatChunk


def many_controls(n=300):
    roles = ["button", "row", "static text", "link", "text field", "image"]
    return [Element(i, roles[i % 6], f"{roles[i % 6]} number {i}", 0, i * 20, 120, 18, editable=(roles[i % 6] == "text field")) for i in range(n)]

def chars(es): return sum(len(e.line()) + 1 for e in es)


def test_everything_is_kept_when_it_fits():
    es = many_controls(10); kept, omitted = fit_controls(es, 9000)
    assert kept == es and omitted == 0

def test_a_big_screen_is_cut_to_the_budget_keeping_what_you_type_into_and_press_first():
    es = many_controls(300); budget = 3000
    kept, omitted = fit_controls(es, budget)
    assert chars(kept) <= budget and omitted == 300 - len(kept) > 0
    assert [e.i for e in kept] == sorted(e.i for e in kept)                              # reading order and the ORIGINAL numbers are preserved
    assert all(any(e.i == k.i for e in es) and e.label == k.label for k in kept for e in [es[k.i]])
    ranks = [priority(e) for e in kept]
    dropped = [e for e in es if e.i not in {k.i for k in kept}]
    assert all(priority(e) <= min(ranks) for e in dropped if e.label) or min(ranks) >= 1  # nothing more important was thrown away to keep something less so
    assert sum(1 for k in kept if k.role == "text field") >= sum(1 for k in kept if k.role == "image")

def test_repeated_controls_and_unlabelled_decoration_go_first():
    rows = [Element(i, "button", "Next", 0, i * 20, 80, 18) for i in range(40)] + [Element(40 + i, "group", "", 0, 900 + i, 80, 18) for i in range(40)] + [Element(80, "text field", "Search", 0, 5, 200, 20, editable=True)]
    tight = len(rows[0].line()) + len(rows[-1].line()) + 2                               # room for exactly one "Next" and the search field
    kept, _ = fit_controls(rows, tight)
    assert [k.label for k in kept] == ["Next", "Search"]                                 # 39 repeats and 40 unlabelled groups are what was dropped
    roomy, _ = fit_controls(rows, tight + 500)                                           # with room to spare the unlabelled ones come back last (a vision model may still use them)
    assert sum(1 for k in roomy if k.label == "Next") == 1 and any(not k.label for k in roomy)

def test_the_text_allowance_is_what_is_left_within_the_old_cap_and_a_floor():
    assert text_allowance(9000, 1000) == 3000 and text_allowance(4000, 3000) == 1000 and text_allowance(2000, 1900) == 600


async def test_a_busy_screen_gives_a_short_prompt_and_an_omitted_control_can_still_be_used_by_name(tmp_path):
    big = {"label": "x"}
    screens = {"s": {"app": "Finder", "title": "Big folder", "text": "page text " * 400,
                     "elements": [{"label": f"File {i:03d}.txt", "role": "row"} for i in range(250)] + [{"label": "Rename", "role": "button"}]}}
    e = Env(tmp_path, screens, "s", computer_prompt_chars=3000)
    m = Model(plan({"action": "click", "target": "File 249.txt"}), done("clicked it"))
    out = await e.run(m, "click the last file")
    p = m.prompt(0)
    assert out.status == "done" and "more controls are not listed" in p
    assert len(p) < 3000 + 3500                                                          # the screen part obeys the budget (the rest is the fixed instructions)
    assert "File 249.txt" not in p                                                       # it really was left out of the prompt ...
    assert any(r["kind"] == "resolve" and r["target"]["label"] == "File 249.txt" for r in e.mac.requests) and e.mac.acts[0]["kind"] == "click"   # ... and still found on the machine

async def test_a_small_screen_is_not_trimmed_at_all(tmp_path):
    screens = {"s": {"app": "Finder", "title": "t", "elements": [{"label": "A"}, {"label": "B"}]}}
    e = Env(tmp_path, screens, "s"); m = Model(done("ok"))
    await e.run(m, "look"); assert "more controls" not in m.prompt(0) and '"A"' in m.prompt(0) and '"B"' in m.prompt(0)

def test_the_budget_setting_is_validated():
    from jarvis_bridge.settings import BridgeSettings
    for bad in (100, 100000): 
        with pytest.raises(ValueError): BridgeSettings(computer_prompt_chars=bad).validate()
    assert BridgeSettings(computer_prompt_chars=5000).validate().computer_prompt_chars == 5000


# ====================================================================== timings
def counting_model(*replies, prompt_tokens=1234, completion_tokens=56, delay=0.0):
    m = Model(*replies); inner = m.__call__
    def call(model, msgs, **kw):
        g = inner(model, msgs, **kw)
        async def gen():
            await asyncio.sleep(delay)
            async for c in g:
                if c.done: c = ChatChunk(done=True, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
                yield c
        return gen()
    m.__call__ = call
    return call, m

async def test_every_run_reports_what_it_cost_in_time_and_tokens_and_nothing_about_the_screen(tmp_path):
    screens, moves = finder_world(); e = Env(tmp_path, screens, "notes", moves)
    call, m = counting_model(plan({"action": "open_app", "name": "Finder"}, {"action": "key", "keys": "cmd+f"}), done("ok"), delay=0.02)
    out = await e.run(call, "Open Finder")
    s = out.stats
    assert s["model_calls"] == 2 and s["actions"] == 2 and s["observes"] == 2
    assert s["model_ms_total"] >= 40 and s["model_ms_avg"] >= 20 and s["wall_ms"] >= s["model_ms_total"]
    assert 0 < s["first_action_ms"] <= s["wall_ms"]
    assert s["prompt_tokens_avg"] == 1234 and s["completion_tokens_avg"] == 56 and s["prompt_chars_max"] > 500
    assert e.runner.last_stats == s
    fin = [d for d in e.audit.query(tool_id="computer:run") if d["decision"] == "run_finished"][-1]["detail"]
    assert fin["model_calls"] == 2 and fin["steps"] == 2 and all(isinstance(v, (int, type(None))) for k, v in fin.items())   # numbers only: no screen text in the log

async def test_the_status_endpoint_shows_the_last_run(tmp_path):
    from test_computer import api
    svc, c = api(tmp_path)
    async with c:
        assert (await c.get("/v1/computer/status")).json()["last_run"] is None
        svc.computer.last_stats = {"model_calls": 3, "first_action_ms": 4100}
        assert (await c.get("/v1/computer/status")).json()["last_run"]["first_action_ms"] == 4100


# ====================================================================== context window
async def test_the_model_is_asked_for_an_explicit_context_window_and_told_when_it_is_nearly_full(tmp_path):
    from jarvis_bridge.computer.agent import stream_options
    screens, moves = finder_world(); e = Env(tmp_path, screens, "notes", moves, computer_num_ctx=4096)
    assert stream_options(e.settings.value)["num_ctx"] == 4096 and stream_options(e.settings.value)["think"] is False
    call, m = counting_model(plan({"action": "open_app", "name": "Finder"}), done("ok"), prompt_tokens=4000)      # 4000 of 4096: the start of the prompt is probably gone
    out = await e.run(call, "Open Finder")
    assert any("context window is full" in ev.get("notice", "") for ev in e.events) and out.stats["context_full_calls"] == 2
    assert sum(1 for ev in e.events if "context window is full" in ev.get("notice", "")) == 1                    # said once, not at every step
    e2 = Env(tmp_path / "b", screens, "notes", moves); call2, _ = counting_model(plan({"action": "open_app", "name": "Finder"}), done("ok"), prompt_tokens=1500)
    out2 = await e2.run(call2, "Open Finder")
    assert out2.stats["context_full_calls"] == 0 and not any("context window" in ev.get("notice", "") for ev in e2.events)

def test_the_context_setting_is_validated_and_reaches_the_api():
    from jarvis_bridge.settings import BridgeSettings
    for bad in (512, 10_000_000):
        with pytest.raises(ValueError): BridgeSettings(computer_num_ctx=bad).validate()
    assert BridgeSettings().validate().computer_num_ctx == 8192


# ====================================================================== the latency benchmark harness (plumbing only: no real model is involved)
from jarvis_bridge.computer import bench as bench_mod

def scripted_stream(*replies, delay=0.0):
    """A stand-in for the model stream: stream_for(cfg) -> stream(model, messages, **kw)."""
    def stream_for(cfg):
        m = Model(*replies)
        def call(model, msgs, **kw):
            g = m(model, msgs, **kw)
            async def gen():
                await asyncio.sleep(delay)
                async for c in g:
                    yield ChatChunk(done=True, prompt_tokens=900, completion_tokens=40) if c.done else c
            return gen()
        return call
    return stream_for

def test_the_simulated_screen_has_the_requested_size_and_a_layout_that_fits_the_window():
    broker = bench_mod.ComputerBroker()
    for n in (12, 30, 120, 400):
        els = bench_mod.SimMac(broker, n).elements()
        assert len(els) == min(n, 160) and [e["i"] for e in els] == list(range(len(els)))
        assert all(0 <= e["x"] and e["x"] + e["w"] <= 1000 and 0 <= e["y"] and e["y"] + e["h"] <= 700 for e in els)
        assert any(e["label"] == "Downloads" for e in els) and any(e["role"] == "text field" and e["editable"] for e in els)

async def test_a_benchmark_case_measures_a_run_that_reaches_the_goal():
    good = scripted_stream(plan({"action": "click", "target": "Downloads", "expect": {"title": "downloads"}}), done("Opened Downloads."), delay=0.01)
    row = await bench_mod.run_case(good, "m", controls=120, budget=3000, vision=False, marks=True, num_ctx=8192)
    assert row["reached_goal"] and row["status"] == "done" and row["model_calls"] == 2 and row["actions"] == 1
    assert row["prompt_tokens_avg"] == 900 and row["first_action_ms"] > 0 and row["controls_avg"] == 120

async def test_a_benchmark_case_reports_a_model_that_misses_the_target_as_not_passed():
    wrong = scripted_stream(plan({"action": "click", "target": "File 050.txt"}), done("Opened Downloads."))
    row = await bench_mod.run_case(wrong, "m", controls=60, budget=9000, vision=False, marks=True, num_ctx=8192)
    assert not row["reached_goal"]                                                         # it said "done", but the simulated machine never got there

async def test_the_whole_grid_runs_summarises_and_prints_a_table():
    good = scripted_stream(*([plan({"action": "click", "target": "Downloads"}), done("ok")] * 8))
    cases = await bench_mod.bench(good, "m", controls=[30, 120], budgets=[3000, 9000], vision=False, marks=True, runs=2, num_ctx=8192)
    assert [(c["controls"], c["budget"]) for c in cases] == [(30, 3000), (30, 9000), (120, 3000), (120, 9000)]
    assert all(c["runs"] == 2 for c in cases)
    txt = bench_mod.table(cases)
    assert "first action" in txt and "ms" in txt and len(txt.splitlines()) == 5

async def test_a_vision_case_sends_a_real_picture(tmp_path):
    seen = []
    def stream_for(cfg):
        def call(model, msgs, **kw):
            seen.append(len(msgs[-1].images_b64))
            r = plan({"action": "click", "target": "Downloads"}) if len(seen) == 1 else done("ok")
            async def gen(): yield ChatChunk(delta=r); yield ChatChunk(done=True)
            return gen()
        return call
    row = await bench_mod.run_case(stream_for, "m", controls=30, budget=9000, vision=True, marks=True, num_ctx=8192)
    assert seen[0] == 1 and row["images_sent"] >= 1 and row["reached_goal"]

def test_the_command_line_refuses_to_run_without_a_model():
    with pytest.raises(SystemExit): bench_mod.main([])


async def test_the_benchmark_command_line_works_end_to_end_against_an_ollama_over_http(capsys, tmp_path):
    """A stand-in Ollama that answers with real plans. Proves the CLI's health check, model preload, request options and table; says nothing about any real model."""
    from fastapi import FastAPI, Request
    from fastapi.responses import StreamingResponse
    from mockservers import serve
    app = FastAPI(); seen = {"chats": [], "loads": 0}

    @app.get("/api/version")
    def version(): return {"version": "0.99-mock"}

    @app.post("/api/generate")
    async def generate(req: Request):
        seen["loads"] += 1; return {"done": True}

    @app.post("/api/chat")
    async def chat(req: Request):
        b = await req.json(); seen["chats"].append(b)
        looked_at_result = "Downloads" in b["messages"][-1]["content"].split("What happened so far:")[1].split("Current screen")[0]
        reply = plan({"action": "click", "target": "Downloads"}) if not looked_at_result else done("Opened the Downloads folder.")
        async def gen():
            yield json.dumps({"message": {"content": reply}, "done": False}) + "\n"
            yield json.dumps({"message": {"content": ""}, "done": True, "prompt_eval_count": 800, "eval_count": 30}) + "\n"
        return StreamingResponse(gen(), media_type="application/x-ndjson")

    out_file = tmp_path / "bench.json"
    with serve(app) as port:
        rc = await asyncio.to_thread(bench_mod.main, ["--model", "stub:7b", "--endpoint", f"http://127.0.0.1:{port}", "--controls", "40", "--budgets", "3000", "--runs", "1", "--json", str(out_file)])
    assert rc == 0 and seen["loads"] == 1                                                  # the model was preloaded once, before any timing
    shown = capsys.readouterr().out
    assert "first action" in shown and "1/1" in shown and "Target: first action in 2-5 s" in shown
    body = seen["chats"][0]
    assert body["options"]["num_ctx"] == 8192 and body["keep_alive"] == "30m" and body["think"] is False and isinstance(body["format"], dict) and body["format"]["required"] == ["plan"]
    assert json.loads(out_file.read_text())[0]["passed"] == 1

def test_the_command_line_says_so_when_ollama_is_not_running(capsys):
    from mockservers import free_port
    assert bench_mod.main(["--model", "x", "--endpoint", f"http://127.0.0.1:{free_port()}", "--runs", "1"]) == 2
    assert "Cannot reach Ollama" in capsys.readouterr().err


# ====================================================================== which display
async def test_every_desktop_request_names_the_chosen_screen_and_browser_requests_do_not(tmp_path):
    screens, moves = finder_world(); e = Env(tmp_path, screens, "notes", moves, computer_display="2")
    m = Model(plan({"action": "open_app", "name": "Finder"}), done("ok"))
    await e.run(m, "Open Finder")
    reqs = [r for r in e.mac.requests if r["kind"] != "end"]
    assert reqs and all(r["display"] == "2" for r in reqs) and {r["kind"] for r in reqs} >= {"observe", "act"}
    b = Env(tmp_path / "b", browser_world(), "shop", computer_display="cursor")
    await b.run(Model(done("ok")), "look", mode="browser")
    assert all("display" not in r for r in b.mac.requests)

def test_the_display_setting_accepts_only_main_cursor_or_a_digit():
    from jarvis_bridge.settings import BridgeSettings
    for ok in ("main", "cursor", "1", "9"): assert BridgeSettings(computer_display=ok).validate().computer_display == ok
    for bad in ("0", "10", "left", "", "main; rm"):
        with pytest.raises(ValueError): BridgeSettings(computer_display=bad).validate()
