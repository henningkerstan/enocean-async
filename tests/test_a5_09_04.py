"""Tests for A5-09-04 (CO2 sensor with humidity and temperature)."""

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
    message = EEPHandler(EEP_SPECIFICATIONS[EEP("A5-09-04")]).decode(telegram)
    return {observable: value.value for observable, value in message.values.items()}


@pytest.mark.parametrize(
    ("data", "co2", "humidity", "temperature"),
    [
        pytest.param("0000000E", 0.0, 0.0, 0.0, id="lowest"),
        pytest.param("6450800E", 800.0, 50.0, 25.6, id="room_air"),
        pytest.param("C8FFFF0E", 2550.0, 100.0, 51.0, id="highest"),
        pytest.param("6450800C", 800.0, 50.0, None, id="no_temperature_sensor"),
        pytest.param("6450800A", 800.0, None, 25.6, id="no_humidity_sensor"),
        pytest.param("64508008", 800.0, None, None, id="co2_only"),
        pytest.param("C950800E", 800.0, None, 25.6, id="humidity_out_of_range"),
    ],
)
def test_values(
    data: str, co2: float, humidity: float | None, temperature: float | None
):
    expected = {Observable.CO2: co2}
    if humidity is not None:
        expected[Observable.HUMIDITY] = humidity
    if temperature is not None:
        expected[Observable.TEMPERATURE] = temperature

    assert decode(data) == pytest.approx(expected)


def test_entities_and_unit():
    spec = EEP_SPECIFICATIONS[EEP("A5-09-04")]

    assert [entity.id for entity in spec.entities] == ["co2", "humidity", "temperature"]
    assert Observable.CO2.unit == "ppm"


def test_eltako_fco2ts_is_listed():
    device_type = DEVICE_TYPES["ELTAKO/FCO2TS"]

    assert device_type.manufacturer == Manufacturer.ELTAKO
    assert device_type.eep == EEP("A5-09-04")
