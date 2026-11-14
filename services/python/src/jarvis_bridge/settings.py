"""User settings owned by the bridge (JSON file, atomic writes, validated). Defaults are privacy-conservative."""
from __future__ import annotations
import json, os, tempfile
from dataclasses import dataclass, asdict, fields
from pathlib import Path

WEB_MODES = ("off", "keyword", "auto")


@dataclass
class BridgeSettings:
    web_search_mode: str = "auto"           # off | keyword (explicit 'search ...' only) | auto (also time-sensitive questions)
    web_search_consented: bool = False      # one-time consent: search QUERIES (not chats) go to DuckDuckGo
    web_search_max_results: int = 5
    memory_auto_inject: bool = True         # surface relevant saved memories to the model
    attachment_context_chars: int = 12000   # max characters of attached-file text given to the model per answer
    browser_enabled: bool = True            # the built-in browser's page can be given to the assistant as context
    page_context_chars: int = 16000         # max characters of the open page given to the model per answer
    read_paths: bool = True                 # files and folders the user names by path in a message are read and given to the model (any file type)
    files_enabled: bool = True              # "create a markdown file": write files into the workspace without a prompt (no overwrite, safe types)
    shell_enabled: bool = True              # master switch for the sandboxed terminal (each command still needs approval)
    obsidian_enabled: bool = False          # use an Obsidian vault as a knowledge base and as storage for memories
    obsidian_vault_path: str = ""           # full path of the vault folder
    obsidian_auto_context: bool = True      # automatically give the model the notes that match what you ask
    obsidian_store_memories: bool = True    # keep memories as notes in the vault (two-way: edit or delete them in Obsidian)
    obsidian_allow_write: bool = True       # the model may create NEW notes in its own folder (it never edits your notes)
    obsidian_context_chars: int = 6000      # most note text given to the model per answer
    obsidian_agent_folder: str = "ArjunOS"  # the only folder the assistant writes to
    computer_consented: bool = False        # one-time permission: a local model may operate the built-in browser / (if switched on) the Mac desktop
    computer_browser_enabled: bool = True   # may drive the built-in browser (only after consent)
    computer_desktop_enabled: bool = False  # may click and type anywhere on the Mac (off by default; needs macOS permissions)
    computer_auto_start: bool = True        # a clear request such as "open Finder and find my Xcode projects" starts a task (after you approve it)
    computer_approval: str = "risky"        # risky = ask before consequential steps | every = ask before every step
    computer_max_steps: int = 40            # most actions in one task
    computer_browser_profile: str = "private"   # private = a throwaway browser with none of your logins | mine = your normal browser data
    computer_screenshot_dim: int = 1280     # longest side of a screenshot given to a vision model
    computer_marks: bool = True             # draw numbered boxes on the screenshot that match the [n] control list (helps small vision models)
    computer_num_ctx: int = 8192            # context window asked of the local model for computer tasks (too small and the model silently drops the START of the prompt, where the instructions are)
    computer_prompt_chars: int = 9000       # most characters of control list + page text given to the model per look (smaller = faster on a local model)
    computer_desktop_backend: str = "builtin"   # builtin = the app's own Accessibility/CGEvent driver | cua = the optional Cua Driver (background input)
    computer_cua_command: str = "cua-driver"    # the Cua Driver executable (a name on PATH or a full path); only used when the backend is cua
    computer_display: str = "main"          # which screen the agent looks at and clicks on: main | cursor (the one the pointer is on) | 1-9

    def validate(self) -> "BridgeSettings":
        if self.web_search_mode not in WEB_MODES:
            raise ValueError(f"web_search_mode must be one of {WEB_MODES}")
        if not (1 <= int(self.web_search_max_results) <= 10):
            raise ValueError("web_search_max_results must be between 1 and 10")
        if not (2000 <= int(self.attachment_context_chars) <= 100_000):
            raise ValueError("attachment_context_chars must be between 2000 and 100000")
        self.attachment_context_chars = int(self.attachment_context_chars)
        if not (2000 <= int(self.page_context_chars) <= 100_000):
            raise ValueError("page_context_chars must be between 2000 and 100000")
        self.page_context_chars = int(self.page_context_chars)
        self.web_search_max_results = int(self.web_search_max_results)
        self.web_search_consented = bool(self.web_search_consented)
        self.memory_auto_inject = bool(self.memory_auto_inject)
        self.shell_enabled = bool(self.shell_enabled)
        self.files_enabled = bool(self.files_enabled)
        self.read_paths = bool(self.read_paths)
        self.browser_enabled = bool(self.browser_enabled)
        self.obsidian_enabled = bool(self.obsidian_enabled)
        self.obsidian_auto_context = bool(self.obsidian_auto_context)
        self.obsidian_store_memories = bool(self.obsidian_store_memories)
        self.obsidian_allow_write = bool(self.obsidian_allow_write)
        if not (1500 <= int(self.obsidian_context_chars) <= 40_000):
            raise ValueError("obsidian_context_chars must be between 1500 and 40000")
        self.obsidian_context_chars = int(self.obsidian_context_chars)
        p = str(self.obsidian_vault_path or "").strip()
        if len(p) > 1000 or "\x00" in p: raise ValueError("obsidian_vault_path is not a valid path")
        self.obsidian_vault_path = p
        f = str(self.obsidian_agent_folder or "").strip()
        if not f or len(f) > 40 or f.startswith(".") or any(c in f for c in '/\\:*?"<>|\x00') or f in ("..", "."):
            raise ValueError("obsidian_agent_folder must be a simple folder name")
        self.obsidian_agent_folder = f
        self.computer_consented = bool(self.computer_consented); self.computer_browser_enabled = bool(self.computer_browser_enabled)
        self.computer_desktop_enabled = bool(self.computer_desktop_enabled); self.computer_auto_start = bool(self.computer_auto_start)
        if self.computer_approval not in ("risky", "every"): raise ValueError("computer_approval must be 'risky' or 'every'")
        if self.computer_browser_profile not in ("private", "mine"): raise ValueError("computer_browser_profile must be 'private' or 'mine'")
        if not (5 <= int(self.computer_max_steps) <= 120): raise ValueError("computer_max_steps must be between 5 and 120")
        if not (640 <= int(self.computer_screenshot_dim) <= 2048): raise ValueError("computer_screenshot_dim must be between 640 and 2048")
        self.computer_max_steps = int(self.computer_max_steps); self.computer_screenshot_dim = int(self.computer_screenshot_dim)
        self.computer_marks = bool(self.computer_marks)
        if not (2048 <= int(self.computer_num_ctx) <= 65_536): raise ValueError("computer_num_ctx must be between 2048 and 65536")
        self.computer_num_ctx = int(self.computer_num_ctx)
        if not (2000 <= int(self.computer_prompt_chars) <= 40_000): raise ValueError("computer_prompt_chars must be between 2000 and 40000")
        self.computer_prompt_chars = int(self.computer_prompt_chars)
        if self.computer_desktop_backend not in ("builtin", "cua"): raise ValueError("computer_desktop_backend must be 'builtin' or 'cua'")
        c = str(self.computer_cua_command or "").strip()
        if not c or len(c) > 500 or any(ch in c for ch in "\x00\n\r;|&$`<>") : raise ValueError("computer_cua_command must be the name or path of an executable")
        self.computer_cua_command = c
        d = str(self.computer_display or "").strip().lower()
        if d not in ("main", "cursor") and not (len(d) == 1 and d in "123456789"): raise ValueError("computer_display must be main, cursor or a number 1-9")
        self.computer_display = d
        return self

    @property
    def web_search_active(self) -> bool:
        return self.web_search_consented and self.web_search_mode != "off"


class SettingsStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.value = self._load()

    def _load(self) -> BridgeSettings:
        try:
            raw = json.loads(self.path.read_text())
            known = {f.name for f in fields(BridgeSettings)}
            return BridgeSettings(**{k: v for k, v in raw.items() if k in known}).validate()
        except FileNotFoundError:
            return BridgeSettings()
        except Exception:                       # corrupt/invalid file: fall back to safe defaults, keep the bad file
            try: self.path.rename(self.path.with_suffix(".corrupt"))
            except OSError: pass
            return BridgeSettings()

    def update(self, **changes) -> BridgeSettings:
        known = {f.name for f in fields(BridgeSettings)}
        bad = set(changes) - known
        if bad: raise ValueError(f"unknown settings: {sorted(bad)}")
        new = BridgeSettings(**{**asdict(self.value), **changes}).validate()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".settings-")
        with os.fdopen(fd, "w") as f: json.dump(asdict(new), f, indent=2)
        os.replace(tmp, self.path)
        self.value = new
        return new
