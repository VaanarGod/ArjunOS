import SwiftUI
import AppKit
import JarvisCore

/// The hands and eyes of computer use. The bridge decides what to do (and enforces the rules and approvals); this class only performs one request
/// at a time and reports what it saw. It never decides anything itself, apart from refusing things that are always off limits.
@MainActor @Observable
final class ComputerController {
    private(set) var active = false
    private(set) var mode = ""
    private(set) var showsAgentBrowser = false              // the pane shows the assistant's private browser instead of yours
    let agentBrowser = BrowserModel(isolated: true)          // throwaway cookies: it can never see the sites you are signed in to

    @ObservationIgnored private let browserDriver = BrowserDriver()
    @ObservationIgnored private let desktopDriver = DesktopDriver()
    @ObservationIgnored private let overlay = ComputerOverlay()
    @ObservationIgnored private let takeover = UserTakeover()          // stops the task by itself when the person touches the mouse or keyboard
    @ObservationIgnored var userBrowser: BrowserModel?
    @ObservationIgnored var post: ((String, ComputerResult) async -> Void)?
    @ObservationIgnored var stop: (() -> Void)?
    @ObservationIgnored var approvalsProvider: (() -> [Approval])?
    @ObservationIgnored var resolveApproval: ((String, Bool) async -> Void)?
    @ObservationIgnored private var approvalWatcher: Task<Void, Never>?

    init() { overlay.onStop = { [weak self] in self?.stop?() } }

    func handle(_ req: ComputerRequest) async {
        if req.kind == "end" { end(); return }
        let m = req.mode ?? "browser"
        begin(m)
        if m == "desktop" {
            if takeover.personTookOver() { await post?(req.id, ComputerResult(ok: true, takeover: true)); return }      // nothing is done once the person has taken over
            takeover.assistantWillAct()
            var result = await desktop(req)
            takeover.assistantDidAct(movedPointer: req.kind == "act")
            if takeover.tripped { result.takeover = true }
            await post?(req.id, result)
            return
        }
        await post?(req.id, await browser(req))
    }

    func end() {
        guard active else { return }
        active = false; mode = ""
        takeover.stop()
        approvalWatcher?.cancel(); approvalWatcher = nil
        overlay.hide()
    }

    func returnToMyBrowser() { showsAgentBrowser = false }

    private func begin(_ m: String) {
        if !active {
            active = true; mode = m
            if m == "desktop" { overlay.show("ArjunOS is controlling your Mac"); takeover.start() }
            watchApprovals()
        }
    }

    /// While a task runs, a step that needs approval is also shown in a floating panel, because ArjunOS's window may be hidden behind the app being operated.
    private func watchApprovals() {
        approvalWatcher?.cancel()
        approvalWatcher = Task { @MainActor [weak self] in
            while !Task.isCancelled {
                guard let self else { return }
                if self.mode == "desktop", let a = self.approvalsProvider?().first(where: { $0.tool.hasPrefix("computer:") && $0.tool != "computer:start" }) {
                    func str(_ k: String) -> String { if case .string(let v)? = a.args[k] { return v } else { return "" } }
                    self.overlay.showApproval(id: a.id, headline: "ArjunOS wants to do this", what: str("do"), where: str("where"), why: str("why")) { ok in
                        Task { @MainActor in self.overlay.hideApproval(); await self.resolveApproval?(a.id, ok) }
                    }
                } else { self.overlay.hideApproval() }
                try? await Task.sleep(nanoseconds: 250_000_000)
            }
        }
    }

    // MARK: browser
    private func browser(_ req: ComputerRequest) async -> ComputerResult {
        let useMine = req.profile == "mine"
        guard let model = useMine ? userBrowser : agentBrowser else { return .fail("The browser is not available.", code: "no_browser") }
        if useMine { if !model.isOpen { model.open() } } else { showsAgentBrowser = true }
        if !useMine || model.isOpen { AppWindows.ensureWidth(1480) }
        if model.selected == nil { let t = model.addTab(nil); model.select(t.id) }
        guard let tab = model.selected else { return .fail("The browser has no tab to work in.", code: "no_browser") }
        let maxDim = req.maxDim ?? 1280
        switch req.kind {
        case "observe":
            if tab.url == nil {                                                  // an empty tab has no page to read
                var st = ComputerState(); st.app = "ArjunOS browser"; st.bundleID = "browser"; st.title = "New tab"; st.source = "dom"; st.elements = []
                st.text = "The browser is empty. Use navigate to open a page."; st.gen = 0
                return ComputerResult(ok: true, observation: st)
            }
            return await browserDriver.observe(tab, maxDim: maxDim, wantImage: req.images ?? false)
        case "state": return tab.url == nil ? .done(state: ComputerState()) : await browserDriver.state(tab)
        case "resolve":
            guard let t = req.target else { return .fail("No target.") }
            return await browserDriver.resolve(tab, target: t)
        case "act":
            guard let a = req.action else { return .fail("No action.") }
            return await browserDriver.act(tab, a, gen: req.gen)
        default: return .fail("Unknown request.")
        }
    }

    // MARK: desktop
    private func desktop(_ req: ComputerRequest) async -> ComputerResult {
        desktopDriver.setDisplay(req.display)
        switch req.kind {
        case "observe": return await desktopDriver.observe(maxDim: req.maxDim ?? 1280, wantImage: req.images ?? false, ocr: req.ocr ?? "auto")
        case "state": return await desktopDriver.state()
        case "resolve":
            guard let t = req.target else { return .fail("No target.") }
            return await desktopDriver.resolve(t)
        case "act":
            guard let a = req.action else { return .fail("No action.") }
            return await desktopDriver.act(a, gen: req.gen)
        default: return .fail("Unknown request.")
        }
    }
}
