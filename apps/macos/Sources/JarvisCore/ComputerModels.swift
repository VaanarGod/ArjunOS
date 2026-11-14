import Foundation

// MARK: - What the bridge asks for (arrives as `computer_request` on the chat stream)

public struct ComputerTarget: Codable, Sendable, Equatable {
    public var i: Int?; public var gen: Int?; public var label: String?; public var role: String?
}

public struct ComputerAction: Codable, Sendable, Equatable {
    public var kind: String                       // click | type | key | scroll | drag | navigate | back | forward | open_app | wait
    public var element: Int?; public var x: Int?; public var y: Int?; public var x2: Int?; public var y2: Int?
    public var text: String?; public var submit: Bool?; public var keys: String?
    public var direction: String?; public var amount: Int?
    public var url: String?; public var name: String?; public var seconds: Double?
    public var button: String?; public var double: Bool?
    public var trusted: Bool?                      // browser click: send a real OS-level mouse event (the bridge sets this when a DOM click changed nothing)
    public var label: String?; public var role: String?
    public init(kind: String) { self.kind = kind }
}

public struct ComputerRequest: Codable, Sendable, Equatable {
    public var id: String
    public var kind: String                       // observe | resolve | act | state | end
    public var mode: String?                      // browser | desktop
    public var profile: String?                   // private | mine (browser only)
    public var maxDim: Int?
    public var images: Bool?                      // the model can see pictures AND the control list was thin: attach a screenshot
    public var ocr: String?                       // "auto": run Apple Vision when Accessibility finds too little
    public var display: String?                   // desktop: main | cursor | 1-9 (which screen to look at and click on)
    public var gen: Int?
    public var target: ComputerTarget?
    public var action: ComputerAction?
}

// MARK: - What the app answers (POST /v1/computer/requests/{id}/result)

public struct ComputerElement: Codable, Sendable, Equatable {
    public var i: Int; public var role: String; public var label: String
    public var x: Int; public var y: Int; public var w: Int; public var h: Int
    public var secure: Bool; public var editable: Bool
    public var value: String?; public var checked: Bool?
    public init(i: Int, role: String, label: String, x: Int, y: Int, w: Int, h: Int, secure: Bool = false, editable: Bool = false, value: String? = nil, checked: Bool? = nil) {
        self.i = i; self.role = role; self.label = label; self.x = x; self.y = y; self.w = w; self.h = h
        self.secure = secure; self.editable = editable; self.value = value; self.checked = checked
    }
}

/// The screen (or, after an action, a light 'state' without the control list or picture).
public struct ComputerState: Codable, Sendable, Equatable {
    public var app: String = ""; public var bundleID: String = ""; public var isSelf = false
    public var title: String = ""; public var url: String = ""
    public var labels: [String] = []; public var focused: String = ""
    public var gen: Int = 0; public var source: String = ""          // ax | dom | ocr | ax+ocr
    public var changed: Bool?; public var hasSecure = false; public var loading = false
    public var width: Int = 0; public var height: Int = 0
    public var text: String = ""
    public var elements: [ComputerElement]?
    public var screenshotB64: String?

    enum CodingKeys: String, CodingKey {
        case app, bundleID = "bundle_id", isSelf = "is_self", title, url, labels, focused, gen, source, changed
        case hasSecure = "has_secure", loading, width, height, text, elements, screenshotB64 = "screenshot_b64"
    }
    public init() {}
}

public struct ComputerResult: Codable, Sendable, Equatable {
    public var ok: Bool
    public var error: String?; public var code: String?; public var note: String?
    public var observation: ComputerState?; public var state: ComputerState?; public var element: ComputerElement?
    public var takeover: Bool?                    // the person used the mouse or keyboard while the assistant was working: the bridge stops the whole task

    public static func fail(_ message: String, code: String? = nil) -> ComputerResult { .init(ok: false, error: message, code: code) }
    public static func done(_ note: String? = nil, state: ComputerState? = nil) -> ComputerResult { .init(ok: true, note: note, state: state) }
    public init(ok: Bool, error: String? = nil, code: String? = nil, note: String? = nil, observation: ComputerState? = nil, state: ComputerState? = nil, element: ComputerElement? = nil, takeover: Bool? = nil) {
        self.ok = ok; self.error = error; self.code = code; self.note = note; self.observation = observation; self.state = state; self.element = element; self.takeover = takeover
    }
}

// MARK: - Pure logic (no AppKit, so it is unit-tested)

/// Finds the control a plan step names by its text. Exact match beats prefix beats substring; a matching role breaks ties;
/// among equals the first one on screen (reading order) wins.
public enum ElementMatcher {
    public static func find(label: String, role: String?, in elements: [ComputerElement]) -> ComputerElement? {
        let want = normalise(label)
        guard !want.isEmpty else { return nil }
        let wantRole = normalise(role ?? "")
        func score(_ e: ComputerElement) -> Int? {
            let have = normalise(e.label)
            guard !have.isEmpty else { return nil }
            var s: Int
            if have == want { s = 300 } else if have.hasPrefix(want) { s = 200 } else if have.contains(want) { s = 100 } else { return nil }
            if !wantRole.isEmpty { s += normalise(e.role).contains(wantRole) ? 50 : -50 }
            return s
        }
        let ranked = elements.compactMap { e in score(e).map { (e, $0) } }
        guard let best = ranked.map(\.1).max() else { return nil }
        return ranked.filter { $0.1 == best }.map(\.0).sorted { ($0.y, $0.x) < ($1.y, $1.x) }.first
    }
    static func normalise(_ s: String) -> String {
        s.lowercased().folding(options: [.diacriticInsensitive], locale: nil)
            .components(separatedBy: .whitespacesAndNewlines).filter { !$0.isEmpty }.joined(separator: " ")
    }
}

/// "cmd+shift+t" -> modifier flags + a macOS virtual key code. The bridge has already normalised and vetted the string.
public struct KeyCombo: Equatable, Sendable {
    public var keyCode: UInt16
    public var command = false, shift = false, option = false, control = false
    public var character: Character?

    static let named: [String: UInt16] = [
        "enter": 36, "tab": 48, "space": 49, "backspace": 51, "esc": 53, "delete": 117, "home": 115, "end": 119, "pageup": 116, "pagedown": 121,
        "left": 123, "right": 124, "down": 125, "up": 126,
        "f1": 122, "f2": 120, "f3": 99, "f4": 118, "f5": 96, "f6": 97, "f7": 98, "f8": 100, "f9": 101, "f10": 109, "f11": 103, "f12": 111]
    static let ansi: [Character: UInt16] = [
        "a": 0, "s": 1, "d": 2, "f": 3, "h": 4, "g": 5, "z": 6, "x": 7, "c": 8, "v": 9, "b": 11, "q": 12, "w": 13, "e": 14, "r": 15, "y": 16, "t": 17,
        "1": 18, "2": 19, "3": 20, "4": 21, "6": 22, "5": 23, "=": 24, "9": 25, "7": 26, "-": 27, "8": 28, "0": 29, "]": 30, "o": 31, "u": 32, "[": 33,
        "i": 34, "p": 35, "l": 37, "j": 38, "'": 39, "k": 40, ";": 41, "\\": 42, ",": 43, "/": 44, "n": 45, "m": 46, ".": 47, "`": 50]

    public static func parse(_ s: String) -> KeyCombo? {
        var combo = KeyCombo(keyCode: 0); var main: String?
        for part in s.lowercased().split(separator: "+").map(String.init) {
            switch part {
            case "cmd", "command": combo.command = true
            case "shift": combo.shift = true
            case "opt", "option", "alt": combo.option = true
            case "ctrl", "control": combo.control = true
            default: if main == nil { main = part } else { return nil }
            }
        }
        guard let m = main else { return nil }
        if let code = named[m] { combo.keyCode = code; return combo }
        if m.count == 1, let c = m.first, let code = ansi[c] { combo.keyCode = code; combo.character = c; return combo }
        return nil
    }
}

/// Which way, and how many "lines", for a scroll request. Positive y scrolls content up (the view moves down).
public enum ScrollMath {
    public static func deltas(direction: String, amount: Int) -> (dx: Int32, dy: Int32) {
        let n = Int32(max(1, min(20, amount))) * 8
        switch direction {
        case "up": return (0, n); case "down": return (0, -n)
        case "left": return (n, 0); case "right": return (-n, 0)
        default: return (0, -n)
        }
    }
}

/// Telling the person's input from the assistant's. Every event the assistant posts carries `marker` in its eventSourceUserData field, so anything else
/// that reaches a global event monitor while a task runs was the person. The pointer check catches a nudge between two actions.
public enum TakeoverMath {
    public static let marker: Int64 = 0x41_52_4A_55                   // "ARJU"
    public static func isAssistantEvent(userData: Int64) -> Bool { userData == marker }
    /// True when the pointer is further from where the assistant last left it than `tolerance` points.
    public static func pointerMoved(expectedX: Double, expectedY: Double, actualX: Double, actualY: Double, tolerance: Double = 12) -> Bool {
        let dx = expectedX - actualX, dy = expectedY - actualY
        return (dx * dx + dy * dy).squareRoot() > tolerance
    }
}

/// Apps the agent may never operate (a second copy of the bridge's list, so the app refuses even if the bridge were fooled).
/// A terminal would bypass the shell sandbox, a password manager holds secrets, and ArjunOS itself holds the Approve buttons.
public enum DesktopGuards {
    static let nameWords = ["terminal", "iterm", "keychain", "system settings", "system preferences", "script editor", "automator", "activity monitor",
                            "1password", "bitwarden", "lastpass", "dashlane", "keeper", "enpass", "arjunos", "jarvis", "disk utility", "shortcuts", "passwords"]
    static let bundlePrefixes = ["com.apple.terminal", "com.googlecode.iterm2", "com.apple.keychainaccess", "com.apple.systempreferences", "com.apple.scripteditor2",
                                 "com.apple.automator", "com.apple.activitymonitor", "com.apple.passwords", "com.apple.shortcuts", "com.apple.diskutility",
                                 "com.agilebits.", "com.1password.", "com.bitwarden.", "com.lastpass.", "com.dashlane.", "com.jarvis", "com.arjun"]
    public static func isOffLimits(name: String, bundleID: String) -> Bool {
        let n = name.lowercased(), b = bundleID.lowercased()
        return nameWords.contains { n.contains($0) } || bundlePrefixes.contains { b.hasPrefix($0) }
    }
    /// Shortcuts the app itself refuses to send, whatever the bridge says.
    public static let blockedKeys: Set<String> = ["cmd+q", "cmd+opt+q", "cmd+shift+q", "cmd+ctrl+q", "cmd+opt+esc", "ctrl+opt+esc", "cmd+shift+delete", "cmd+opt+shift+delete", "cmd+space"]
}
