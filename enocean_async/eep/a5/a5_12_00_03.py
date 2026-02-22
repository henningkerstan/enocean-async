"""A5-02-XX: Temperature sensors."""

from ..id import EEPID
from ..profile import EEPDataField, SingleTelegramEEP


def _compute_mr_scale_max(raw_values: dict[str, int]) -> float:
    """Compute MR scale_max based on DIV field value."""
    div_value = raw_values.get("DIV", 0)
    divisors = [1, 10, 100, 1000]
    divisor = divisors[div_value] if div_value < len(divisors) else 1
    return 16777215.0 / divisor


class _EEP_A5_12_00_03(SingleTelegramEEP):
    def __init__(self, _type: int, info_id: str, info_name: str):
        name_suffix = "counter"
        match _type:
            case 0x01:
                name_suffix = "electricity"
            case 0x02:
                name_suffix = "gas"
            case 0x03:
                name_suffix = "water"

        super().__init__(
            id=EEPID.from_string(f"A5-12-{_type:02X}"),
            name=f"Automated meter reading (AMR), {name_suffix}",
            datafields=[
                EEPDataField(
                    id="MR",
                    name="Meter reading",
                    offset=0,
                    size=24,
                    scale_min_fn=lambda _: 0.0,
                    scale_max_fn=_compute_mr_scale_max,
                ),
                EEPDataField(
                    id=info_id,
                    name=info_name,
                    offset=24,
                    size=4,
                    scale_min_fn=lambda _: 0.0,
                    scale_max_fn=lambda _: 15.0,
                    unit_fn=lambda _: "",
                ),
                EEPDataField(
                    id="DT",
                    name="Data type (unit)",
                    offset=29,
                    size=1,
                    range_enum={
                        0: "Cumulative value",
                        1: "Current value",
                    },
                ),
                EEPDataField(
                    id="DIV",
                    name="Divisor (scale)",
                    offset=30,
                    size=2,
                    range_enum={
                        0: "x/1",
                        1: "x/10",
                        2: "x/100",
                        3: "x/1000",
                    },
                ),
            ],
        )


EEP_A5_12_00 = _EEP_A5_12_00_03(
    _type=0x01, info_id="CH", info_name="Measurement channel"
)
EEP_A5_12_01 = _EEP_A5_12_00_03(_type=0x01, info_id="TI", info_name="Tariff info")
EEP_A5_12_02 = _EEP_A5_12_00_03(_type=0x02, info_id="TI", info_name="Tariff info")
EEP_A5_12_03 = _EEP_A5_12_00_03(_type=0x03, info_id="TI", info_name="Tariff info")
