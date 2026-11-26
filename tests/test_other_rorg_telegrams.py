"""Tests for telegrams with another RORG than the EEP's, and for the Eltako FSB, which sends them."""

import pytest

from enocean_async import EEP, EURID, Observable
from enocean_async.eep import EEP_SPECIFICATIONS
from enocean_async.eep.handler import EEPHandler
from enocean_async.eep.profile import (
    EEPDataField,
    EEPTelegram,
    SimpleProfileSpecification,
)
from enocean_async.protocol.erp1.rorg import RORG
from enocean_async.protocol.erp1.telegram import ERP1Telegram

SENDER = EURID("01:02:03:04")

SPEC_WITH_ANOTHER_RORG = SimpleProfileSpecification(
    eep=EEP("A5-02-05"),
    name="4BS profile whose device confirms with RPS",
    datafields=[
        EEPDataField(
            id="TMP",
            name="Temperature",
            offset=16,
            size=8,
            observable=Observable.TEMPERATURE,
        )
    ],
    other_rorg_telegrams={
        RORG.RORG_RPS: EEPTelegram(
            name="Confirmation",
            datafields=[EEPDataField(id="CONF", name="Confirmation", offset=0, size=8)],
        )
    },
)


def test_telegram_with_another_rorg_is_decoded_with_its_own_fields():
    telegram = ERP1Telegram(RORG.RORG_RPS, bytes([0x70]), SENDER)

    message = EEPHandler(SPEC_WITH_ANOTHER_RORG).decode(telegram)

    assert message.raw == {"CONF": 0x70}
    assert message.message_type.description == "Confirmation"
    assert Observable.TEMPERATURE not in message.values


def test_telegram_with_the_eeps_own_rorg_is_decoded_as_before():
    telegram = ERP1Telegram(RORG.RORG_4BS, bytes([0, 0, 0x80, 0x08]), SENDER)

    message = EEPHandler(SPEC_WITH_ANOTHER_RORG).decode(telegram)

    assert message.raw == {"TMP": 0x80}
    assert Observable.TEMPERATURE in message.values


def test_profile_declares_no_other_rorg_telegrams_by_default():
    assert EEP_SPECIFICATIONS[EEP("A5-02-05")].other_rorg_telegrams == {}


# ---------------------------------------------------------------------------
# Eltako FSB (FSB14, FSB61, FSB71): a 4BS profile with RPS confirmations
# ---------------------------------------------------------------------------

FSB = EEP("A5-3F-7F.ELTAKO.FSB")


def decode_fsb(rorg: RORG, data: str, config: dict | None = None) -> dict:
    telegram = ERP1Telegram(rorg, bytes.fromhex(data), SENDER)
    message = EEPHandler(EEP_SPECIFICATIONS[FSB]).decode(telegram, config)
    return {observable: value.value for observable, value in message.values.items()}


@pytest.mark.parametrize(
    ("data", "state"),
    [
        pytest.param("01", "opening", id="started_up"),
        pytest.param("02", "closing", id="started_down"),
        pytest.param("70", "open", id="upper_end_position"),
        pytest.param("50", "closed", id="lower_end_position"),
    ],
)
def test_fsb_rps_confirmation_gives_the_cover_state(data: str, state: str):
    assert decode_fsb(RORG.RORG_RPS, data) == {Observable.COVER_STATE: state}


@pytest.mark.parametrize("data", ["00", "30", "10", "FF"])
def test_fsb_other_rps_telegram_gives_no_cover_state(data: str):
    assert decode_fsb(RORG.RORG_RPS, data) == {}


@pytest.mark.parametrize(
    ("data", "config"),
    [
        pytest.param("0020020A", None, id="3.2_s_down"),
        pytest.param("0078010A", None, id="12_s_up"),
        pytest.param("0078010E", None, id="blocked"),
        # also after more than the configured travel time: a full movement ends
        # with the RPS telegram of an end position, never with this one
        pytest.param("0384010A", {"max_travel_time": 60}, id="longer_than_travel_time"),
        pytest.param("0064020A", {"max_travel_time": None}, id="no_travel_time_set"),
    ],
)
def test_fsb_status_telegram_means_the_cover_was_stopped(
    data: str, config: dict | None
):
    assert decode_fsb(RORG.RORG_4BS, data, config) == {
        Observable.COVER_STATE: "stopped"
    }


@pytest.mark.parametrize(
    "data",
    [
        pytest.param("FFF80D80", id="learn_telegram"),
        pytest.param("00200102", id="teach_in_bit"),
        pytest.param("0020000A", id="direction_0"),
        pytest.param("0020030A", id="direction_3"),
    ],
)
def test_fsb_learn_telegram_and_unknown_direction_give_no_cover_state(data: str):
    assert decode_fsb(RORG.RORG_4BS, data) == {}
