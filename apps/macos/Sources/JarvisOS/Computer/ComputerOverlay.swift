import SwiftUI
import AppKit
import JarvisCore

/// While the assistant controls your Mac: a thin orange frame (four edge strips, never a screen-sized window), a Stop banner, and, when a step
/// needs your approval, a small panel with Deny / Approve right here, because ArjunOS's own window may be behind the app being operated.
/// Control-Option-Escape also stops it from anywhere. These windows belong to ArjunOS, so they never appear in the assistant's own screenshots,
/// and the assistant's clicks are refused inside them.
@MainActor
final class ComputerOverlay {
    private var banner: NSPanel?
    private var strips: [NSPanel] = []
    private var approvalPanel: NSPanel?
    private var shownApproval: String?
    private let hotKey = GlobalHotKey(id: 2)
    var onStop: (() -> Void)?

    func show(_ text: String) {
        guard banner == nil, let screen = NSScreen.main else { return }
        let f = screen.frame, t: CGFloat = 4
        for r in [CGRect(x: f.minX, y: f.maxY - t, width: f.width, height: t), CGRect(x: f.minX, y: f.minY, width: f.width, height: t),
                  CGRect(x: f.minX, y: f.minY, width: t, height: f.height), CGRect(x: f.maxX - t, y: f.minY, width: t, height: f.height)] {
            strips.append(panel(frame: r, ignoresMouse: true, content: Color.orange))
        }
        let size = CGSize(width: 520, height: 46)
        banner = panel(frame: CGRect(x: f.midX - size.width / 2, y: f.minY + 22, width: size.width, height: size.height),    // bottom centre: the top of the screen is where address bars and toolbars are
                       ignoresMouse: false, content: BannerView(text: text) { [weak self] in self?.onStop?() })
        hotKey.onPress = { [weak self] in self?.onStop?() }
        hotKey.register(HotKeyCombo(keyCode: 53, modifiers: [.control, .option]))      // 53 = Escape
    }

    func hide() {
        hotKey.unregister()
        hideApproval()
        banner?.orderOut(nil); strips.forEach { $0.orderOut(nil) }; banner = nil; strips = []
    }

    /// One consequential step is waiting. Shown above every app; clicking it does not take focus away from the app being operated.
    func showApproval(id: String, headline: String, what: String, where place: String, why: String, decide: @escaping (Bool) -> Void) {
        guard shownApproval != id, let screen = NSScreen.main else { return }
        hideApproval()
        shownApproval = id
        let size = CGSize(width: 520, height: why.isEmpty ? 150 : 176)
        let f = screen.frame
        approvalPanel = panel(frame: CGRect(x: f.midX - size.width / 2, y: f.minY + 22 + 46 + 10, width: size.width, height: size.height), ignoresMouse: false,
                              content: ApprovalView(headline: headline, what: what, place: place, why: why, decide: decide))
    }

    func hideApproval() { approvalPanel?.orderOut(nil); approvalPanel = nil; shownApproval = nil }

    private func panel<V: View>(frame: CGRect, ignoresMouse: Bool, content: V) -> NSPanel {
        let p = NSPanel(contentRect: frame, styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
        p.level = .statusBar; p.isOpaque = false; p.backgroundColor = .clear; p.hasShadow = false
        p.ignoresMouseEvents = ignoresMouse; p.hidesOnDeactivate = false; p.isReleasedWhenClosed = false; p.becomesKeyOnlyIfNeeded = true
        p.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .stationary, .ignoresCycle]
        p.contentView = NSHostingView(rootView: content)
        p.setFrame(frame, display: true); p.orderFrontRegardless()
        return p
    }

    private struct BannerView: View {
        let text: String; let stop: () -> Void
        var body: some View {
            HStack(spacing: 10) {
                Image(systemName: "cursorarrow.rays").foregroundStyle(.orange)
                Text(text).font(.callout.weight(.medium)).lineLimit(1)
                Spacer(minLength: 6)
                Text("⌃⌥⎋").font(.caption.monospaced()).foregroundStyle(.secondary)
                Button("Stop", action: stop).buttonStyle(.borderedProminent).tint(.red).controlSize(.small)
            }
            .padding(.horizontal, 14).frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(.regularMaterial, in: Capsule()).overlay(Capsule().strokeBorder(Color.orange.opacity(0.7), lineWidth: 1.5))
        }
    }

    private struct ApprovalView: View {
        let headline: String, what: String, place: String, why: String; let decide: (Bool) -> Void
        var body: some View {
            VStack(alignment: .leading, spacing: 8) {
                Text(headline).font(.callout.weight(.semibold))
                Text(what).font(.system(size: 13, weight: .semibold)).lineLimit(3).frame(maxWidth: .infinity, alignment: .leading)
                if !place.isEmpty { Text("In: \(place)").font(.caption).foregroundStyle(.secondary).lineLimit(1) }
                if !why.isEmpty { Text("Why I am asking: \(why)").font(.caption).foregroundStyle(.secondary).lineLimit(2) }
                HStack {
                    Spacer()
                    Button("Deny") { decide(false) }.controlSize(.regular)
                    Button("Approve once") { decide(true) }.buttonStyle(.borderedProminent).controlSize(.regular).keyboardShortcut(.defaultAction)
                }
            }
            .padding(14).frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 16, style: .continuous).strokeBorder(Color.orange.opacity(0.7), lineWidth: 1.5))
        }
    }
}
