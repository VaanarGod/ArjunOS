"""What a computer task cost in time: how long the model, the screen reads and the actions took. Collected on every run (it is only numbers and counts,
never screen content) so that latency on a real model can be read from the audit log, the status endpoint or the benchmark script instead of guessed."""
from __future__ import annotations
import time
from dataclasses import dataclass, field


def _avg(xs: list) -> int: return int(sum(xs) / len(xs)) if xs else 0


@dataclass
class RunStats:
    t0: float = field(default_factory=time.monotonic)
    first_act_ms: int | None = None
    observes: list = field(default_factory=list)      # (ms, controls, screenshot_kb)
    models: list = field(default_factory=list)        # dicts: ms, prompt_chars, prompt_tokens, completion_tokens, images
    acts: list = field(default_factory=list)          # ms

    def now_ms(self) -> int: return int((time.monotonic() - self.t0) * 1000)

    def observe(self, ms: float, controls: int, screenshot_b64_len: int):
        self.observes.append((int(ms), controls, screenshot_b64_len * 3 // 4096))

    def model(self, ms: float, prompt_chars: int, images: int, prompt_tokens: int | None, completion_tokens: int | None, ctx_full: bool = False):
        self.models.append({"ms": int(ms), "prompt_chars": prompt_chars, "images": images, "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens, "ctx_full": ctx_full})

    def act(self, ms: float):
        if self.first_act_ms is None: self.first_act_ms = self.now_ms()
        self.acts.append(int(ms))

    def summary(self) -> dict:
        m = [x["ms"] for x in self.models]; pc = [x["prompt_chars"] for x in self.models]
        pt = [x["prompt_tokens"] for x in self.models if x["prompt_tokens"]]
        ct = [x["completion_tokens"] for x in self.models if x["completion_tokens"]]
        return {"wall_ms": self.now_ms(), "first_action_ms": self.first_act_ms, "model_calls": len(m), "model_ms_total": sum(m), "model_ms_avg": _avg(m), "model_ms_max": max(m, default=0),
                "prompt_chars_avg": _avg(pc), "prompt_chars_max": max(pc, default=0), "prompt_tokens_avg": _avg(pt) or None, "completion_tokens_avg": _avg(ct) or None,
                "images_sent": sum(x["images"] for x in self.models), "context_full_calls": sum(1 for x in self.models if x.get("ctx_full")), "observes": len(self.observes), "observe_ms_avg": _avg([o[0] for o in self.observes]),
                "controls_avg": _avg([o[1] for o in self.observes]), "screenshot_kb_avg": _avg([o[2] for o in self.observes]), "actions": len(self.acts), "act_ms_avg": _avg(self.acts)}
