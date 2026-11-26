"""Tests for A5-06-01.ELTAKO (Eltako FAH65S): the two brightness ranges."""

import pytest

from enocean_async import EEP, EURID, Observable
from enocean_async.eep import EEP_SPECIFICATIONS
from enocean_async.eep.handler import EEPHandler
from enocean_async.eep.manufacturer import Manufacturer
from enocean_async.protocol.erp1.rorg import RORG
from enocean_async.protocol.erp1.telegram import ERP1Telegram

SENDER = EURID("01:02:03:04")


@pytest.mark.parametrize(
    ("data", "lux"),
    [
        # low range: DB3 holds 0–100 lx as the raw values 0–100
        pytest.param("0000000F", 0.0, id="dark"),
        pytest.param("3200000F", 50.0, id="low_range_50_lx"),
        pytest.param("6400000F", 100.0, id="low_range_100_lx"),
        # high range: DB2 holds 300–30000 lx as the raw values 0–255
        pytest.param("6401000F", 300 + 29700 / 255, id="high_range_first_step"),
        pytest.param("64FF000F", 30000.0, id="high_range_30000_lx"),
    ],
)
def test_illumination_ranges(data: str, lux: float):
    handler = EEPHandler(EEP_SPECIFICATIONS[EEP("A5-06-01", Manufacturer.ELTAKO)])
    telegram = ERP1Telegram(RORG.RORG_4BS, bytes.fromhex(data), SENDER)

    message = handler.decode(telegram)

    assert message.values[Observable.ILLUMINATION].value == pytest.approx(lux)
