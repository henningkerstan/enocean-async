# enocean-async
This is a light-weight, asynchronous, fully typed Python implementation of the [EnOcean Serial Protocol Version 3 (ESP3)](https://www.enocean.com/wp-content/uploads/Knowledge-Base/EnOceanSerialProtocol3-1.pdf) based on [pyserial-asyncio-fast](https://pypi.org/project/pyserial-asyncio-fast/). 

**It is currently still a proof of concept (PoC) implementation loosely based on my previous [Node.js implementation](https://www.npmjs.com/package/enocean-core), so anything may change at anytime!**

What works:
- Receiving ESP3 packets and parsing them into ERP1 telegrams
- Sending ESP3 packets (only tested with Common Command telegrams so far) incl. waiting for response (or time-out) and reacting to the response
- Retrieving EURID, Base ID and version info from the EnOcean module
- Changing the Base ID
- Sending ERP1 telegrams
- Parsing EEPs (with F6-02-01 as tested/implemented example)
- Parse Universal Teach-In (UTE) Queries
- logging (partially)

What is missing/untested:
- create and send Universal Teach-In (UTE) responses
- handle Teach-in (UTE, 4BS, 1BS)
- add (and test) more EEPs


## Implemented EEPs
See [SUPPORTED_EEPS.md](https://github.com/henningkerstan/enocean-async/blob/main/SUPPORTED_EEPS.md).


## Contributing
See [CONTRIBUTING](https://github.com/henningkerstan/enocean-async/blob/main/CONTRIBUTING.md).


## Dependencies
This library only has one dependency, namely

- [pyserial-asyncio-fast](https://pypi.org/project/pyserial-asyncio-fast/) in version 0.16, which is BSD-3 licensed.


## Technology documentation
The EnOcean technology is documented in several, publicly available sources, particularly:
- the [EnOcean Serial Protocol Version 3 (ESP3)](https://www.enocean.com/wp-content/uploads/Knowledge-Base/EnOceanSerialProtocol3-1.pdf) specification
-  the [EnOcean Radio Protocol 1 (ERP1)](https://www.enocean.com/wp-content/uploads/Knowledge-Base/EnOceanRadioProtocol1.pdf) specification
- the [EnOcean Alliance's Specifications](https://www.enocean-alliance.org/specifications/),
    - the [EnOcean Unique Radio Identifier – EURID Specification, V1.2](https://www.enocean-alliance.org/wp-content/uploads/2021/03/EURID-v1.2.pdf)
    - a high level spec of [EnOcean Equipment Profiles (EEP), V3.1](https://www.enocean-alliance.org/wp-content/uploads/2020/07/EnOcean-Equipment-Profiles-3-1.pdf)
    - the individual EEPs can be viewed using the [EEPViewer](https://tools.enocean-alliance.org/EEPViewer), which replaces the previously maintained [EEP Spec V.2.6.8 from Dec 31, 2017](https://www.enocean-alliance.org/wp-content/uploads/2019/10/EEP268_R3_Feb022018_public.pdf)


## Copyright & license
Copyright 2026 Henning Kerstan

Licensed under the Apache License, Version 2.0 (the "License"). See [LICENSE](./LICENSE) file for details.