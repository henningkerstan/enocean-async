from enocean_async import Manufacturer


def test_manufacturer_code_values():
    assert Manufacturer.ENOCEAN.id == 0x00B


def test_manufacturer_str_values():
    assert str(Manufacturer.ENOCEAN) == "EnOcean GmbH"
    assert Manufacturer.ENOCEAN.display_name == "EnOcean GmbH"


def test_manufacturer_without_alliance_code():
    assert str(Manufacturer.JUNG) == "Jung"
    assert Manufacturer.JUNG.id is None
    assert str(Manufacturer.NODON) == "NodOn"
    assert str(Manufacturer.OMNIO) == "Omnio"


def test_manufacturer_code_link():
    assert Manufacturer.ELTAKO.id == 0x00D


def test_from_code():
    assert Manufacturer.from_id(0x00D) is Manufacturer.ELTAKO
    assert Manufacturer.from_id(0x00B) is Manufacturer.ENOCEAN
    assert Manufacturer.from_id(0xFFF) is None
