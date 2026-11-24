"""Tests for D5-00-01 (single input contact, 1BS)."""

import pytest

from enocean_async import EEP, EURID, Observable
from enocean_async.eep import DEVICE_TYPES, EEP_SPECIFICATIONS
from enocean_async.eep.handler import EEPHandler
from enocean_async.eep.manufacturer import Manufacturer
from enocean_async.protocol.erp1.rorg import RORG
from enocean_async.protocol.erp1.telegram import ERP1Telegram

SENDER = EURID("01:02:03:04")


def telegram(db0: int) -> ERP1Telegram:
    return ERP1Telegram(RORG.RORG_1BS, bytes([db0]), SENDER)


@pytest.mark.parametrize(
    ("db0", "expected"),
    [
        pytest.param(0x08, True, id="open"),
        pytest.param(0x09, False, id="closed"),
    ],
)
def test_contact_state_is_decoded(db0: int, expected: bool):
    handler = EEPHandler(EEP_SPECIFICATIONS[EEP("D5-00-01")])

    message = handler.decode(telegram(db0))

    assert message.values[Observable.CONTACT_STATE].value is expected


def test_lrn_bit_marks_teach_in_telegram():
    # DB0.3 (LRN) = 0: teach-in, which the gateway does not decode as data
    assert telegram(0x00).is_learning_telegram
    assert not telegram(0x08).is_learning_telegram


def test_nodon_sdo_2_1_05_is_listed():
    assert any(
        d.manufacturer == Manufacturer.NODON
        and d.model == "SDO-2-1-05"
        and d.eep == EEP("D5-00-01")
        for d in DEVICE_TYPES.values()
    )
