from __future__ import annotations

from collections.abc import Callable, Iterator
from enum import StrEnum
from pathlib import Path
from typing import Self

import av
import av.video.frame
import numpy as np
from numpy import ndarray

from aniseek.core.interfaces.source import IFrameSource
from aniseek.core.keyframes import extract_keyframe_indices


class PyAVFormat(StrEnum):
    """Supported color formats for PyAV frame decoding."""

    BGR = "bgr"
    RGB = "rgb"
    GRAY = "gray"
    BGRA = "bgra"
    RGBA = "rgba"

    @property
    def channels(self) -> int:
        """Number of color channels in the format."""
        return {
            PyAVFormat.GRAY: 1,
            PyAVFormat.BGR: 3,
            PyAVFormat.RGB: 3,
            PyAVFormat.BGRA: 4,
            PyAVFormat.RGBA: 4,
        }[self]

    @property
    def has_alpha(self) -> bool:
        """Whether the format contains an alpha transparency channel."""
        return self in (PyAVFormat.BGRA, PyAVFormat.RGBA)

    def to_pix_fmt(self, dtype: np.dtype | type = np.uint8) -> str:
        """Resolve the PyAV/FFmpeg pixel format string for the given NumPy dtype.

        Args:
            dtype (np.dtype | type): Desired data type (uint8, uint16, float32).

        Returns:
            str: PyAV compatible pixel format string.

        Raises:
            ValueError: If the combination of format and dtype is not supported.
        """
        resolved_dtype = np.dtype(dtype)

        if self == PyAVFormat.GRAY:
            if resolved_dtype == np.uint8:
                return "gray"
            if resolved_dtype == np.uint16:
                return "gray16le"
            if resolved_dtype == np.float32:
                return "grayf32le"

        elif self == PyAVFormat.BGR:
            if resolved_dtype == np.uint8:
                return "bgr24"
            if resolved_dtype == np.uint16:
                return "bgr48le"

        elif self == PyAVFormat.RGB:
            if resolved_dtype == np.uint8:
                return "rgb24"
            if resolved_dtype == np.uint16:
                return "rgb48le"
            if resolved_dtype == np.float32:
                return "rgbf32le"

        elif self == PyAVFormat.BGRA:
            if resolved_dtype == np.uint8:
                return "bgra"
            if resolved_dtype == np.uint16:
                return "bgra64le"

        elif self == PyAVFormat.RGBA:
            if resolved_dtype == np.uint8:
                return "rgba"
            if resolved_dtype == np.uint16:
                return "rgba64le"
            if resolved_dtype == np.float32:
                return "rgbaf32le"

        raise ValueError(
            f"Unsupported combination for PyAVFormat.{self.name}: dtype={resolved_dtype}"
        )


def _resolve_pix_fmt(
    format_spec: PyAVFormat | str,
    dtype: np.dtype | type,
) -> tuple[str, np.dtype]:
    """Resolve format specification and dtype to a PyAV pixel format string and dtype."""
    resolved_dtype = np.dtype(dtype)

    if isinstance(format_spec, PyAVFormat):
        return format_spec.to_pix_fmt(resolved_dtype), resolved_dtype

    format_str = str(format_spec).strip()
    try:
        enum_val = PyAVFormat(format_str.lower())
        return enum_val.to_pix_fmt(resolved_dtype), resolved_dtype
    except ValueError:
        pass

    if format_str in av.video.frame.supported_np_pix_fmts:
        return format_str, resolved_dtype

    raise ValueError(
        f"Unknown or unsupported video format: '{format_spec}' with dtype {resolved_dtype}"
    )


class PyAVVideoSource(IFrameSource):
    """High-performance video frame source backed by PyAV (FFmpeg/libdav1d)."""

    def __init__(
        self,
        path: str | Path,
        *,
        format: PyAVFormat | str = PyAVFormat.BGR,
        dtype: np.dtype | type = np.uint8,
        readonly: bool = False,
        buffersize: int = 30,
        fps: float | None = None,
        thread_type: str = "AUTO",
        thread_count: int = 0,
    ) -> None:
        self.path = Path(path)
        if not self.path.exists():
            raise RuntimeError(f"Could not open video file: {self.path}")
        if self.path.is_dir():
            raise RuntimeError(f"Path is a directory, not a video file: {self.path}")

        self._pix_fmt, self._dtype = _resolve_pix_fmt(format, dtype)
        self._format_spec = format
        self.readonly = readonly

        try:
            self._container: av.container.InputContainer | None = av.open(
                str(self.path), mode="r"
            )
        except Exception as exc:
            raise RuntimeError(f"Could not open video file: {self.path}") from exc

        video_streams = self._container.streams.video
        if not video_streams:
            self.release()
            raise RuntimeError(f"No video streams found in {self.path}")

        self._stream: av.video.stream.VideoStream = video_streams[0]

        if thread_type:
            try:
                self._stream.codec_context.thread_type = thread_type
            except (AttributeError, ValueError):
                pass
        if thread_count > 0:
            try:
                self._stream.codec_context.thread_count = thread_count
            except (AttributeError, ValueError):
                pass

        detected_fps = float(
            self._stream.average_rate or self._stream.guessed_rate or 24.0
        )
        self._fps = float(fps) if fps is not None and fps > 0.0 else detected_fps

        if self._stream.frames > 0:
            self._frame_count = self._stream.frames
        elif self._container.duration is not None and self._container.duration > 0:
            self._frame_count = int(
                round((self._container.duration / 1_000_000.0) * self._fps)
            )
        elif self._stream.duration is not None and self._stream.duration > 0:
            self._frame_count = int(
                round(float(self._stream.duration * self._stream.time_base) * self._fps)
            )
        else:
            self._frame_count = 0

        self.buffersize = max(1, buffersize)
        self._start_offset: int = self._stream.start_time or 0
        self._time_base: float = float(self._stream.time_base)

        self._current_pos: int = 0
        self._generator: Iterator[av.VideoFrame] | None = None
        self._pending_frame: av.VideoFrame | None = None
        self._eof: bool = False

        self._keyframe_indices: list[int] | None = None
        self._callback: Callable[[int, int], None] = lambda old, new: None

    @property
    def frame_count(self) -> int:
        """Total number of frames available in the video."""
        return self._frame_count

    @property
    def fps(self) -> float:
        """Frames per second of the video."""
        return self._fps

    @property
    def width(self) -> int:
        """Video frame width in pixels."""
        return self._stream.width

    @property
    def height(self) -> int:
        """Video frame height in pixels."""
        return self._stream.height

    @property
    def shape(self) -> tuple[int, ...]:
        """Shape of the decoded NumPy ndarray (H, W) or (H, W, C)."""
        if self._pix_fmt in ("gray", "gray16le", "grayf32le"):
            return self.height, self.width
        if self._pix_fmt in ("rgba", "rgba64le", "bgra", "bgra64le", "rgbaf32le"):
            return self.height, self.width, 4
        return self.height, self.width, 3

    @property
    def format(self) -> PyAVFormat | str:
        """Configured format specification."""
        return self._format_spec

    @property
    def dtype(self) -> np.dtype:
        """Target NumPy dtype for decoded frames."""
        return self._dtype

    @property
    def codec_name(self) -> str:
        """Underlying codec name (e.g. 'libdav1d', 'h264', 'hevc')."""
        return self._stream.codec_context.name

    def on_frame_count_changed(self, old_count: int, new_count: int) -> None:
        """Hook called when the decodable frame count is adjusted."""
        self._callback(old_count, new_count)

    def get_keyframes(self) -> list[int] | None:
        """Get or lazily extract keyframe indices for the underlying video file.

        Returns:
            list[int] | None: Sorted list of keyframe frame indices if available.
        """
        if self._keyframe_indices is None:
            self._keyframe_indices = extract_keyframe_indices(self.path, self._fps)
        return self._keyframe_indices

    def is_opened(self) -> bool:
        """Check if the underlying container is currently open.

        Returns:
            bool: True if open, False otherwise.
        """
        return self._container is not None

    def release(self) -> None:
        """Close container and release all decoding resources."""
        if self._container is not None:
            self._container.close()
            self._container = None
        self._generator = None
        self._pending_frame = None
        self._eof = True

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.release()

    def _get_generator(self) -> Iterator[av.VideoFrame]:
        if self._generator is None and self._container is not None:
            self._generator = self._container.decode(self._stream)
        if self._generator is None:
            return iter([])
        return self._generator

    def _decode_next(self) -> av.VideoFrame | None:
        if self._eof or self._container is None:
            return None
        try:
            return next(self._get_generator())
        except (StopIteration, av.AVError):
            self._eof = True
            return None

    def seek(self, frame_id: int) -> None:
        """Position cursor at frame_id with exact keyframe resolution.

        Args:
            frame_id (int): Target frame index (0-based).
        """
        if self._container is None:
            return

        if self._frame_count > 0 and frame_id >= self._frame_count:
            frame_id = max(0, self._frame_count - 1)
        if frame_id < 0:
            frame_id = 0

        if frame_id == self._current_pos and (
            self._pending_frame is not None or not self._eof
        ):
            return

        if 0 < frame_id - self._current_pos <= 5 and not self._eof:
            skip_count = frame_id - self._current_pos
            for _ in range(skip_count):
                if not self.grab():
                    break
            return

        target_pts = self._start_offset + int(
            round(frame_id / (self._fps * self._time_base))
        )
        self._container.seek(target_pts, stream=self._stream, backward=True)
        self._generator = self._container.decode(self._stream)
        self._pending_frame = None
        self._eof = False

        while True:
            frame = self._decode_next()
            if frame is None:
                self._current_pos = frame_id
                return

            if frame.pts is not None:
                pts_relative = frame.pts - self._start_offset
                f_idx = int(round(pts_relative * self._time_base * self._fps))
            else:
                f_idx = self._current_pos

            if f_idx >= frame_id:
                self._pending_frame = frame
                self._current_pos = f_idx
                break

    def read(self) -> tuple[bool, ndarray | None]:
        """Read and decode the next frame.

        Returns:
            tuple[bool, ndarray | None]: (success, frame).
        """
        if not self.is_opened():
            return False, None

        if self._pending_frame is not None:
            frame = self._pending_frame
            self._pending_frame = None
            self._current_pos += 1
        else:
            frame = self._decode_next()
            if frame is None:
                return False, None
            self._current_pos += 1

        arr = frame.to_ndarray(format=self._pix_fmt)
        if self.readonly:
            arr.flags.writeable = False
        return True, arr

    def grab(self) -> bool:
        """Advance cursor without decoding/converting the full array.

        Returns:
            bool: True if next frame could be grabbed/skipped, False otherwise.
        """
        if not self.is_opened():
            return False

        if self._pending_frame is not None:
            self._pending_frame = None
            self._current_pos += 1
            return True

        frame = self._decode_next()
        if frame is None:
            return False

        self._current_pos += 1
        return True

    @classmethod
    def fast_gray(
        cls,
        path: str | Path,
        *,
        buffersize: int = 30,
        fps: float | None = None,
    ) -> PyAVVideoSource:
        """Create a grayscale PyAVVideoSource for high throughput and single-channel processing."""
        return cls(
            path,
            format=PyAVFormat.GRAY,
            dtype=np.uint8,
            buffersize=buffersize,
            fps=fps,
        )

    @classmethod
    def high_fidelity(
        cls,
        path: str | Path,
        *,
        format: PyAVFormat | str = PyAVFormat.BGR,
        buffersize: int = 30,
        fps: float | None = None,
    ) -> PyAVVideoSource:
        """Create a 16-bit high-fidelity PyAVVideoSource preserving 10-bit/12-bit HDR color depth."""
        return cls(
            path,
            format=format,
            dtype=np.uint16,
            buffersize=buffersize,
            fps=fps,
        )
