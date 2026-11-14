import SwiftUI
import AppKit
import ApplicationServices
import JarvisCore

/// Computer use: a local model plans, ArjunOS performs and checks each step. Every switch here is off or narrow by default.
struct ComputerSettingsPage: View {
    @Environment(AppModel.self) private var model
    @State private var accessibility = DesktopDriver.hasAccessibility
    @State private var screenRecording = DesktopDriver.hasScreenRecording
    @State private var cuaCommand = ""

    var body: some View {
        let s = model.settings
        let consented = s?.computerConsented ?? false
        SettingsPageScaffold(.computer) {
            SettingsGroup("Permission", footer: "A local model on this Mac plans the steps and ArjunOS carries them out. Nothing is sent anywhere. Screenshots and the text read from your screen stay on this Mac. You can stop a task at any time with the Stop button or ⌃⌥⎋.") {
                SettingToggleRow(title: "Let \(model.assistantName) operate the browser and apps", subtitle: "Off until you turn it on. Passwords, payment details and codes are never typed for you.",
                                 isOn: Binding(get: { consented }, set: { v in Task { await model.updateComputerSettings(consented: v) } }))
                    .disabled(s == nil)
            }
            SettingsGroup("What it may control", footer: "The browser mode is the safer one: it reads and clicks the page itself and needs no macOS permission. Desktop mode can click and type in any app except terminals, password managers and System Settings, and it asks before it uses each app for the first time.") {
                SettingToggleRow(title: "The built-in browser", subtitle: "Works on web pages in ArjunOS.",
                                 isOn: Binding(get: { s?.computerBrowserEnabled ?? true }, set: { v in Task { await model.updateComputerSettings(browser: v) } }))
                    .disabled(!consented)
                SettingRow("Browser profile", subtitle: (s?.computerBrowserProfile ?? "private") == "private" ? "A throwaway browser with none of your logins. Safest." : "Your own browser, including the sites you are signed in to.") {
                    DropdownPicker(options: [SettingOption(value: "private", title: "Private (recommended)"), SettingOption(value: "mine", title: "Mine (uses my logins)")],
                                   selection: Binding(get: { s?.computerBrowserProfile ?? "private" }, set: { v in Task { await model.updateComputerSettings(profile: v) } }))
                }.disabled(!consented)
                SettingToggleRow(title: "Other apps on this Mac", subtitle: "Needs macOS Accessibility permission. Screen Recording adds OCR for apps that expose little.",
                                 isOn: Binding(get: { s?.computerDesktopEnabled ?? false }, set: { v in Task { await model.updateComputerSettings(desktop: v) } }))
                    .disabled(!consented)
            }
            if consented && (s?.computerDesktopEnabled ?? false) {
                SettingsGroup("macOS permissions") {
                    SettingBlock { SettingStatus(text: accessibility ? "Accessibility: allowed" : "Accessibility: not allowed yet. Needed to read and click other apps.", kind: accessibility ? .good : .warning) }
                    if !accessibility {
                        SettingRow("Allow Accessibility", subtitle: "macOS shows its own prompt. If you rebuilt the app, remove ArjunOS from the list and add it again.") {
                            Button("Ask macOS") { DesktopDriver.promptAccessibility(); refreshSoon() }.buttonStyle(GlassButtonStyle(prominent: true))
                        }
                    }
                    SettingBlock { SettingStatus(text: screenRecording ? "Screen Recording: allowed (OCR and screenshots)" : "Screen Recording: not allowed. Optional: only used to read apps that expose little.", kind: screenRecording ? .good : .warning) }
                    if !screenRecording {
                        SettingRow("Allow Screen Recording", subtitle: "Optional.") { Button("Ask macOS") { _ = CGRequestScreenCaptureAccess(); refreshSoon() }.buttonStyle(GlassButtonStyle()) }
                    }
                    SettingRow("Open Privacy settings") {
                        Button("Open") { NSWorkspace.shared.open(URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy")!) }.buttonStyle(GlassButtonStyle())
                    }
                }
            }
            if consented && (s?.computerDesktopEnabled ?? false) {
                SettingsGroup("Desktop control", footer: "The built-in driver uses the real mouse, so you should leave the Mac alone while it works; it stops by itself if you touch the mouse or keyboard. The optional Cua Driver sends input to one window in the background, so you can keep working in another app. Install it from cua.ai, then choose it here. Cua Driver may send anonymous usage statistics of its own; ArjunOS starts it with that switched off, and you can turn it off for good with “cua-driver config telemetry disable”.") {
                    SettingRow("Driver", subtitle: (s?.computerDesktopBackend ?? "builtin") == "cua" ? "Cua Driver: background input. Needs its own macOS permissions." : "Built-in: Accessibility and the real mouse.") {
                        DropdownPicker(options: [SettingOption(value: "builtin", title: "Built-in"), SettingOption(value: "cua", title: "Cua Driver (optional)")],
                                       selection: Binding(get: { s?.computerDesktopBackend ?? "builtin" }, set: { v in Task { await model.updateComputerSettings(backend: v) } }))
                    }.disabled(!consented)
                    if (s?.computerDesktopBackend ?? "builtin") == "cua" {
                        SettingRow("Cua Driver program", subtitle: "A name on your PATH or a full path, for example /usr/local/bin/cua-driver.") {
                            TextField("cua-driver", text: $cuaCommand).glassField().frame(width: 280)
                                .onSubmit { Task { await model.updateComputerSettings(cuaCommand: cuaCommand) } }
                        }.disabled(!consented)
                    }
                    SettingRow("Screen to use", subtitle: "Which display it looks at and clicks on (built-in driver). “Where the pointer is” is picked fresh for each look.") {
                        DropdownPicker(options: [SettingOption(value: "main", title: "Main display"), SettingOption(value: "cursor", title: "Where the pointer is"),
                                                 SettingOption(value: "1", title: "Display 1 (main)"), SettingOption(value: "2", title: "Display 2"), SettingOption(value: "3", title: "Display 3")],
                                       selection: Binding(get: { s?.computerDisplay ?? "main" }, set: { v in Task { await model.updateComputerSettings(display: v) } }))
                    }.disabled(!consented)
                    SettingToggleRow(title: "Numbered boxes on screenshots", subtitle: "Helps small vision models point at the right control. Only numbers are drawn.",
                                     isOn: Binding(get: { s?.computerMarks ?? true }, set: { v in Task { await model.updateComputerSettings(marks: v) } }))
                        .disabled(!consented)
                }
            }
            SettingsGroup("Starting and approvals") {
                SettingToggleRow(title: "Start from a plain request", subtitle: "“Open Finder and find my Xcode projects” starts a task after you approve it. Questions never do.",
                                 isOn: Binding(get: { s?.computerAutoStart ?? true }, set: { v in Task { await model.updateComputerSettings(autoStart: v) } }))
                    .disabled(!consented)
                SettingRow("Ask before", subtitle: (s?.computerApproval ?? "risky") == "risky" ? "Purchases, sending, deleting, new sites, first use of each app, and anything on a page that tries to give orders." : "Every single step.") {
                    DropdownPicker(options: [SettingOption(value: "risky", title: "Consequential steps"), SettingOption(value: "every", title: "Every step")],
                                   selection: Binding(get: { s?.computerApproval ?? "risky" }, set: { v in Task { await model.updateComputerSettings(approval: v) } }))
                }.disabled(!consented)
                SettingRow("Most steps per task", subtitle: "A task stops here even if it is not finished.") {
                    NumberStepper(value: Binding(get: { s?.computerMaxSteps ?? 40 }, set: { v in Task { await model.updateComputerSettings(maxSteps: v) } }), range: 5...120, step: 5)
                }.disabled(!consented)
            }
        }
        .task { accessibility = DesktopDriver.hasAccessibility; screenRecording = DesktopDriver.hasScreenRecording; cuaCommand = model.settings?.computerCuaCommand ?? "cua-driver" }
    }

    private func refreshSoon() { Task { try? await Task.sleep(nanoseconds: 1_500_000_000); accessibility = DesktopDriver.hasAccessibility; screenRecording = DesktopDriver.hasScreenRecording } }
}
