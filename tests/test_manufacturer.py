from enocean_async import Manufacturer


def test_manufacturer_values():
    assert Manufacturer.ENOCEAN_GMBH.value == 0x00B
    assert Manufacturer.ENOCEAN_GMBH.friendly_name == "EnOcean GmbH"
    assert str(Manufacturer.ENOCEAN_GMBH) == "EnOcean GmbH"
