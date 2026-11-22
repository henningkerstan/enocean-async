from enum import StrEnum


class SerialProtocol(StrEnum):
    """The serial protocol spoken by the EnOcean module connected to the gateway."""

    ESP2 = "esp2"
    """EnOcean Serial Protocol Version 2, e.g. Eltako FAM-USB."""

    ESP3 = "esp3"
    """EnOcean Serial Protocol Version 3, e.g. USB 300."""

    @property
    def default_baudrate(self) -> int:
        """The baudrate the protocol specifies for the serial connection."""
        return 9600 if self is SerialProtocol.ESP2 else 57600
