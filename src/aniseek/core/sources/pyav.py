from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable, Iterator
from pathlib import Path

import av
from numpy import ndarray

from aniseek.core.interfaces.source import IFrameSource
from aniseek.core.keyframes import extract_keyframe_indices


class PyAVBuffer:
    """Low-level decoding buffer managing PyAV streams and cached VideoFrames."""

    def __init__(
        self,
        container: av.container.InputContainer,
        stream: av.video.stream.VideoStream,
        fps: float,
        max_size: int = 60,
    ) -> None:
        self.container = container
        self.stream = stream
        self.fps = fps
        self.time_base = float(stream.time_base)
        self.start_offset = stream.start_time or 0
        self.max_size = max(1, max_size)

        self.cache: OrderedDict[int, av.VideoFrame] = OrderedDict()
        self._iterator: Iterator[av.VideoFrame] | None = None

    def _frame_id_of(self, frame: av.VideoFrame) -> int | None:
        """Convert frame PTS to 0-based frame index."""
        if frame.pts is None:
            return None
        return int(round((frame.pts - self.start_offset) * self.time_base * self.fps))

    def _ensure_iterator(self) -> Iterator[av.VideoFrame]:
        if self._iterator is None:
            self._iterator = self.container.decode(self.stream)
        return self._iterator

    def seek(self, frame_id: int) -> None:
        """Position container at nearest preceding keyframe if frame_id not cached."""
        if frame_id in self.cache:
            return

        target_pts = self.start_offset + int(
            round(frame_id / (self.fps * self.time_base))
        )
        self.container.seek(target_pts, stream=self.stream, backward=True)
        self._iterator = self.container.decode(self.stream)
        self.cache.clear()

    def decode(self, frame_id: int) -> av.VideoFrame | None:
        """Retrieve decoded frame from cache or advance decoding until found."""
        if frame_id in self.cache:
            return self.cache.pop(frame_id)

        iterator = self._ensure_iterator()
        while True:
            try:
                frame = next(iterator)
            except (StopIteration, av.FFmpegError):
                break

            fid = self._frame_id_of(frame)
            if fid is None:
                continue

            if fid == frame_id:
                return frame
            else:
                self.cache[fid] = frame
                if len(self.cache) > self.max_size:
                    self.cache.popitem(last=False)

        return None

    def probe(self, frame_id: int) -> bool:
        """Check if frame_id can be reached and decoded."""
        if frame_id in self.cache:
            return True
        self.seek(frame_id)
        frame = self.decode(frame_id)
        if frame is not None:
            self.cache[frame_id] = frame
            return True
        return False

    def release(self) -> None:
        """Clear cached frames and reset iterator."""
        self.cache.clear()
        self._iterator = None


class PyAVVideoSource(IFrameSource):
    """Frame source implementation backed by PyAV (FFmpeg/libdav1d)."""

    def __init__(
        self,
        path: str | Path,
        *,
        buffersize: int = 30,
        fps: float | None = None,
    ) -> None:
        self.path = Path(path)
        if not self.path.exists():
            raise RuntimeError(f"Could not open video file: {self.path}")
        if self.path.is_dir():
            raise RuntimeError(f"Path is a directory, not a video file: {self.path}")

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

        detected_fps = float(
            self._stream.average_rate or self._stream.guessed_rate or 0.0
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

        width = int(self._stream.width or 0)
        height = int(self._stream.height or 0)
        self._size = (width, height)

        self.buffersize = max(1, buffersize)
        self._cursor = 0
        self._buffer = PyAVBuffer(
            self._container,
            self._stream,
            self._fps,
            max_size=max(60, self.buffersize * 2),
        )

        self._keyframe_indices: list[int] | None = None
        self._callback: Callable[[int, int], None] = lambda old, new: None

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

    @property
    def frame_count(self) -> int:
        """Total number of frames available in the video."""
        return self._frame_count

    @property
    def fps(self) -> float:
        """Frames per second of the video."""
        return self._fps

    @property
    def size(self) -> tuple[int, int]:
        """Video frame dimensions as (width, height) in pixels."""
        return self._size

    def seek(self, frame_id: int) -> None:
        """Position the cursor at the specified frame ID.

        Args:
            frame_id (int): Target frame index (0-based).
        """
        if self._container is None:
            return

        if self._frame_count > 0 and frame_id >= self._frame_count:
            frame_id = max(0, self._frame_count - 1)
        if frame_id < 0:
            frame_id = 0

        self._cursor = frame_id
        self._buffer.seek(frame_id)

    def read(self) -> tuple[bool, ndarray | None]:
        """Read and decode the next frame.

        Returns:
            tuple[bool, ndarray | None]: (success, frame).
        """
        if not self.is_opened():
            return False, None

        frame = self._buffer.decode(self._cursor)
        if frame is not None:
            self._cursor += 1
            arr = frame.to_ndarray(format="bgr24")
            return True, arr

        self._handle_read_failure(self._cursor)
        return False, None

    def grab(self) -> bool:
        """Advance cursor without decoding the frame.

        Returns:
            bool: True if next frame could be grabbed, False otherwise.
        """
        if not self.is_opened():
            return False

        frame = self._buffer.decode(self._cursor)
        if frame is not None:
            self._cursor += 1
            return True

        self._handle_read_failure(self._cursor)
        return False

    def probe(self, frame_id: int) -> bool:
        """Test if frame_id can be positioned and grabbed without failure."""
        if not self.is_opened() or frame_id < 0:
            return False
        return self._buffer.probe(frame_id)

    def is_opened(self) -> bool:
        """Check if the video source is currently open.

        Returns:
            bool: True if open, False otherwise.
        """
        return self._container is not None

    def release(self) -> None:
        """Release underlying video capture and decoding resources."""
        self._callback = lambda old, new: None
        if self._buffer is not None:
            self._buffer.release()
        if self._container is not None:
            self._container.close()
            self._container = None

    def __enter__(self) -> PyAVVideoSource:
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.release()
