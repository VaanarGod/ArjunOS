# Computer use

ArjunOS can operate the built-in browser and (optionally) other Mac apps. A local model plans; the app performs and checks each step.
Nothing leaves the Mac: the planner is the chat model you already run in Ollama, screenshots and OCR are processed on-device, and no extra model is used.

## How a task runs (plan, execute, verify, replan)

1. **Look.** The app reads the screen: the browser DOM (inside an isolated JavaScript world), or the macOS Accessibility tree. If Accessibility finds fewer than 8 controls, Apple Vision OCR (on a ScreenCaptureKit picture) adds positioned text. A screenshot is attached for the model only if the model has vision *and* the control list was thin.
2. **Plan once.** The model answers with up to 8 steps. Controls are named by their text (`"target": "Search"`), because numbers go stale as soon as anything happens. Steps can carry `expect` (app, window title, URL, a label that must appear or vanish).
3. **Execute without the model.** For each step the bridge asks the app to find the control *now*, applies the safety rules, asks the user when the step is consequential, has the app do it, and checks the expectations against fresh Accessibility/DOM facts (retrying briefly: UIs lag).
4. **Replan only on surprises:** control missing, expectation not met, step refused, page changed, injection spotted, screen not changing. A finished plan also goes back once, so the model sees the result before it says `done` (it may not claim success in the same plan).

"Open Finder, locate my Xcode projects, and show me the results" is one plan (open, search shortcut, type, Enter) and one look at the result: two model calls, not one per click.

## Where it lives

| Piece | Location |
|---|---|
| Action/plan protocol, clamping of everything the model or app sends | `services/python/src/jarvis_bridge/computer/protocol.py` |
| Safety rules (block / approve / ok), deterministic | `computer/safety.py` |
| Verification | `computer/verify.py` |
| Plan-execute-verify loop, approvals, audit | `computer/agent.py` |
| bridge-to-app round trip | `computer/broker.py` (event `computer_request` on the chat stream; answer `POST /v1/computer/requests/{id}/result`) |
| Request detection ("Open Finder and ...") | `computer/intent.py` |
| Chat integration | `chat/orchestrator.py` (composer switch, plain-words start, or a `<computer mode=...>` tag the model may emit) |
| Mac side | `apps/macos/Sources/JarvisOS/Computer/` (`BrowserDriver`, `DesktopDriver`, `ComputerController`, `ComputerOverlay`, `ComputerMenu`) |
| Settings | Settings, Computer use |

## Security model

* **Off until consent.** `computer_consented` false by default; desktop control is a separate switch, also off.
* **Never, whatever anyone approves:** typing into password fields or fields labelled as credentials/payment; typing text that looks like a secret or a card number (Luhn); Terminal/iTerm, password managers, Keychain, System Settings, Script Editor, Automator, Activity Monitor and ArjunOS itself; quitting apps, Spotlight, lock; navigating to LAN/link-local/cloud-metadata addresses, non-https public sites, or anything while Offline mode is on. The app keeps its own copy of the app/shortcut lists.
* **Always asks (one step, single use):** first use of each app, opening an app, new websites, buttons whose label looks like buying/sending/deleting/posting/installing, checkout/payment/banking pages, paste, close, drag. "Ask before every step" is a setting.
* **Prompt injection.** Everything on screen is untrusted data: fenced, injection-screened; if a screen contains text that gives the assistant orders, every step on it needs approval. The goal comes only from the user. Rules look at the real target (labels, URLs, app names reported by the app), never at what the model says it is doing.
* **Private browser by default.** The agent works in a throwaway WebKit store with none of your logins. "Mine" is opt-in.
* **Can't reach other abilities.** The computer agent has only its own action set: no terminal, files, MCP or vault. It is switched off for crew workers and while a web page is in the chat context.
* **Stop.** Stop button (chat and on-screen banner), Control-Option-Escape, and the step limit. Grants for safe steps are per-run and revoked at the end; consequential steps can never be pre-approved.
* **Audit.** Run start/finish, every allowed/blocked step (typed text is logged as a length only).

## Performance choices

Ollama gets `keep_alive: 30m` (model stays loaded), JSON-constrained output, temperature 0.1 and a 900-token cap; the system prompt is identical on every call so engines can reuse the processed prefix; only the latest screen is sent (history is one line per step). Accessibility scans run off the main thread with a 1.6 s cap. The bridge's own overhead measured about 100 ms for a 3-action task (including one approval and verification) with a scripted model. Real latency depends on your model and Mac and has not been measured.

## Known limits

* The main display only (coordinates are relative to it).
* Browser clicks are DOM events (not "trusted" OS events); a few sites ignore them. Cross-origin iframes and closed shadow DOM are not scanned.
* Cmd/Ctrl shortcuts cannot be sent to a web page (use clicks or `navigate`).
* Accessibility grants are tied to the app's code signature. The packaged app is ad-hoc signed, so macOS may reset the grant after each rebuild: remove ArjunOS from Privacy & Security, Accessibility and add it again.
* Small models may produce poor plans. The loop refuses bad output, replans, and stops after three unusable answers.

## Tests

`pytest services/python/tests/test_computer.py` covers the protocol, every safety rule, verification, the plan/replan loop, approvals, injection, limits, stop, intent rules, chat integration, the API, and an end-to-end run over real HTTP/SSE with a scripted Ollama. `apps/macos/Tests/JarvisCoreTests/ComputerTests.swift` covers the pure Swift logic (needs `swift test` on a Mac). The Accessibility, WebKit, CGEvent, ScreenCaptureKit and Vision drivers can only be verified on a real Mac with permissions: see the manual checklist in the project README section "Computer use".


## Evaluation: Cua (trycua/cua)

Cua is MIT-licensed. The part that matters here is **Cua Driver**: a macOS driver (Swift, macOS 14+) that exposes the Accessibility tree and screenshots, and performs clicks and typing **in the background without moving your cursor or stealing focus**, over MCP (stdio) or a CLI. ArjunOS already has MCP infrastructure and its own approval policy.

Why it is a good fit: background input removes the focus and cursor collisions that the built-in desktop driver has; it is a separately signed app, so the macOS Accessibility and Screen Recording grants attach to *it* and survive rebuilds of ArjunOS (the ad-hoc signed ArjunOS loses them); it is maintained by people whose whole job is this problem.

Open questions to settle before adopting it (none checked on a real Mac by the author): its telemetry (a maintainer described limited command-level telemetry; for a local-first app it must be switched off and verified), how it installs (a script and a background daemon, so a trust decision), a few cases that still need the app in the foreground, and the exact tool output formats, which the bridge adapter must be written against on a real machine.

Suggested path: keep the built-in driver as the default, add Cua Driver as an optional "desktop backend" behind the same plan/execute/verify loop and the same safety rules (the rules look at the real element, app and URL, so they apply to any backend), and compare them on real tasks.


## Second round: takeover, marks, budget, timings, trusted clicks, displays, optional Cua Driver

**Verification status.** Python: 926 tests pass (`tests/test_computer_next.py`, `tests/test_cua.py`, `tests/test_crew_split.py` are new or extended; every safety guard below was mutation-tested: removing it fails a test). Swift: parsed with a real Swift parser, **not compiled and not run**. Cua: tested only against `tests/fake_cua_driver.py`, a fake MCP server written from Cua's published tool reference, never against a real Cua Driver.

| Feature | Where | Status |
|---|---|---|
| User takeover: the task stops if you touch the mouse or keyboard | Bridge: `UserTookOver`, `ComputerRunner._ask`. App: `UserTakeover.swift`, events stamped by `postAsAgent` | Bridge tested. Swift unbuilt. macOS may ask for Input Monitoring before it reports key presses. |
| Marked screenshots (numbered boxes matching the `[n]` list) | `computer/marks.py` (Pillow, optional), setting `computer_marks` | Tested, and checked by eye on a sample image. Whether it raises accuracy on small vision models is unmeasured. |
| Prompt budget | `computer/budget.py`, setting `computer_prompt_chars` (default 9000 = the old worst case, so no change until you tune it) | Tested. Dropped controls are still found by name. |
| Timings on every run | `computer/stats.py`; audit `run_finished`, `GET /v1/computer/status` → `last_run` | Tested. Numbers only, no screen content. |
| Latency benchmark | `python -m jarvis_bridge.computer.bench --model <name>` | Plumbing tested against a stand-in Ollama. **Not run on a real model: the 2–5 s target is unmeasured.** |
| Context window | `computer_num_ctx` (default 8192) sent as `num_ctx`; a notice appears when the prompt fills it | Tested. Before this the instructions could be silently cut off on a long screen. |
| Trusted clicks in web pages | A DOM click that changed nothing is retried once as a real mouse event. Never when the page did change, never for a step that needed approval. App: `BrowserDriver.trustedClick` | Bridge tested. Swift unbuilt. |
| Multi-display | `computer_display` = main / cursor / 1–9, sent with every desktop request; display locked per look. App: `DesktopDriver.chooseDisplay` | Bridge tested. Swift unbuilt and untested with two screens. |
| Crew: failed part → stronger model | Escalation now steps up after the 1st **and** 2nd failure, and never leaves the models you switched on | Tested. Per-part progress on the graph was already built. |
| Optional Cua Driver | `computer/cua.py`, `routing.py`; setting `computer_desktop_backend` = `cua` | See below. |

### Cua Driver backend
Install Cua Driver from cua.ai, then Settings → Computer use → Driver → Cua Driver. The runner is unchanged: `RoutingBroker` answers the same four requests (observe, resolve, act, state) from Cua tool calls, so planning, verification, approvals and every "never" list are the same code.

* Only 14 Cua tools can be called. `kill_app`, clipboard, scripts, menus, `set_value` and `bring_to_front` are refused before they leave the bridge. Off-limits apps and blocked shortcuts are checked again inside the backend.
* Background delivery only. Retrying in the foreground (which briefly raises the window) happens only if enabled in code (`foreground_for`); there is no setting yet.
* At connect the bridge compares the parameters it sends with the driver's own `tools/list` schema and refuses to start with a clear message if they differ.
* The driver is started with `CUA_DRIVER_TELEMETRY_ENABLED=0`. The bridge does not change Cua's saved config; run `cua-driver config telemetry disable` to switch it off for good.
* Takeover detection and display choice apply to the built-in driver only: Cua works on one window at a time wherever it is.
* **Things the first real run must confirm:** the shape of each element's `frame` (assumed window-local pixels), the `check_permissions` result keys, the `hotkey` parameter name (`keys`), the `scroll` and `drag` parameter names, and that `launch_app` returns `pid` and `windows`. A mismatch in names is reported at connect; a mismatch in coordinates would show up as clicks landing in the wrong place (try the marked screenshot to see).
