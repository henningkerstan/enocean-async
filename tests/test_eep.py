import pytest

from enocean_async import EEP
from enocean_async.eep.manufacturer import Manufacturer


def test_from_and_to_string():
    assert str(EEP("F6-02-01")) == "F6-02-01"


def test_wrong_string():
    with pytest.raises(ValueError):
        EEP("F6-0201")

    with pytest.raises(ValueError):
        EEP("FZ-06-01")


def test_hash():
    assert EEP("F6-02-01").__hash__() == hash((0xF6, 0x02, 0x01, None))


def test_repr():
    # __repr__ delegates to __str__; manufacturer is shown as enum member name.
    id = EEP("F6-02-01", Manufacturer.ENOCEAN_GMBH)
    assert repr(id) == "F6-02-01.ENOCEAN_GMBH"
