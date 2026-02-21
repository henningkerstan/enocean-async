from enocean_async.device.db import DEVICE_TYPE_DB
from enocean_async.device.type import DeviceType

for key, device_type in DEVICE_TYPE_DB.items():
      
    if device_type.uid is not None and device_type.uid == device_type.eepid.to_string():
        print(f"EEP \033[33m{device_type.eepid.to_string()}\033[0m {device_type.model if device_type.model else ''}")
    else:
        print(f"{device_type.manufacturer} {device_type.model} (EEP \033[33m{device_type.eepid.to_string()}\033[0m)")