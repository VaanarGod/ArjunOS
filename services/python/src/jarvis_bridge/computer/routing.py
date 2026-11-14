"""Chooses who answers the runner's questions about the desktop: the app's own driver (the default) or the optional Cua Driver.
Browser requests always go to the app. The runner talks to this object exactly as it talks to ComputerBroker."""
from __future__ import annotations
from .broker import BrokerError, ComputerBroker
from .cua import CuaConnection


class RoutingBroker:
    def __init__(self, app: ComputerBroker, cua: CuaConnection, settings):
        self.app, self.cua, self.settings = app, cua, settings
        self._backend = None

    def uses_cua(self, mode: str | None) -> bool:
        return mode == "desktop" and self.settings.value.computer_desktop_backend == "cua"

    async def request(self, kind: str, payload: dict, emit, timeout: float = 60.0) -> dict:
        if not self.uses_cua(payload.get("mode")): return await self.app.request(kind, payload, emit, timeout)
        try: self._backend = await self.cua.get()
        except BrokerError: raise
        return await self._backend.request(kind, payload, emit, timeout)

    def resolve(self, rid: str, result: dict) -> bool: return self.app.resolve(rid, result)

    def cancel_all(self) -> int:
        n = self.app.cancel_all()
        if self._backend is not None: n += self._backend.cancel_all()
        return n

    @property
    def waiting(self) -> int: return self.app.waiting

    async def end(self, mode: str):
        if self.uses_cua(mode) and self._backend is not None: await self._backend.end()
