"""NotifierAdapter interface + implementations (Task 20).

Isolates the dispatch *channel* from the EmergencyService. The MVP ships only
`SimulatedNotifier`, which records/returns the dispatch WITHOUT contacting any
real recipient (Req 11.6). Real channels are interface-only stubs that require
explicit opt-in config + consent before they could ever be implemented.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..db.care_models import Provider


@dataclass(slots=True)
class DispatchResult:
    delivered: bool
    channel: str
    detail: str


class NotifierAdapter(Protocol):
    def send(self, recipient: Provider, payload: dict) -> DispatchResult: ...


class SimulatedNotifier:
    """Default MVP notifier. Never contacts a real recipient; just reports success."""

    channel = "simulated"

    def send(self, recipient: Provider, payload: dict) -> DispatchResult:
        return DispatchResult(
            delivered=True,
            channel=self.channel,
            detail=(
                f"SIMULATED: would notify {recipient.kind} '{recipient.name}' "
                f"({recipient.phone or 'no phone'}). No real message was sent."
            ),
        )


class SmsNotifierAdapter:  # pragma: no cover - interface-only, future
    """Future: send an SMS. Requires opt-in config + consent + a provider integration."""

    channel = "real"

    def send(self, recipient: Provider, payload: dict) -> DispatchResult:
        raise NotImplementedError("SmsNotifierAdapter is not implemented in the MVP.")


class VoiceCallNotifierAdapter:  # pragma: no cover - interface-only, future
    """Future: place a voice call. Requires opt-in config + consent."""

    channel = "real"

    def send(self, recipient: Provider, payload: dict) -> DispatchResult:
        raise NotImplementedError("VoiceCallNotifierAdapter is not implemented in the MVP.")
