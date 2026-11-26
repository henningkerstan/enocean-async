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
    assert str(EEP("A5-3F-7F.ELTAKO.FSB")) == "A5-3F-7F.ELTAKO.FSB"


def test_variant_kwarg():
    eep = EEP("A5-3F-7F", Manufacturer.ELTAKO, variant="FSB")
    assert str(eep) == "A5-3F-7F.ELTAKO.FSB"
    assert eep.variant == "FSB"


def test_variant_is_uppercased():
    assert EEP("A5-3F-7F.ELTAKO.fsb").variant == "FSB"


def test_variant_equality():
    assert EEP("A5-3F-7F.ELTAKO.FSB") == EEP("A5-3F-7F.ELTAKO.FSB")
    assert EEP("A5-3F-7F.ELTAKO.FSB") != EEP("A5-3F-7F.ELTAKO.FRGBW")
    assert EEP("A5-3F-7F.ELTAKO.FSB") != EEP("A5-3F-7F.ELTAKO")


def test_variant_conflict_raises():
    with pytest.raises(ValueError):
        EEP("A5-3F-7F.ELTAKO.FSB", variant="FRGBW")


def test_former_name_of_the_eltako_fsb_profile_gives_the_profile():
    """The FSB profile was named with FUNC and TYPE swapped; the old name still works."""
    from enocean_async.eep import DEVICE_TYPES, EEP_SPECIFICATIONS

    current = EEP("A5-3F-7F.ELTAKO.FSB")

    assert EEP("A5-7F-3F.ELTAKO.FSB") == current
    assert EEP("A5-7F-3F", Manufacturer.ELTAKO, variant="fsb") == current
    assert EEP([0xA5, 0x7F, 0x3F], Manufacturer.ELTAKO, variant="FSB") == current
    assert str(EEP("A5-7F-3F.ELTAKO.FSB")) == "A5-3F-7F.ELTAKO.FSB"
    assert EEP_SPECIFICATIONS[EEP("A5-7F-3F.ELTAKO.FSB")].eep == current
    # only this profile: the same numbers of another variant or manufacturer are untouched
    assert str(EEP("A5-7F-3F.ELTAKO")) == "A5-7F-3F.ELTAKO"
    assert str(EEP("A5-7F-3F.ELTAKO.FRGBW")) == "A5-7F-3F.ELTAKO.FRGBW"
    assert str(EEP("A5-7F-3F")) == "A5-7F-3F"

    assert DEVICE_TYPES["ELTAKO/A5-7F-3F/FSB"] is DEVICE_TYPES["ELTAKO/A5-3F-7F/FSB"]
    assert "ELTAKO/A5-7F-3F/FSB" in DEVICE_TYPES
    assert DEVICE_TYPES.get("ELTAKO/A5-7F-3F/FSB").eep == current
    assert DEVICE_TYPES.get("ELTAKO/NOTHING") is None
    assert "ELTAKO/NOTHING" not in DEVICE_TYPES
    assert "ELTAKO/A5-7F-3F/FSB" not in list(DEVICE_TYPES)
    assert DEVICE_TYPES["ELTAKO/FSB61"].eep == current


def test_former_import_name_of_the_eltako_fsb_profile():
    from enocean_async.eep.a5 import EEP_A5_3F_7F_ELTAKO_FSB, EEP_A5_7F_3F_ELTAKO_FSB

    assert EEP_A5_7F_3F_ELTAKO_FSB is EEP_A5_3F_7F_ELTAKO_FSB
