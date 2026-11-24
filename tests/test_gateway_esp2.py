"""Tests for the Gateway talking to an ESP2 module (simulated on the serial level)."""

import asyncio

import pytest

from enocean_async import (
    EEP,
    EURID,
    BaseAddress,
    CentralSwitch,
    CoverStop,
    Gateway,
    LearnTelegram,
    LearningToggle,
    Observable,
    Observation,
    SerialProtocol,
    SetSwitchOutput,
)
from enocean_async.eep import device_type_for_eep
from enocean_async.gateway import BaseIDChangeError
from enocean_async.protocol.erp1.rorg import RORG
from enocean_async.protocol.erp1.telegram import ERP1Telegram
from enocean_async.protocol.esp2.packet import (
    ESP2ORG,
    ESP2CommandCode,
    ESP2HeaderSequence,
    ESP2MessageCode,
    ESP2Packet,
)
from enocean_async.protocol.esp2.protocol import EnOceanSerialProtocol2
from enocean_async.protocol.esp3.response import ResponseCode

BASE_ID = BaseAddress("FF:80:12:80")
RPS_PRESS = bytes.fromhex("a55a0b05700000000123456730" + "80")


class FakeESP2Module:
    """Stands in for the serial transport and answers like an ESP2 module."""

    def __init__(self) -> None:
        self.protocol: EnOceanSerialProtocol2 | None = None
        self.baudrate: int | None = None
        self.written: list[bytes] = []
        self.closed = False
        self.port_released = asyncio.Event()
        self.port_released.set()
        self.waiting_for_release = asyncio.Event()

    def write(self, data: bytes) -> None:
        self.written.append(data)
        answer = self.__answer(ESP2Packet.from_bytes(data))
        asyncio.get_running_loop().call_soon(
            self.protocol.data_received, answer.to_bytes()
        )

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        self.waiting_for_release.set()
        await self.port_released.wait()

    def receive(self, data: bytes) -> None:
        """Simulate bytes arriving from the module."""
        self.protocol.data_received(data)

    @staticmethod
    def __answer(request: ESP2Packet) -> ESP2Packet:
        payload = bytes(9)
        code = ESP2MessageCode.OK
        if request.header_sequence == ESP2HeaderSequence.TCT:
            if request.org == ESP2CommandCode.RD_IDBASE:
                code = ESP2MessageCode.INF_IDBASE
                payload = bytes(BASE_ID.bytelist) + bytes(5)
            elif request.org == ESP2CommandCode.RD_SW_VER:
                code = ESP2MessageCode.INF_SW_VER
                payload = bytes.fromhex("020100000204020400")
        return ESP2Packet(
            ESP2HeaderSequence.RCT, code, payload[:4], payload[4:8], payload[8]
        )


@pytest.fixture
def module(monkeypatch: pytest.MonkeyPatch) -> FakeESP2Module:
    fake = FakeESP2Module()

    async def create_serial_connection(loop, protocol_factory, port, baudrate):
        fake.protocol = protocol_factory()
        fake.baudrate = baudrate
        fake.protocol.connection_made(fake)
        return fake, fake.protocol

    monkeypatch.setattr(
        "enocean_async.gateway.serialx.create_serial_connection",
        create_serial_connection,
    )
    return fake


@pytest.fixture
async def gateway(module: FakeESP2Module):
    gateway = Gateway("/dev/null", protocol=SerialProtocol.ESP2)
    await gateway.start(auto_reconnect=False)
    yield gateway
    await gateway.stop()


def test_default_baudrate_follows_protocol():
    assert SerialProtocol.ESP2.default_baudrate == 9600
    assert SerialProtocol.ESP3.default_baudrate == 57600


async def test_start_uses_esp2_protocol_and_baudrate(gateway, module):
    assert isinstance(module.protocol, EnOceanSerialProtocol2)
    assert module.baudrate == 9600
    assert gateway.serial_protocol is SerialProtocol.ESP2


async def test_explicit_baudrate_is_kept(module):
    gateway = Gateway("/dev/null", baudrate=57600, protocol=SerialProtocol.ESP2)
    await gateway.start(auto_reconnect=False)
    await gateway.stop()

    assert module.baudrate == 57600


async def test_start_reads_base_id_and_version(gateway, module):
    assert module.written == [
        bytes.fromhex("a55aab58000000000000000000" + "03"),
        bytes.fromhex("a55aab4b000000000000000000" + "f6"),
    ]
    assert gateway.base_id == BASE_ID
    assert gateway.version_info.app_version.version_string == "2.1.0"
    assert gateway.version_info.api_version.version_string == "2.4.2b4"


async def test_esp2_module_has_no_eurid_and_is_identified_by_base_id(gateway):
    assert gateway.eurid is None
    assert gateway.device_address == BASE_ID


async def test_gateway_observations_use_base_id_as_device(module):
    observations: list[Observation] = []
    gateway = Gateway("/dev/null", protocol=SerialProtocol.ESP2)
    gateway.add_observation_callback(observations.append)
    await gateway.start(auto_reconnect=False)
    await asyncio.sleep(0)  # callbacks are dispatched via the event loop
    await gateway.stop()

    connected = [
        observation
        for observation in observations
        if observation.values.get(Observable.CONNECTION_STATUS) == "connected"
    ]
    assert len(connected) == 1
    assert connected[0].device == BASE_ID


async def test_sender_slots_contain_base_addresses_only(gateway):
    slots = gateway.sender_slots

    assert len(slots) == 128
    assert all(isinstance(sender, BaseAddress) for sender in slots)
    assert all(value != "eurid" for value, _, _ in gateway.learning_sender_options())


def _sender_choices(entities, entity_id: str) -> tuple[str, ...]:
    (entity,) = [entity for entity in entities if entity.id == entity_id]
    return entity.config_spec.options


@pytest.mark.parametrize(
    ("protocol", "offers_eurid"),
    [(SerialProtocol.ESP2, False), (SerialProtocol.ESP3, True)],
)
def test_sender_choices_offer_eurid_only_for_a_module_with_eurid(
    protocol, offers_eurid
):
    # known from the protocol alone, i.e. already before start()
    gateway = Gateway("/dev/null", protocol=protocol)
    gateway.add_device(EURID("01:23:45:67"), device_type_for_eep(EEP("A5-02-05")))
    device_entities = gateway.device_spec(EURID("01:23:45:67")).entities

    for choices in (
        _sender_choices(gateway.gateway_entities, "learning_sender"),
        _sender_choices(gateway.gateway_entities, "default_sender"),
        _sender_choices(device_entities, "sender_slot"),
    ):
        assert ("eurid" in choices) is offers_eurid
        assert choices[:2] == ("auto", "0") and choices[128] == "127"


@pytest.mark.parametrize("key", ["learning_sender", "default_sender"])
async def test_gateway_sender_config_rejects_eurid(gateway, key):
    with pytest.raises(ValueError, match="does not report its EURID"):
        gateway.set_gateway_config(key, "eurid")
    assert gateway.config[key] == "auto"

    gateway.set_gateway_config(key, "5")
    assert gateway.config[key] == "5"


async def test_device_sender_slot_rejects_eurid(gateway):
    address = EURID("01:23:45:67")
    gateway.add_device(address, device_type_for_eep(EEP("A5-02-05")))
    gateway.set_device_config(address, "sender_slot", "3")

    with pytest.raises(ValueError, match="does not report its EURID"):
        gateway.set_device_config(address, "sender_slot", "eurid")

    # the previous slot is kept
    assert gateway.sender_slots[BaseAddress(int(BASE_ID) + 3)] == [address]


async def test_learning_with_eurid_sender_config_is_rejected(gateway):
    # e.g. a config restored from an ESP3 setup, bypassing set_gateway_config()
    gateway.config["learning_sender"] = "eurid"

    with pytest.raises(ValueError, match="does not report its EURID"):
        await gateway.gateway_command(LearningToggle())


async def test_eurid_default_sender_config_falls_back_to_base_id(module):
    # e.g. a config restored from an ESP3 setup, bypassing set_gateway_config()
    gateway = Gateway("/dev/null", protocol=SerialProtocol.ESP2)
    gateway.config["default_sender"] = "eurid"
    address = EURID("01:23:45:67")
    # registered before start(): no base ID yet, so the device gets no sender of its own
    gateway.add_device(address, device_type_for_eep(EEP("A5-38-08")))
    await gateway.start(auto_reconnect=False)

    result = await gateway.send_command(address, CentralSwitch(switch_on=True))
    await gateway.stop()

    sent = ESP2Packet.from_bytes(module.written[-1])
    assert sent.header_sequence == ESP2HeaderSequence.TRT
    assert sent.sender == bytes(BASE_ID.bytelist)
    assert result.response.return_code == ResponseCode.OK


async def test_received_radio_telegram_reaches_erp1_callback(gateway, module):
    telegrams: list[ERP1Telegram] = []
    gateway.add_erp1_received_callback(telegrams.append)

    module.receive(RPS_PRESS)
    await asyncio.sleep(0)  # callbacks are dispatched via the event loop

    assert len(telegrams) == 1
    assert telegrams[0].rorg == RORG.RORG_RPS
    assert telegrams[0].sender == EURID("01:23:45:67")
    assert telegrams[0].telegram_data == b"\x70"
    assert telegrams[0].status == 0x30


def sender_number(number: int) -> EURID:
    return EURID(f"01:00:00:{number:02X}")


def telegram_from(sender: EURID) -> bytes:
    """A 4BS telegram (A5-04-02: 50 %, 20 °C) as the module reports it when received over the air."""
    return ESP2Packet(
        ESP2HeaderSequence.RRT,
        ESP2ORG.ORG_4BS,
        bytes([0x00, 125, 125, 0x0A]),
        bytes(sender.bytelist),
        0x00,
    ).to_bytes()


async def callbacks_have_run() -> None:
    """Callbacks are dispatched via the event loop; a decoded telegram takes several turns."""
    for _ in range(5):
        await asyncio.sleep(0)


async def test_new_sender_is_reported_once(gateway: Gateway, module: FakeESP2Module):
    new: list[EURID] = []
    gateway.add_new_device_callback(new.append)

    module.receive(telegram_from(sender_number(1)))
    module.receive(telegram_from(sender_number(1)))
    await callbacks_have_run()

    assert new == [sender_number(1)]


async def test_only_a_limited_number_of_senders_is_remembered(
    gateway: Gateway, module: FakeESP2Module, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("enocean_async.gateway.MAX_KNOWN_SENDERS", 3)
    new: list[EURID] = []
    gateway.add_new_device_callback(new.append)

    for number in range(1, 11):
        module.receive(telegram_from(sender_number(number)))
    await callbacks_have_run()

    assert new == [sender_number(number) for number in range(1, 11)]
    assert list(gateway._Gateway__known_senders) == [
        sender_number(n) for n in (8, 9, 10)
    ]


async def test_forgotten_sender_is_new_again_and_a_remembered_one_is_not(
    gateway: Gateway, module: FakeESP2Module, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("enocean_async.gateway.MAX_KNOWN_SENDERS", 3)
    new: list[EURID] = []
    for number in range(1, 5):
        module.receive(telegram_from(sender_number(number)))
    await callbacks_have_run()
    gateway.add_new_device_callback(new.append)

    module.receive(telegram_from(sender_number(4)))
    module.receive(telegram_from(sender_number(1)))
    await callbacks_have_run()

    assert new == [sender_number(1)]


async def test_registered_device_is_never_reported_as_new(
    gateway: Gateway, module: FakeESP2Module, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("enocean_async.gateway.MAX_KNOWN_SENDERS", 3)
    device = EURID("01:23:45:67")
    gateway.add_device(address=device, device_type=device_type_for_eep(EEP("A5-04-02")))
    new: list[EURID] = []
    gateway.add_new_device_callback(new.append)

    for number in range(1, 11):
        module.receive(telegram_from(sender_number(number)))
    module.receive(telegram_from(device))
    await callbacks_have_run()

    assert device not in new
    assert device not in gateway._Gateway__known_senders


async def test_removed_device_is_forgotten_as_a_sender(
    gateway: Gateway, module: FakeESP2Module
):
    device = EURID("01:23:45:67")
    module.receive(telegram_from(device))
    await callbacks_have_run()
    gateway.add_device(address=device, device_type=device_type_for_eep(EEP("A5-04-02")))

    gateway.remove_device(device)

    assert device not in gateway._Gateway__known_senders


async def test_send_radio_telegram_as_transmit_request(gateway, module):
    telegram = ERP1Telegram(
        rorg=RORG.RORG_RPS, telegram_data=b"\x70", sender=BASE_ID, status=0x30
    )

    result = await gateway.send_esp3_packet(telegram.to_esp3())

    assert module.written[-1] == bytes.fromhex("a55a6b0570000000ff80128030" + "21")
    assert result.response is not None
    assert result.response.return_code == ResponseCode.OK


async def test_send_telegram_esp2_cannot_carry_raises_and_sends_nothing(
    gateway, module
):
    written_before = len(module.written)
    telegram = ERP1Telegram(
        rorg=RORG.RORG_VLD, telegram_data=bytes.fromhex("0100"), sender=BASE_ID
    )

    with pytest.raises(ValueError):
        await gateway.send_esp3_packet(telegram.to_esp3())

    assert len(module.written) == written_before


def _sent_counts(observations: list[Observation]) -> list[int]:
    return [
        observation.values[Observable.TELEGRAMS_SENT]
        for observation in observations
        if Observable.TELEGRAMS_SENT in observation.values
    ]


async def test_command_esp2_cannot_carry_is_not_counted_as_sent(gateway, module):
    observations: list[Observation] = []
    gateway.add_observation_callback(observations.append)
    switch = EURID("01:23:45:67")
    gateway.add_device(switch, device_type_for_eep(EEP("D2-01-00")))
    written_before = len(module.written)

    with pytest.raises(ValueError, match="cannot be sent via ESP2"):
        await gateway.send_command(switch, SetSwitchOutput(output_value=100))
    await asyncio.sleep(0)  # callbacks are dispatched via the event loop

    assert len(module.written) == written_before
    assert _sent_counts(observations) == []


async def test_command_is_counted_once_as_sent(gateway):
    observations: list[Observation] = []
    gateway.add_observation_callback(observations.append)
    address = EURID("01:23:45:67")
    gateway.add_device(address, device_type_for_eep(EEP("A5-38-08")))

    await gateway.send_command(address, CentralSwitch(switch_on=True))
    await asyncio.sleep(0)  # callbacks are dispatched via the event loop

    assert _sent_counts(observations) == [1]


async def test_change_base_id_is_not_supported(gateway):
    with pytest.raises(BaseIDChangeError):
        await gateway.change_base_id(BaseAddress("FF:80:12:00"), safety_flag=0x7B)


async def test_stop_waits_until_the_port_is_released(module: FakeESP2Module):
    gateway = Gateway("/dev/null", protocol=SerialProtocol.ESP2)
    await gateway.start(auto_reconnect=False)
    module.port_released.clear()

    stop = asyncio.ensure_future(gateway.stop())
    await module.waiting_for_release.wait()

    assert module.closed
    assert not stop.done()

    module.port_released.set()
    await stop


async def test_failed_start_waits_until_the_port_is_released(
    module: FakeESP2Module, monkeypatch: pytest.MonkeyPatch
):
    def write(data: bytes) -> None:
        raise OSError("module does not take data")

    monkeypatch.setattr(module, "write", write)
    module.port_released.clear()
    gateway = Gateway("/dev/null", protocol=SerialProtocol.ESP2)

    start = asyncio.ensure_future(gateway.start(auto_reconnect=False))
    await module.waiting_for_release.wait()

    assert module.closed
    assert not start.done()

    module.port_released.set()
    with pytest.raises(ConnectionError):
        await start


async def test_stop_gives_up_on_a_port_that_is_not_released(
    module: FakeESP2Module, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("enocean_async.gateway._PORT_RELEASE_TIMEOUT", 0)
    gateway = Gateway("/dev/null", protocol=SerialProtocol.ESP2)
    await gateway.start(auto_reconnect=False)
    module.port_released.clear()

    await gateway.stop()

    assert module.closed
    assert module.waiting_for_release.is_set()

    # let the shielded wait finish
    module.port_released.set()
    await asyncio.sleep(0)


async def let_callbacks_run() -> None:
    """Callbacks are dispatched via the event loop; decoded values take several turns."""
    for _ in range(5):
        await asyncio.sleep(0)


def received_4bs(sender: EURID | BaseAddress, data: bytes) -> bytes:
    """A 4BS telegram as the module reports it when received over the air."""
    return ESP2Packet(
        ESP2HeaderSequence.RRT, ESP2ORG.ORG_4BS, data, bytes(sender.bytelist), 0x00
    ).to_bytes()


@pytest.mark.parametrize(
    "address",
    [
        pytest.param(EURID("01:23:45:67"), id="own_eurid"),
        pytest.param(BaseAddress("FF:AA:00:02"), id="base_address_of_another_gateway"),
    ],
)
async def test_telegram_of_registered_device_is_decoded(
    gateway: Gateway, module: FakeESP2Module, address: EURID | BaseAddress
):
    observations: list[Observation] = []
    gateway.add_device(
        address=address, device_type=device_type_for_eep(EEP("A5-04-02"))
    )
    gateway.add_observation_callback(observations.append)

    module.receive(received_4bs(address, bytes([0x00, 125, 125, 0x0A])))
    await let_callbacks_run()

    decoded = {
        observation.entity: observation.values
        for observation in observations
        if observation.device == address
    }
    assert decoded["temperature"] == {Observable.TEMPERATURE: 20.0}
    assert decoded["humidity"] == {Observable.HUMIDITY: 50.0}


async def test_telegram_of_unregistered_base_address_is_not_decoded(
    gateway: Gateway, module: FakeESP2Module
):
    observations: list[Observation] = []
    gateway.add_observation_callback(observations.append)

    module.receive(
        received_4bs(BaseAddress("FF:AA:00:02"), bytes([0x00, 125, 125, 0x0A]))
    )
    await let_callbacks_run()

    assert not [o for o in observations if o.entity in ("temperature", "humidity")]


# Sender slots of devices the gateway teaches in (#4): a sender-addressed device, e.g. an Eltako
# FSB61 shutter actuator, reacts to every telegram from a sender it has learned. Devices that learned
# the same sender all react to it, so each one needs a slot of its own (BaseID+1…+127).

FSB = device_type_for_eep(EEP("A5-7F-3F.ELTAKO.FSB"))
"""A sender-addressed device which the gateway teaches in with a learn telegram."""

SHUTTERS = [EURID("04:2C:42:C1"), EURID("04:2C:45:28"), EURID("04:2D:A2:E3")]


def sender_slot(offset: int) -> BaseAddress:
    return BaseAddress(int(BASE_ID) + offset)


def registered_device(gateway: Gateway, address: EURID):
    return gateway._Gateway__devices[address]


def radio_senders(module: FakeESP2Module) -> list[BaseAddress]:
    """The senders of the radio telegrams the gateway has sent."""
    packets = [ESP2Packet.from_bytes(frame) for frame in module.written]
    return [
        BaseAddress(packet.sender)
        for packet in packets
        if packet.header_sequence == ESP2HeaderSequence.TRT
    ]


async def teach_in(gateway: Gateway, address: EURID) -> None:
    await gateway.send_command(address, LearnTelegram(entity_id="learn_telegram"))


async def test_each_taught_in_device_gets_its_own_sender_slot(gateway: Gateway):
    for address in SHUTTERS:
        gateway.add_device(address=address, device_type=FSB)
    for address in SHUTTERS:
        await teach_in(gateway, address)

    assert [registered_device(gateway, a).sender for a in SHUTTERS] == [
        sender_slot(1),
        sender_slot(2),
        sender_slot(3),
    ]
    assert [registered_device(gateway, a).config["sender_slot"] for a in SHUTTERS] == [
        "1",
        "2",
        "3",
    ]
    # how an integration finds the slot to keep it
    assert gateway.sender_slots[sender_slot(2)] == [SHUTTERS[1]]


async def test_device_not_taught_in_sends_from_the_default_sender(
    gateway: Gateway, module: FakeESP2Module
):
    """A device taught in by an earlier version learned BaseID+0, so it must keep using it."""
    gateway.add_device(address=SHUTTERS[0], device_type=FSB)

    await gateway.send_command(SHUTTERS[0], CoverStop(entity_id="cover"))

    assert radio_senders(module) == [BASE_ID]
    assert registered_device(gateway, SHUTTERS[0]).sender is None
    assert registered_device(gateway, SHUTTERS[0]).config["sender_slot"] == "auto"


async def test_command_before_the_teach_in_does_not_fix_the_sender(
    gateway: Gateway, module: FakeESP2Module
):
    gateway.add_device(address=SHUTTERS[0], device_type=FSB)

    await gateway.send_command(SHUTTERS[0], CoverStop(entity_id="cover"))
    await teach_in(gateway, SHUTTERS[0])
    await gateway.send_command(SHUTTERS[0], CoverStop(entity_id="cover"))

    assert radio_senders(module) == [BASE_ID, sender_slot(1), sender_slot(1)]


async def test_explicit_sender_slot_is_kept_for_the_teach_in(gateway: Gateway):
    gateway.add_device(address=SHUTTERS[0], device_type=FSB, sender=sender_slot(5))

    await teach_in(gateway, SHUTTERS[0])

    assert registered_device(gateway, SHUTTERS[0]).sender == sender_slot(5)


async def test_teach_in_does_not_take_a_slot_in_use(gateway: Gateway):
    gateway.add_device(address=SHUTTERS[0], device_type=FSB, sender=sender_slot(1))
    gateway.add_device(address=SHUTTERS[1], device_type=FSB)

    await teach_in(gateway, SHUTTERS[1])

    assert registered_device(gateway, SHUTTERS[1]).sender == sender_slot(2)


async def test_destination_addressed_device_gets_the_default_sender(gateway: Gateway):
    address = EURID("05:00:00:01")

    gateway.add_device(
        address=address, device_type=device_type_for_eep(EEP("D2-01-00"))
    )

    assert registered_device(gateway, address).sender == BASE_ID
    assert registered_device(gateway, address).config["sender_slot"] == "0"


def received_rps(sender: EURID | BaseAddress, data: int, status: int) -> bytes:
    """An RPS telegram as the module reports it when received over the air."""
    return ESP2Packet(
        ESP2HeaderSequence.RRT,
        ESP2ORG.ORG_RPS,
        bytes([data, 0, 0, 0]),
        bytes(sender.bytelist),
        status,
    ).to_bytes()


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [
        pytest.param(0x30, 0x21, [True, False], id="water_then_repeated_no_water"),
        pytest.param(0x20, 0x31, [False, True], id="no_water_then_repeated_water"),
        pytest.param(0x30, 0x31, [True], id="repeated_copy_is_dropped"),
    ],
)
async def test_telegrams_which_differ_in_the_status_only_are_not_repeats(
    gateway: Gateway,
    module: FakeESP2Module,
    first: int,
    second: int,
    expected: list[bool],
):
    sensor = EURID("01:23:45:67")
    observations: list[Observation] = []
    gateway.add_device(
        address=sensor, device_type=device_type_for_eep(EEP("F6-05-01.ELTAKO"))
    )
    gateway.add_observation_callback(observations.append)

    module.receive(received_rps(sensor, 0x11, first))
    module.receive(received_rps(sensor, 0x11, second))
    await let_callbacks_run()

    assert [
        observation.values[Observable.WATER_DETECTED]
        for observation in observations
        if observation.entity == "water_detected"
    ] == expected
