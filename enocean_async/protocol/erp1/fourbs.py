from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional

from enocean_async.eep.manufacturer import Manufacturer

from ...address import EURID, BroadcastAddress, SenderAddress
from ...eep.id import EEP
from .rorg import RORG
from .telegram import ERP1Telegram


class FourBSLearnType(IntEnum):
    TELEGRAM_WITHOUT_EEP_AND_NO_MANUFACTURER = 0
    TELEGRAM_WITH_EEP_AND_MANUFACTURER = 1


class FourBSTeachInResult(IntEnum):
    SENDER_ID_NOT_STORED_OR_DELETED = 0
    SENDER_ID_STORED = 1


class FourBSLearnStatus(IntEnum):
    QUERY = 0
    RESPONSE = 1


class FourBSEEPResult(IntEnum):
    NOT_SUPPORTED = 0
    SUPPORTED = 1


@dataclass
class FourBSTeachInTelegram:
    # convenience wrapper for the sender/destination fields of the underlying ERP1 telegram
    sender: SenderAddress

    learn_type: FourBSLearnType = FourBSLearnType.TELEGRAM_WITH_EEP_AND_MANUFACTURER
    learn_status: FourBSLearnStatus = FourBSLearnStatus.QUERY
    eep: EEP | None = None

    # result fields (only valid for responses)
    eep_result: Optional[FourBSEEPResult] = field(default=None, repr=False)
    learn_result: Optional[FourBSTeachInResult] = field(default=None, repr=False)

    @classmethod
    def from_erp1(cls, erp1: ERP1Telegram) -> "FourBSTeachInTelegram":
        if erp1.rorg != RORG.RORG_4BS:
            raise ValueError("Wrong RORG.")

        if not erp1.is_learning_telegram:
            raise ValueError("Not a learning telegram")

        learn_type = FourBSLearnType(erp1.bitstring_raw_value(24, 1))
        learn_status = FourBSLearnStatus(erp1.bitstring_raw_value(27, 1))

        eep: EEP | None = None

        if learn_type == FourBSLearnType.TELEGRAM_WITH_EEP_AND_MANUFACTURER:
            func = erp1.bitstring_raw_value(0, 6)
            type_ = erp1.bitstring_raw_value(6, 7)
            manufacturer_id = erp1.bitstring_raw_value(13, 11)
            try:
                manufacturer = (
                    Manufacturer.from_id(manufacturer_id) or Manufacturer.RESERVED
                )
            except ValueError:
                manufacturer = Manufacturer.RESERVED

            eep = EEP([0xA5, func, type_], manufacturer)

        return cls(
            learn_type=learn_type,
            learn_status=learn_status,
            eep=eep,
            sender=erp1.sender,
        )

    @classmethod
    def response_for_query(
        cls,
        query: "FourBSTeachInTelegram",
        result: FourBSTeachInResult,
        sender: SenderAddress,
    ) -> "FourBSTeachInTelegram":
        """Build a bidirectional 4BS teach-in response for a given query."""
        if not query.learn_status == FourBSLearnStatus.QUERY:
            raise ValueError("Cannot create response: not a query.")
        if query.eep is None:
            raise ValueError("Cannot create response: query has no EEP.")
        return cls(
            learn_type=FourBSLearnType.TELEGRAM_WITH_EEP_AND_MANUFACTURER,
            learn_status=FourBSLearnStatus.RESPONSE,
            eep=query.eep,
            sender=sender,
            learn_result=result,
        )

    def to_erp1(self) -> ERP1Telegram:
        """Serialise this response to an ERP1 telegram for sending."""
        if self.learn_result is None or self.learn_status != FourBSLearnStatus.RESPONSE:
            raise ValueError(
                "to_erp1() is only valid for response telegrams (use response_for_query())."
            )
        if (
            self.eep is None
            or self.learn_type != FourBSLearnType.TELEGRAM_WITH_EEP_AND_MANUFACTURER
        ):
            raise ValueError("to_erp1() requires an EEP.")

        telegram = ERP1Telegram(
            rorg=RORG.RORG_4BS,
            telegram_data=bytes(4),
            sender=self.sender,
        )

        # DB3..DB1: echo FUNC / TYPE / Manufacturer ID (same layout as query)
        telegram.set_bitstring_raw_value(0, 6, self.eep.func)
        telegram.set_bitstring_raw_value(6, 7, self.eep.type)
        telegram.set_bitstring_raw_value(13, 11, self.eep.manufacturer.id)

        # DB0 (bits 24-31):
        telegram.set_bitstring_raw_value(24, 1, self.learn_type.value)
        telegram.set_bitstring_raw_value(
            25,
            1,
            self.eep_result.value
            if self.eep_result is not None
            else FourBSEEPResult.NOT_SUPPORTED.value,
        )
        telegram.set_bitstring_raw_value(26, 1, self.learn_result.value)
        telegram.set_bitstring_raw_value(27, 1, self.learn_status.value)
        telegram.set_bitstring_raw_value(
            28, 1, 0
        )  # teach-in telegram (not data telegram)
        telegram.set_bitstring_raw_value(29, 3, 0)  # reserved/unused, set to 0

        return telegram
