from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import cv2
from numpy import ndarray

from aniseek.core.interfaces.source import IFrameSource
from aniseek.core.keyframes import extract_keyframe_indices


class OpenCVVideoSource(IFrameSource):
    """Frame source implementation backed by its own internal OpenCV VideoCapture."""

    def __init__(
        self,
        path: str | Path,
        *,
        buffersize: int = 30,
        fps: float | None = None,
    ) -> None:
        self.path = Path(path)
        self.cap = cv2.VideoCapture(str(self.path))
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open video file: {self.path}")

        self._frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        detected_fps = float(self.cap.get(cv2.CAP_PROP_FPS) or 0.0)
        self._fps = float(fps) if fps is not None and fps > 0.0 else detected_fps
        self.buffersize = max(1, buffersize)
        self._keyframe_indices: list[int] | None = None
        self._callback: Callable[[int, int], None] = lambda old, new: None

    def on_frame_count_changed(self, old_count: int, new_count: int) -> None:
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

    def seek(self, frame_id: int) -> None:
        """Position the cursor at the specified frame ID.

        Args:
            frame_id (int): Target frame index (0-based).
        """
        if self.cap is None or not self.cap.isOpened():
            return
        if self._frame_count > 0 and frame_id >= self._frame_count:
            frame_id = max(0, self._frame_count - 1)
        current_pos = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        if current_pos != frame_id:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)

    def read(self) -> tuple[bool, ndarray | None]:
        """Read and decode the next frame.

        Returns:
            tuple[bool, ndarray | None]: (success, frame).
        """
        if self.cap is None or not self.cap.isOpened():
            return False, None

        ret, frame = self.cap.read()
        if ret and frame is not None:
            return ret, frame

        current_pos = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        self._handle_read_failure(current_pos)
        return False, None

    def grab(self) -> bool:
        """Advance cursor without decoding the frame.

        Returns:
            bool: True if next frame could be grabbed, False otherwise.
        """
        if self.cap is None or not self.cap.isOpened():
            return False

        success = bool(self.cap.grab())
        if success:
            return True

        current_pos = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        self._handle_read_failure(current_pos)
        return False

    def probe(self, frame_id: int) -> bool:
        """Test if a frame at frame_id can be positioned and grabbed without failure."""
        if self.cap is None or not self.cap.isOpened() or frame_id < 0:
            return False
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
        return bool(self.cap.grab())

    def is_opened(self) -> bool:
        """Check if the video capture is currently open.

        Returns:
            bool: True if opened, False otherwise.
        """
        return self.cap is not None and bool(self.cap.isOpened())

    def release(self) -> None:
        """Release underlying video capture resources."""
        self._callback = lambda old, new: None
        if self.cap is not None:
            if self.cap.isOpened():
                self.cap.release()
            self.cap = None

    def __enter__(self) -> OpenCVVideoSource:
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.release()
