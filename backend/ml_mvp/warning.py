"""Process-local CLI warning/countdown state machine; never dispatches."""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class WarningEvent:
    status: str
    created_at_seconds: float
    deadline_seconds: float
    resolved_at_seconds: float | None = None
    escalation_channel: str | None = None


class CliWarningMachine:
    """A deliberately non-production state machine with simulated-only expiry."""

    def __init__(self, countdown_seconds: float) -> None:
        if countdown_seconds <= 0:
            raise ValueError("countdown_seconds must be positive")
        self.countdown_seconds = float(countdown_seconds)
        self.event: WarningEvent | None = None
        self.simulated_escalations = 0

    def raise_warning(self, now_seconds: float) -> WarningEvent:
        if self.event is None:
            self.event = WarningEvent(
                status="active",
                created_at_seconds=float(now_seconds),
                deadline_seconds=float(now_seconds) + self.countdown_seconds,
            )
        return self.event

    def cancel(self, now_seconds: float) -> tuple[WarningEvent, bool]:
        if self.event is None:
            raise RuntimeError("no warning exists")
        if self.event.status == "cancelled_by_user":
            return self.event, False
        if self.event.status != "active":
            raise RuntimeError(f"cannot cancel warning in state {self.event.status}")
        self.event = replace(self.event, status="cancelled_by_user", resolved_at_seconds=float(now_seconds))
        return self.event, True

    def expire(self, now_seconds: float) -> tuple[WarningEvent | None, str | None]:
        if self.event is None or self.event.status != "active" or now_seconds < self.event.deadline_seconds:
            return self.event, None
        self.event = replace(
            self.event,
            status="escalated",
            resolved_at_seconds=float(now_seconds),
            escalation_channel="simulated_cli_only",
        )
        self.simulated_escalations += 1
        return self.event, "SIMULATED escalation — no dispatch, request, or notification was sent"
