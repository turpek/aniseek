from __future__ import annotations

from pathlib import Path

import cv2
from loguru import logger
from numpy import ndarray

from aniseek.core.interfaces.source import IFrameSource


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
        ret, frame = self.cap.read()
        if ret and frame is not None:
            return ret, frame

        self._handle_read_failure()
        return False, None

    def grab(self) -> bool:
        """Advance cursor without decoding the frame.

        Returns:
            bool: True if next frame could be grabbed, False otherwise.
        """
        success = bool(self.cap.grab())
        if success:
            return True

        self._handle_read_failure()
        return False

    def _handle_read_failure(self, probe_window: int = 5) -> None:
        """Handle unexpected read or grab failure with tolerance probe and binary search."""
        if self._frame_count <= 0:
            return

        current_pos = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        if current_pos >= self._frame_count:
            return

        # 1. Probe de tolerância para descartar frame corrompido pontual (Caso 3)
        for offset in range(1, probe_window + 1):
            target = current_pos + offset
            if target >= self._frame_count:
                break
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, target)
            if self.cap.grab():
                logger.warning(
                    f"Corrupted frame detected at index {current_pos}; "
                    f"recovered decodable stream at index {target}."
                )
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, current_pos + 1)
                return

        # 2. Probe falhou: stream encerrou prematuramente (Caso 2)
        self._find_true_frame_count()

    def _find_true_frame_count(self) -> int:
        """Locate the exact last decodable frame using binary search and update frame_count."""
        low = 0
        high = self._frame_count - 1
        ans = -1

        # Verifica se o primeiro frame é decodificável
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, low)
        if self.cap.grab():
            ans = low
            b_low = low + 1
            b_high = high
            while b_low <= b_high:
                mid = (b_low + b_high) // 2
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, mid)
                if self.cap.grab():
                    ans = mid
                    b_low = mid + 1
                else:
                    b_high = mid - 1

        new_count = ans + 1 if ans >= 0 else 0
        if new_count != self._frame_count:
            logger.info(
                f"Adjusted frame count from nominal {self._frame_count} "
                f"to actual decodable {new_count}."
            )
            self._frame_count = new_count

        return self._frame_count

    def validate_frame_count(self) -> int:
        """Validate and adjust frame_count on-demand via binary search.

        Returns:
            int: The actual decodable frame count.
        """
        if self._frame_count <= 0:
            return 0

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self._frame_count - 1)
        if not self.cap.grab():
            return self._find_true_frame_count()

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        return self._frame_count

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
