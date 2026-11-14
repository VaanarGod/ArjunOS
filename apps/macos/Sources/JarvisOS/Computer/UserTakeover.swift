import AppKit
import JarvisCore

/// Notices when the person uses the mouse or keyboard while the assistant is driving the desktop, so the task can stop by itself.
///
/// Two signals: (1) a global event monitor sees every click, scroll and key press that goes to other apps; the assistant's own events are stamped with
/// `TakeoverMath.marker` (see `postAsAgent`), so anything unstamped was the person. (2) Between two actions the pointer must still be where the assistant
/// left it; a larger move is the person's hand. Events sent to ArjunOS itself (the Stop button, approval buttons) never reach a global monitor.
/// Needs the same Accessibility permission the desktop driver already has; macOS may also ask for Input Monitoring before it reports key presses.
@MainActor
final class UserTakeover {
    private var monitor: Any?
    private(set) var tripped = false
    private var busy = false
    private var expected: (x: Double, y: Double)?

    func start() {
        stop()
        expected = Self.pointer()
        let mask: NSEvent.EventTypeMask = [.leftMouseDown, .rightMouseDown, .otherMouseDown, .scrollWheel, .keyDown]
        monitor = NSEvent.addGlobalMonitorForEvents(matching: mask) { [weak self] event in
            let userData = event.cgEvent?.getIntegerValueField(.eventSourceUserData) ?? 0
            if TakeoverMath.isAssistantEvent(userData: userData) { return }
            Task { @MainActor in self?.tripped = true }
        }
    }

    func stop() {
        if let m = monitor { NSEvent.removeMonitor(m) }
        monitor = nil; tripped = false; busy = false; expected = nil
    }

    func assistantWillAct() { busy = true }

    /// Call after the request (and its settle time) is over. Only an action can have moved the pointer; for anything else the old reference stays,
    /// so a nudge during a plain screen read is still noticed.
    func assistantDidAct(movedPointer: Bool) { busy = false; if movedPointer { expected = Self.pointer() } }

    /// True when the person has taken over (an event, or a pointer that moved while the assistant was not acting).
    func personTookOver() -> Bool {
        if !tripped, !busy, let e = expected, let now = Self.pointer(),
           TakeoverMath.pointerMoved(expectedX: e.x, expectedY: e.y, actualX: now.x, actualY: now.y) { tripped = true }
        return tripped
    }

    private static func pointer() -> (x: Double, y: Double)? {
        guard let p = CGEvent(source: nil)?.location else { return nil }
        return (Double(p.x), Double(p.y))
    }
}

extension CGEvent {
    /// Posts an event the assistant made, stamped so `UserTakeover` can tell it from the person's.
    func postAsAgent() {
        setIntegerValueField(.eventSourceUserData, value: TakeoverMath.marker)
        post(tap: .cghidEventTap)
    }
}
