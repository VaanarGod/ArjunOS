import SwiftUI
import JarvisCore

/// The composer's Computer switch: while it is on, the next messages are carried out on the browser or the desktop instead of just answered.
struct ComputerMenu: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        let s = model.settings
        let ready = s?.computerConsented ?? false
        Menu {
            if !ready {
                Button("Set up computer use…") { model.settingsSection = .computer; model.selection = .settings }
            } else {
                Button { model.computerMode = nil } label: { Label("Chat only", systemImage: model.computerMode == nil ? "checkmark" : "bubble.left") }
                if (s?.computerBrowserEnabled ?? true) && (s?.computerDesktopEnabled ?? false) {
                    Button { model.computerMode = "auto" } label: { Label("Auto (browser or my Mac)", systemImage: model.computerMode == "auto" ? "checkmark" : "wand.and.sparkles") }
                }
                if s?.computerBrowserEnabled ?? true {
                    Button { model.computerMode = "browser" } label: { Label("Operate the browser", systemImage: model.computerMode == "browser" ? "checkmark" : "globe") }
                }
                if s?.computerDesktopEnabled ?? false {
                    Button { model.computerMode = "desktop" } label: { Label("Operate my Mac", systemImage: model.computerMode == "desktop" ? "checkmark" : "desktopcomputer") }
                }
                Divider()
                Button("Computer settings…") { model.settingsSection = .computer; model.selection = .settings }
            }
        } label: {
            Label(title, systemImage: "cursorarrow.rays").font(.callout)
                .foregroundStyle(model.computerMode == nil ? Color.secondary : Color.orange)
        }
        .menuStyle(.borderlessButton).menuIndicator(.hidden).fixedSize()
        .help(model.computerMode == nil ? "Let the assistant operate the browser or your Mac for this chat" : "Messages are carried out on the computer (\(model.computerMode ?? "")). Click to change.")
    }

    private var title: String {
        switch model.computerMode { case "browser": "Browser"; case "desktop": "Mac"; case "auto": "Auto"; default: "Computer" }
    }
}
