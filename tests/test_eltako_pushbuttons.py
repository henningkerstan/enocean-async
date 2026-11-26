"""Tests for the Eltako pushbuttons and hand-held transmitters in the device catalog (F6-02-01)."""

import pytest

from enocean_async import EEP, EURID
from enocean_async.eep import DEVICE_TYPES, EEP_SPECIFICATIONS
from enocean_async.eep.handler import EEPHandler
from enocean_async.eep.manufacturer import Manufacturer
from enocean_async.protocol.erp1.rorg import RORG
from enocean_async.protocol.erp1.telegram import ERP1Telegram

SENDER = EURID("01:02:03:04")
PRESSED = 0x30
RELEASED = 0x20


@pytest.mark.parametrize("model", ["FT55", "F2T55E", "F4T55E", "FMH8"])
def test_pushbutton_is_listed_with_f6_02_01(model: str):
    device_type = DEVICE_TYPES[f"ELTAKO/{model}"]

    assert device_type.manufacturer == Manufacturer.ELTAKO
    assert device_type.eep == EEP("F6-02-01")


@pytest.mark.parametrize(
    ("data", "button"),
    [
        # the four codes a radio module sends, as in the Eltako manuals of the
        # pushbuttons and of the FMH8 (two modules, the same four codes each)
        pytest.param(0x70, "b0", id="0x70"),
        pytest.param(0x50, "b1", id="0x50"),
        pytest.param(0x30, "a0", id="0x30"),
        pytest.param(0x10, "a1", id="0x10"),
    ],
)
def test_button_press_is_decoded(data: int, button: str):
    handler = EEPHandler(EEP_SPECIFICATIONS[EEP("F6-02-01")])

    message = handler.decode(
        ERP1Telegram(RORG.RORG_RPS, bytes([data]), SENDER, PRESSED)
    )

    assert message.decoded["R1"].value == button
    assert message.decoded["EB"].value == "pressed"
    assert message.decoded["SA"].value == "No 2nd action"


def test_release_is_decoded():
    handler = EEPHandler(EEP_SPECIFICATIONS[EEP("F6-02-01")])

    message = handler.decode(
        ERP1Telegram(RORG.RORG_RPS, bytes([0x00]), SENDER, RELEASED)
    )

    assert message.decoded["EB"].value == "released"


def test_two_buttons_pressed_at_once_are_both_decoded():
    # as sent by a pushbutton with two rockers: a1 together with b0
    handler = EEPHandler(EEP_SPECIFICATIONS[EEP("F6-02-01")])

    message = handler.decode(
        ERP1Telegram(RORG.RORG_RPS, bytes([0x17]), SENDER, PRESSED)
    )

    assert message.decoded["R1"].value == "a1"
    assert message.decoded["R2"].value == "b0"
    assert message.decoded["SA"].value == "2nd action valid"
