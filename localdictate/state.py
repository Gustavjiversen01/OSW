"""Application state enum for LocalDictate."""

from enum import IntEnum


class AppState(IntEnum):
    IDLE = 0
    RECORDING = 1
    PROCESSING = 2
    DOWNLOADING = 3
