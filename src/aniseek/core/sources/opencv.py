from __future__ import annotations

from pathlib import Path

import cv2
from numpy import ndarray

from aniseek.core.interfaces.source import IFrameSource


class OpenCVVideoSource(IFrameSource):
    """Frame source implementation backed by its own internal OpenCV VideoCapture."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.cap = cv2.VideoCapture(str(self.path))
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open video file: {self.path}")

        self._frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self._fps = float(self.cap.get(cv2.CAP_PROP_FPS) or 0.0)

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
        current_pos = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        if current_pos != frame_id:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)

    def read(self) -> tuple[bool, ndarray | None]:
        """Read and decode the next frame.

        Returns:
            tuple[bool, ndarray | None]: (success, frame).
        """
        return self.cap.read()

    def grab(self) -> bool:
        """Advance cursor without decoding the frame.

        Returns:
            bool: True if next frame could be grabbed, False otherwise.
        """
        return bool(self.cap.grab())

    def is_opened(self) -> bool:
        """Check if the video capture is currently open.

        Returns:
            bool: True if opened, False otherwise.
        """
        return bool(self.cap.isOpened())

    def release(self) -> None:
        """Release underlying video capture resources."""
        if self.cap is not None and self.cap.isOpened():
            self.cap.release()

    def __enter__(self) -> OpenCVVideoSource:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()
