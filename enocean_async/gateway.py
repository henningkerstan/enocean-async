import asyncio
from dataclasses import dataclass
import logging
import time
from typing import Callable, Optional

import serial_asyncio_fast as serial_asyncio

from .address import EURID, BaseAddress, SenderAddress
from .device import Device
from .eep import EEP_SPECIFICATIONS, device_type_for_eep
from .eep.device_type import DeviceType
from .eep.handler import EEPHandler
from .eep.id import EEP
from .eep.message import EEPMessage
from .protocol.erp1.fourbs import (
    FourBSLearnStatus,
    FourBSLearnType,
    FourBSTeachInResult,
    FourBSTeachInTelegram,
)
from .protocol.erp1.telegram import RORG, ERP1Telegram
from .protocol.erp1.ute import (
    EEPTeachInResponseMessageExpectation,
    UTEMessage,
    UTEQueryRequestType,
    UTEResponseType,
)
from .protocol.esp3.common_command import CommonCommandTelegram
from .protocol.esp3.packet import ESP3Packet, ESP3PacketType
from .protocol.esp3.protocol import EnOceanSerialProtocol3
from .protocol.esp3.response import ResponseCode, ResponseTelegram
from .protocol.version import VersionIdentifier, VersionInfo
from .semantics.device_spec import DeviceSpec
from .semantics.entity import Entity, EntityCategory
from .semantics.instruction import Instruction
from .semantics.observable import Observable
from .semantics.observation import Observation, ObservationCallback, ObservationSource
from .semantics.observers.metadata import MetaDataObserver

type RSSI = int

_METADATA_ENTITIES = [
    Entity(
        id="rssi",
        observables=frozenset({Observable.RSSI}),
        category=EntityCategory.DIAGNOSTIC,
    ),
    Entity(
        id="last_seen",
        observables=frozenset({Observable.LAST_SEEN}),
        category=EntityCategory.DIAGNOSTIC,
    ),
    Entity(
        id="telegram_count",
        observables=frozenset({Observable.TELEGRAM_COUNT}),
        category=EntityCategory.DIAGNOSTIC,
    ),
]

_GATEWAY_ENTITIES: list[Entity] = [
    Entity(
        id="connection_status",
        observables=frozenset({Observable.CONNECTION_STATUS}),
    ),
    Entity(
        id="telegrams_received",
        observables=frozenset({Observable.TELEGRAMS_RECEIVED}),
        category=EntityCategory.DIAGNOSTIC,
    ),
    Entity(
        id="telegrams_sent",
        observables=frozenset({Observable.TELEGRAMS_SENT}),
        category=EntityCategory.DIAGNOSTIC,
    ),
]


@dataclass
class SendResult:
    response: Optional[ResponseTelegram]
    duration_ms: Optional[float]


# callback types
type ESP3Callback = Callable[[ESP3Packet], None]
type ERP1Callback = Callable[[ERP1Telegram], None]
type EEPMessageCallback = Callable[[EEPMessage], None]
type UTECallback = Callable[[UTEMessage], None]
type ResponseCallback = Callable[[ResponseTelegram], None]
type NewDeviceCallback = Callable[[EURID], None]
type ParsingFailedCallback = Callable[[str], None]
type TeachInCallback = Callable[[FourBSTeachInTelegram], None]


type DeviceTaughtInCallback = Callable[[EURID, EEP], None]


@dataclass
class CallbackWithFilter:
    callback: Callable
    sender_filter: SenderAddress | None = None


@dataclass
class ERP1CallbackWithFilter(CallbackWithFilter):
    callback: ERP1Callback


@dataclass
class EEPCallbackWithFilter(CallbackWithFilter):
    callback: EEPMessageCallback


class BaseIDChangeError(Exception):
    pass


class Gateway:
    """EnOcean gateway that connects to a serial port and processes incoming ESP3 packets."""

    def __init__(self, port: str, baudrate: int = 57600):
        """Create an instance of an EnOcean gateway that connects to the supplied port at supplied baudrate (optional) and processes incoming ESP3 packets."""

        # serial connection, transport and protocol parameters
        self.__port: str = port
        self.__baudrate: int = baudrate
        self.__transport: serial_asyncio.SerialTransport | None = None
        self.__protocol: EnOceanSerialProtocol3 | None = None

        # cached information about the connected module (to avoid unnecessary requests for information that doesn't change)
        self.__version_info: VersionInfo | None = None
        self.__base_id_remaining_write_cycles: int | None = None
        self.__base_id: BaseAddress | None = None

        # device and EEP management
        self.__known_senders: list[SenderAddress] = []
        self.__eep_handlers: dict[EEP, EEPHandler] = {}
        self.__devices: dict[EURID, Device] = {}
        self.__observation_callbacks: list[ObservationCallback] = []

        # callbacks
        self.__esp3_receive_callbacks: list[ESP3Callback] = []
        self.__erp1_receive_callbacks: list[ERP1CallbackWithFilter] = []
        self.__ute_receive_callbacks: list[UTECallback] = []
        self.__eep_receive_callbacks: list[EEPCallbackWithFilter] = []
        self.__parsing_failed_callbacks: list[ParsingFailedCallback] = []
        self.__response_callbacks: list[ResponseCallback] = []

        self.__new_device_callbacks: list[NewDeviceCallback] = []
        self.__device_taught_in_callbacks: list[DeviceTaughtInCallback] = []

        self.__esp3_send_callbacks: list[ESP3Callback] = []

        # send handling
        self.__send_lock: asyncio.Lock = asyncio.Lock()
        self.__send_future: asyncio.Future | None = None

        # learning
        self.__is_learning: bool = False
        self.__learning_timeout_task: asyncio.Task | None = None
        self.__sender_id_for_learning: SenderAddress | None = None
        self.__allow_teach_out: bool = False

        # logging
        self._logger = logging.getLogger(__name__)

        # gateway device counters (ERP1 only; not reset on reconnect)
        self.__erp1_received: int = 0
        self.__erp1_sent: int = 0
        self.__connection_status: str = "disconnected"

        # auto-reconnect
        self.__reconnect_task: asyncio.Task | None = None
        self.__stopped: bool = False

        # background tasks (teach-in response sends); tracked for clean cancellation on stop()
        self.__background_tasks: set[asyncio.Task] = set()

        self.auto_reconnect: bool = True
        """If True (default), automatically attempt to reconnect when the connection is lost. Set to False to disable reconnection entirely."""

    # ------------------------------------------------------------------
    # callback registration
    # ------------------------------------------------------------------
    def add_esp3_received_callback(self, cb: ESP3Callback):
        """Add a callback that will be called for every received ESP3 packet.

        This is a low-level callback that will be called for every ESP3 packet as they are received from the serial port, before any parsing or processing. This can be useful for debugging or for implementing custom processing of ESP3 packets that is not covered by the built-in functionality of the Gateway class."""
        self.__esp3_receive_callbacks.append(cb)

    def add_esp3_send_callback(self, cb: ESP3Callback):
        """Add a callback that will be called for every ESP3 packet that is sent to the EnOcean module.

        This can be useful for debugging or for implementing custom logging of sent packets."""
        self.__esp3_send_callbacks.append(cb)

    def add_device_taught_in_callback(self, cb: DeviceTaughtInCallback) -> None:
        """Add a callback fired after a device is successfully taught in and auto-registered.

        The callback receives a ``TaughtInDevice`` (fields: ``address``, ``eep``).
        It fires for UTE and 4BS-with-profile teach-ins that carry a complete EEP.
        """
        self.__device_taught_in_callbacks.append(cb)

    def add_new_device_callback(self, cb: NewDeviceCallback):
        """Add a callback that will be called for every newly detected EURID from incoming ERP1 telegrams.

        BaseAddress senders (other controllers/gateways) are silently tracked but do not trigger this callback.
        This can be useful for implementing custom handling of new devices."""
        self.__new_device_callbacks.append(cb)

    def add_erp1_received_callback(
        self, cb: ERP1Callback, sender_filter: SenderAddress | None = None
    ):
        """Add a callback that will be called for every received ERP1 telegram. If sender_filter is provided, the callback will only be called for telegrams that have a sender address matching the filter.

        This is a semi-high-level callback that will be called for every received ERP1 telegram after parsing and basic processing, but before any EEP-specific decoding. This can be useful for handling ERP1 telegrams in a custom way, for example by implementing custom decoding for specific RORGs or by handling telegrams from unknown devices."""
        self.__erp1_receive_callbacks.append(ERP1CallbackWithFilter(cb, sender_filter))

    def add_eep_message_received_callback(
        self, cb: EEPMessageCallback, sender_filter: SenderAddress | None = None
    ):
        """Add a callback that will be called for every received ERP1 telegram that could successfully be decoded as an EEP message. If sender_filter is provided, the callback will only be called for messages that have a sender address matching the filter.

        This is a high-level callback that will be called for every received EEP message after parsing, basic processing, and EEP-specific decoding. Prerequisite for this callback to be called for a message are:
        - the sender address of the message is known (by adding it to this gateway as known-device along with its eep), and
        - there is an EEPHandler capable of handling the eep of the sender device."""
        self.__eep_receive_callbacks.append(EEPCallbackWithFilter(cb, sender_filter))

    def add_ute_received_callback(self, cb: UTECallback):
        self.__ute_receive_callbacks.append(cb)

    def add_parsing_failed_callback(self, cb: ParsingFailedCallback):
        self.__parsing_failed_callbacks.append(cb)

    def add_response_callback(self, cb: ResponseCallback):
        self.__response_callbacks.append(cb)

    def add_observation_callback(self, cb: ObservationCallback) -> None:
        """Add a callback that is called for every Observation emitted by a device observer.

        The current gateway connection status is replayed immediately to the new subscriber
        (if the base ID is already known), so callers do not need to register before
        ``start()`` to receive the initial state.
        """
        self.__observation_callbacks.append(cb)
        if self.__version_info is not None:
            try:
                loop = asyncio.get_running_loop()
                loop.call_soon(
                    cb,
                    Observation(
                        device=self.__version_info.eurid,
                        entity="connection_status",
                        values={Observable.CONNECTION_STATUS: self.__connection_status},
                        timestamp=time.time(),
                        source=ObservationSource.GATEWAY,
                    ),
                )
            except RuntimeError:
                pass  # no running event loop; next status change will deliver the state

    # ------------------------------------------------------------------
    # start and stop
    # ------------------------------------------------------------------
    async def start(self, auto_reconnect: bool = True) -> None:
        """Open the serial connection to the EnOcean module and start processing incoming packets.

        Args:
            auto_reconnect: If True (default), automatically attempt to reconnect when the
                            connection is lost. Set to False to disable reconnection entirely.
        """
        self.__stopped = False
        self.auto_reconnect = auto_reconnect
        loop = asyncio.get_running_loop()
        try:
            (
                self.__transport,
                self.__protocol,
            ) = await serial_asyncio.create_serial_connection(
                loop,
                lambda: EnOceanSerialProtocol3(self),
                self.__port,
                baudrate=self.__baudrate,
            )

            self._logger.info(
                f"Successfully connected to EnOcean module on {self.__port} at baudrate {self.__baudrate}"
            )
            await (
                self.fetch_base_id()
            )  # ensure __base_id is populated so gateway observations can be emitted
            await self.fetch_version_info()  # ensure __version_info is populated so gateway observations can be emitted
            self.__emit_gateway_observation(
                "connection_status", Observable.CONNECTION_STATUS, "connected"
            )
        except Exception as e:
            self._logger.error(
                f"Failed to connect to EnOcean module on {self.__port} at baudrate {self.__baudrate}: {e}"
            )
            raise ConnectionError(
                f"Failed to connect to EnOcean module on {self.__port} at baudrate {self.__baudrate}: {e}"
            )

    def stop(self) -> None:
        """Close the serial connection to the EnOcean module."""
        self.__stopped = True
        if self.__reconnect_task is not None:
            self.__reconnect_task.cancel()
            self.__reconnect_task = None
        for task in self.__background_tasks:
            task.cancel()
        self.__background_tasks.clear()
        if self.__transport is not None:
            self.__transport.close()
            self.__transport = None
            self._logger.info(
                f"Serial connection to EnOcean module on {self.__port} closed"
            )

    def is_valid_sender(self, sender: SenderAddress) -> bool:
        """Return ``True`` if *sender* is a valid sender for this gateway.

        Valid senders are the gateway's EURID and any ``BaseAddress`` in the
        range ``base_id … base_id+127``. Returns ``False`` if the gateway's
        base ID or EURID is not yet cached (before ``start()``).
        """
        if sender == self.eurid:
            return True
        if isinstance(sender, BaseAddress) and self.base_id is not None:
            offset = int(sender) - int(self.base_id)
            return 0 <= offset <= 127
        return False

    @property
    def sender_slots(self) -> dict[SenderAddress, list[EURID]]:
        """Return every valid sender address mapped to the list of devices using it.

        Keys are the gateway EURID and BaseID+0…+127.
        An empty list means the address is unoccupied.  Normally each BaseID+n slot
        holds at most one device, but ``list`` handles manual duplicates gracefully.

        Useful for building a sender-address selection UI: present each address with
        an indication of whether it is already in use and, if so, by which device.
        Pass the chosen ``BaseAddress`` as ``sender_id`` to `start_learning`
        to override automatic allocation (the gateway EURID is a technically valid
        but poor choice as a learning sender).

        Returns an empty dict if the gateway's base ID or EURID is not yet cached
        (before ``start()``).
        """
        if self.base_id is None or self.eurid is None:
            return {}
        base_number = int(self.base_id)

        # Group registered devices by their assigned sender address
        occupied: dict[SenderAddress, list[EURID]] = {}
        for device in self.__devices.values():
            if device.sender is not None:
                occupied.setdefault(device.sender, []).append(device.address)

        senders: list[SenderAddress] = [self.eurid, self.base_id] + [
            BaseAddress(base_number + i) for i in range(1, 128)
        ]
        return {s: occupied.get(s, []) for s in senders}

    async def start_learning(
        self,
        timeout: int = 30,
        allow_teach_out: bool = False,
        sender_id: SenderAddress | None = None,
    ) -> None:
        """Start learning mode for pairing new EnOcean devices.

        This method enables the gateway to learn new device configurations. When learning mode
        is active, the gateway will accept teach-in telegrams from EnOcean devices. The learning
        session will automatically terminate after the specified timeout period.

        Args:
            timeout: Duration in seconds before learning mode automatically stops. Defaults to 30.
            allow_teach_out: If True, teach-out requests are honored during this session.
                Defaults to False.
            sender_id: Sender address used in UTE responses. Defaults to the gateway's base ID.
        """

        base_id = self.base_id
        if base_id is None:
            raise RuntimeError(
                "Cannot start learning mode: gateway's base ID is not set. Ensure the gateway is properly connected and configured."
            )

        self.__is_learning = True
        self.__allow_teach_out = allow_teach_out

        if sender_id is not None and not self.is_valid_sender(sender_id):
            raise ValueError(
                f"Invalid sender_id {sender_id} for learning mode. Must be a valid sender address for this gateway."
            )

        self.__sender_id_for_learning = sender_id if sender_id is not None else base_id

        if sender_id is not None:
            sender_info = f"Manually selected sender {self.__sender_id_for_learning}"
        else:
            try:
                next_sender = self.__next_available_sender()
            except RuntimeError:
                next_sender = None
            if next_sender is not None:
                sender_info = (
                    f"Gateway selected sender {base_id} (base ID) for destination-addressed devices and "
                    f"{next_sender} (base ID + {int(next_sender) - int(base_id)}) for sender-addressed devices"
                )
            else:
                sender_info = f"Gateway selected sender {base_id} (base ID), but no sender-addressed slots are available; consider freeing up sender-addressed slots"
        self._logger.info(
            f"Learning mode started. {sender_info}. Learning mode will timeout after {timeout} seconds."
        )
        if self.__learning_timeout_task is not None:
            self.__learning_timeout_task.cancel()
        self.__learning_timeout_task = asyncio.create_task(
            self.__learning_timeout(timeout)
        )

    def stop_learning(self) -> None:
        """Stop learning mode."""
        self.__is_learning = False
        self._logger.info("Learning mode stopped.")
        if self.__learning_timeout_task is not None:
            self.__learning_timeout_task.cancel()
            self.__learning_timeout_task = None

    async def __learning_timeout(self, timeout_seconds: int):
        try:
            await asyncio.sleep(timeout_seconds)
            if self.__is_learning:
                self.stop_learning()
        except asyncio.CancelledError:
            pass

    # ------------------------------------------------------------------
    # sending commands and receiving responses
    # ------------------------------------------------------------------
    async def send_esp3_packet(self, packet: ESP3Packet) -> SendResult:
        """Send an ESP3 packet to the EnOcean module and wait up to 500ms for a response (as per ESP3 specification).

        This method is thread-safe and can be called from multiple coroutines concurrently; the send operations will be serialized using an internal lock, and each call will wait for its corresponding response before allowing the next send operation to proceed. The method returns a SendResult object containing the received response (if any) and the duration in milliseconds between sending the request and receiving the response.
        """

        if not self.__transport:
            self._logger.error(
                "Cannot send: gateway is not connected to an EnOcean module."
            )
            return SendResult(None, None)

        async with self.__send_lock:
            self.__send_future = asyncio.get_running_loop().create_future()

            try:
                # emit to the send callbacks; we do this before sending the packet (WHY?)
                self.__emit(self.__esp3_send_callbacks, packet)
                self._logger.debug(
                    f"Sending ESP3 packet: {packet}. Waiting for response..."
                )

                # start a timer before sending the packet, so that we can measure the time it takes to receive the response after sending the packet
                start = time.perf_counter()

                # send the frame
                self.__transport.write(packet.to_bytes())
                response: ResponseTelegram | None = await asyncio.wait_for(
                    self.__send_future, timeout=0.5
                )

                # stop the timer and calculate duration
                end = time.perf_counter()

                self._logger.debug(
                    f"Received response to sent packet: {response}. Duration: {(end - start) * 1000:.2f} ms"
                )

                return SendResult(response, (end - start) * 1000)

            finally:
                self.__send_future = None

    async def send_command(
        self,
        destination: EURID,
        command: Instruction,
        sender: SenderAddress | None = None,
    ) -> SendResult:
        """Send a typed command to a registered device.

        Args:
            destination: The device's address (must have been registered via add_device()).
                         Used to look up the correct EEP; not necessarily the RF destination.
            command: A typed Command instance (e.g. SetCoverPosition, Dim).
            sender: Sender address to use. If None, uses the device's registered sender
                    or falls back to the gateway's base ID.

        Returns:
            SendResult with the response and duration.

        Raises:
            ValueError: If the device is unknown, or the command is not supported by its EEP.
            ConnectionError: If not connected to the EnOcean module.
        """
        device = self.__devices.get(destination)
        if device is None:
            raise ValueError(f"Unknown device {destination}: call add_device() first")

        eep_id = device.eep

        if eep_id not in self.__eep_handlers:
            raise ValueError(f"No EEP handler loaded for {eep_id}")

        spec = EEP_SPECIFICATIONS[eep_id]
        if command.action not in spec.encoders:
            raise ValueError(
                f"Command '{command.action}' is not supported for EEP {eep_id}"
            )

        # Resolve sender: explicit > device sender > gateway base ID
        if sender is None:
            if device.sender:
                sender = device.sender
            else:
                sender = self.base_id
                if sender is not None:
                    # Backfill: device was registered before base ID was available
                    device.sender = sender
                    self._logger.debug(
                        f"Device {destination} did not have a sender configured; using base ID {sender}."
                    )
        if sender is None:
            raise ValueError(
                "Could not determine sender address; pass sender= explicitly or connect first"
            )

        message: EEPMessage = spec.encoders[command.action](command)
        message.sender = sender
        # Only set a device-specific destination for addressed EEPs (e.g. VLD/D2).
        if spec.uses_addressed_sending:
            message.destination = destination

        erp1 = self.__eep_handlers[eep_id].encode(message)
        self.__erp1_sent += 1
        self.__emit_gateway_observation(
            "telegrams_sent", Observable.TELEGRAMS_SENT, self.__erp1_sent
        )
        return await self.send_esp3_packet(erp1.to_esp3())

    def connection_made(self) -> None:
        pass

    def connection_lost(self, exc: Exception | None) -> None:
        self.__transport = None
        if self.__stopped:
            return
        if not self.auto_reconnect:
            self._logger.error(
                "Connection to EnOcean module lost and auto-reconnect is disabled. You must manually call start() to reconnect."
            )
            self.__emit_gateway_observation(
                "connection_status", Observable.CONNECTION_STATUS, "disconnected"
            )
            return
        self._logger.warning(
            "Connection to EnOcean module lost, attempting to reconnect ..."
        )
        self.__emit_gateway_observation(
            "connection_status", Observable.CONNECTION_STATUS, "disconnected"
        )
        self.__emit_gateway_observation(
            "connection_status", Observable.CONNECTION_STATUS, "reconnecting"
        )
        if self.__reconnect_task is not None:
            self.__reconnect_task.cancel()
        self.__reconnect_task = asyncio.create_task(self.__try_to_reconnect())

    async def __try_to_reconnect(self):
        for attempt in range(1, 721):
            await asyncio.sleep(5)
            try:
                self._logger.info(
                    f"Trying to reconnect to EnOcean Module (attempt #{attempt}/720)"
                )
                await self.start()
                self.__reconnect_task.cancel()
                self.__reconnect_task = None
                self._logger.info("Reconnect successfull")
                return
            except Exception:
                self._logger.warning(
                    f"Reconnection attempt #{attempt}/720 failed, retrying again in 5s."
                )
                continue

        self._logger.error(
            "Could not reconnect to EnOcean module after 720 attempts (1 hour). Stopping auto-reconnect."
        )

    # ------------------------------------------------------------------
    # device registry
    # ------------------------------------------------------------------
    def add_device(
        self,
        address: EURID,
        device_type: DeviceType,
        sender: SenderAddress | None = None,
        name: str | None = None,
    ) -> None:
        """Register a device with its DeviceType (EEP + optional manufacturer/model).

        This allows the gateway to recognize incoming messages from this device and decode them according to the registered EEP (if a handler for that EEP is found).
        """
        if address in self.__devices:
            self._logger.warning(
                f"Tried to add device with address {address}, but it is already registered."
            )
            raise ValueError(f"Device {address} is already registered.")

        eep = device_type.eep

        if sender is None:
            sender = self.__base_id
            if sender is None:
                self._logger.debug(
                    f"No sender provided when adding device {address} and base ID not yet fetched; "
                    "sender will be set on first send."
                )
            else:
                self._logger.debug(
                    f"No sender provided when adding device {address}; using base ID {sender} as sender."
                )

        device = Device(
            address=address,
            device_type=device_type,
            name=name or str(address),
            sender=sender,
        )
        self.__devices[address] = device
        self._logger.info(
            f"Added device with address {address}, EEP {eep} and sender {sender}"
        )

        # get the EEP handler for this EEP
        if eep not in self.__eep_handlers:
            if eep not in EEP_SPECIFICATIONS:
                self._logger.warning(
                    f"EEP {eep} is not supported. Messages from device {address} will not be decoded."
                )
                return
            self.__eep_handlers[eep] = EEPHandler(EEP_SPECIFICATIONS[eep])
            self._logger.info(f"Loaded EEP handler for previously unused EEP {eep}")
        else:
            self._logger.debug(f"Reusing existing EEP handler for EEP {eep}.")

        eep_spec = EEP_SPECIFICATIONS[eep]

        # build observer list from EEP observers
        if not eep_spec.observers:
            self._logger.debug(
                f"EEP {eep} has no observers; Observation processing unavailable for device {address}."
            )
            return

        cb = self.__on_observation
        capabilities = [MetaDataObserver(device_address=address, on_state_change=cb)]
        for factory in eep_spec.observers:
            capabilities.append(factory(address, cb))

        device.capabilities = capabilities
        self._logger.debug(
            f"Initialized device {address} with {len(device.capabilities)} capabilities"
        )

    def __on_observation(self, observation: Observation) -> None:
        """Internal callback forwarding observer Observations to registered callbacks."""
        self.__emit(self.__observation_callbacks, observation)

    def __emit_gateway_observation(
        self, entity: str, observable: Observable, value: object
    ) -> None:
        """Emit a gateway-device observation if the base ID is known."""
        if self.__version_info is None:
            return
        if observable is Observable.CONNECTION_STATUS:
            self.__connection_status = str(value)
            source = ObservationSource.GATEWAY
        else:
            source = ObservationSource.TELEGRAM
        self.__emit(
            self.__observation_callbacks,
            Observation(
                device=self.__version_info.eurid,
                entity=entity,
                values={observable: value},
                timestamp=time.time(),
                source=source,
            ),
        )

    @property
    def gateway_entities(self) -> list[Entity]:
        """Entities exposed by the gateway device itself."""
        return _GATEWAY_ENTITIES

    def remove_device(self, address: EURID) -> None:
        """Deregister a device by its sender address (EURID). This removes the device from the registry of known devices, so that incoming messages from this address will no longer be recognized as coming from a known device and will not be decoded as EEP messages."""
        if address in self.__devices:
            for observer in self.__devices[address].capabilities:
                observer.stop()
            del self.__devices[address]
            self._logger.info(f"Removed device with address {address}")
        else:
            self._logger.warning(
                f"Tried to remove device with address {address}, but it was not found in the registry of known devices."
            )

    def device_spec(self, address: EURID) -> DeviceSpec | None:
        """Return a DeviceSpec for a registered device, or None if not found.

        The DeviceSpec describes what observables and commands the device supports,
        allowing integrations (e.g. Home Assistant) to create entities at setup time
        without waiting for the first incoming telegram.
        """
        device = self.__devices.get(address)
        if device is None:
            return None
        spec = EEP_SPECIFICATIONS.get(device.eep)
        if spec is None:
            return None
        return DeviceSpec(
            device_type=device.device_type,
            entities=spec.entities + _METADATA_ENTITIES,
        )

    @property
    def device_specs(self) -> dict[EURID, DeviceSpec]:
        """Return a DeviceSpec for every registered device, keyed by address.
        Devices whose EEP is not in the registry are silently skipped.
        """
        result: dict[EURID, DeviceSpec] = {}
        for address in self.__devices:
            ds = self.device_spec(address)
            if ds is not None:
                result[address] = ds
        return result

    # ------------------------------------------------------------------
    # Gateway properties and methods
    # ------------------------------------------------------------------
    @property
    def base_id(self) -> BaseAddress | None:
        """The cached base ID of the connected EnOcean module, or ``None`` before ``start()``."""
        return self.__base_id

    async def fetch_base_id(self) -> BaseAddress | None:
        """Fetch and cache the base ID from the module. Returns the cached value immediately if already known."""
        if self.__base_id is not None:
            return self.__base_id

        if self.__transport is None:
            raise ConnectionError("Not connected to EnOcean module")

        cmd = CommonCommandTelegram.CO_RD_IDBASE()
        result: SendResult = await self.send_esp3_packet(cmd.to_esp3_packet())
        response = result.response

        if (
            response is None
            or response.return_code != ResponseCode.OK
            or len(response.response_data) < 4
        ):
            return None

        self.__base_id = BaseAddress(response.response_data[:4])

        if len(response.optional_data) >= 1:
            self.__base_id_remaining_write_cycles = response.optional_data[0]

        return self.__base_id

    async def change_base_id(
        self, new_base_id: BaseAddress, safety_flag: int = 0
    ) -> BaseAddress | None:
        """Change the base ID of the connected EnOcean module. Returns True if successful, False otherwise.

        To prevent accidental changes, this function requires a safety flag to be provided. The safety_flag must be set to 0x7B, otherwise the function will return False without sending the command."""

        if safety_flag != 0x7B:
            raise ValueError(
                "Invalid safety flag. To change the base ID, you must provide a safety flag of 0x7B to confirm that you understand the consequences of this action."
            )

        if self.__transport is None:
            raise ConnectionError("Not connected to EnOcean module")

        base_id_before_change = (
            await self.fetch_base_id()
        )  # populate cache if not yet done

        if new_base_id == base_id_before_change:
            raise ValueError("New base ID is the same as the current base ID")

        # send WR ID base id request
        cmd = CommonCommandTelegram.CO_WR_IDBASE(new_base_id)
        send_result = await self.send_esp3_packet(cmd.to_esp3_packet())
        response = send_result.response

        # check response for errors; if we got a response, but it indicates an error, we can be pretty sure that the base ID change failed, so we can raise an exception with the error message
        if response is not None and response.return_code != ResponseCode.OK:
            match response.return_code:
                case ResponseCode.NOT_SUPPORTED:
                    raise BaseIDChangeError(
                        "Base ID change is not supported by this module"
                    )
                case ResponseCode.BASEID_OUT_OF_RANGE:
                    raise BaseIDChangeError(
                        "Base ID change failed: provided base ID is out of allowed range (must be in range FF:80:00:00 to FF:FF:FF:80)"
                    )
                case ResponseCode.BASEID_MAX_REACHED:
                    raise BaseIDChangeError(
                        "Base ID change failed: maximum number of allowed base ID changes has been reached"
                    )
                case _:
                    raise BaseIDChangeError(
                        f"Base ID change failed with error code: {response.return_code.name} ({response.return_code.value})"
                    )

        # now either we got a successful response, or no response at all (timeout). In both cases, we should check if the base ID was actually changed by reading it again, because the module might have accepted the command but failed to send a response.
        self.__base_id = None  # reset cached base ID to force re-fetching it
        self.__base_id_remaining_write_cycles = (
            None  # reset cached remaining write cycles as well
        )
        reported_base_id = await self.fetch_base_id()
        if reported_base_id == new_base_id:
            return reported_base_id
        elif reported_base_id == base_id_before_change:
            raise BaseIDChangeError(
                "Base ID change failed: after sending the command, the base ID of the module is still the same as before"
            )
        else:
            raise BaseIDChangeError(
                f"Base ID change failed: after sending the command, the module reports a different base ID ({reported_base_id}) than the one we tried to set ({new_base_id}) and the one that was set before ({base_id_before_change}), which is very unexpected and likely indicates a communication error or a bug in the module's firmware."
            )

    @property
    def version_info(self) -> VersionInfo | None:
        """The cached version information of the connected EnOcean module, or ``None`` before ``start()``."""
        return self.__version_info

    async def fetch_version_info(self) -> VersionInfo | None:
        """Fetch and cache version info from the module. Returns the cached value immediately if already known."""
        if self.__version_info is not None:
            return self.__version_info

        if self.__transport is None:
            raise ConnectionError("Not connected to EnOcean module")

        cmd = CommonCommandTelegram.CO_RD_VERSION()
        send_result = await self.send_esp3_packet(cmd.to_esp3_packet())
        response = send_result.response

        if (
            response is None
            or response.return_code != ResponseCode.OK
            or len(response.response_data) < 32
        ):
            return None

        self.__version_info = VersionInfo(
            app_version=VersionIdentifier(
                main=response.response_data[0],
                beta=response.response_data[1],
                alpha=response.response_data[2],
                build=response.response_data[3],
            ),
            api_version=VersionIdentifier(
                main=response.response_data[4],
                beta=response.response_data[5],
                alpha=response.response_data[6],
                build=response.response_data[7],
            ),
            eurid=EURID(response.response_data[8:12]),
            device_version=response.response_data[12],
            app_description=response.response_data[16:32]
            .decode("ascii")
            .rstrip("\x00"),
        )

        return self.__version_info

    @property
    def base_id_remaining_write_cycles(self) -> int | None:
        """The cached remaining base ID write cycles, or ``None`` before ``fetch_base_id()`` / ``start()``."""
        return self.__base_id_remaining_write_cycles

    @property
    def eurid(self) -> EURID | None:
        """The cached EURID of the connected EnOcean module, or ``None`` before ``start()``."""
        return self.__version_info.eurid if self.__version_info else None

    # ------------------------------------------------------------------
    # Internal packet processing
    # ------------------------------------------------------------------
    def process_esp3_packet(self, packet: ESP3Packet):
        """Process a received ESP3 packet. This includes emitting the raw packet to registered callbacks and further processing based on packet type."""
        self.__emit(self.__esp3_receive_callbacks, packet)

        self._logger.debug(f"Received ESP3 packet: {packet}")

        # handle packet based on type; currently we only process RESPONSE and RADIO_ERP1 packets, other types are ignored
        if packet.packet_type == ESP3PacketType.RESPONSE:
            response: ResponseTelegram
            try:
                response = ResponseTelegram.from_esp3_packet(packet)
            except Exception as e:
                self._logger.debug(
                    f"Failed to parse ESP3 RESPONSE packet: {packet}. Ignoring packet. Error: {e}"
                )
                return
            self.__process_response(response)
            return

        if packet.packet_type != ESP3PacketType.RADIO_ERP1:
            self._logger.debug(
                f"Received ESP3 packet of type {packet.packet_type.name}, which is currently not processed by the gateway. Ignoring packet."
            )
            return

        self.__process_erp1_packet(packet)

    def __process_erp1_packet(self, packet: ESP3Packet) -> None:
        """Parse ESP3 RADIO_ERP1 packet into ERP1 telegram and process it."""
        try:
            erp1 = ERP1Telegram.from_esp3(packet)
        except Exception as e:
            self._logger.debug(
                f"Failed to parse ESP3 packet to ERP1 telegram: {packet}. Ignoring packet. Error: {e}"
            )
            return

        self.__process_erp1_telegram(erp1)

    def __create_tracked_task(self, coro) -> None:
        """Schedule a coroutine as a background task, tracking it for cancellation on stop()."""
        task = asyncio.get_running_loop().create_task(coro)
        self.__background_tasks.add(task)
        task.add_done_callback(self.__background_tasks.discard)

    def __emit(self, callbacks: list[Callable], *args):
        """Emit arguments to all registered callbacks of the given type."""
        loop = asyncio.get_running_loop()
        for cb in callbacks:
            loop.call_soon(cb, *args)

    def __emit_with_sender_filter(
        self, callbacks: list[CallbackWithFilter], sender: SenderAddress, obj
    ):
        """Emit an object to all registered callbacks of the given type that have a sender filter matching the sender address."""
        loop = asyncio.get_running_loop()
        for cb in callbacks:
            if cb.sender_filter is None or cb.sender_filter == sender:
                loop.call_soon(cb.callback, obj)

    def __is_sender_known(self, sender: SenderAddress) -> bool:
        """Check if the sender address is known (i.e. if we have an EEP ID for it)."""
        return sender in self.__devices or sender in self.__known_senders

    def __process_response(self, response: ResponseTelegram):
        """Process a received RESPONSE packet. If we are currently awaiting a response, try to parse it and store it for the send() method to retrieve."""
        self.__emit(self.__response_callbacks, response)
        self._logger.debug(f"Processing received RESPONSE packet: {response}")

        if self.__send_future and not self.__send_future.done():
            self.__send_future.set_result(response)

    def __process_erp1_telegram(self, erp1: ERP1Telegram):
        """Process a received ERP1 telegram. This includes emitting it to registered callbacks and further processing based on RORG and learning bit."""
        self.__erp1_received += 1
        self.__emit_gateway_observation(
            "telegrams_received", Observable.TELEGRAMS_RECEIVED, self.__erp1_received
        )
        # emit the raw telegram
        self.__emit_with_sender_filter(self.__erp1_receive_callbacks, erp1.sender, erp1)
        self._logger.debug(f"ESP3 packet successfully decoded to ERP1 telegram: {erp1}")

        # check if sender is known; if not, track it and notify callbacks (EURIDs only)
        if not self.__is_sender_known(erp1.sender):
            self.__known_senders.append(erp1.sender)
            if isinstance(erp1.sender, EURID):
                self.__emit(self.__new_device_callbacks, erp1.sender)
                self._logger.info(
                    f"New device detected with sender address: {erp1.sender}"
                )
            else:
                self._logger.debug(f"New non-EURID sender observed: {erp1.sender}")

        # if it's a UTE telegram, try to parse to UTE message; if parsing fails, ignore the packet and return;
        if erp1.rorg == RORG.RORG_UTE:
            try:
                ute_message = UTEMessage.from_erp1(erp1)
            except Exception as e:
                self._logger.debug(
                    f"Failed to parse ERP1 telegram to UTE message: {erp1}. Ignoring packet. Error: {e}"
                )
                return

            self.__handle_ute_message(ute_message)
            return

        # 1BS teach-in: no EEP info available; NewDeviceCallback already fired above
        if erp1.rorg == RORG.RORG_1BS and erp1.is_learning_telegram:
            self._logger.debug(
                f"1BS teach-in from {erp1.sender}: no EEP info in telegram; cannot auto-register."
            )
            return

        if erp1.rorg == RORG.RORG_4BS and erp1.is_learning_telegram:
            self.__handle_4bs_teach_in_telegram(erp1)
            return

        self.__process_eep_telegram(erp1)

    def __process_eep_telegram(self, erp1: ERP1Telegram) -> None:
        """Detect EEP ID for ERP1 telegram and decode to EEP message."""
        # There are two options for determining the EEP ID of an incoming ERP1 telegram: either we look it up by the sender address, or by the destination address (if the destination is not a broadcast address).
        # We first check if we have a known device with the sender address, and if not, we check if we have a known device with the destination address.
        # If we cannot find a known device for either the sender or the destination, we cannot determine the EEP ID for this telegram, so we emit a parsing failed message and return.
        # If we can find a known device for either the sender or the destination, we use that device's EEP ID for further processing.
        eep_id: EEP
        sender_device = self.__devices.get(erp1.sender)
        if sender_device is not None:
            eep_id = sender_device.eep
        else:
            if erp1.destination is None or erp1.destination.is_broadcast():
                msg = (
                    f"Failed to decode ERP1 telegram to EEP message: sender {erp1.sender} "
                    "is unknown and destination is not specified."
                )
                self._logger.debug(msg)
                self.__emit(self.__parsing_failed_callbacks, msg)
                return

            destination_device = self.__devices.get(erp1.destination)
            if destination_device is None:
                msg = (
                    f"Failed to decode ERP1 telegram to EEP message: sender {erp1.sender} "
                    f"is unknown and destination {erp1.destination} is also unknown."
                )
                self._logger.debug(msg)
                self.__emit(self.__parsing_failed_callbacks, msg)
                return

            self._logger.debug(
                f"Sender {erp1.sender} is unknown, but destination {erp1.destination} "
                "is known, using EEP ID of destination for EEP decoding."
            )
            eep_id = destination_device.eep

        if eep_id not in self.__eep_handlers:
            self._logger.debug(
                f"Failed to decode ERP1 telegram to EEP message: No EEP handler for {eep_id}."
            )
            self.__emit(
                self.__parsing_failed_callbacks,
                f"Failed to decode ERP1 telegram to EEP message: No EEP handler for {eep_id}.",
            )
            return

        try:
            eep_message = self.__eep_handlers[eep_id](erp1)
            self.__process_eep_message(eep_message)
        except Exception as e:
            self._logger.debug(f"Failed to decode ERP1 telegram to EEP message: {e}")
            self.__emit(
                self.__parsing_failed_callbacks,
                f"Failed to decode ERP1 telegram to EEP message: {e}",
            )
            return

    def __process_eep_message(self, eep_message: EEPMessage) -> None:
        """Emit callbacks for a decoded EEP message."""
        self.__emit_with_sender_filter(
            self.__eep_receive_callbacks, eep_message.sender, eep_message
        )
        self._logger.debug(
            f"ERP1 telegram successfully decoded to EEP message: {eep_message}"
        )
        self.__process_capability_message(eep_message)

    def __process_capability_message(self, eep_message: EEPMessage) -> None:
        """Decode EEP message using device capabilities."""
        if eep_message.sender is None:
            self.__emit(
                self.__parsing_failed_callbacks,
                "Failed to decode capability: sender is not specified.",
            )
            return

        device = self.__devices.get(eep_message.sender)
        if device is None:
            self.__emit(
                self.__parsing_failed_callbacks,
                "Failed to decode capability: no device.",
            )
            return

        for capability in device.capabilities:
            try:
                capability.decode(eep_message)
            except Exception as e:
                self._logger.debug(
                    f"Failed to decode EEP message {eep_message} using capability {capability}: {e}"
                )
                self.__emit(
                    self.__parsing_failed_callbacks,
                    f"Failed to decode EEP message {eep_message} using capability {capability}: {e}",
                )

    async def __send_ute_response(self, response: UTEMessage) -> None:
        try:
            self._logger.debug(f"Sending UTE response: {response}")
            erp1 = response.to_erp1()
            esp3 = erp1.to_esp3()
            send_result = await self.send_esp3_packet(esp3)

        except Exception as e:
            self._logger.error(f"Failed to send UTE response: {e}")
            return

        if (
            send_result.response is None
            or send_result.response.return_code != ResponseCode.OK
        ):
            self._logger.error(
                f"Failed to send UTE response. Send result: {send_result}"
            )
            return

        action = (
            "teach-out"
            if response.request_type == UTEResponseType.ACCEPTED_DELETION_OF_TEACH_IN
            else "teach-in"
        )
        self._logger.info(
            f"Successfully confirmed bidirectional UTE {action} for device {response.sender} with EEP {response.eep}."
        )

    async def __send_4bs_teach_in_response(
        self, response: FourBSTeachInTelegram
    ) -> None:
        try:
            erp1 = response.to_erp1()
            esp3 = erp1.to_esp3()
            send_result = await self.send_esp3_packet(esp3)
        except Exception as e:
            self._logger.error(f"Failed to send 4BS teach-in response: {e}")
            return

        if (
            send_result.response is None
            or send_result.response.return_code != ResponseCode.OK
        ):
            self._logger.error(
                f"Failed to send 4BS teach-in response. Send result: {send_result}"
            )
            return

        result = (
            "accepted"
            if response.learn_result == FourBSTeachInResult.SENDER_ID_STORED
            else "not accepted"
        )
        self._logger.info(
            f"Successfully sent bidirectional 4BS teach-in response ({result})  with EEP {response.eep}."
        )

    def __handle_ute_message(self, ute: UTEMessage):
        self.__emit(self.__ute_receive_callbacks, ute)

        # ignore messages when not in learning mode — teach-out also requires an active session
        if not self.__is_learning:
            self._logger.debug(
                f"UTE message from {ute.sender} received but not in learning mode; ignoring."
            )
            return

        # ignore responses
        if isinstance(ute.request_type, UTEResponseType):
            return

        request_type = ute.request_type
        response_expected = (
            ute.teach_in_response_message_expectation
            == EEPTeachInResponseMessageExpectation.RESPONSE_EXPECTED
        )
        device_address = ute.sender  # always set when decoded from ERP1

        match request_type:
            case UTEQueryRequestType.TEACH_IN:
                self._logger.info(f"UTE teach-in query from {device_address}.")
                self.__handle_ute_teach_in(ute, device_address, response_expected)

            case UTEQueryRequestType.TEACH_IN_OR_DELETION_OF_TEACH_IN:
                if device_address in self.__devices:
                    self._logger.info(
                        f"UTE teach-in or deletion-of-teach-in from {device_address}: device registered → treating as teach-out."
                    )
                    self.__handle_ute_teach_out(ute, device_address, response_expected)
                else:
                    self._logger.info(
                        f"UTE teach-in or deletion-of-teach-in from {device_address}: device not registered → treating as teach-in."
                    )
                    self.__handle_ute_teach_in(ute, device_address, response_expected)

            case UTEQueryRequestType.TEACH_IN_DELETION:
                self._logger.info(
                    f"UTE explicit teach-out request from {device_address}."
                )
                self.__handle_ute_teach_out(ute, device_address, response_expected)

    def __handle_ute_teach_in(
        self,
        ute: UTEMessage,
        device_address: EURID,
        response_expected: bool,
    ) -> None:
        generic_eep = EEP([ute.eep.rorg, ute.eep.func, ute.eep.type])
        if ute.eep in EEP_SPECIFICATIONS:
            eep = ute.eep
        elif generic_eep in EEP_SPECIFICATIONS:
            eep = generic_eep
        else:
            eep = None
        if eep is None:
            self._logger.info(
                f"UTE teach-in from {device_address}: EEP {ute.eep} not supported."
            )
            if response_expected:
                self.__create_tracked_task(
                    self.__send_ute_response(
                        UTEMessage.response_for_query(
                            ute,
                            UTEResponseType.NOT_ACCEPTED_EEP_NOT_SUPPORTED,
                            sender=self.__sender_id_for_learning,
                        )
                    )
                )
            return

        spec = EEP_SPECIFICATIONS[eep]
        # Re-teach-in of a known device: reuse existing sender slot
        existing = self.__devices.get(device_address)
        if existing is not None:
            self._logger.info(
                f"UTE re-teach-in from {device_address}: device already registered; reusing sender slot."
            )
            sender = existing.sender
        elif spec.uses_addressed_sending:
            sender = self.__sender_id_for_learning or self.__base_id
        else:
            sender = self.__next_available_sender()

        if response_expected:
            self.__create_tracked_task(
                self.__send_ute_response(
                    UTEMessage.response_for_query(
                        ute,
                        UTEResponseType.ACCEPTED_TEACH_IN,
                        sender=sender or self.__sender_id_for_learning,
                    )
                )
            )
        if existing is None:
            self.add_device(
                address=device_address,
                device_type=device_type_for_eep(eep),
                sender=sender,
            )
        if not response_expected:
            self._logger.info(
                f"UTE teach-in from {device_address}: successfully registered with EEP {eep}."
            )
        self.__emit(self.__device_taught_in_callbacks, device_address, eep)

    def __handle_ute_teach_out(
        self,
        ute: UTEMessage,
        device_address: EURID,
        response_expected: bool,
    ) -> None:
        if not self.__allow_teach_out:
            self._logger.info(
                f"UTE teach-out from {device_address}: teach-out not allowed in this learning session; rejecting."
            )
            if response_expected:
                self.__create_tracked_task(
                    self.__send_ute_response(
                        UTEMessage.response_for_query(
                            ute,
                            UTEResponseType.NOT_ACCEPTED_GENERAL_REASON,
                            sender=self.__sender_id_for_learning,
                        )
                    )
                )
            return

        if device_address not in self.__devices:
            self._logger.info(
                f"UTE teach-out from {device_address}: device not registered; rejecting."
            )
            if response_expected:
                self.__create_tracked_task(
                    self.__send_ute_response(
                        UTEMessage.response_for_query(
                            ute,
                            UTEResponseType.NOT_ACCEPTED_GENERAL_REASON,
                            sender=self.__sender_id_for_learning,
                        )
                    )
                )
            return

        self.remove_device(device_address)
        self._logger.info(
            f"UTE teach-out from {device_address}: device successfully removed."
        )
        if response_expected:
            self.__create_tracked_task(
                self.__send_ute_response(
                    UTEMessage.response_for_query(
                        ute,
                        UTEResponseType.ACCEPTED_DELETION_OF_TEACH_IN,
                        sender=self.__sender_id_for_learning,
                    )
                )
            )

    def __next_available_sender(self) -> BaseAddress:
        """Return the lowest free BaseAddress slot (offset 1–127).

        Derives used offsets from Device.sender values already in the live device registry.
        Raises RuntimeError if the pool is exhausted (> 127 broadcast devices).
        """
        if self.__base_id is None:
            raise RuntimeError(
                "Base ID not available; cannot assign sender address for new device. Make sure to connect to the EnOcean module and fetch the base ID before adding devices without explicit sender addresses."
            )
        used = {
            int(device.sender) - int(self.__base_id)
            for device in self.__devices.values()
            if isinstance(device.sender, BaseAddress)
        }
        offset = next((o for o in range(1, 128) if o not in used), None)
        if offset is None:
            raise RuntimeError(
                "Sender address pool exhausted (127 sender-addressed devices maximum)"
            )
        return BaseAddress(int(self.__base_id) + offset)

    def __handle_4bs_teach_in_telegram(self, erp1: ERP1Telegram):
        if not self.__is_learning:
            self._logger.debug(
                "4BS teach-in telegram received but not in learning mode; ignoring telegram."
            )
            return
        try:
            teach_in_telegram = FourBSTeachInTelegram.from_erp1(erp1)
        except ValueError as e:
            self._logger.warning(f"Failed to parse 4BS teach-in telegram: {e}")
            return

        if teach_in_telegram.learn_status != FourBSLearnStatus.QUERY:
            self._logger.debug(
                f"Received 4BS learn telegram which is not QUERY; ignoring telegram."
            )
            return

        if (
            teach_in_telegram.learn_type
            == FourBSLearnType.TELEGRAM_WITHOUT_EEP_AND_NO_MANUFACTURER
        ):
            self._logger.info(
                f"4BS profileless teach-in from {erp1.sender}; "
                "cannot auto-register without EEP."
            )
            return

        existing = self.__devices.get(erp1.sender)
        if existing is not None:
            self._logger.info(
                f"4BS re-teach-in from {erp1.sender}: device already registered; checking if EEP matches."
            )
            if existing.eep == teach_in_telegram.eep:
                self._logger.info(
                    f"4BS re-teach-in from {erp1.sender}: received EEP {teach_in_telegram.eep} matches existing registration ({existing.eep}); ignoring."
                )
                return

            self._logger.info(
                f"4BS re-teach-in from {erp1.sender}: device previously registered with different EEP {existing.eep}; taught-in EEP is {teach_in_telegram.eep} - checking if that is available."
            )

        eep = teach_in_telegram.eep
        if eep is None or eep not in EEP_SPECIFICATIONS:
            self._logger.info(
                f"4BS teach-in from {erp1.sender}: EEP {eep} not supported; ignoring."
            )
            return

        spec = EEP_SPECIFICATIONS[eep]

        if existing is not None:
            existing.device_type = device_type_for_eep(eep)
            if eep not in self.__eep_handlers:
                self.__eep_handlers[eep] = EEPHandler(spec)
                self._logger.info(
                    f"Loaded EEP handler for previously unused EEP {eep} due to re-teach-in."
                )
            self._logger.info(
                f"4BS re-teach-in from {erp1.sender}: updated EEP of existing device registration to {eep}."
            )

            self.__create_tracked_task(
                self.__send_4bs_teach_in_response(
                    FourBSTeachInTelegram.response_for_query(
                        teach_in_telegram,
                        FourBSTeachInResult.SENDER_ID_STORED,
                        existing.sender,
                    )
                )
            )
            return

        sender = (
            self.__next_available_sender()
            if not spec.uses_addressed_sending
            else self.__sender_id_for_learning or self.__base_id
        )
        self.add_device(
            address=erp1.sender, device_type=device_type_for_eep(eep), sender=sender
        )
        self._logger.info(
            f"4BS teach-in from {erp1.sender}: successfully registered with EEP {eep}"
            + (f" using sender slot {sender}" if sender is not None else "")
            + "."
        )

        self.__create_tracked_task(
            self.__send_4bs_teach_in_response(
                FourBSTeachInTelegram.response_for_query(
                    teach_in_telegram, FourBSTeachInResult.SENDER_ID_STORED, sender
                )
            )
        )
        self.__emit(self.__device_taught_in_callbacks, erp1.sender, eep)
