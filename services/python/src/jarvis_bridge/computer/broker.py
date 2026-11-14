"""The bridge -> app -> bridge round trip. The bridge asks (an event on the open chat stream), the app does the thing and answers with
one REST call. Request ids are unguessable and single-use; an answer for an id nobody is waiting for is refused."""
from __future__ import annotations
import asyncio, secrets
from typing import Callable


class BrokerError(Exception):
    pass


class UserTookOver(BrokerError):
    """The machine reported that the person used the mouse or keyboard while the agent was working. The whole task stops.
    Its message stays "stopped" so every place that already re-raises a stop treats it the same way."""
    def __init__(self): super().__init__("stopped")


class ComputerBroker:
    def __init__(self):
        self._pending: dict[str, asyncio.Future] = {}

    async def request(self, kind: str, payload: dict, emit: Callable[[dict], None], timeout: float = 60.0) -> dict:
        rid = "cr_" + secrets.token_hex(12)
        fut = asyncio.get_running_loop().create_future()
        self._pending[rid] = fut
        emit({"computer_request": {"id": rid, "kind": kind, **payload}})
        try:
            return await asyncio.wait_for(fut, timeout)
        except asyncio.TimeoutError:
            raise BrokerError("The app did not answer in time. Is ArjunOS open and in front of the task?") from None
        finally:
            self._pending.pop(rid, None)

    def resolve(self, rid: str, result: dict) -> bool:
        f = self._pending.get(rid)
        if f is None or f.done(): return False
        f.set_result(result)
        return True

    def cancel_all(self) -> int:
        n = 0
        for f in list(self._pending.values()):
            if not f.done(): f.set_exception(BrokerError("stopped")); n += 1
        return n

    @property
    def waiting(self) -> int:
        return len(self._pending)
