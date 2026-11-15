"""Asynchronous EnOcean Serial Protocol Version 2 (ESP2) implementation."""

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...gateway import Gateway

import serialx

from .packet import PACKET_LENGTH, SYNC_BYTES, ESP2HeaderSequence, ESP2Packet


class EnOceanSerialProtocol2(asyncio.Protocol):
    """
    Minimal asynchronous EnOcean Serial Protocol Version 2 (ESP2).
    - Parses ESP2 frames
    - Translates received radio telegrams into ESP3 RADIO_ERP1 packets and emits them, so the
      gateway processes them exactly like packets coming from an ESP3 module
    """

    def __init__(self, gateway: "Gateway"):
        self.__buffer = bytearray()
        self.__gateway: "Gateway" = gateway
        self.__logger = logging.getLogger(__name__)

    def connection_made(self, transport: serialx.SerialTransport) -> None:
        self.__gateway.connection_made()

    def data_received(self, data: bytes) -> None:
        """Process the internal buffer to extract complete ESP2 packets and emit them."""
        self.__buffer.extend(data)

        while True:
            # find sync bytes
            sync_index = self.__buffer.find(SYNC_BYTES)
            if sync_index < 0:
                # keep a trailing first sync byte; its second half may arrive with the next chunk
                keep = 1 if self.__buffer.endswith(SYNC_BYTES[:1]) else 0
                del self.__buffer[: len(self.__buffer) - keep]
                return

            # drop garbage before sync
            if sync_index > 0:
                del self.__buffer[:sync_index]

            if len(self.__buffer) < PACKET_LENGTH:
                return

            try:
                packet = ESP2Packet.from_bytes(bytes(self.__buffer[:PACKET_LENGTH]))
            except ValueError as e:
                self.__logger.debug(f"Invalid ESP2 packet ({e}); skipping byte.")
                del self.__buffer[:1]
                continue

            # Remove processed bytes
            del self.__buffer[:PACKET_LENGTH]

            self.__process_packet(packet)

    def __process_packet(self, packet: ESP2Packet) -> None:
        """Hand a received radio telegram to the gateway as ESP3 RADIO_ERP1 packet."""
        if packet.header_sequence != ESP2HeaderSequence.RRT:
            self.__logger.debug(
                f"Received ESP2 packet which is not a received radio telegram; ignoring packet: {packet}"
            )
            return

        try:
            self.__gateway.process_esp3_packet(packet.to_esp3())
        except Exception as e:
            self.__logger.debug(
                f"Failed to process ESP2 packet {packet}: {e}",
                exc_info=True,
            )

    def connection_lost(self, exception: Exception | None) -> None:
        self.__gateway.connection_lost(exception)

    def eof_received(self) -> bool | None:
        pass
