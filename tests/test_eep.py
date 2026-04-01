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
    assert EEP("F6-02-01").__hash__() == hash((0xF6, 0x02, 0x01, None, None))


def test_repr():
    # __repr__ delegates to __str__; manufacturer is shown as enum member name.
    id = EEP("F6-02-01", Manufacturer.ENOCEAN)
    assert repr(id) == "F6-02-01.ENOCEAN"


def test_variant_str():
    assert str(EEP("A5-7F-3F.ELTAKO.FSB")) == "A5-7F-3F.ELTAKO.FSB"


def test_variant_kwarg():
    eep = EEP("A5-7F-3F", Manufacturer.ELTAKO, variant="FSB")
    assert str(eep) == "A5-7F-3F.ELTAKO.FSB"
    assert eep.variant == "FSB"


def test_variant_is_uppercased():
    assert EEP("A5-7F-3F.ELTAKO.fsb").variant == "FSB"


def test_variant_equality():
    assert EEP("A5-7F-3F.ELTAKO.FSB") == EEP("A5-7F-3F.ELTAKO.FSB")
    assert EEP("A5-7F-3F.ELTAKO.FSB") != EEP("A5-7F-3F.ELTAKO.FRGBW")
    assert EEP("A5-7F-3F.ELTAKO.FSB") != EEP("A5-7F-3F.ELTAKO")


def test_variant_conflict_raises():
    with pytest.raises(ValueError):
        EEP("A5-7F-3F.ELTAKO.FSB", variant="FRGBW")
