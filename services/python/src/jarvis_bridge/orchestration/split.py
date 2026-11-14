"""Splitting long files across several workers, and spreading the work over the models the user switched on.

The boss does not need to guess: the length of every file is measured, and a long one is cut into balanced parts at page boundaries
(PDF text carries `--- Page N ---` markers) or paragraph boundaries, so several small models can read it at the same time.
Pure functions only. `crew.py` calls them for both the live preview and the real run, so what the preview promises is what runs.
"""
from __future__ import annotations
import math, re
from dataclasses import dataclass, field
from .resources import ModelRow

_PAGE = re.compile(r"^--- Page (\d+) ---[ \t]*$", re.M)
MIN_PART_CHARS = 4000          # never cut a file into pieces smaller than this: the overhead would cost more than it saves
IMAGES_PER_PART = 6            # scanned pages are heavy for a vision model
PAGE_EST_CHARS = 2500          # for a size hint without text


@dataclass
class Sized:
    """One file, as far as splitting is concerned."""
    name: str
    chars: int = 0
    images: int = 0
    pages: int = 0


def _ceil_div(a: int, b: int) -> int: return -(-a // max(b, 1))


def parts_wanted(item: Sized, *, n_models: int, target_chars: int, max_parts: int) -> int:
    """How many pieces a file should become."""
    if item.images and not item.chars:                                   # a scanned PDF: only page pictures
        units = item.images
        k = _ceil_div(units, IMAGES_PER_PART)
        if n_models > 1 and units >= n_models * 2: k = max(k, n_models)
        return max(1, min(k, max_parts, units))
    k = _ceil_div(item.chars, max(target_chars, MIN_PART_CHARS))
    if n_models > 1: k = max(k, min(n_models, item.chars // MIN_PART_CHARS))   # as many parts as the selected models can each get a real share of
    return max(1, min(k, max_parts, max(1, item.chars // MIN_PART_CHARS)))


def balanced_groups(sizes: list, k: int) -> list:
    """Cut a list of unit sizes into `k` contiguous groups of nearly equal total size. -> [(start, end_exclusive), ...]."""
    n = len(sizes)
    k = max(1, min(k, n))
    if k == 1: return [(0, n)]
    total, out, start, acc = sum(sizes) or n, [], 0, 0
    for i, s in enumerate(sizes):
        acc += s or 1
        left_units, left_groups = n - (i + 1), k - len(out) - 1
        if len(out) < k - 1 and (acc >= total * (len(out) + 1) / k or left_units == left_groups):
            out.append((start, i + 1)); start = i + 1
    out.append((start, n))
    return out


def _units(text: str, target_chars: int):
    """The natural pieces of a text: pages when the text has page markers, otherwise paragraphs. -> (units, page numbers or None)."""
    marks = list(_PAGE.finditer(text))
    if len(marks) >= 2:
        units, nums = [], []
        if marks[0].start() > 0 and text[:marks[0].start()].strip(): units.append(text[:marks[0].start()]); nums.append(None)
        for i, m in enumerate(marks):
            units.append(text[m.start(): marks[i + 1].start() if i + 1 < len(marks) else len(text)]); nums.append(int(m.group(1)))
        return units, nums
    from .crew import chunk_text
    return chunk_text(text, max(1000, target_chars // 4)), None


def split_text_input(inp, k: int, target_chars: int) -> list:
    """Cut one CrewInput into `k` parts (a list of new CrewInputs); returns [inp] when it should stay whole."""
    from .crew import CrewInput
    if k <= 1: return [inp]
    parts = []
    if inp.text:
        units, nums = _units(inp.text, target_chars)
        groups = balanced_groups([len(u) for u in units], k)
        for i, (a, b) in enumerate(groups, 1):
            body = "\n\n".join(u.strip("\n") for u in units[a:b])
            got = [n for n in (nums[a:b] if nums else []) if n is not None]
            label = (f"pages {got[0]}-{got[-1]}" if len(got) > 1 and got[0] != got[-1] else f"page {got[0]}") if got else f"part {i} of {len(groups)}"
            parts.append(CrewInput(f"{inp.name} ({label})", inp.kind, body, [], inp.worker_model,
                                   f"Part {i} of {len(groups)} of {inp.name} ({label}). Other workers read the other parts at the same time.",
                                   parent=inp.name, part_index=i, part_total=len(groups), label=label))
        return parts if len(parts) > 1 else [inp]
    if inp.images_b64:                                                      # scanned: split the page pictures
        groups = balanced_groups([1] * len(inp.images_b64), k)
        for i, (a, b) in enumerate(groups, 1):
            label = f"pages {a + 1}-{b}" if b - a > 1 else f"page {a + 1}"
            parts.append(CrewInput(f"{inp.name} ({label})", inp.kind, "", inp.images_b64[a:b], inp.worker_model,
                                   f"Part {i} of {len(groups)} of {inp.name} ({label}). Other workers read the other parts at the same time.",
                                   parent=inp.name, part_index=i, part_total=len(groups), label=label))
        return parts if len(parts) > 1 else [inp]
    return [inp]


def split_hint_input(inp, k: int) -> list:
    """For the preview, where only sizes are known (no text): parts that carry a size hint, not content."""
    from .crew import CrewInput
    if k <= 1: return [inp]
    total_chars = inp.hint_chars or (inp.hint_pages * PAGE_EST_CHARS)
    total_pages = inp.hint_pages or 0
    parts = []
    for i, (a, b) in enumerate(balanced_groups([1] * (total_pages or k), k), 1):
        label = (f"pages {a + 1}-{b}" if b - a > 1 else f"page {a + 1}") if total_pages else f"part {i} of {k}"
        parts.append(CrewInput(f"{inp.name} ({label})", inp.kind, "", [], inp.worker_model, None, parent=inp.name, part_index=i, part_total=k, label=label,
                               hint_chars=total_chars // k, hint_pages=b - a if total_pages else 0, hint_images=(b - a) if inp.hint_images else 0))
    return parts


def size_of(inp) -> Sized:
    return Sized(inp.name, len(inp.text) or inp.hint_chars or (inp.hint_pages * PAGE_EST_CHARS if inp.hint_pages and not inp.hint_images else 0),
                 len(inp.images_b64) if inp.images_b64 and inp.images_b64 != ["-"] else (inp.hint_pages if inp.hint_images else 0), inp.hint_pages)


def split_inputs(inputs: list, *, n_models: int, target_chars: int, max_total: int, max_parts_per_file: int = 8) -> tuple:
    """-> (inputs with long files replaced by their parts, report). `max_total` caps the number of workers overall."""
    sizes = [size_of(i) for i in inputs]
    ks = [parts_wanted(s, n_models=n_models, target_chars=target_chars, max_parts=max_parts_per_file) for s in sizes]
    while sum(ks) > max(max_total, len(inputs)):                            # too many workers in total: trim the file with the most parts
        j = max(range(len(ks)), key=lambda x: ks[x])
        if ks[j] <= 1: break
        ks[j] -= 1
    out, report = [], []
    for inp, s, k in zip(inputs, sizes, ks):
        if k <= 1: out.append(inp); continue
        has_text = bool(inp.text)
        parts = split_text_input(inp, k, target_chars) if (has_text or inp.images_b64 and inp.images_b64 != ["-"]) else split_hint_input(inp, k)
        out.extend(parts)
        if len(parts) > 1:
            report.append({"name": inp.name, "pages": s.pages or None, "chars": s.chars, "parts": [p.label for p in parts]})
    return out, report


# ------------------------------------------------------------------ which model reads which part
@dataclass
class Job:
    name: str
    weight: int = 1                  # characters (or images x 3000): how much there is to read
    vision: bool = False
    large: bool = False


def _cost(m: ModelRow) -> float:
    """Relative time per character: bigger models are slower."""
    return max(0.5, m.params_b if m.params_b is not None else ((m.size_bytes or 4 * 1024 ** 3) / (0.6 * 1024 ** 3)))


def distribute(jobs: list, pool: list) -> tuple:
    """Spread jobs over the models the user switched on. Every model gets real work first (biggest jobs go to distinct models), then each
    remaining job goes where it would finish soonest, so small fast models read more and big slow ones read less.
    -> ({job name: ModelRow | None}, unused models). None means no model in the pool can do that job (e.g. a scanned page and no vision model)."""
    load = {m.ref: 0.0 for m in pool}
    used: dict = {}
    assign: dict = {}
    for job in sorted(jobs, key=lambda j: -j.weight):
        able = [m for m in pool if (not job.vision or m.vision is True)]
        if not able: assign[job.name] = None; continue
        if job.large: able = [max(able, key=_cost)]
        fresh = [m for m in able if m.ref not in used]
        if fresh: pick = min(fresh, key=_cost)                              # first, every switched-on model gets real work
        else: pick = min(able, key=lambda m: (load[m.ref] + job.weight) * _cost(m))      # then: wherever it would finish soonest
        used[pick.ref] = used.get(pick.ref, 0) + 1
        load[pick.ref] += job.weight
        assign[job.name] = pick
    return assign, [m for m in pool if m.ref not in used]
