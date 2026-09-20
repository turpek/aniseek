from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("aniseek")
except PackageNotFoundError:
    __version__ = "0.1.0a1"

from aniseek.core.video_reader import (
    BaseVideoReader,
    Direction,
    ForwardReader,
    ReverseReader,
    VideoReader,
)
from aniseek.time_utils import (
    frame_to_seconds,
    frame_to_timestamp,
    resolve_frame_range,
    seconds_to_timestamp,
    time_to_frame,
    timestamp_to_seconds,
)

__all__ = [
    "BaseVideoReader",
    "Direction",
    "ForwardReader",
    "ReverseReader",
    "VideoReader",
    "__version__",
    "frame_to_seconds",
    "frame_to_timestamp",
    "resolve_frame_range",
    "seconds_to_timestamp",
    "time_to_frame",
    "timestamp_to_seconds",
]
