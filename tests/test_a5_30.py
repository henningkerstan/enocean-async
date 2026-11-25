"""Tests for A5-30 (digital input) and the Eltako FSM60B water sensor variants."""

import pytest

from enocean_async import EEP, EURID, Observable
from enocean_async.eep import DEVICE_TYPES, EEP_SPECIFICATIONS
from enocean_async.eep.handler import EEPHandler
from enocean_async.eep.manufacturer import Manufacturer
from enocean_async.protocol.erp1.rorg import RORG
from enocean_async.protocol.erp1.telegram import ERP1Telegram

SENDER = EURID("01:02:03:04")


def decode(eep: str, data: str) -> dict:
    telegram = ERP1Telegram(RORG.RORG_4BS, bytes.fromhex(data), SENDER)
    message = EEPHandler(EEP_SPECIFICATIONS[EEP(eep)]).decode(telegram)
    return {observable: value.value for observable, value in message.values.items()}


@pytest.mark.parametrize(
    ("data", "is_open", "battery_low"),
    [
        pytest.param("00FF0008", False, False, id="closed_battery_ok"),
        pytest.param("0000FF08", True, True, id="open_battery_low"),
        pytest.param("0079C308", False, False, id="upper_limit_of_closed"),
        pytest.param("0078C408", True, True, id="lower_limit_of_open"),
    ],
)
def test_a5_30_01_contact_and_battery(data: str, is_open: bool, battery_low: bool):
    values = decode("A5-30-01", data)

    assert values == {
        Observable.CONTACT_STATE: is_open,
        Observable.BATTERY_LOW: battery_low,
    }


@pytest.mark.parametrize(
    ("data", "temperature"),
    [
        pytest.param("00FF0008", 0.0, id="coldest"),
        pytest.param("00000008", 40.0, id="warmest"),
    ],
)
def test_a5_30_03_temperature(data: str, temperature: float):
    values = decode("A5-30-03", data)

    assert values == {Observable.TEMPERATURE: pytest.approx(temperature)}


def test_a5_30_03_inputs_are_decoded_but_not_interpreted():
    telegram = ERP1Telegram(RORG.RORG_4BS, bytes.fromhex("00001508"), SENDER)

    message = EEPHandler(EEP_SPECIFICATIONS[EEP("A5-30-03")]).decode(telegram)

    assert {
        field: message.decoded[field].value
        for field in ("WA0", "DI3", "DI2", "DI1", "DI0")
    } == {"WA0": "High", "DI3": "Low", "DI2": "High", "DI1": "Low", "DI0": "High"}
    assert set(message.values) == {Observable.TEMPERATURE}


@pytest.mark.parametrize(
    ("data", "water"),
    [
        pytest.param("00000F08", True, id="wake_low_is_water"),
        pytest.param("00001F08", False, id="wake_high_is_no_water"),
        pytest.param("00000008", True, id="inputs_do_not_count_for_water"),
        pytest.param("00001008", False, id="inputs_do_not_count_for_no_water"),
    ],
)
def test_fsm60b_a5_30_03_reports_water(data: str, water: bool):
    values = decode("A5-30-03.ELTAKO.FSM60B", data)

    assert values == {Observable.WATER_DETECTED: water}


@pytest.mark.parametrize(
    ("data", "water", "battery_low"),
    [
        pytest.param("00FF0008", True, False, id="closed_is_water"),
        pytest.param("00FFFF08", False, False, id="open_is_no_water"),
        pytest.param("0000FF08", False, True, id="battery_low"),
    ],
)
def test_fsm60b_a5_30_01_reports_water_and_battery(
    data: str, water: bool, battery_low: bool
):
    values = decode("A5-30-01.ELTAKO.FSM60B", data)

    assert values == {
        Observable.WATER_DETECTED: water,
        Observable.BATTERY_LOW: battery_low,
    }


def test_teach_in_telegram_is_not_data():
    # DB0.3 (LRN) = 0: teach-in, which the gateway does not decode as data
    assert ERP1Telegram(
        RORG.RORG_4BS, bytes.fromhex("C0182D80"), SENDER
    ).is_learning_telegram
    assert not ERP1Telegram(
        RORG.RORG_4BS, bytes.fromhex("00000F08"), SENDER
    ).is_learning_telegram


def test_fsm60b_is_listed_with_its_factory_setting():
    assert any(
        d.manufacturer == Manufacturer.ELTAKO
        and d.model == "FSM60B"
        and d.eep == EEP("A5-30-03.ELTAKO.FSM60B")
        for d in DEVICE_TYPES.values()
    )
