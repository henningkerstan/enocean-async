from abc import ABC
from dataclasses import dataclass


@dataclass
class Capability(ABC):
    uid: str


class PushButtonCabapility(Capability):
    pass
