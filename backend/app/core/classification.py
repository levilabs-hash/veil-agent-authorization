"""Explicit resource classifications in the simulated environment.

The engine uses this metadata. Filenames are not a classification signal.
"""

from enum import Enum


class Classification(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
