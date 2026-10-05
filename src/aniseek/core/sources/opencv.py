from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import cv2
from loguru import logger
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

        # 1. Reverse tail probe for common stream end / container off-by-one mismatch
        if current_pos >= self._frame_count - probe_window:
            for target in range(current_pos - 1, max(-1, current_pos - probe_window - 1), -1):
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, target)
                if self.cap.grab():
                    new_count = target + 1
                    logger.info(
                        f"Adjusted frame count from nominal {self._frame_count} "
                        f"to actual decodable {new_count} via tail probe."
                    )
                    old_count = self._frame_count
                    self._frame_count = new_count
                    self.on_frame_count_changed(old_count, new_count)
                    return

        # 2. Forward probe to recover from isolated corrupted frame
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

        # 3. Probes failed: locate true end via keyframe candidates or galloping search
        self._find_true_frame_count()

    def _find_true_frame_count(self) -> int:
        """Locate the exact last decodable frame using keyframe candidates or galloping binary search."""
        if self._frame_count <= 0:
            return 0

        # Attempt candidate keyframe search first (1 seek in typical tail/overflow case)
        kfs = self.get_keyframes()
        if kfs:
            candidates = [k for k in kfs if k < self._frame_count]
            if candidates:
                last_good = -1
                # Check last keyframe candidate first (optimal guess for tail/overflow)
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, candidates[-1])
                if self.cap.grab():
                    last_good = candidates[-1]
                else:
                    # Binary search on candidate indices
                    low_idx = 0
                    high_idx = len(candidates) - 2
                    while low_idx <= high_idx:
                        mid_idx = (low_idx + high_idx) // 2
                        target = candidates[mid_idx]
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, target)
                        if self.cap.grab():
                            last_good = target
                            low_idx = mid_idx + 1
                        else:
                            high_idx = mid_idx - 1

                if last_good >= 0:
                    # Sequential finish from last_good to EOF (within 1 GOP)
                    curr = last_good
                    while self.cap.grab():
                        curr += 1
                    new_count = curr + 1
                    if new_count != self._frame_count:
                        logger.info(
                            f"Adjusted frame count from nominal {self._frame_count} "
                            f"to actual decodable {new_count} via keyframe candidates."
                        )
                        old_count = self._frame_count
                        self._frame_count = new_count
                        self.on_frame_count_changed(old_count, new_count)
                    return self._frame_count

        # Fallback: Galloping search backwards + binary search + sequential finish
        new_count = self._galloping_find_true_frame_count()
        if new_count != self._frame_count:
            logger.info(
                f"Adjusted frame count from nominal {self._frame_count} "
                f"to actual decodable {new_count} via galloping search."
            )
            old_count = self._frame_count
            self._frame_count = new_count
            self.on_frame_count_changed(old_count, new_count)

        return self._frame_count

    def _galloping_find_true_frame_count(self, sequential_threshold: int = 64) -> int:
        """Locate last decodable frame using reverse galloping and sequential finish."""
        high = self._frame_count - 1
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, high)
        if self.cap.grab():
            return high + 1

        # 1. Reverse exponential backoff
        step = 16
        b_low = None
        b_high = high
        while step < self._frame_count:
            target = max(0, high - step)
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, target)
            if self.cap.grab():
                b_low = target
                b_high = high - (step // 16) if step > 16 else high
                break
            step *= 16

        if b_low is None:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            if not self.cap.grab():
                return 0
            b_low = 0

        # 2. Binary search on narrowed window
        last_good = b_low
        while (b_high - b_low) > sequential_threshold:
            mid = (b_low + b_high) // 2
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, mid)
            if self.cap.grab():
                last_good = mid
                b_low = mid + 1
            else:
                b_high = mid - 1

        # 3. Sequential finish from last known good frame
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, last_good)
        self.cap.grab()
        curr = last_good
        while self.cap.grab():
            curr += 1

        return curr + 1

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
