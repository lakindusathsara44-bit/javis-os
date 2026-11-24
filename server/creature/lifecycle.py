"""Explicit lifecycle state machine; no background work is started here."""
from __future__ import annotations

from .models import CreatureState


_ALLOWED: dict[CreatureState, frozenset[CreatureState]] = {
    CreatureState.DORMANT: frozenset({CreatureState.INITIALIZING, CreatureState.STOPPED}),
    CreatureState.INITIALIZING: frozenset({CreatureState.ACTIVE, CreatureState.ERROR, CreatureState.STOPPED}),
    CreatureState.ACTIVE: frozenset({CreatureState.PAUSED, CreatureState.ERROR, CreatureState.STOPPED}),
    CreatureState.PAUSED: frozenset({CreatureState.ACTIVE, CreatureState.ERROR, CreatureState.STOPPED}),
    CreatureState.ERROR: frozenset({CreatureState.DORMANT, CreatureState.STOPPED}),
    CreatureState.STOPPED: frozenset(),
}


class CreatureLifecycle:
    def __init__(self) -> None:
        self._state = CreatureState.DORMANT

    @property
    def state(self) -> CreatureState:
        return self._state

    def transition(self, target: CreatureState) -> CreatureState:
        if not isinstance(target, CreatureState):
            raise TypeError("target must be a CreatureState")
        if target not in _ALLOWED[self._state]:
            raise ValueError(f"invalid lifecycle transition: {self._state.value} -> {target.value}")
        self._state = target
        return self._state

    def start(self) -> CreatureState:
        self.transition(CreatureState.INITIALIZING)
        return self.transition(CreatureState.ACTIVE)

    def pause(self) -> CreatureState:
        return self.transition(CreatureState.PAUSED)

    def resume(self) -> CreatureState:
        return self.transition(CreatureState.ACTIVE)

    def stop(self) -> CreatureState:
        return self.transition(CreatureState.STOPPED)

    def fail(self) -> CreatureState:
        return self.transition(CreatureState.ERROR)
