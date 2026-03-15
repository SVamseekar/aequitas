"""Constants loader — thin wrapper around core/constants.py.

Provides a unified entry point for all pipeline constants.
"""

from aequitas.core.constants import DESNZ, TAG, LSOA_COUNT_ENGLAND, POPULATION_ENGLAND

__all__ = ["TAG", "DESNZ", "POPULATION_ENGLAND", "LSOA_COUNT_ENGLAND"]
