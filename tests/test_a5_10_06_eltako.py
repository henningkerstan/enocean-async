"""Tests for the Eltako variant of A5-10-06 (temperature controllers FTR55ESB and siblings)."""

import pytest

from enocean_async import EEP, EURID, Observable
from enocean_async.eep import DEVICE_TYPES, EEP_SPECIFICATIONS
from enocean_async.eep.handler import EEPHandler
from enocean_async.eep.manufacturer import Manufacturer
from enocean_async.protocol.erp1.rorg import RORG
from enocean_async.protocol.erp1.telegram import ERP1Telegram

SENDER = EURID("01:02:03:04")
ELTAKO = EEP("A5-10-06", Manufacturer.ELTAKO)


def decode(eep: EEP, data: str) -> dict:
    telegram = ERP1Telegram(RORG.RORG_4BS, bytes.fromhex(data), SENDER)
    message = EEPHandler(EEP_SPECIFICATIONS[eep]).decode(telegram)
    return {observable: value.value for observable, value in message.values.items()}


@pytest.mark.parametrize(
    ("data", "set_point", "temperature"),
    [
        pytest.param("0082620F", 20.4, 24.6, id="captured_from_an_ftr55esb"),
        pytest.param("0000FF0F", 0.0, 0.0, id="lower_end_of_both_scales"),
        pytest.param("00FF000F", 40.0, 40.0, id="upper_end_of_both_scales"),
        pytest.param("00B3750F", 28.1, 21.6, id="captured_at_the_28_mark"),
        pytest.param("0032750F", 7.8, 21.6, id="captured_at_the_lower_stop"),
    ],
)
def test_set_point_is_a_temperature(data: str, set_point: float, temperature: float):
    values = decode(ELTAKO, data)

    assert values == {
        Observable.TEMPERATURE_SETPOINT: pytest.approx(set_point, abs=0.05),
        Observable.TEMPERATURE: pytest.approx(temperature, abs=0.05),
    }


def test_the_generic_profile_is_unchanged():
    """The set point of the generic A5-10-06 has no unit, and it has a day/night switch."""
    values = decode(EEP("A5-10-06"), "0082620F")

    assert values[Observable.SET_POINT] == pytest.approx(130.0)
    assert Observable.DAY_NIGHT in values
    assert Observable.TEMPERATURE_SETPOINT not in values


def test_ftr55esb_is_in_the_device_catalog():
    assert DEVICE_TYPES["ELTAKO/FTR55ESB"].eep == ELTAKO
