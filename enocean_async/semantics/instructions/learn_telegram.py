"""Learn telegram command for sender-addressed Eltako devices."""

from dataclasses import dataclass
from typing import ClassVar

from ..instructable import Instructable
from ..instruction import Instruction


@dataclass
class LearnTelegram(Instruction):
    """Send the learn telegram to a sender-addressed device.

    Can be issued at any time after the device has been registered —
    at initial commissioning, after a device hardware reset, or whenever
    the sender slot needs to be re-taught.

    The gateway bypasses the normal encoder path and sends the fixed
    ``learn_telegram_payload`` bytes from the EEP specification directly as a
    4BS ERP1 telegram with the device's registered sender address.
    """

    action: ClassVar[Instructable] = Instructable.LEARN_TELEGRAM
