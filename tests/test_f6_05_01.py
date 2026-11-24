"""Tests for F6-05-01 (liquid leakage sensor) and for fields in the status byte."""

import pytest

from enocean_async import EEP, EURID, Observable
from enocean_async.eep import DEVICE_TYPES, EEP_SPECIFICATIONS
from enocean_async.eep.handler import EEPHandler
from enocean_async.eep.manufacturer import Manufacturer
from enocean_async.eep.message import EEPMessageType, RawEEPMessage
from enocean_async.eep.profile import (
    EEPDataField,
    EEPTelegram,
    SimpleProfileSpecification,
)
from enocean_async.protocol.erp1.rorg import RORG
from enocean_async.protocol.erp1.telegram import ERP1Telegram

SENDER = EURID("01:02:03:04")
GENERIC = EEP("F6-05-01")
FWS81 = EEP("F6-05-01", Manufacturer.ELTAKO)


def decode(eep: EEP, data: int, status: int) -> dict:
    telegram = ERP1Telegram(RORG.RORG_RPS, bytes([data]), SENDER, status=status)
    message = EEPHandler(EEP_SPECIFICATIONS[eep]).decode(telegram)
    return {observable: value.value for observable, value in message.values.items()}


def test_generic_profile_reports_water():
    assert decode(GENERIC, 0x11, 0x30) == {Observable.WATER_DETECTED: True}


@pytest.mark.parametrize(
    ("data", "status"),
    [
        pytest.param(0x00, 0x30, id="unknown_data_byte"),
        pytest.param(0x70, 0x30, id="rocker_data_byte"),
        pytest.param(0x11, 0x20, id="status_the_eep_does_not_define"),
    ],
)
def test_generic_profile_says_nothing_else(data: int, status: int):
    assert decode(GENERIC, data, status) == {}


@pytest.mark.parametrize(
    ("status", "water"),
    [
        pytest.param(0x30, True, id="water"),
        pytest.param(0x20, False, id="no_water"),
        pytest.param(0x31, True, id="water_repeated_once"),
        pytest.param(0x21, False, id="no_water_repeated_once"),
    ],
)
def test_fws81_reads_water_from_the_status_byte(status: int, water: bool):
    assert decode(FWS81, 0x11, status) == {Observable.WATER_DETECTED: water}


@pytest.mark.parametrize(
    ("data", "status"),
    [
        pytest.param(0x70, 0x30, id="rocker_pressed"),
        pytest.param(0x00, 0x20, id="rocker_released"),
    ],
)
def test_fws81_ignores_any_other_data_byte(data: int, status: int):
    assert decode(FWS81, data, status) == {}


def test_fws81_is_listed():
    assert any(
        d.manufacturer == Manufacturer.ELTAKO and d.model == "FWS81" and d.eep == FWS81
        for d in DEVICE_TYPES.values()
    )


@pytest.mark.parametrize(
    ("offset", "size", "status", "expected"),
    [
        pytest.param(2, 1, 0x20, 1, id="t21_set"),
        pytest.param(2, 1, 0x10, 0, id="t21_not_set"),
        pytest.param(2, 2, 0x30, 3, id="t21_and_nu"),
        pytest.param(4, 4, 0x3A, 0x0A, id="low_nibble"),
        pytest.param(0, 8, 0xA5, 0xA5, id="whole_byte"),
    ],
)
def test_status_field_is_read_from_the_status_byte(
    offset: int, size: int, status: int, expected: int
):
    field = EEPDataField(id="X", name="X", offset=offset, size=size, in_status=True)
    handler = EEPHandler(
        SimpleProfileSpecification(eep=GENERIC, name="test", datafields=[field])
    )

    message = handler.decode(
        ERP1Telegram(RORG.RORG_RPS, bytes([0x11]), SENDER, status=status)
    )

    assert message.raw["X"] == expected
    assert message.decoded["X"].value == expected


@pytest.mark.parametrize(
    ("offset", "size"),
    [
        pytest.param(-1, 1, id="before_the_byte"),
        pytest.param(8, 1, id="after_the_byte"),
        pytest.param(6, 4, id="over_the_end"),
        pytest.param(0, 0, id="no_bits"),
    ],
)
def test_status_field_outside_the_status_byte_is_rejected(offset: int, size: int):
    with pytest.raises(ValueError, match="status byte"):
        EEPDataField(id="X", name="X", offset=offset, size=size, in_status=True)


def test_status_field_does_not_count_for_the_size_of_the_data():
    telegram = EEP_SPECIFICATIONS[FWS81].telegrams[0x11]

    assert telegram.byte_size == 1
    assert EEPTelegram(name=None, datafields=[]).byte_size == 0


def test_status_field_is_not_written_when_encoding():
    handler = EEPHandler(EEP_SPECIFICATIONS[FWS81])
    message = RawEEPMessage(
        sender=SENDER, message_type=EEPMessageType(id=0x11, description="")
    )
    message.raw["NU"] = 1

    telegram = handler.encode(message)

    assert telegram.telegram_data == bytes([0x11])
    assert telegram.status == 0x00
