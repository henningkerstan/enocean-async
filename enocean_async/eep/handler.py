import logging
from typing import Any

from enocean_async.address import BroadcastAddress

from ..protocol.erp1.telegram import RORG, ERP1Telegram
from .message import EEPMessage, EEPMessageType, RawEEPMessage, ValueWithContext
from .profile import EEPSpecification


class EEPHandler:
    """An EEP handler is responsible for encoding and decoding messages for a specific EEP."""

    def __init__(self, eep: EEPSpecification):
        self.__eep = eep
        self.__logger = logging.getLogger(__name__)

    def decode(
        self, telegram: ERP1Telegram, config: dict[str, Any] | None = None
    ) -> EEPMessage:
        """Convert an ERP1Telegram into an EEPMessage."""

        msg = EEPMessage(
            sender=telegram.sender,
            eep=self.__eep.eep,
            rssi=telegram.rssi,
        )

        if telegram.destination is not None and not telegram.destination.is_broadcast():
            msg.destination = telegram.destination

        # determine the command/telegram type based on the EEP's cmd_size and cmd_offset, if applicable
        cmd_value = 0

        if self.__eep.cmd_size > 0 and self.__eep.cmd_offset is not None:
            offset = (
                self.__eep.cmd_offset
                if self.__eep.cmd_offset >= 0
                else len(telegram.telegram_data) * 8 + self.__eep.cmd_offset
            )

            cmd_value = telegram.bitstring_raw_value(
                offset=offset, size=self.__eep.cmd_size
            )

        if cmd_value not in self.__eep.telegrams:
            self.__logger.debug(
                f"Unknown telegram command 0x{cmd_value:02X} for EEP {self.__eep.eep}; ignoring telegram."
            )
            return msg

        msg.message_type = EEPMessageType(
            id=cmd_value,
            description=self.__eep.telegrams[cmd_value].name
            if self.__eep.telegrams[cmd_value].name
            else f"Telegram {cmd_value}",
        )

        # First pass: collect all raw values
        for field in self.__eep.telegrams[cmd_value].datafields:
            msg.raw[field.id] = telegram.bitstring_raw_value(
                offset=field.offset, size=field.size
            )

        # Second pass: decode scaled values with context (for field interdependencies)
        for field in self.__eep.telegrams[cmd_value].datafields:
            raw_value = msg.raw[field.id]
            value = None

            if field.range_enum is not None:
                value = field.range_enum.get(raw_value, f"Unknown({raw_value})")
            elif field.range_min is not None and field.range_max is not None:
                value = telegram.bitstring_scaled_value(
                    offset=field.offset,
                    size=field.size,
                    range_min=field.range_min,
                    range_max=field.range_max,
                    scale_min=field.scale_min_fn(msg.raw),
                    scale_max=field.scale_max_fn(msg.raw),
                )
            else:
                value = raw_value

            unit = field.unit_fn(msg.raw) or None  # "" treated as None (no unit)
            msg.decoded[field.id] = ValueWithContext(
                name=field.name or field.id, value=value, unit=unit
            )

        # Third pass: entity observable propagation — copy scaled values to semantic entity keys
        for field in self.__eep.telegrams[cmd_value].datafields:
            if field.observable is not None and field.id in msg.decoded:
                msg.values[field.observable] = msg.decoded[field.id]

        # Fourth pass: semantic resolvers — combine multiple fields into a single entity value
        cfg = config or {}
        for observable, resolver in self.__eep.semantic_resolvers.items():
            result = resolver(msg.raw, msg.decoded, cfg)
            if result is not None:
                msg.values[observable] = result

        return msg

    def encode(self, message: RawEEPMessage) -> ERP1Telegram:
        """Convert a RawEEPMessage into an ERP1Telegram.

        The message must have:
        - message.sender set to a valid sender address (BaseAddress or EURID) for the gateway
        - message.message_type.id set to the telegram command value (0 for single-telegram EEPs)
        - message.raw_values[field_id] = <int> for each field to encode

        Raises:
            ValueError: if message.sender is None or the telegram type is unknown.
        """
        if message.sender is None:
            raise ValueError("message.sender must be set before encoding")

        cmd_value = message.message_type.id if message.message_type else 0

        if cmd_value not in self.__eep.telegrams:
            raise ValueError(
                f"Unknown telegram type {cmd_value} for EEP {self.__eep.eep}"
            )

        telegram_def = self.__eep.telegrams[cmd_value]
        datafields = telegram_def.datafields
        buffer_size = telegram_def.byte_size

        rorg = RORG(self.__eep.eep.rorg)
        erp1 = ERP1Telegram(
            rorg=rorg,
            telegram_data=bytes(buffer_size),
            sender=message.sender,
            destination=message.destination,
        )

        # Write each field's raw value
        for f in datafields:
            raw = message.raw.get(f.id)
            if raw is None:
                self.__logger.debug(
                    f"encode: field '{f.id}' not provided for EEP {self.__eep.eep}; defaulting to 0."
                )
                raw = 0
            erp1.set_bitstring_raw_value(offset=f.offset, size=f.size, value=raw)

        # Write CMD bits last so they are never overwritten by the field loop
        # (the CMD field may also appear in datafields for decoding purposes).
        if self.__eep.cmd_size > 0 and self.__eep.cmd_offset is not None:
            cmd_bit_offset = (
                self.__eep.cmd_offset
                if self.__eep.cmd_offset >= 0
                else buffer_size * 8 + self.__eep.cmd_offset
            )
            erp1.set_bitstring_raw_value(
                offset=cmd_bit_offset, size=self.__eep.cmd_size, value=cmd_value
            )

        return erp1

    def __call__(
        self, telegram: ERP1Telegram, config: dict[str, Any] | None = None
    ) -> EEPMessage:
        """Allow decoder instances to be called like functions."""
        return self.decode(telegram, config)
