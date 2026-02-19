from enocean_async import EnOceanManufacturers


def test_manufacturer_values():
    assert EnOceanManufacturers.ENOCEAN_GMBH.value == 0x00B
    assert EnOceanManufacturers.ENOCEAN_GMBH.friendly_name == "EnOcean GmbH"
    assert str(EnOceanManufacturers.ENOCEAN_GMBH) == "EnOcean GmbH"
