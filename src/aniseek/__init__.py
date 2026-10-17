from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("aniseek")
except PackageNotFoundError:
    __version__ = "0.3.0a0"

from aniseek.config import config
from aniseek.core.sources.pyav import PyAVVideoSource
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
    "PyAVVideoSource",
    "ReverseReader",
    "VideoReader",
    "__version__",
    "config",
    "frame_to_seconds",
    "frame_to_timestamp",
    "resolve_frame_range",
    "seconds_to_timestamp",
    "time_to_frame",
    "timestamp_to_seconds",
]
