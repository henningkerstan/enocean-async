"""A5-38-08: Central command - gateway."""

from ...semantics.instructable import Instructable
from ...semantics.instructions.dimmer import Dim
from ...semantics.observable import Observable
from ..id import EEP
from ..message import EEPMessageType, RawEEPMessage, ValueWithContext
from ..profile import EEPDataField, EEPSpecification, EEPTelegram


def _resolve_edim(raw: dict, _scaled: dict) -> ValueWithContext | None:
    """Convert EDIM raw value to a percentage using EDIMR to select the scale."""
    edim = raw.get("EDIM")
    edimr = raw.get("EDIMR")
    if edim is None or edimr is None:
        return None
    # EDIMR=1 (relative): raw 0–100 maps directly to 0–100 %
    # EDIMR=0 (absolute): raw 0–255 maps to 0–100 %
    if edimr == 1:
        pct = float(edim)
    else:
        pct = edim * 100.0 / 255.0
    return ValueWithContext(name="Dimming value", value=round(pct, 1), unit="%")


def _encode_dim(action: Dim) -> RawEEPMessage:
    msg = RawEEPMessage(
        sender=None,
        message_type=EEPMessageType(id=2, description="Dimming"),
    )
    # dim_value is 0–100 %. Always sent as absolute (EDIMR=0): raw 0–255.
    raw_edim = max(0, min(255, round(action.dim_value / 100.0 * 255)))
    msg.raw["EDIM"] = raw_edim
    msg.raw["RMP"] = action.ramp_time
    msg.raw["EDIMR"] = 0  # always absolute
    msg.raw["STR"] = int(action.store)
    msg.raw["SW"] = int(action.switch_on)
    return msg


EEP_A5_38_08 = EEPSpecification(
    eep=EEP.from_string("A5-38-08"),
    name="Central command - gateway",
    cmd_size=8,
    cmd_offset=0,
    telegrams={
        2: EEPTelegram(
            name="Dimming",
            datafields=[
                EEPDataField(
                    id="CMD",
                    name="Command",
                    offset=0,
                    size=8,
                    range_enum={2: "Dimming"},
                ),
                EEPDataField(
                    id="EDIM",
                    name="Dimming value",
                    offset=8,
                    size=8,
                    range_min=0,
                    range_max=255,
                    scale_min_fn=lambda _: None,  # scaling done by semantic resolver
                ),
                EEPDataField(
                    id="RMP",
                    name="Ramping time",
                    offset=16,
                    size=8,
                    scale_min_fn=lambda _: 0.0,
                    scale_max_fn=lambda _: 255.0,
                    unit_fn=lambda _: "s",
                ),
                EEPDataField(
                    id="EDIMR",
                    name="Dimming range",
                    offset=29,
                    size=1,
                    range_enum={
                        0: "Absolute",
                        1: "Relative",
                    },
                ),
                EEPDataField(
                    id="STR",
                    name="Store final value",
                    offset=30,
                    size=1,
                    range_enum={
                        0: "No",
                        1: "Yes",
                    },
                ),
                EEPDataField(
                    id="SW",
                    name="Switching command",
                    offset=31,
                    size=1,
                    range_enum={
                        0: "Off",
                        1: "On",
                    },
                ),
            ],
        )
    },
    semantic_resolvers={
        Observable.OUTPUT_VALUE: _resolve_edim,
    },
    encoders={
        Instructable.DIM: _encode_dim,
    },
    uses_addressed_sending=False,
)
