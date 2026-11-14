import AppKit
import WebKit
import JarvisCore

/// Operates the built-in browser through the page's DOM. This is the preferred way to act on a web page: it needs no screen permission,
/// finds controls by what they ARE rather than where they are drawn, and reuses the same WKWebView and PageReader the rest of ArjunOS uses.
@MainActor
final class BrowserDriver {
    private let world = WKContentWorld.world(name: "ArjunComputer")
    private var cache: (gen: Int, elements: [ComputerElement])?
    private var scale = 1.0                                           // observation pixels per CSS pixel
    private var maxDim = 1280.0
    private var lastSignature = ""

    // MARK: perception
    func observe(_ tab: BrowserTab, maxDim: Int, wantImage: Bool) async -> ComputerResult {
        self.maxDim = Double(max(640, min(2048, maxDim)))
        guard let scan = await scanPage(tab) else { return .fail("The page did not respond (it may still be loading, or it blocks scripts).", code: "no_browser") }
        var st = scan.state
        st.source = "dom"; st.app = "ArjunOS browser"; st.bundleID = "browser"
        // visible text through the existing PageReader (no OCR: it is only for context)
        let read = await PageReader.read(tab, forceOCR: false, allowOCR: false)
        st.text = String(read.payload.visibleText.isEmpty ? read.payload.text.prefix(2500) : read.payload.visibleText.prefix(2500))
        if wantImage, let (b64, w, h) = await snapshot(tab, maxDim: maxDim, vw: scan.vw, vh: scan.vh) { st.screenshotB64 = b64; st.width = w; st.height = h }
        lastSignature = signature(st, scan.scrollY)
        return ComputerResult(ok: true, observation: st)
    }

    func state(_ tab: BrowserTab) async -> ComputerResult {
        guard var scan = await scanPage(tab) else { return .fail("The page did not respond.", code: "no_browser") }
        scan.state.elements = nil
        scan.state.changed = signature(scan.state, scan.scrollY) != lastSignature
        return ComputerResult(ok: true, state: scan.state)
    }

    func resolve(_ tab: BrowserTab, target: ComputerTarget) async -> ComputerResult {
        if let i = target.i, let c = cache, c.gen == target.gen, let e = c.elements.first(where: { $0.i == i }) {
            var st = ComputerState(); st.url = tab.url?.absoluteString ?? ""; st.title = tab.title; st.app = "ArjunOS browser"; st.bundleID = "browser"; st.gen = c.gen
            return ComputerResult(ok: true, state: st, element: e)
        }
        guard let scan = await scanPage(tab) else { return .fail("The page did not respond.", code: "no_browser") }
        let found: ComputerElement? = {
            if let l = target.label, !l.isEmpty { return ElementMatcher.find(label: l, role: target.role, in: scan.elements) }
            if let i = target.i { return scan.elements.first { $0.i == i } }                                  // a stale number: the page has changed, so only a label can be trusted
            return nil
        }()
        guard let e = found else {
            let near = scan.elements.prefix(6).map(\.label).filter { !$0.isEmpty }.joined(separator: ", ")
            return .fail("No control called “\(target.label ?? "#\(target.i ?? -1)")” on this page. Visible: \(near)", code: "not_found")
        }
        var st = scan.state; st.elements = nil
        return ComputerResult(ok: true, state: st, element: e)
    }

    // MARK: action
    func act(_ tab: BrowserTab, _ a: ComputerAction, gen: Int?) async -> ComputerResult {
        switch a.kind {
        case "navigate":
            guard case .url(let u) = BrowserURL.resolve(a.url ?? ""), ["http", "https"].contains(u.scheme ?? "") else { return .fail("That is not a web address I can open.") }
            tab.load(u); await settle(tab, long: true)
        case "back": guard tab.canGoBack else { return .fail("There is no page to go back to.") }; tab.goBack(); await settle(tab, long: true)
        case "forward": guard tab.canGoForward else { return .fail("There is no page to go forward to.") }; tab.goForward(); await settle(tab, long: true)
        case "wait": try? await Task.sleep(nanoseconds: UInt64(min(10, max(0.2, a.seconds ?? 1)) * 1_000_000_000))
        case "click" where a.trusted == true:
            // The page ignored a script-made click (a DOM event is not "trusted"). Send a REAL mouse event through the window instead: WebKit treats it as the user clicking.
            guard let i = a.element, let c = cache, c.gen == gen, let e = c.elements.first(where: { $0.i == i }) else { return .fail("The page changed since I looked. Look again.", code: "stale") }
            guard trustedClick(tab, cssX: Double(e.x + e.w / 2) / scale, cssY: Double(e.y + e.h / 2) / scale, right: a.button == "right", double: a.double == true) else {
                return .fail("A real click could not be sent: the browser is not showing this page.")
            }
            await settle(tab, long: true)
        case "click", "type", "key", "scroll":
            guard let payload = try? JSONEncoder().encode(JSAction(a: a, gen: gen, scale: scale)), let json = String(data: payload, encoding: .utf8) else { return .fail("Could not build the action.") }
            guard let reply = await evaluate(tab, ComputerScripts.source(op: "act", argJSON: json)),
                  let obj = try? JSONSerialization.jsonObject(with: Data(reply.utf8)) as? [String: Any] else { return .fail("The page did not respond.") }
            if (obj["ok"] as? Bool) != true { return .fail((obj["error"] as? String) ?? "The page refused the action.", code: obj["code"] as? String) }
            await settle(tab, long: a.kind == "click" || (a.kind == "type" && a.submit == true) || a.kind == "key")
        default: return .fail("“\(a.kind)” is not available in the browser.")
        }
        return await state(tab)
    }

    // MARK: trusted input
    /// A genuine AppKit mouse click inside the web view, at a point given in CSS pixels from the page's top-left corner. Only ever aimed at the browser pane
    /// of this app, and only at a point that is inside it.
    private func trustedClick(_ tab: BrowserTab, cssX: Double, cssY: Double, right: Bool, double: Bool) -> Bool {
        let wv = tab.webView
        guard let window = wv.window, wv.bounds.width > 10, cssX >= 0, cssY >= 0, cssX <= wv.bounds.width, cssY <= wv.bounds.height else { return false }
        let inView = NSPoint(x: cssX, y: wv.isFlipped ? cssY : wv.bounds.height - cssY)
        let at = wv.convert(inView, to: nil)
        let down: NSEvent.EventType = right ? .rightMouseDown : .leftMouseDown, up: NSEvent.EventType = right ? .rightMouseUp : .leftMouseUp
        func send(_ type: NSEvent.EventType, _ count: Int) {
            guard let e = NSEvent.mouseEvent(with: type, location: at, modifierFlags: [], timestamp: ProcessInfo.processInfo.systemUptime, windowNumber: window.windowNumber,
                                             context: nil, eventNumber: 0, clickCount: count, pressure: type == up ? 0 : 1) else { return }
            window.sendEvent(e)
        }
        send(.mouseMoved, 0)
        for n in 1...(double ? 2 : 1) { send(down, n); send(up, n) }
        return true
    }

    // MARK: pieces
    private struct JSAction: Encodable {                              // the action as the page script wants it, with coordinates back in CSS pixels
        var kind: String, text: String?, submit: Bool?, keys: String?, direction: String?, amount: Int?, button: String?, double: Bool?
        var element: Int?, x: Double?, y: Double?, gen: Int?
        init(a: ComputerAction, gen: Int?, scale: Double) {
            kind = a.kind; text = a.text; submit = a.submit; keys = a.keys; direction = a.direction; amount = a.amount; button = a.button; double = a.double
            element = a.element; self.gen = gen
            x = a.x.map { Double($0) / scale }; y = a.y.map { Double($0) / scale }
        }
    }

    private struct Scan { var state: ComputerState; var elements: [ComputerElement]; var vw: Double; var vh: Double; var scrollY: Int }

    private func scanPage(_ tab: BrowserTab) async -> Scan? {
        guard let reply = await evaluate(tab, ComputerScripts.source(op: "scan", argJSON: "{\"max\":120}")),
              let o = try? JSONSerialization.jsonObject(with: Data(reply.utf8)) as? [String: Any] else { return nil }
        let vw = (o["vw"] as? Double) ?? 1, vh = (o["vh"] as? Double) ?? 1
        scale = min(1.0, maxDim / max(vw, vh, 1))
        let raw = (o["elements"] as? [[String: Any]]) ?? []
        let k = scale                                                         // a plain copy: closures below must not touch the main-actor property
        let els: [ComputerElement] = raw.compactMap { r in
            guard let i = r["i"] as? Int else { return nil }
            func n(_ key: String) -> Int { Int(((r[key] as? Double) ?? 0) * k) }
            return ComputerElement(i: i, role: (r["role"] as? String) ?? "element", label: (r["label"] as? String) ?? "", x: n("x"), y: n("y"), w: max(1, n("w")), h: max(1, n("h")),
                                   secure: (r["secure"] as? Bool) ?? false, editable: (r["editable"] as? Bool) ?? false, value: r["value"] as? String, checked: r["checked"] as? Bool)
        }
        var st = ComputerState()
        st.gen = (o["gen"] as? Int) ?? 0; st.url = (o["url"] as? String) ?? ""; st.title = (o["title"] as? String) ?? ""
        st.labels = (o["labels"] as? [String]) ?? []; st.focused = (o["focused"] as? String) ?? ""; st.hasSecure = (o["has_secure"] as? Bool) ?? false
        st.loading = (o["loading"] as? Bool) ?? false; st.elements = els; st.width = Int(vw * scale); st.height = Int(vh * scale)
        st.app = "ArjunOS browser"; st.bundleID = "browser"; st.source = "dom"
        cache = (st.gen, els)
        return Scan(state: st, elements: els, vw: vw, vh: vh, scrollY: (o["scroll_y"] as? Int) ?? 0)
    }

    private func signature(_ s: ComputerState, _ scrollY: Int) -> String { "\(s.url)|\(s.title)|\(s.labels.joined(separator: ","))|\(scrollY)" }

    /// Runs the script in the isolated world with a time limit (a hung page must not hang the agent).
    private func evaluate(_ tab: BrowserTab, _ js: String, timeout: TimeInterval = 6) async -> String? {
        let wv = tab.webView, world = self.world
        return await withTaskGroup(of: String?.self) { group in
            group.addTask { @MainActor in
                do { return try await wv.evaluateJavaScript(js, in: nil, contentWorld: world) as? String } catch { return nil }
            }
            group.addTask { try? await Task.sleep(nanoseconds: UInt64(timeout * 1_000_000_000)); return nil }
            let first = await group.next() ?? nil
            group.cancelAll()
            return first
        }
    }

    /// Waits for a navigation to finish and for a dynamic page to stop changing, instead of sleeping for a fixed time.
    private func settle(_ tab: BrowserTab, long: Bool) async {
        try? await Task.sleep(nanoseconds: 250_000_000)
        let deadline = Date().addingTimeInterval(long ? 12 : 3)
        while tab.isLoading && Date() < deadline { try? await Task.sleep(nanoseconds: 100_000_000) }
        var quiet = 0
        while Date().timeIntervalSince(tab.lastMutationAt) < 0.3 && quiet < 8 { quiet += 1; try? await Task.sleep(nanoseconds: 100_000_000) }
    }

    private func snapshot(_ tab: BrowserTab, maxDim: Int, vw: Double, vh: Double) async -> (String, Int, Int)? {
        let wv = tab.webView
        guard wv.window != nil, wv.bounds.width > 10 else { return nil }
        let w = max(1, Int(vw * scale)), h = max(1, Int(vh * scale))
        let cfg = WKSnapshotConfiguration(); cfg.rect = wv.bounds; cfg.snapshotWidth = NSNumber(value: w)
        guard let image = try? await wv.takeSnapshot(configuration: cfg), let cg = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else { return nil }
        let box = SendableImage(image: cg)
        guard let b64 = await Task.detached(priority: .userInitiated, operation: { ComputerImaging.jpegBase64(box.image, width: w, height: h) }).value else { return nil }
        return (b64, w, h)
    }
}
