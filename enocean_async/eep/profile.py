from dataclasses import dataclass, field
import logging
import math
from typing import Callable

_logger = logging.getLogger(__name__)

from ..semantics.entity import Entity  # noqa: F401  (re-exported for EEP files)
from ..semantics.instructable import Instructable
from ..semantics.observable import Observable
from ..semantics.observer_factory import ObserverFactory  # noqa: F401  (re-exported)
from ..semantics.types import (  # noqa: F401  (re-exported)
    InstructionEncoder,
    SemanticResolver,
)
from .id import EEP

type TelegramRawValues = dict[str, int]
type ScaleFunction = Callable[[TelegramRawValues], float]
type UnitFunction = Callable[[TelegramRawValues], str]


@dataclass
class EEPDataField:
    """An EEP data field represents a single data point within an EEP, such as a sensor value or a control command."""

    id: str
    """Unique identifier for the data field, typically a short string like 'R1', 'POS' etc."""

    name: str
    """Human-readable name for the data field, providing a descriptive label."""

    offset: int
    """Bit offset of the data field within the EEP."""

    size: int
    """Size of the data field in bits."""

    range_min: int = 0
    """Minimum value of the data field's range."""

    range_max: int | None = None
    """Maximum value of the data field's range, defaulting to the maximum representable by the given size in bits (e.g. 2^size - 1)."""

    scale_min_fn: ScaleFunction = lambda _: 0.0
    """Function to compute scale_min based on message values. Defaults to constant 0.0."""

    scale_max_fn: ScaleFunction | None = None
    """Function to compute scale_max based on message values. Defaults to constant 0.0."""

    unit_fn: UnitFunction = lambda _: ""
    """Function to compute unit based on message values. Defaults to empty string."""

    range_enum: dict[int, str] | None = None
    """Enumeration of possible values for the data field, if applicable."""

    observable: Observable | None = None
    """Observable type to which this field's decoded value is propagated (e.g. Observable.TEMPERATURE).
    When set, EEPHandler copies msg.interpreted_values[field.id] → msg.values[observable] after decoding."""

    def __post_init__(self):
        if self.range_enum:
            # If an enumeration is provided, range_min and range_max are derived from the enum keys
            enum_keys = self.range_enum.keys()
            if self.range_min != 0 or self.range_max is not None:
                _logger.warning(
                    f"EEPDataField '{self.id}': range_min/range_max are ignored when range_enum is provided."
                )
            self.range_min = min(enum_keys)
            self.range_max = max(enum_keys)
        else:
            # If no enumeration, ensure range_max is set based on size if not provided
            bit_max = (1 << self.size) - 1
            if self.range_max is None:
                self.range_max = bit_max
            elif self.range_max > bit_max:
                _logger.warning(
                    f"EEPDataField '{self.id}': range_max {self.range_max} exceeds maximum for {self.size}-bit field ({bit_max}); clamping."
                )
                self.range_max = bit_max

        if self.scale_max_fn is None:
            self.scale_max_fn = lambda _: float(self.range_max)


@dataclass
class EEPTelegram:
    """An EEP telegram represents a specific type of message defined within an EEP, which may have its own structure and data fields."""

    name: str | None
    """Human-readable name for the telegram, describing its purpose or function."""

    datafields: list[EEPDataField] = field(default_factory=list)
    """List of data fields within the telegram, including the CMD selector field if applicable."""

    @property
    def byte_size(self) -> int:
        """Minimum number of bytes required to hold all data fields (including the CMD field if present)."""
        max_bit = max((f.offset + f.size for f in self.datafields), default=0)
        return math.ceil(max_bit / 8)


@dataclass
class EEPSpecification:
    """A full specification of an EnOcean Equipment Profile (EEP). This contains all information to fully de- and encode messages according to the EEP."""

    eep: EEP
    """Unique identifier for the EEP."""

    name: str
    """Human-readable name/description for the EEP."""

    cmd_size: int = 0
    """Size of the telegram's command/message identifier in bits. If zero, there is only one telegram type."""

    cmd_offset: int | None = None
    """Bit offset of the telegram's command/message identifier within the EEP; either measured from left (if cmd_offset is non-negative) or from right (if cmd_offset is negative)."""

    ecid_size: int = 0
    """Size of the telegram's extended command/message identifier in bits. If zero, there is only one telegram type."""

    ecid_offset: int | None = None
    """Bit offset of the telegram's extended command/message identifier within the EEP; either measured from left (if ecid_offset is non-negative) or from right (if ecid_offset is negative)."""

    telegrams: dict[int, EEPTelegram] = field(default_factory=dict)
    """Dictionary of telegrams defined for this EEP, keyed by their command/message identifier, each with its own structure and data fields."""

    semantic_resolvers: dict[Observable, SemanticResolver] = field(default_factory=dict)
    """Dict mapping Observable → resolver function. Each resolver receives (raw_values: dict[str, int],
    scaled_values: dict[str, ValueWithUnit]) and returns a ValueWithUnit (or None) for that Observable."""

    observers: list[ObserverFactory] = field(default_factory=list)
    """Ordered list of observer factory callables. Each factory takes (device_address, on_state_change)
    and returns an Observer instance. MetaDataObserver is always prepended by the gateway."""

    encoders: dict[Instructable, InstructionEncoder] = field(default_factory=dict)
    """Dict mapping Instructable → encoder function. Each encoder takes an Instruction and returns
    a RawEEPMessage with message_type.id set and raw_values filled (field_id → raw int).
    The gateway sets message.sender and message.destination before calling EEPHandler.encode()."""

    entities: list[Entity] = field(default_factory=list)
    """Physical entities declared by this EEP — one per real-world sub-unit (push button,
    relay channel, sensor element, cover motor). Consumed by ``device_spec()``."""

    uses_addressed_sending: bool = True
    """If True (default), the device is destination-addressed (VLD): the gateway uses BaseID+0
    and sets the destination field to the device's EURID.
    If False, the device is sender-addressed: it learned the gateway's sender address at teach-in
    and filters commands by sender. The gateway allocates a dedicated BaseID+n slot per device."""


@dataclass
class SimpleProfileSpecification(EEPSpecification):
    """Simpler variant for profiles with a single telegram type (cmd_size=0, no telegram selector)."""

    def __init__(
        self,
        eep: EEP,
        name: str,
        datafields: list[EEPDataField],
        semantic_resolvers: dict[Observable, SemanticResolver] | None = None,
        observers: list[ObserverFactory] | None = None,
        encoders: dict[Instructable, InstructionEncoder] | None = None,
        entities: list[Entity] | None = None,
        uses_addressed_sending: bool = True,
    ):
        """Initialize a single-telegram EEP.

        Args:
            eep: Unique identifier for the EEP.
            name: Human-readable name/description.
            datafields: List of data fields in the unique telegram that is defined for this EEP.
            semantic_resolvers: Optional dict of Observable → resolver for multi-field combinations.
            observers: Optional list of observer factory callables.
            encoders: Optional dict of Instructable → encoder callables.
            entities: Optional list of Entity declarations for this EEP.
            uses_addressed_sending: See EEPSpecification.uses_addressed_sending.
        """

        super().__init__(
            eep=eep,
            name=name,
            cmd_size=0,
            cmd_offset=None,
            telegrams={0: EEPTelegram(name=None, datafields=datafields)},
            semantic_resolvers=semantic_resolvers or {},
            observers=observers or [],
            encoders=encoders or {},
            entities=entities or [],
            uses_addressed_sending=uses_addressed_sending,
        )
