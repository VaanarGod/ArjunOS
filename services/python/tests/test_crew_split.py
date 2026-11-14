"""Long files are measured and cut into balanced parts; the parts are spread over the models the user switched on; every part gets its own worker."""
import json, re
import pytest
from test_crew import BOSS, MINI, VIS, SIZES, Machine, Team, rows, engine, run_crew, of, GB
from test_api import Env
from test_crew_api import env_with_team, body
from jarvis_bridge.orchestration.crew import CrewConfig, CrewInput, CrewEngine
from jarvis_bridge.orchestration.resources import ModelRow
from jarvis_bridge.orchestration.split import (Job, Sized, balanced_groups, distribute, parts_wanted, split_inputs, split_text_input)

TINY, MID = "ol|small:1.5b", "ol|mid:7b"
SIZES.update({TINY: 1 * GB, MID: 5 * GB})


def many_rows():
    r = rows(); r[TINY] = ModelRow(TINY, "small:1.5b", SIZES[TINY], 1.5, False); r[MID] = ModelRow(MID, "mid:7b", SIZES[MID], 7, False); return r

def long_pdf(pages=40, per_page=1500, name="report.pdf"):
    return CrewInput(name, "pdf", "\n\n".join(f"--- Page {i} ---\n" + (f"P{i} " * (per_page // 4)) for i in range(1, pages + 1)))


# ================================================================ cutting
def test_balanced_groups_are_contiguous_cover_everything_and_are_near_equal():
    sizes = [5, 1, 9, 2, 2, 7, 3, 3, 8, 4]
    for k in (1, 2, 3, 4, 7, 10, 25):
        g = balanced_groups(sizes, k)
        assert g[0][0] == 0 and g[-1][1] == len(sizes) and all(a < b for a, b in g) and all(g[i][1] == g[i + 1][0] for i in range(len(g) - 1))
        assert len(g) == min(k, len(sizes))
    g = balanced_groups([10] * 12, 3); assert [sum([10] * (b - a)) for a, b in g] == [40, 40, 40]

def test_how_many_parts_a_file_needs():
    kw = dict(target_chars=24000, max_parts=8)
    assert parts_wanted(Sized("a", chars=3000), n_models=4, **kw) == 1                  # tiny: never cut, even with 4 models
    assert parts_wanted(Sized("a", chars=20000), n_models=1, **kw) == 1                 # fits one worker
    assert parts_wanted(Sized("a", chars=60000), n_models=1, **kw) == 3                 # by length
    assert parts_wanted(Sized("a", chars=20000), n_models=4, **kw) == 4                 # long enough that every selected model gets a real share
    assert parts_wanted(Sized("a", chars=9000), n_models=4, **kw) == 2                  # only as many parts as stay above the minimum size
    assert parts_wanted(Sized("a", chars=900000), n_models=2, **kw) == 8                # capped
    assert parts_wanted(Sized("s", images=7), n_models=1, **kw) == 2 and parts_wanted(Sized("s", images=4), n_models=1, **kw) == 1
    assert parts_wanted(Sized("s", images=12), n_models=3, **kw) == 3

def test_a_pdf_is_cut_at_page_boundaries_and_nothing_is_lost_or_repeated():
    pdf = long_pdf(30)
    parts = split_text_input(pdf, 4, 24000)
    assert len(parts) == 4 and all(p.parent == "report.pdf" and p.part_total == 4 for p in parts)
    assert [p.part_index for p in parts] == [1, 2, 3, 4] and re.fullmatch(r"report\.pdf \(pages \d+-\d+\)", parts[0].name)
    seen = [int(n) for p in parts for n in re.findall(r"^--- Page (\d+) ---", p.text, re.M)]
    assert seen == list(range(1, 31))                                                   # every page exactly once, in order
    sizes = [len(p.text) for p in parts]; assert max(sizes) < 1.4 * min(sizes)           # balanced
    assert parts[0].label == "pages 1-%d" % int(re.findall(r"^--- Page (\d+)", parts[0].text, re.M)[-1])

def test_plain_text_is_cut_at_paragraphs_without_losing_text():
    text = "\n\n".join(f"Paragraph {i}. " + "word " * 120 for i in range(40))
    parts = split_text_input(CrewInput("notes.txt", "text", text), 3, 12000)
    assert len(parts) == 3 and all(p.label.startswith("part ") for p in parts)
    assert [re.sub(r"\s+", " ", " ".join(p.text for p in parts)).strip()] == [re.sub(r"\s+", " ", text).strip()]

def test_scanned_pages_are_split_into_page_ranges_for_vision_workers():
    parts = split_text_input(CrewInput("scan.pdf", "pdf", "", [f"img{i}" for i in range(13)]), 3, 24000)
    assert [p.label for p in parts] == ["pages 1-5", "pages 6-9", "pages 10-13"] or sum(len(p.images_b64) for p in parts) == 13
    assert [i for p in parts for i in p.images_b64] == [f"img{i}" for i in range(13)] and all(not p.text for p in parts)

def test_the_total_number_of_workers_is_capped():
    ins = [long_pdf(60, name=f"f{i}.pdf") for i in range(4)]
    out, report = split_inputs(ins, n_models=4, target_chars=24000, max_total=12)
    assert len(out) <= 12 and len(report) == 4 and all(len(r["parts"]) >= 2 for r in report)


# ================================================================ spreading over the chosen models
def pool(*refs): return [many_rows()[r] for r in refs]

def test_every_switched_on_model_gets_real_work_before_any_model_gets_a_second_job():
    jobs = [Job(f"p{i}", 10000) for i in range(3)]
    got, unused = distribute(jobs, pool(MINI, TINY, MID))
    assert {m.ref for m in got.values()} == {MINI, TINY, MID} and unused == []

def test_small_fast_models_read_more_and_big_slow_ones_read_less():
    jobs = [Job(f"p{i}", 10000) for i in range(8)]
    got, _ = distribute(jobs, pool(TINY, MID))
    counts = {r: sum(1 for m in got.values() if m.ref == r) for r in (TINY, MID)}
    assert counts[TINY] > counts[MID] >= 1

def test_vision_jobs_only_go_to_vision_models_and_a_pool_without_one_says_so():
    got, _ = distribute([Job("scan", 9000, vision=True), Job("txt", 9000)], pool(MINI, VIS))
    assert got["scan"].ref == VIS
    got, _ = distribute([Job("scan", 9000, vision=True)], pool(MINI, TINY))
    assert got["scan"] is None

def test_models_with_nothing_to_read_are_reported_as_unused():
    got, unused = distribute([Job("only", 5000)], pool(MINI, TINY, MID))
    assert len(got) == 1 and len(unused) == 2

def test_large_jobs_go_to_the_biggest_model_in_the_pool():
    got, _ = distribute([Job("hard", 5000, large=True)], pool(MINI, TINY, MID))
    assert got["hard"].ref == MID


# ================================================================ the engine's layout (preview and run share it)
def test_layout_spreads_a_long_pdf_over_all_selected_models():
    m = Machine(64, 60); eng = engine(m, Team(m), many_rows())
    lay = eng.layout(CrewConfig(BOSS, worker_models=[MINI, TINY, MID]), [long_pdf(60)])
    assert len(lay.inputs) >= 3 and {r.ref for r in lay.rows} == {MINI, TINY, MID} and lay.unused == []
    assert lay.report[0]["name"] == "report.pdf" and len(lay.report[0]["parts"]) == len(lay.inputs)

def test_layout_for_the_preview_works_from_size_hints_without_any_text():
    m = Machine(64, 60); eng = engine(m, Team(m), many_rows())
    hint = CrewInput("big.pdf", "pdf", "", hint_chars=150000, hint_pages=84)
    lay = eng.layout(CrewConfig(BOSS, worker_models=[MINI, MID]), [hint])
    assert len(lay.inputs) >= 2 and all(p.text == "" for p in lay.inputs) and {r.ref for r in lay.rows} == {MINI, MID}
    assert lay.inputs[0].label.startswith("pages 1-") and lay.inputs[-1].label.endswith("-84")

def test_a_model_forced_for_one_file_is_respected_and_automatic_still_works():
    m = Machine(64, 60); eng = engine(m, Team(m), many_rows())
    forced = CrewInput("a.pdf", "pdf", "x " * 3000, worker_model=MID)
    lay = eng.layout(CrewConfig(BOSS), [forced, CrewInput("b.pdf", "pdf", "y " * 3000)])
    assert lay.assign["a.pdf"].ref == MID and lay.assign["b.pdf"].ref in (MINI, TINY)

def test_the_old_single_worker_model_setting_still_means_a_pool_of_one():
    m = Machine(64, 60); eng = engine(m, Team(m), many_rows())
    lay = eng.layout(CrewConfig(BOSS, worker_model=MID), [long_pdf(60)])
    assert {r.ref for r in lay.rows} == {MID}

async def test_memory_planning_counts_every_distinct_model_that_will_run():
    m = Machine(16, 14); eng = engine(m, Team(m), many_rows())
    one, _ = await eng.make_plan(CrewConfig(BOSS, worker_models=[MINI]), [long_pdf(60)])
    three, rows3 = await eng.make_plan(CrewConfig(BOSS, worker_models=[MINI, TINY, MID]), [long_pdf(60)])
    assert len(rows3) == 3 and three.max_workers >= 1 and (three.mode.value != "parallel" or one.mode.value == "parallel")


# ================================================================ a real run
async def test_a_long_pdf_is_split_and_read_by_all_three_models_in_parallel_then_combined():
    m = Machine(64, 60)
    t = Team(m, {"subtasks": [{"title": "Everything", "instructions": "Summarise the whole report.", "inputs": ["report.pdf"]}]},     # a boss that ignores the split
             workers={}, final="Combined across all parts.")
    ev = await run_crew(engine(m, t, many_rows()), "Summarise this report", [long_pdf(60)], CrewConfig(BOSS, worker_models=[MINI, TINY, MID], review=False), timeout=30)
    notices = [e["notice"] for e in ev if "notice" in e]
    assert any("report.pdf is long" in n and "pages" in n and "split into" in n for n in notices)
    subs = of(ev, "plan")[0]["subtasks"]
    assert len(subs) >= 3 and all(len(s["inputs"]) == 1 for s in subs)                  # one worker per part, whatever the boss wrote
    assert {s["model"] for s in subs} == {MINI, TINY, MID}                               # all three selected models were deployed
    texts = [c[2][1].attachments[0]["text"] for c in t.worker_calls if c[2][1].attachments]
    pages = [int(n) for tx in texts for n in re.findall(r"^--- Page (\d+) ---", tx, re.M)]
    assert sorted(set(pages)) == list(range(1, 61))                                      # every page was read by someone
    assert any(re.search(r"You read ONLY pages \d+-\d+ of report\.pdf", s["instructions"]) for s in subs)
    assert of(ev, "final")[0]["text"].startswith("Combined across all parts.")

async def test_extra_models_with_nothing_to_read_are_announced_not_silently_ignored():
    m = Machine(64, 60)
    t = Team(m, None)
    ev = await run_crew(engine(m, t, many_rows()), "Read it", [CrewInput("tiny.txt", "text", "short note " * 20)], CrewConfig(BOSS, worker_models=[MINI, TINY, MID], review=False))
    assert sum("nothing to read" in e.get("notice", "") for e in ev) == 2

async def test_a_short_file_is_not_cut_and_older_behaviour_is_unchanged():
    m = Machine(32, 28); t = Team(m, None)
    ev = await run_crew(engine(m, t), "x", [CrewInput("a.pdf", "pdf", "fact " * 400)], CrewConfig(BOSS, review=False))
    assert not any("is long" in e.get("notice", "") for e in ev) and len(of(ev, "plan")[0]["subtasks"]) == 1


# ================================================================ API
async def test_preview_reports_the_split_and_which_model_reads_what(tmp_path):
    e, m, _ = env_with_team(tmp_path, Machine(64, 60))
    e.svc.crew_engine = (lambda: _async(CrewEngine(llm=Team(m).llm, agent_chat=Team(m).agent_chat, models=many_rows(), runtime=m, sysmem=m.sysmem)))
    b = body(worker_models=[MINI, TINY, MID], inputs=[{"name": "big.pdf", "kind": "pdf", "text": "", "chars": 180000, "pages": 90}])
    async with e.client() as c:
        j = (await c.post("/v1/crew/preview", json=b)).json()
    parts = j["layout"]["parts"]
    assert len(parts) >= 3 and {p["model"] for p in parts} == {MINI, TINY, MID} and parts[0]["label"].startswith("pages 1-")
    assert j["layout"]["split"][0]["name"] == "big.pdf" and j["layout"]["unused"] == [] and {w["ref"] for w in j["workers"]} == {MINI, TINY, MID}

async def _async(x): return x

async def test_unknown_or_too_many_pool_models_are_rejected(tmp_path):
    e, _, _ = env_with_team(tmp_path)
    async with e.client() as c:
        assert (await c.post("/v1/crew/preview", json=body(worker_models=[MINI, "ol|nope:1b"]))).status_code == 422
        assert (await c.post("/v1/crew/preview", json=body(worker_models=[f"ol|m{i}" for i in range(9)]))).status_code == 422


# ================================================================ escalation inside the pool
async def test_a_failed_part_retries_on_a_stronger_model_from_the_switched_on_pool_not_from_outside_it():
    m = Machine(64, 60)
    boom = lambda msgs: {"error": {"kind": "http", "message": "model crashed"}}
    t = Team(m, None, workers={"w1": [boom, "Recovered report. " * 20]}, fix="Read it carefully.")
    cfg = CrewConfig(BOSS, worker_models=[TINY, MID], review=False)                      # MINI is installed but NOT switched on
    ev = await run_crew(engine(m, t, many_rows()), "Read it", [CrewInput("note.txt", "text", "short note " * 20)], cfg)
    refs = [c[1] for c in t.worker_calls if c[0] == "w1"]
    assert refs[0] == TINY and refs[1] == MID and MINI not in refs                      # first the smallest pool model, then the next one up, never an unselected model
    assert any(a.get("detail") == "trying a stronger model" and a["model"] == MID for a in of(ev, "agent_state"))
    assert of(ev, "result")[0]["summary"].startswith("Recovered")


async def test_each_failure_moves_the_part_one_model_further_up_the_switched_on_pool_and_the_user_is_asked_before_the_last_try():
    m = Machine(64, 60)
    boom = lambda msgs: {"error": {"kind": "http", "message": "model crashed"}}
    t = Team(m, None, workers={"w1": [boom, boom, "Recovered report. " * 20]}, fix="Read it carefully.")
    cfg = CrewConfig(BOSS, worker_models=[TINY, MINI, MID], review=False)
    asked = []
    ev = await run_crew(engine(m, t, many_rows()), "Read it", [CrewInput("note.txt", "text", "short note " * 20)], cfg, user=lambda n: (asked.append(n), "focus on the numbers")[1])
    refs = [c[1] for c in t.worker_calls if c[0] == "w1"]
    assert len(refs) == 3 and len(set(refs)) == 3 and refs[0] == TINY and set(refs) <= {TINY, MINI, MID}      # three different pool models, never one from outside it
    order = sorted(refs, key=lambda r: SIZES[r]); assert refs == order                                       # each one stronger than the one before
    assert [a["model"] for a in of(ev, "agent_state") if a.get("detail") == "trying a stronger model"] == refs[1:]
    assert len(asked) == 1 and "focus on the numbers" in t.worker_calls[2][2][1].content                      # the person was asked once, between the second failure and the last try
    assert of(ev, "result")[0]["summary"].startswith("Recovered")

async def test_a_part_already_on_the_strongest_pool_model_stays_there_when_it_fails_again():
    m = Machine(64, 60)
    boom = lambda msgs: {"error": {"kind": "http", "message": "model crashed"}}
    t = Team(m, None, workers={"w1": [boom, boom, "Recovered report. " * 20]}, fix="Read it carefully.")
    cfg = CrewConfig(BOSS, worker_models=[TINY, MID], review=False)
    ev = await run_crew(engine(m, t, many_rows()), "Read it", [CrewInput("note.txt", "text", "short note " * 20)], cfg, user=lambda n: "again")
    refs = [c[1] for c in t.worker_calls if c[0] == "w1"]
    assert refs[0] == TINY and refs[1] == MID and refs[2] == MID and of(ev, "result")[0]["summary"].startswith("Recovered")
