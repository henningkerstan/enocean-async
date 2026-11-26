"""Tests for A5-14-09 (window/door sensor with states open/closed/tilt, supply voltage)."""

import pytest

from enocean_async import EEP, EURID, Observable
from enocean_async.eep import DEVICE_TYPES, EEP_SPECIFICATIONS
from enocean_async.eep.handler import EEPHandler
from enocean_async.eep.manufacturer import Manufacturer
from enocean_async.protocol.erp1.rorg import RORG
from enocean_async.protocol.erp1.telegram import ERP1Telegram

SENDER = EURID("01:02:03:04")


def decode(data: str) -> dict:
    telegram = ERP1Telegram(RORG.RORG_4BS, bytes.fromhex(data), SENDER)
    message = EEPHandler(EEP_SPECIFICATIONS[EEP("A5-14-09")]).decode(telegram)
    return {observable: value.value for observable, value in message.values.items()}


@pytest.mark.parametrize(
    ("data", "state", "voltage"),
    [
        # DB0 as in the Eltako manual of the FFG7B: 0x08, 0x0A, 0x0E
        pytest.param("96000008", "closed", 3.0, id="closed"),
        pytest.param("0000000A", "tilted", 0.0, id="tilted"),
        pytest.param("FA00000E", "open", 5.0, id="open"),
    ],
)
def test_window_state_and_supply_voltage(data: str, state: str, voltage: float):
    values = decode(data)

    assert values[Observable.WINDOW_STATE] == state
    assert values[Observable.VOLTAGE] == pytest.approx(voltage)


def test_reserved_contact_value_gives_no_window_state():
    values = decode("9600000C")

    assert Observable.WINDOW_STATE not in values
    assert values[Observable.VOLTAGE] == pytest.approx(3.0)


def test_teach_in_telegram_gives_no_window_state():
    # the learn telegram of the Eltako FFG7B
    values = decode("50480D80")

    assert Observable.WINDOW_STATE not in values


def test_entities():
    spec = EEP_SPECIFICATIONS[EEP("A5-14-09")]

    assert [entity.id for entity in spec.entities] == ["supply_voltage", "window_state"]


def test_eltako_ffg7b_is_listed():
    device_type = DEVICE_TYPES["ELTAKO/FFG7B"]

    assert device_type.manufacturer == Manufacturer.ELTAKO
    assert device_type.eep == EEP("A5-14-09")
