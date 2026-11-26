"""Supply voltages with a valid range of 0–250 give no voltage for the reserved values 251–255."""

import pytest

from enocean_async import EEP, EURID, Observable
from enocean_async.eep import EEP_SPECIFICATIONS
from enocean_async.eep.handler import EEPHandler
from enocean_async.protocol.erp1.rorg import RORG
from enocean_async.protocol.erp1.telegram import ERP1Telegram

SENDER = EURID("01:02:03:04")

# DB0 of a data telegram (LRN bit set); A5-07-01 also needs its "supply voltage supported" bit
PROFILES = [
    pytest.param("A5-07-01", 0x09, id="A5-07-01"),
    pytest.param("A5-07-03", 0x08, id="A5-07-03"),
    pytest.param("A5-10-1A", 0x08, id="A5-10-1A"),
    pytest.param("A5-10-1B", 0x08, id="A5-10-1B"),
    pytest.param("A5-10-1E", 0x08, id="A5-10-1E"),
    pytest.param("A5-14-09", 0x08, id="A5-14-09"),
]


def voltage(eep: str, svc: int, db0: int):
    telegram = ERP1Telegram(RORG.RORG_4BS, bytes([svc, 0x00, 0x00, db0]), SENDER)
    message = EEPHandler(EEP_SPECIFICATIONS[EEP(eep)]).decode(telegram)
    value = message.values.get(Observable.VOLTAGE)
    return None if value is None else value.value


@pytest.mark.parametrize(("eep", "db0"), PROFILES)
def test_valid_range_gives_the_voltage(eep: str, db0: int):
    assert voltage(eep, 0, db0) == pytest.approx(0.0)
    assert voltage(eep, 250, db0) == pytest.approx(5.0)


@pytest.mark.parametrize(("eep", "db0"), PROFILES)
@pytest.mark.parametrize("svc", [251, 255])
def test_reserved_values_give_no_voltage(eep: str, db0: int, svc: int):
    assert voltage(eep, svc, db0) is None
