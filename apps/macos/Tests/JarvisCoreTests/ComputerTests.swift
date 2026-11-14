import XCTest
@testable import JarvisCore

/// The pure parts of computer use: what the bridge sends, what the app answers, which control a step means, which key to press,
/// and the app-side "never" lists. (The drivers that touch Accessibility, WebKit and CGEvent can only be tested on a real, permitted Mac.)
final class ComputerTests: XCTestCase {
    private func decoder() -> JSONDecoder { let d = JSONDecoder(); d.keyDecodingStrategy = .convertFromSnakeCase; return d }
    private func els(_ labels: [(String, String)]) -> [ComputerElement] {
        labels.enumerated().map { ComputerElement(i: $0.offset, role: $0.element.1, label: $0.element.0, x: 10, y: 10 + 30 * $0.offset, w: 100, h: 20) }
    }

    // MARK: protocol
    func testRequestsFromTheBridgeDecode() throws {
        let json = #"{"computer_request":{"id":"cr_ab12","kind":"act","mode":"desktop","profile":"private","max_dim":1280,"gen":4,"action":{"kind":"type","text":"xcodeproj","submit":true,"label":"Search"},"target":{"i":2,"gen":4}}}"#
        let ev = try decoder().decode(ChatEvent.self, from: Data(json.utf8))
        let r = try XCTUnwrap(ev.computerRequest)
        XCTAssertEqual(r.id, "cr_ab12"); XCTAssertEqual(r.kind, "act"); XCTAssertEqual(r.maxDim, 1280); XCTAssertEqual(r.gen, 4)
        XCTAssertEqual(r.action?.kind, "type"); XCTAssertEqual(r.action?.text, "xcodeproj"); XCTAssertEqual(r.action?.submit, true); XCTAssertEqual(r.target?.i, 2)
        let end = try decoder().decode(ChatEvent.self, from: Data(#"{"computer_request":{"id":"end","kind":"end"}}"#.utf8))
        XCTAssertEqual(end.computerRequest?.kind, "end")
    }

    func testResultsEncodeWithTheFieldNamesThePythonBridgeReads() throws {
        var st = ComputerState(); st.app = "Finder"; st.bundleID = "com.apple.finder"; st.isSelf = false; st.hasSecure = true; st.screenshotB64 = "QUJD"; st.changed = true
        st.elements = [ComputerElement(i: 0, role: "text field", label: "Search", x: 1, y: 2, w: 3, h: 4, secure: false, editable: true)]
        let e = JSONEncoder(); e.keyEncodingStrategy = .convertToSnakeCase
        let obj = try XCTUnwrap(JSONSerialization.jsonObject(with: e.encode(ComputerResult(ok: true, observation: st))) as? [String: Any])
        let o = try XCTUnwrap(obj["observation"] as? [String: Any])
        for k in ["app", "bundle_id", "is_self", "has_secure", "screenshot_b64", "changed", "elements", "labels", "gen"] { XCTAssertNotNil(o[k], k) }
        XCTAssertEqual(obj["ok"] as? Bool, true)
        let fail = try XCTUnwrap(JSONSerialization.jsonObject(with: e.encode(ComputerResult.fail("nope", code: "permission"))) as? [String: Any])
        XCTAssertEqual(fail["ok"] as? Bool, false); XCTAssertEqual(fail["code"] as? String, "permission")
    }

    func testSettingsFromAnOlderBridgeStillDecode() throws {
        let s = try decoder().decode(AppSettings.self, from: Data(#"{"web_search_mode":"auto"}"#.utf8))
        XCTAssertNil(s.computerConsented)
    }

    // MARK: choosing the control a step names
    func testExactMatchBeatsPrefixBeatsSubstring() {
        let e = els([("Search results", "row"), ("Search", "text field"), ("Advanced search options", "button")])
        XCTAssertEqual(ElementMatcher.find(label: "search", role: nil, in: e)?.label, "Search")
        XCTAssertEqual(ElementMatcher.find(label: "Advanced", role: nil, in: e)?.label, "Advanced search options")
        XCTAssertNil(ElementMatcher.find(label: "Downloads", role: nil, in: e))
        XCTAssertNil(ElementMatcher.find(label: "   ", role: nil, in: e))
    }
    func testRoleBreaksTiesAndReadingOrderBreaksTheRest() {
        let e = els([("Send", "link"), ("Send", "button"), ("Send", "button")])
        XCTAssertEqual(ElementMatcher.find(label: "Send", role: "button", in: e)?.i, 1)       // the first button, not the link
        XCTAssertEqual(ElementMatcher.find(label: "Send", role: nil, in: e)?.i, 0)
    }
    func testMatchingIgnoresCaseAccentsAndSpacing() {
        XCTAssertNotNil(ElementMatcher.find(label: "cafe  menu", role: nil, in: els([("Café Menu", "link")])))
    }

    // MARK: keys
    func testKeyCombosParseToModifiersAndKeyCodes() throws {
        let f = try XCTUnwrap(KeyCombo.parse("cmd+f")); XCTAssertTrue(f.command); XCTAssertFalse(f.shift); XCTAssertEqual(f.keyCode, 3)
        let t = try XCTUnwrap(KeyCombo.parse("cmd+shift+t")); XCTAssertTrue(t.command && t.shift); XCTAssertEqual(t.keyCode, 17)
        XCTAssertEqual(KeyCombo.parse("enter")?.keyCode, 36); XCTAssertEqual(KeyCombo.parse("esc")?.keyCode, 53); XCTAssertEqual(KeyCombo.parse("down")?.keyCode, 125)
        XCTAssertEqual(KeyCombo.parse("ctrl+opt+esc")?.control, true)
        XCTAssertNil(KeyCombo.parse("cmd+bananas")); XCTAssertNil(KeyCombo.parse("cmd+")); XCTAssertNil(KeyCombo.parse("a+b"))
    }
    func testScrollDirections() {
        XCTAssertEqual(ScrollMath.deltas(direction: "down", amount: 3).dy, -24); XCTAssertEqual(ScrollMath.deltas(direction: "up", amount: 3).dy, 24)
        XCTAssertEqual(ScrollMath.deltas(direction: "right", amount: 1).dx, -8); XCTAssertEqual(ScrollMath.deltas(direction: "down", amount: 999).dy, -160)    // capped at 20
    }

    // MARK: the app's own "never" lists
    func testOffLimitsAppsAndShortcuts() {
        for (n, b) in [("Terminal", "com.apple.Terminal"), ("iTerm2", "com.googlecode.iterm2"), ("1Password", "com.1password.1password"), ("Keychain Access", "com.apple.keychainaccess"),
                       ("System Settings", "com.apple.systempreferences"), ("ArjunOS", "com.arjun.os"), ("Passwords", "com.apple.Passwords")] {
            XCTAssertTrue(DesktopGuards.isOffLimits(name: n, bundleID: b), n)
        }
        XCTAssertFalse(DesktopGuards.isOffLimits(name: "Finder", bundleID: "com.apple.finder"))
        XCTAssertFalse(DesktopGuards.isOffLimits(name: "Notes", bundleID: "com.apple.Notes"))
        for k in ["cmd+q", "cmd+space", "ctrl+opt+esc", "cmd+shift+delete"] { XCTAssertTrue(DesktopGuards.blockedKeys.contains(k), k) }
        XCTAssertFalse(DesktopGuards.blockedKeys.contains("cmd+f"))
    }

    // MARK: how progress shows up in the chat
    func testComputerProgressIsOneChipThatUpdatesInPlace() throws {
        func ev(_ j: String) throws -> ChatEvent { try decoder().decode(ChatEvent.self, from: Data(j.utf8)) }
        var m = ChatMessage(role: "assistant", content: "")
        _ = ChatReducer.apply(try ev(#"{"tool":{"id":1,"name":"computer","status":"running","args":{"goal":"find projects","mode":"desktop","action":"Open the app Finder","plan":["Open the app Finder","Press cmd+f"],"plan_done":0}}}"#), to: &m)
        XCTAssertEqual(m.activity?.count, 1); XCTAssertEqual(m.activity?.first?.kind, "computer"); XCTAssertEqual(m.activity?.first?.title, "Using your Mac")
        XCTAssertTrue(m.activity?.first?.detail?.contains("step 1 of 2") ?? false)
        _ = ChatReducer.apply(try ev(#"{"tool":{"id":1,"name":"computer","status":"waiting_approval","args":{"action":"Click “Place order”"}}}"#), to: &m)
        XCTAssertEqual(m.activity?.count, 1); XCTAssertEqual(m.activity?.first?.status, "waiting_approval")
        _ = ChatReducer.apply(try ev(#"{"tool":{"id":1,"name":"computer","status":"done","output":"• Open the app Finder","args":{"goal":"find projects","mode":"desktop"}}}"#), to: &m)
        XCTAssertEqual(m.activity?.count, 1); XCTAssertEqual(m.activity?.first?.status, "done"); XCTAssertEqual(m.activity?.first?.title, "Used your Mac")
        _ = ChatReducer.apply(try ev(#"{"tool":{"id":2,"name":"computer","status":"error","error":"You said no, so I stopped.","args":{"goal":"x","mode":"browser"}}}"#), to: &m)
        XCTAssertEqual(m.activity?.last?.status, "error"); XCTAssertEqual(m.activity?.last?.detail, "You said no, so I stopped.")
    }

    // MARK: takeover, display, trusted click
    func testTheAssistantsOwnEventsAreToldApartFromThePersonsAndASmallDriftIsIgnored() {
        XCTAssertTrue(TakeoverMath.isAssistantEvent(userData: TakeoverMath.marker))
        XCTAssertFalse(TakeoverMath.isAssistantEvent(userData: 0)); XCTAssertFalse(TakeoverMath.isAssistantEvent(userData: TakeoverMath.marker + 1))
        XCTAssertFalse(TakeoverMath.pointerMoved(expectedX: 100, expectedY: 100, actualX: 104, actualY: 103))        // 5 points: a jiggle of the trackpad is not a takeover
        XCTAssertTrue(TakeoverMath.pointerMoved(expectedX: 100, expectedY: 100, actualX: 130, actualY: 100))
        XCTAssertTrue(TakeoverMath.pointerMoved(expectedX: 100, expectedY: 100, actualX: 100, actualY: 60, tolerance: 12))
    }

    func testATakeoverTravelsInTheResultAndIsAbsentOtherwise() throws {
        let e = JSONEncoder(); e.keyEncodingStrategy = .convertToSnakeCase
        let stopped = String(data: try e.encode(ComputerResult(ok: true, takeover: true)), encoding: .utf8)!
        XCTAssertTrue(stopped.contains("\"takeover\":true"))
        XCTAssertFalse(String(data: try e.encode(ComputerResult(ok: true)), encoding: .utf8)!.contains("takeover"))
    }

    func testTheBridgeSendsTheChosenDisplayAndATrustedClickFlag() throws {
        let json = #"{"computer_request":{"id":"cr_1","kind":"act","mode":"desktop","display":"2","action":{"kind":"click","element":3,"trusted":true}}}"#
        let r = try XCTUnwrap(decoder().decode(ChatEvent.self, from: Data(json.utf8)).computerRequest)
        XCTAssertEqual(r.display, "2"); XCTAssertEqual(r.action?.trusted, true)
        let plain = try XCTUnwrap(decoder().decode(ChatEvent.self, from: Data(#"{"computer_request":{"id":"cr_2","kind":"observe","mode":"browser"}}"#.utf8)).computerRequest)
        XCTAssertNil(plain.display); XCTAssertNil(plain.action?.trusted)
    }
}
