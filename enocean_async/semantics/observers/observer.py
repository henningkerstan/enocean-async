from __future__ import annotations

from abc import ABC
import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from ...address import Address
from ..observation import Observation, ObservationCallback

if TYPE_CHECKING:
    from ...eep.message import EEPMessage


@dataclass
class Observer(ABC):
    """An observer represents a specific functionality of a device, such as a button, a temperature sensor, or a motion detector.
    It is responsible for decoding EEP messages related to that functionality and emitting observations accordingly."""

    device_address: Address
    on_observation: Optional[ObservationCallback] = None

    def decode(self, message: EEPMessage) -> None:
        """Decode the given EEPMessage according to this observer's logic.

        Only processes messages from the bound device.
        Emits observations via the on_observation callback.
        """
        if message.sender != self.device_address:
            return

        self._decode_impl(message)

    def _decode_impl(self, message: EEPMessage) -> None:
        """Implementation of decode logic. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement the _decode_impl method.")

    def _emit(self, observation: Observation) -> None:
        """Emit an observation via callback, scheduled on the running event loop."""
        if self.on_observation:
            asyncio.get_running_loop().call_soon(self.on_observation, observation)
