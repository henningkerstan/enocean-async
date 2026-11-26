"""The former name of the Eltako FSB profile, kept so that imports of it keep working.

The profile is ``A5-3F-7F.ELTAKO.FSB``: see :mod:`.a5_3f_7f`.
"""

from .a5_3f_7f import EEP_A5_3F_7F_ELTAKO_FSB

EEP_A5_7F_3F_ELTAKO_FSB = EEP_A5_3F_7F_ELTAKO_FSB
"""Former name of :data:`EEP_A5_3F_7F_ELTAKO_FSB`."""

__all__ = ["EEP_A5_7F_3F_ELTAKO_FSB"]
