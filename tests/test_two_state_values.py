"""Tests for two-state values: motion, contact, occupancy button, day/night and error level are booleans."""

import pytest

from enocean_async.address import EURID
from enocean_async.eep import EEP_SPECIFICATIONS
from enocean_async.eep.handler import EEPHandler
from enocean_async.eep.id import EEP
from enocean_async.eep.manufacturer import Manufacturer
from enocean_async.protocol.erp1.rorg import RORG
from enocean_async.protocol.erp1.telegram import ERP1Telegram
from enocean_async.semantics.observable import Observable
from enocean_async.semantics.value_kind import ValueKind

SENDER = EURID("01:23:45:67")


def _decode(eep: EEP, rorg: RORG, data: str) -> dict:
    telegram = ERP1Telegram(rorg=rorg, telegram_data=bytes.fromhex(data), sender=SENDER)
    message = EEPHandler(EEP_SPECIFICATIONS[eep]).decode(telegram)
    return {observable: value.value for observable, value in message.values.items()}


@pytest.mark.parametrize(
    ("eep", "data", "observable", "expected"),
    [
        # motion
        (EEP("A5-07-03"), "00000080", Observable.MOTION, True),
        (EEP("A5-07-03"), "00000000", Observable.MOTION, False),
        (EEP("A5-08-01"), "96640008", Observable.MOTION, True),
        (EEP("A5-08-01"), "9664000A", Observable.MOTION, False),
        (EEP("A5-08-01", Manufacturer.ELTAKO), "9664000D", Observable.MOTION, True),
        (EEP("A5-08-01", Manufacturer.ELTAKO), "9664000F", Observable.MOTION, False),
        # occupancy button: pressed
        (EEP("A5-08-01"), "9664000A", Observable.OCCUPANCY_BUTTON, True),
        (EEP("A5-08-01"), "9664000B", Observable.OCCUPANCY_BUTTON, False),
        (EEP("A5-10-01"), "00000008", Observable.OCCUPANCY_BUTTON, True),
        (EEP("A5-10-01"), "00000009", Observable.OCCUPANCY_BUTTON, False),
        (EEP("A5-10-18"), "00000008", Observable.OCCUPANCY_BUTTON, True),
        (EEP("A5-10-18"), "00000009", Observable.OCCUPANCY_BUTTON, False),
        # occupancy of type 23: occupied
        (EEP("A5-10-23"), "00000009", Observable.OCCUPANCY_BUTTON, True),
        (EEP("A5-10-23"), "00000008", Observable.OCCUPANCY_BUTTON, False),
        # day and night: day
        (EEP("A5-10-02"), "00000009", Observable.DAY_NIGHT, True),
        (EEP("A5-10-02"), "00000008", Observable.DAY_NIGHT, False),
        # contact: open
        (EEP("A5-10-0A"), "00000009", Observable.CONTACT_STATE, True),
        (EEP("A5-10-0A"), "00000008", Observable.CONTACT_STATE, False),
    ],
)
def test_two_state_values_are_booleans(
    eep: EEP, data: str, observable: Observable, expected: bool
):
    values = _decode(eep, RORG.RORG_4BS, data)

    assert values[observable] is expected


@pytest.mark.parametrize(("data", "is_open"), [("08", True), ("09", False)])
def test_d5_00_01_contact_is_open_or_not(data: str, is_open: bool):
    values = _decode(EEP("D5-00-01"), RORG.RORG_1BS, data)

    assert values == {Observable.CONTACT_STATE: is_open}


def test_text_of_a_two_state_field_is_kept_beside_the_boolean():
    telegram = ERP1Telegram(
        rorg=RORG.RORG_1BS, telegram_data=bytes([0x08]), sender=SENDER
    )

    message = EEPHandler(EEP_SPECIFICATIONS[EEP("D5-00-01")]).decode(telegram)

    assert message.decoded["CO"].value == "Open"
    assert message.values[Observable.CONTACT_STATE].value is True


@pytest.mark.parametrize("data", ["9664000C", "9664000E", "96640008", "96640000"])
def test_value_the_enumeration_does_not_know_gives_no_two_state_value(data: str):
    values = _decode(EEP("A5-08-01", Manufacturer.ELTAKO), RORG.RORG_4BS, data)

    assert Observable.MOTION not in values
    assert Observable.ILLUMINATION in values


@pytest.mark.parametrize(
    ("data", "problem"),
    [
        pytest.param("040000", False, id="hardware_ok"),
        pytest.param("042000", True, id="hardware_warning"),
        pytest.param("044000", True, id="hardware_failure"),
        pytest.param("046000", None, id="not_supported_says_neither"),
    ],
)
def test_d2_01_error_level_says_whether_there_is_a_problem(
    data: str, problem: bool | None
):
    values = _decode(EEP("D2-01-00"), RORG.RORG_VLD, data)

    if problem is None:
        assert Observable.ERROR_LEVEL not in values
    else:
        assert values[Observable.ERROR_LEVEL] is problem


def test_no_two_state_field_reports_a_text():
    """A text counts as true whatever it says: every such field must name its true values."""
    without = sorted(
        {
            f"{spec.eep}: {field.id}"
            for spec in EEP_SPECIFICATIONS.values()
            for telegram in (
                *spec.telegrams.values(),
                *spec.other_rorg_telegrams.values(),
            )
            for field in telegram.datafields
            if field.observable is not None
            and field.observable.kind == ValueKind.BINARY
            and field.true_values is None
        }
    )

    assert without == []


def test_switch_state_is_the_only_two_state_value_from_a_resolver():
    """A resolver could report a text too; the switch state is the only one that uses one."""
    resolved = {
        observable
        for spec in EEP_SPECIFICATIONS.values()
        for observable in spec.semantic_resolvers
        if observable.kind == ValueKind.BINARY
    }

    assert resolved == {Observable.SWITCH_STATE}
