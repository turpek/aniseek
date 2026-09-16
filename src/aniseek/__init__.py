from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("aniseek")
except PackageNotFoundError:
    __version__ = "0.1.0a1"

from aniseek.video_reader import (
    BaseVideoReader,
    ForwardReader,
    ReverseReader,
    VideoReader,
)

__all__ = [
    "BaseVideoReader",
    "ForwardReader",
    "ReverseReader",
    "VideoReader",
    "__version__",
]
