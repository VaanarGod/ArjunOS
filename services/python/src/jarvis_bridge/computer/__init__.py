"""Computer use: a vision model that operates the built-in browser or the desktop, one checked step at a time.

The bridge owns the thinking, the rules and the approvals. The macOS app owns the hands and eyes (screenshots, clicks, typing),
because only the app holds the Screen Recording / Accessibility permissions and the browser views. They talk over the existing
chat event stream (bridge -> app: `computer_request`) and one REST call (app -> bridge: `/v1/computer/requests/{id}/result`).
"""
