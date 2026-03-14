from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class ObserverFactory:
    """Wraps an observer constructor for use in ``EEPSpecification.observers``.

    Entity metadata (observables, actions) is now declared separately via
    ``EEPSpecification.entities`` rather than on the factory itself.
    """

    factory: Callable[[Any, Any], Any]
    """Callable that takes ``(device_address, on_state_change)`` and returns an Observer."""

    def __call__(self, device_address: Any, on_state_change: Any) -> Any:
        return self.factory(device_address, on_state_change)
