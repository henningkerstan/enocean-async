"""Tests for A5-07-01 (occupancy with supply voltage monitor)."""

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
    message = EEPHandler(EEP_SPECIFICATIONS[EEP("A5-07-01")]).decode(telegram)
    return {observable: value.value for observable, value in message.values.items()}


@pytest.mark.parametrize(
    ("data", "motion"),
    [
        # DB1 as in the Eltako manual of the FB65B: 0xC8 and 0xFF
        pytest.param("0000C808", True, id="eltako_semi_automatic"),
        pytest.param("0000FF08", True, id="eltako_fully_automatic"),
        pytest.param("00008008", True, id="lowest_value_for_on"),
        pytest.param("00007F08", False, id="highest_value_for_off"),
        pytest.param("00000008", False, id="off"),
    ],
)
def test_motion_is_a_boolean(data: str, motion: bool):
    assert decode(data) == {Observable.MOTION: motion}


@pytest.mark.parametrize(
    ("data", "voltage"),
    [
        pytest.param("96000009", 3.0, id="3_volts"),
        pytest.param("FA000009", 5.0, id="5_volts"),
        pytest.param("00000009", 0.0, id="0_volts"),
        pytest.param("96000008", None, id="not_supported"),
        pytest.param("FB000009", None, id="error_code"),
    ],
)
def test_supply_voltage_only_if_supported(data: str, voltage: float | None):
    values = decode(data)

    if voltage is None:
        assert Observable.VOLTAGE not in values
    else:
        assert values[Observable.VOLTAGE] == pytest.approx(voltage)


def test_entities():
    spec = EEP_SPECIFICATIONS[EEP("A5-07-01")]

    assert [entity.id for entity in spec.entities] == ["supply_voltage", "motion"]


def test_eltako_fb65b_is_listed():
    device_type = DEVICE_TYPES["ELTAKO/FB65B"]

    assert device_type.manufacturer == Manufacturer.ELTAKO
    assert device_type.eep == EEP("A5-07-01")
