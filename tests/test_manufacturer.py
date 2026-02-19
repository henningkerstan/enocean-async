from enocean_async import EnOceanManufacturers


def test_manufacturer_values():
    assert EnOceanManufacturers.ENOCEAN_GMBH.value == 0x00B
    assert EnOceanManufacturers.ENOCEAN_GMBH.friendly_name == "EnOcean GmbH"
    assert str(EnOceanManufacturers.ENOCEAN_GMBH) == "EnOcean GmbH"


def test_corrected_manufacturer_names():
    assert (
        EnOceanManufacturers.VIESSMANN_HAUSAUTOMATION_GMBH.friendly_name
        == "MSR Solutions or Viessmann Hausautomation GmbH"
    )
    assert (
        EnOceanManufacturers.TIANSU_AUTOMATION_CONTROL_SYSTEM_CO_LTD.friendly_name
        == "Tiansu Automation Control System Co., Ltd."
    )
    assert EnOceanManufacturers.GLEN_DIMPLEX_GMBH.friendly_name == "Glen Dimplex GmbH"
    assert EnOceanManufacturers.HUBBEL_LIGHTNING.friendly_name == "Hubbell Lighting"
    assert EnOceanManufacturers.HOLTER_REGELARMATUREN.friendly_name == "Holter Regelarmaturen"