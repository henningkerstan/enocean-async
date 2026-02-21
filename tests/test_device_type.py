from enocean_async.device.db import DEVICE_TYPE_DB
from enocean_async.device.type import DeviceType


def test_device_type_db():
    assert isinstance(DEVICE_TYPE_DB, dict)
    for key, value in DEVICE_TYPE_DB.items():
        assert isinstance(key, str)
        assert isinstance(value, DeviceType)