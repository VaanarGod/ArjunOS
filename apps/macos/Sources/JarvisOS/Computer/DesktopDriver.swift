import AppKit
import ApplicationServices
import CoreGraphics
import ScreenCaptureKit
import JarvisCore

/// Operates other Mac apps. Perception order: the Accessibility tree first (fast, exact, needs no screen permission), then Apple Vision OCR on a
/// ScreenCaptureKit picture only when the tree is thin, and a picture for the model only when asked. Actions prefer Accessibility "press" over
/// moving the mouse, and every result is re-read from Accessibility so the bridge can VERIFY without another model call.
/// Coordinates the bridge sees are "observation pixels": points on the CHOSEN display (Settings → Computer use: main, the one the pointer is on, or a number) times `scale`.
@MainActor
final class DesktopDriver {
    private var targetPID: pid_t?
    private var scale = 1.0
    private var cache: (gen: Int, elements: [ComputerElement], handles: [Int: AXUIElement])?
    private var gen = 0
    private var lastSignature = ""
    private var displayChoice = "main"                                   // main | cursor | 1-9, from the bridge's setting
    private var locked: (id: CGDirectDisplayID, bounds: CGRect)?          // the display of the latest observation: every action of that plan uses the SAME one, even if the pointer moves to another screen meanwhile
    private let selfBundle = Bundle.main.bundleIdentifier ?? "ArjunOS"

    // MARK: permissions
    static var hasAccessibility: Bool { AXIsProcessTrusted() }
    static var hasScreenRecording: Bool { CGPreflightScreenCaptureAccess() }
    static func promptAccessibility() { _ = AXIsProcessTrustedWithOptions([kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true] as CFDictionary) }
    static let accessibilityHelp = "ArjunOS needs permission to control your Mac. Open System Settings → Privacy & Security → Accessibility, switch ArjunOS on, then ask again. (If you rebuilt the app, remove it from the list and add it again.)"

    // MARK: which display?
    func setDisplay(_ choice: String?) { if let c = choice, !c.isEmpty { displayChoice = c } }

    /// Active displays, the main one first and the rest left to right, so "2" always means the same screen.
    nonisolated static func orderedDisplays() -> [CGDirectDisplayID] {
        var count: UInt32 = 0
        CGGetActiveDisplayList(0, nil, &count)
        var ids = [CGDirectDisplayID](repeating: 0, count: Int(count))
        CGGetActiveDisplayList(count, &ids, &count)
        let main = CGMainDisplayID()
        return [main] + ids.prefix(Int(count)).filter { $0 != main }.sorted { CGDisplayBounds($0).minX < CGDisplayBounds($1).minX }
    }

    private func chooseDisplay() -> (id: CGDirectDisplayID, bounds: CGRect) {
        let all = Self.orderedDisplays()
        var pick = CGMainDisplayID()
        if displayChoice == "cursor", let at = CGEvent(source: nil)?.location, let hit = all.first(where: { CGDisplayBounds($0).contains(at) }) { pick = hit }
        else if let n = Int(displayChoice), n >= 1, n <= all.count { pick = all[n - 1] }
        return (pick, CGDisplayBounds(pick))
    }

    // MARK: which app are we working on?
    /// The app being operated: normally the front-most app that is not ArjunOS (the user is typing to us, so we are in front, but the task is about
    /// whatever is behind us). nil when nothing else has a window.
    private func resolveTarget() -> NSRunningApplication? {
        if let pid = targetPID, let app = NSRunningApplication(processIdentifier: pid), !app.isTerminated { return app }
        let me = ProcessInfo.processInfo.processIdentifier
        guard let list = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] else { return nil }
        for w in list {                                                     // front-to-back
            guard (w[kCGWindowLayer as String] as? Int) == 0, let pid = w[kCGWindowOwnerPID as String] as? Int32, pid != me,
                  let app = NSRunningApplication(processIdentifier: pid), app.activationPolicy == .regular else { continue }
            targetPID = pid
            return app
        }
        return nil
    }

    // MARK: perception
    func observe(maxDim: Int, wantImage: Bool, ocr: String) async -> ComputerResult {
        guard Self.hasAccessibility else { return .fail(Self.accessibilityHelp, code: "permission") }
        let chosen = chooseDisplay(); locked = chosen
        let display = chosen.bounds
        scale = min(1.0, Double(max(640, min(2048, maxDim))) / Double(max(display.width, display.height)))
        var st = ComputerState()
        st.width = Int(display.width * scale); st.height = Int(display.height * scale)
        guard let app = resolveTarget() else {
            st.title = "Desktop"; st.text = "No other app window is open. Use open_app to start one."; st.source = "ax"; st.gen = nextGen()
            st.elements = []; cache = (st.gen, [], [:])
            return ComputerResult(ok: true, observation: st)
        }
        st.app = app.localizedName ?? ""; st.bundleID = app.bundleIdentifier ?? ""
        if DesktopGuards.isOffLimits(name: st.app, bundleID: st.bundleID) { st.gen = nextGen(); st.elements = []; return ComputerResult(ok: true, observation: st) }   // nothing is read from it
        let scanned = await scan(app: app, limit: 140, display: display)
        st.title = scanned.title; st.labels = scanned.labels; st.focused = scanned.focused; st.hasSecure = scanned.nodes.contains { $0.secure }
        var els = scanned.nodes.enumerated().map { toObservation($1, index: $0, display: display) }
        st.source = "ax"
        var handles: [Int: AXUIElement] = [:]
        for (i, n) in scanned.nodes.enumerated() { handles[i] = n.element }

        // thin Accessibility data (games, canvases, some Electron apps): read the screen with Apple Vision instead
        let doOCR = ocr == "always" || (ocr == "auto" && els.count < 8)      // "always": the model cannot see pictures, so every screen gets read by Apple Vision
        let needPicture = wantImage || doOCR
        if needPicture, Self.hasScreenRecording, let cg = await capture(displayID: chosen.id, bounds: display) {
            let box = SendableImage(image: cg)
            let width = st.width, height = st.height
            if doOCR {
                let boxes = await Task.detached(priority: .userInitiated) { ComputerImaging.recognizeBoxes(box.image) }.value
                let k = Double(st.width) / Double(max(cg.width, 1))
                for b in boxes.prefix(80) {
                    let i = els.count
                    els.append(ComputerElement(i: i, role: "text", label: String(b.text.prefix(90)), x: Int(b.rect.minX * k), y: Int(b.rect.minY * k), w: max(1, Int(b.rect.width * k)), h: max(1, Int(b.rect.height * k))))
                    st.labels.append(b.text.lowercased())
                }
                st.source = scanned.nodes.isEmpty ? "ocr" : "ax+ocr"
            }
            if wantImage { st.screenshotB64 = await Task.detached(priority: .userInitiated) { ComputerImaging.jpegBase64(box.image, width: width, height: height) }.value }
        } else if needPicture && !Self.hasScreenRecording && (doOCR || els.count < 8) {
            st.text = "Few controls were found and Screen Recording is not allowed, so I cannot read the screen by OCR. (System Settings → Privacy & Security → Screen Recording.)"
        }
        st.gen = nextGen(); st.elements = els
        cache = (st.gen, els, handles)
        lastSignature = signature(st)
        return ComputerResult(ok: true, observation: st)
    }

    func state() async -> ComputerResult {
        guard Self.hasAccessibility else { return .fail(Self.accessibilityHelp, code: "permission") }
        guard let app = resolveTarget() else { var st = ComputerState(); st.title = "Desktop"; st.changed = true; return ComputerResult(ok: true, state: st) }
        var st = ComputerState()
        st.app = app.localizedName ?? ""; st.bundleID = app.bundleIdentifier ?? ""
        if !DesktopGuards.isOffLimits(name: st.app, bundleID: st.bundleID) {
            let s = await scan(app: app, limit: 140, display: (locked ?? chooseDisplay()).bounds)
            st.title = s.title; st.labels = s.labels; st.focused = s.focused; st.hasSecure = s.nodes.contains { $0.secure }
        }
        st.source = "ax"; st.gen = cache?.gen ?? gen
        st.changed = signature(st) != lastSignature
        return ComputerResult(ok: true, state: st)
    }

    func resolve(_ target: ComputerTarget) async -> ComputerResult {
        guard Self.hasAccessibility else { return .fail(Self.accessibilityHelp, code: "permission") }
        if let i = target.i, let c = cache, c.gen == target.gen, let e = c.elements.first(where: { $0.i == i }) { return resolved(e) }
        // by name: look again, now (the screen may have changed since the plan was made)
        guard let app = resolveTarget() else { return .fail("No app is open to look in.", code: "not_found") }
        let obs = await observe(maxDim: Int(Double((locked ?? chooseDisplay()).bounds.width) * scale), wantImage: false, ocr: "auto")
        guard obs.ok, let o = obs.observation, let els = o.elements else { return obs }
        if let l = target.label, !l.isEmpty, let e = ElementMatcher.find(label: l, role: target.role, in: els) { return resolved(e, state: o) }
        let near = els.prefix(6).map(\.label).filter { !$0.isEmpty }.joined(separator: ", ")
        return .fail("No control called “\(target.label ?? "#\(target.i ?? -1)")” in \(app.localizedName ?? "this app"). Visible: \(near)", code: "not_found")
    }
    private func resolved(_ e: ComputerElement, state: ComputerState? = nil) -> ComputerResult {
        var st = state ?? ComputerState()
        if state == nil, let app = resolveTarget() { st.app = app.localizedName ?? ""; st.bundleID = app.bundleIdentifier ?? "" }
        st.elements = nil; st.screenshotB64 = nil; st.gen = cache?.gen ?? gen
        return ComputerResult(ok: true, state: st, element: e)
    }

    // MARK: action
    func act(_ a: ComputerAction, gen g: Int?) async -> ComputerResult {
        guard Self.hasAccessibility else { return .fail(Self.accessibilityHelp, code: "permission") }
        if a.kind == "open_app" { return await openApp(a.name ?? "") }
        if a.kind == "wait" { try? await Task.sleep(nanoseconds: UInt64(min(10, max(0.2, a.seconds ?? 1)) * 1_000_000_000)); return await state() }
        if a.kind == "key", let k = a.keys, DesktopGuards.blockedKeys.contains(k) { return .fail("That shortcut is never sent by the assistant.") }
        guard let app = resolveTarget() else { return .fail("No app is open to act in. Use open_app first.") }
        if DesktopGuards.isOffLimits(name: app.localizedName ?? "", bundleID: app.bundleIdentifier ?? "") { return .fail("That app is off limits for computer control.") }
        guard await bringToFront(app) else { return .fail("Could not bring \(app.localizedName ?? "the app") to the front.") }
        let display = (locked ?? chooseDisplay()).bounds
        func point(_ x: Int, _ y: Int) -> CGPoint { CGPoint(x: display.minX + Double(x) / scale, y: display.minY + Double(y) / scale) }

        switch a.kind {
        case "click":
            let button = a.button ?? "left", dbl = a.double ?? false
            if let i = a.element {
                guard let c = cache, c.gen == g, let el = c.handles[i], let info = c.elements.first(where: { $0.i == i }) else { return .fail("The screen changed since I looked. Look again.", code: "stale") }
                if button == "left", !dbl {                                  // act through Accessibility first: no mouse movement, nothing to collide with
                    if info.editable { if AXUIElementSetAttributeValue(el, kAXFocusedAttribute as CFString, kCFBooleanTrue) == .success { break } }
                    else if AXUIElementPerformAction(el, kAXPressAction as CFString) == .success { break }
                }
                guard click(point(info.x + info.w / 2, info.y + info.h / 2), button: button, double: dbl) else { return .fail("That spot is covered by one of ArjunOS's own windows, which the assistant never clicks. Try a different control.") }
            } else if let x = a.x, let y = a.y {
                guard click(point(x, y), button: button, double: dbl) else { return .fail("That spot is covered by one of ArjunOS's own windows, which the assistant never clicks. Try a different control.") }
            } else { return .fail("click needs a control or a position.") }
        case "type":
            guard let text = a.text, !text.isEmpty else { return .fail("Nothing to type.") }
            if let i = a.element {
                guard let c = cache, c.gen == g, let el = c.handles[i], let info = c.elements.first(where: { $0.i == i }) else { return .fail("The screen changed since I looked. Look again.", code: "stale") }
                if info.secure { return .fail("Password fields are never typed into by the assistant.", code: "secure") }
                if AXUIElementSetAttributeValue(el, kAXFocusedAttribute as CFString, kCFBooleanTrue) != .success {
                    guard click(point(info.x + info.w / 2, info.y + info.h / 2), button: "left", double: false) else { return .fail("That spot is inside ArjunOS.") }
                }
                try? await Task.sleep(nanoseconds: 80_000_000)
                press("cmd+a")                                              // with a target the field's text is replaced
            } else if let x = a.x, let y = a.y {
                guard click(point(x, y), button: "left", double: false) else { return .fail("That spot is inside ArjunOS.") }
                try? await Task.sleep(nanoseconds: 80_000_000); press("cmd+a")
            }
            await typeText(text)
            if a.submit == true { press("enter") }
        case "key":
            guard let k = a.keys, press(k) else { return .fail("I cannot press that key combination.") }
        case "scroll":
            var at = CGPoint(x: display.midX, y: display.midY)
            if let i = a.element, let c = cache, c.gen == g, let e = c.elements.first(where: { $0.i == i }) { at = point(e.x + e.w / 2, e.y + e.h / 2) }
            else if let f = frontWindowFrame(app) { at = CGPoint(x: f.midX, y: f.midY) }
            guard !insideOwnWindows(at) else { return .fail("That spot is inside ArjunOS.") }
            let d = ScrollMath.deltas(direction: a.direction ?? "down", amount: a.amount ?? 3)
            CGEvent(mouseEventSource: nil, mouseType: .mouseMoved, mouseCursorPosition: at, mouseButton: .left)?.postAsAgent()
            CGEvent(scrollWheelEvent2Source: nil, units: .line, wheelCount: 2, wheel1: d.dy, wheel2: d.dx, wheel3: 0)?.postAsAgent()
        case "drag":
            guard let x = a.x, let y = a.y, let x2 = a.x2, let y2 = a.y2 else { return .fail("drag needs start and end points.") }
            guard drag(from: point(x, y), to: point(x2, y2)) else { return .fail("That drag touches ArjunOS, which the assistant never uses.") }
        default: return .fail("“\(a.kind)” is not available on the desktop.")
        }
        try? await Task.sleep(nanoseconds: 350_000_000)                     // let the app react before it is read back
        return await state()
    }

    // MARK: open an app
    private func openApp(_ name: String) async -> ComputerResult {
        guard !name.isEmpty else { return .fail("No app name given.") }
        guard let url = Self.findApp(named: name) else { return .fail("I could not find an app called “\(name)”.") }
        let bundle = Bundle(url: url)?.bundleIdentifier ?? ""
        let shown = url.deletingPathExtension().lastPathComponent
        if DesktopGuards.isOffLimits(name: shown, bundleID: bundle) { return .fail("\(shown) is off limits for computer control.") }
        let cfg = NSWorkspace.OpenConfiguration(); cfg.activates = true
        do {
            let app = try await NSWorkspace.shared.openApplication(at: url, configuration: cfg)
            targetPID = app.processIdentifier
            _ = await bringToFront(app)
            try? await Task.sleep(nanoseconds: 900_000_000)                 // a freshly launched app needs a moment to draw its window
            return await state()
        } catch { return .fail("Could not open \(shown): \(error.localizedDescription)") }
    }

    static func findApp(named name: String) -> URL? {
        let want = name.lowercased().replacingOccurrences(of: ".app", with: "")
        let dirs = ["/Applications", "/System/Applications", "/System/Applications/Utilities", "/System/Library/CoreServices", NSHomeDirectory() + "/Applications"]
        var partial: URL?
        for d in dirs {
            guard let items = try? FileManager.default.contentsOfDirectory(atPath: d) else { continue }
            for item in items where item.hasSuffix(".app") {
                let base = String(item.dropLast(4)).lowercased()
                if base == want { return URL(fileURLWithPath: d + "/" + item) }
                if partial == nil, base.contains(want) { partial = URL(fileURLWithPath: d + "/" + item) }
            }
        }
        return partial
    }

    private func bringToFront(_ app: NSRunningApplication) async -> Bool {
        if NSWorkspace.shared.frontmostApplication?.processIdentifier == app.processIdentifier { return true }
        app.activate(options: [.activateIgnoringOtherApps])
        for _ in 0..<25 {                                                   // up to ~2.5 s
            try? await Task.sleep(nanoseconds: 100_000_000)
            if NSWorkspace.shared.frontmostApplication?.processIdentifier == app.processIdentifier { return true }
        }
        return false
    }

    // MARK: input events
    private func insideOwnWindows(_ p: CGPoint) -> Bool {
        let me = ProcessInfo.processInfo.processIdentifier
        guard let list = CGWindowListCopyWindowInfo([.optionOnScreenOnly], kCGNullWindowID) as? [[String: Any]] else { return false }
        for w in list where (w[kCGWindowOwnerPID as String] as? Int32) == me {
            if let d = w[kCGWindowBounds as String] as? [String: CGFloat], CGRect(x: d["X"] ?? 0, y: d["Y"] ?? 0, width: d["Width"] ?? 0, height: d["Height"] ?? 0).contains(p) { return true }
        }
        return false
    }

    private func click(_ p: CGPoint, button: String, double: Bool) -> Bool {
        guard !insideOwnWindows(p) else { return false }
        let right = button == "right"
        let down: CGEventType = right ? .rightMouseDown : .leftMouseDown, up: CGEventType = right ? .rightMouseUp : .leftMouseUp
        let b: CGMouseButton = right ? .right : .left
        CGEvent(mouseEventSource: nil, mouseType: .mouseMoved, mouseCursorPosition: p, mouseButton: b)?.postAsAgent()
        for n in 1...(double ? 2 : 1) {
            for t in [down, up] {
                let e = CGEvent(mouseEventSource: nil, mouseType: t, mouseCursorPosition: p, mouseButton: b)
                e?.setIntegerValueField(.mouseEventClickState, value: Int64(n)); e?.postAsAgent()
            }
        }
        return true
    }

    private func drag(from a: CGPoint, to b: CGPoint) -> Bool {
        guard !insideOwnWindows(a), !insideOwnWindows(b) else { return false }
        CGEvent(mouseEventSource: nil, mouseType: .mouseMoved, mouseCursorPosition: a, mouseButton: .left)?.postAsAgent()
        CGEvent(mouseEventSource: nil, mouseType: .leftMouseDown, mouseCursorPosition: a, mouseButton: .left)?.postAsAgent()
        for s in 1...12 {
            let t = Double(s) / 12
            CGEvent(mouseEventSource: nil, mouseType: .leftMouseDragged, mouseCursorPosition: CGPoint(x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t), mouseButton: .left)?.postAsAgent()
            usleep(15_000)
        }
        CGEvent(mouseEventSource: nil, mouseType: .leftMouseUp, mouseCursorPosition: b, mouseButton: .left)?.postAsAgent()
        return true
    }

    @discardableResult
    private func press(_ keys: String) -> Bool {
        guard !DesktopGuards.blockedKeys.contains(keys), let combo = KeyCombo.parse(keys) else { return false }
        var flags: CGEventFlags = []
        if combo.command { flags.insert(.maskCommand) }; if combo.shift { flags.insert(.maskShift) }
        if combo.option { flags.insert(.maskAlternate) }; if combo.control { flags.insert(.maskControl) }
        for down in [true, false] {
            let e = CGEvent(keyboardEventSource: nil, virtualKey: CGKeyCode(combo.keyCode), keyDown: down)
            e?.flags = flags; e?.postAsAgent()
        }
        return true
    }

    /// Types any text (accents, emoji, other scripts) as Unicode key events, a few characters at a time.
    private func typeText(_ text: String) async {
        let units = Array(text.utf16)
        var i = 0
        while i < units.count {
            let chunk = Array(units[i..<min(i + 16, units.count)]); i += 16
            for down in [true, false] {
                let e = CGEvent(keyboardEventSource: nil, virtualKey: 0, keyDown: down)
                e?.keyboardSetUnicodeString(stringLength: chunk.count, unicodeString: chunk); e?.postAsAgent()
            }
            try? await Task.sleep(nanoseconds: 8_000_000)
        }
    }

    // MARK: screen capture (ScreenCaptureKit), without ArjunOS's own windows
    private func capture(displayID: CGDirectDisplayID, bounds: CGRect) async -> CGImage? {
        guard let content = try? await SCShareableContent.excludingDesktopWindows(true, onScreenWindowsOnly: true),
              let d = content.displays.first(where: { $0.displayID == displayID }) ?? content.displays.first else { return nil }
        let own = content.applications.filter { $0.bundleIdentifier == selfBundle }
        let filter = SCContentFilter(display: d, excludingApplications: own, exceptingWindows: [])
        let cfg = SCStreamConfiguration()
        cfg.width = Int(bounds.width * scale * 2); cfg.height = Int(bounds.height * scale * 2); cfg.showsCursor = false     // 2x so OCR can read small text
        return try? await SCScreenshotManager.captureImage(contentFilter: filter, configuration: cfg)
    }

    // MARK: Accessibility
    fileprivate struct Node: @unchecked Sendable {
        var element: AXUIElement; var role: String; var label: String; var frame: CGRect
        var secure: Bool; var editable: Bool; var value: String; var checked: Bool?
    }
    fileprivate struct Scanned: @unchecked Sendable { var nodes: [Node]; var labels: [String]; var title: String; var focused: String }

    /// The Accessibility walk talks to another process, so it runs off the main thread.
    private func scan(app: NSRunningApplication, limit: Int, display: CGRect) async -> Scanned {
        let pid = app.processIdentifier
        return await Task.detached(priority: .userInitiated) { Self.scanSync(pid: pid, limit: limit, display: display) }.value
    }

    fileprivate func toObservation(_ n: Node, index: Int, display: CGRect) -> ComputerElement {
        ComputerElement(i: index, role: n.role, label: n.label, x: Int((n.frame.minX - display.minX) * scale), y: Int((n.frame.minY - display.minY) * scale),
                        w: max(1, Int(n.frame.width * scale)), h: max(1, Int(n.frame.height * scale)), secure: n.secure, editable: n.editable,
                        value: n.secure || n.value.isEmpty ? nil : String(n.value.prefix(60)), checked: n.checked)
    }

    fileprivate nonisolated static func scanSync(pid: pid_t, limit: Int, display: CGRect) -> Scanned {
        let root = AXUIElementCreateApplication(pid)
        AXUIElementSetMessagingTimeout(root, 0.4)
        let deadline = Date().addingTimeInterval(1.6)
        var nodes: [Node] = [], labels: [String] = [], visited = 0
        func attr(_ e: AXUIElement, _ k: String) -> CFTypeRef? { var v: CFTypeRef?; return AXUIElementCopyAttributeValue(e, k as CFString, &v) == .success ? v : nil }
        func el(_ e: AXUIElement, _ k: String) -> AXUIElement? { guard let v = attr(e, k), CFGetTypeID(v) == AXUIElementGetTypeID() else { return nil }; return (v as! AXUIElement) }
        func str(_ e: AXUIElement, _ k: String) -> String { ((attr(e, k) as? String) ?? "").trimmingCharacters(in: .whitespacesAndNewlines) }
        func frame(_ e: AXUIElement) -> CGRect? {
            var p = CGPoint.zero, s = CGSize.zero
            guard let pv = attr(e, kAXPositionAttribute), CFGetTypeID(pv) == AXValueGetTypeID(), AXValueGetValue(pv as! AXValue, .cgPoint, &p),
                  let sv = attr(e, kAXSizeAttribute), CFGetTypeID(sv) == AXValueGetTypeID(), AXValueGetValue(sv as! AXValue, .cgSize, &s) else { return nil }
            return CGRect(origin: p, size: s)
        }
        func textBelow(_ e: AXUIElement, depth: Int = 0) -> [String] {
            guard depth < 3 else { return [] }
            var out: [String] = []
            for c in (attr(e, kAXChildrenAttribute) as? [AXUIElement]) ?? [] {
                if str(c, kAXRoleAttribute) == "AXStaticText" { let t = str(c, kAXValueAttribute); if !t.isEmpty { out.append(t) } }
                out += textBelow(c, depth: depth + 1)
                if out.count >= 3 { break }
            }
            return out
        }
        let roles: [String: String] = ["AXButton": "button", "AXTextField": "text field", "AXTextArea": "text field", "AXCheckBox": "checkbox", "AXRadioButton": "radio button",
                                       "AXPopUpButton": "pop up button", "AXComboBox": "combo box", "AXMenuItem": "menu item", "AXMenuBarItem": "menu bar item", "AXMenuButton": "menu button",
                                       "AXLink": "link", "AXRow": "row", "AXSlider": "slider", "AXDisclosureTriangle": "disclosure triangle"]
        let window = el(root, kAXFocusedWindowAttribute) ?? el(root, kAXMainWindowAttribute) ?? (attr(root, kAXWindowsAttribute) as? [AXUIElement])?.first
        let title = window.map { str($0, kAXTitleAttribute) } ?? ""
        var focused = ""
        if let fe = el(root, kAXFocusedUIElementAttribute) { focused = [str(fe, kAXTitleAttribute), str(fe, kAXDescriptionAttribute), str(fe, kAXPlaceholderValueAttribute)].first { !$0.isEmpty } ?? "" }

        var queue: [(AXUIElement, Int)] = []
        if let mb = el(root, kAXMenuBarAttribute) { queue.append((mb, 0)) }
        if let w = window { queue.append((w, 0)) }
        var head = 0
        while head < queue.count, nodes.count < limit, visited < 1500, Date() < deadline {
            let (e, depth) = queue[head]; head += 1; visited += 1
            let role = str(e, kAXRoleAttribute), sub = str(e, kAXSubroleAttribute)
            var label = [str(e, kAXTitleAttribute), str(e, kAXDescriptionAttribute)].first { !$0.isEmpty } ?? ""
            if label.isEmpty, role != "AXRow" { label = str(e, kAXValueAttribute) }
            if role == "AXStaticText" { if !label.isEmpty { labels.append(String(label.prefix(90)).lowercased()) } }
            if let kind = roles[role], let f = frame(e), f.width > 2, f.height > 2, f.intersects(display) {
                let enabled = (attr(e, kAXEnabledAttribute) as? Bool) ?? true
                if enabled {
                    if label.isEmpty, role == "AXRow" || role == "AXMenuItem" { label = textBelow(e).joined(separator: "  ") }
                    if label.isEmpty { label = str(e, kAXPlaceholderValueAttribute) }
                    let secure = sub == "AXSecureTextField"
                    let editable = role == "AXTextField" || role == "AXTextArea" || role == "AXComboBox"
                    let val = editable && !secure ? str(e, kAXValueAttribute) : ""
                    let checked: Bool? = (role == "AXCheckBox" || role == "AXRadioButton") ? ((attr(e, kAXValueAttribute) as? NSNumber)?.boolValue) : nil
                    let name = sub == "AXSearchField" ? "search field" : kind
                    if !label.isEmpty { labels.append(String(label.prefix(90)).lowercased()) }
                    nodes.append(Node(element: e, role: name, label: String(label.prefix(90)), frame: f, secure: secure, editable: editable, value: val, checked: checked))
                }
            }
            if depth < 14, role != "AXButton", role != "AXPopUpButton" {
                for c in (attr(e, kAXChildrenAttribute) as? [AXUIElement]) ?? [] { queue.append((c, depth + 1)) }
            }
        }
        return Scanned(nodes: nodes, labels: Array(labels.prefix(300)), title: title, focused: focused)
    }

    private func frontWindowFrame(_ app: NSRunningApplication) -> CGRect? {
        let root = AXUIElementCreateApplication(app.processIdentifier)
        AXUIElementSetMessagingTimeout(root, 0.4)
        var w: CFTypeRef?
        guard AXUIElementCopyAttributeValue(root, kAXFocusedWindowAttribute as CFString, &w) == .success, let wv = w, CFGetTypeID(wv) == AXUIElementGetTypeID() else { return nil }
        let win = wv as! AXUIElement
        var pv: CFTypeRef?, sv: CFTypeRef?, p = CGPoint.zero, sz = CGSize.zero
        guard AXUIElementCopyAttributeValue(win, kAXPositionAttribute as CFString, &pv) == .success, let pvv = pv, CFGetTypeID(pvv) == AXValueGetTypeID(),
              AXUIElementCopyAttributeValue(win, kAXSizeAttribute as CFString, &sv) == .success, let svv = sv, CFGetTypeID(svv) == AXValueGetTypeID(),
              AXValueGetValue(pvv as! AXValue, .cgPoint, &p), AXValueGetValue(svv as! AXValue, .cgSize, &sz) else { return nil }
        return CGRect(origin: p, size: sz)
    }

    private func nextGen() -> Int { gen += 1; return gen }
    private func signature(_ s: ComputerState) -> String { "\(s.app)|\(s.title)|\(s.focused)|\(s.labels.joined(separator: ","))" }
}
