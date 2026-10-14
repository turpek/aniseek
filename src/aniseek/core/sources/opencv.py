from __future__ import annotations

import bisect
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

        self._handle_read_failure()
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

        self._handle_read_failure()
        return False

    def _handle_read_failure(self, probe_window: int = 5) -> None:
        """Handle unexpected read or grab failure with 2^N progressive probing and EOF resolution."""
        if self.cap is None or not self.cap.isOpened() or self._frame_count <= 0:
            return

        current_pos = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        if current_pos >= self._frame_count:
            return

        # 1. Reverse tail probe se a falha ocorreu proximo a cauda do stream
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
            self._find_true_frame_count()
            return

        # 2. Tentativas exponenciais 2^N para N de 0 a 4 (passos 1, 2, 4, 8, 16)
        last_failed = current_pos
        for n in range(5):  # 2^0=1, 2^1=2, 2^2=4, 2^3=8, 2^4=16
            target = current_pos + (1 << n)
            if target >= self._frame_count:
                break
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, target)
            if self.cap.grab():
                logger.warning(
                    f"Corrupted frame detected at index {current_pos}; "
                    f"recovered decodable stream at index {target}."
                )
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, target + 1)
                return
            last_failed = target

        # 3. Se o vídeo possui keyframes, busca galopante exponencial nos keyframes a frente
        kfs = self.get_keyframes()
        if kfs:
            start_idx = bisect.bisect_right(kfs, last_failed)
            step_kf = 1
            curr_idx = start_idx
            b_low = start_idx
            b_high = None

            while curr_idx < len(kfs) and kfs[curr_idx] < self._frame_count:
                target = kfs[curr_idx]
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, target)
                if self.cap.grab():
                    b_high = curr_idx
                    break
                last_failed = target
                b_low = curr_idx + 1
                curr_idx = start_idx + step_kf
                step_kf *= 2

            if b_high is not None:
                low = b_low
                high = b_high
                best_kf_idx = b_high
                while low <= high:
                    mid = (low + high) // 2
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, kfs[mid])
                    if self.cap.grab():
                        best_kf_idx = mid
                        high = mid - 1
                    else:
                        low = mid + 1
                first_valid_kf = kfs[best_kf_idx]
                logger.warning(
                    f"Stream hole detected starting at index {current_pos}; "
                    f"recovered decodable stream at keyframe {first_valid_kf}."
                )
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, first_valid_kf + 1)
                return

        else:
            # 4. Se NÃO possui keyframes, continua galope 2^N para N >= 5 (32, 64, 128...)
            n = 5
            first_valid = None
            while True:
                step = 1 << n
                target = current_pos + step
                if target >= self._frame_count:
                    break
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, target)
                if self.cap.grab():
                    first_valid = target
                    break
                last_failed = target
                n += 1

            if first_valid is not None:
                low = last_failed + 1
                high = first_valid
                exact_recovery = first_valid
                while low <= high:
                    mid = (low + high) // 2
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, mid)
                    if self.cap.grab():
                        exact_recovery = mid
                        high = mid - 1
                    else:
                        low = mid + 1

                logger.warning(
                    f"Stream hole detected starting at index {current_pos}; "
                    f"recovered decodable stream at index {exact_recovery}."
                )
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, exact_recovery + 1)
                return

        # 5. Nenhum frame decodifica até o fim: o arquivo físico acabou ali!
        self._find_true_frame_count()

    def _find_true_frame_count(self) -> int:
        """Locate the exact last decodable frame using keyframe candidates or binary search."""
        if self.cap is None or not self.cap.isOpened() or self._frame_count <= 0:
            return self._frame_count

        kfs = self.get_keyframes()
        if kfs:
            candidates = [k for k in kfs if k < self._frame_count]
            if candidates:
                last_good = -1
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, candidates[-1])
                if self.cap.grab():
                    last_good = candidates[-1]
                else:
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
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, last_good)
                    self.cap.grab()
                    curr = last_good
                    while self.cap.grab():
                        curr += 1
                    new_count = curr + 1
                    if 0 < new_count != self._frame_count:
                        logger.info(
                            f"Adjusted frame count from nominal {self._frame_count} "
                            f"to actual decodable {new_count} via keyframe candidates."
                        )
                        old_count = self._frame_count
                        self._frame_count = new_count
                        self.on_frame_count_changed(old_count, new_count)
                    return self._frame_count

        # Fallback sem keyframes: busca binária
        low = 0
        high = self._frame_count - 1
        last_good = -1
        while low <= high:
            mid = (low + high) // 2
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, mid)
            if self.cap.grab():
                last_good = mid
                low = mid + 1
            else:
                high = mid - 1

        if last_good >= 0:
            new_count = last_good + 1
            if 0 < new_count != self._frame_count:
                logger.info(
                    f"Adjusted frame count from nominal {self._frame_count} "
                    f"to actual decodable {new_count} via binary search."
                )
                old_count = self._frame_count
                self._frame_count = new_count
                self.on_frame_count_changed(old_count, new_count)

        return self._frame_count

    def validate_frame_count(self) -> int:
        """Validate and adjust frame_count on-demand via binary search.

        Returns:
            int: The actual decodable frame count.
        """
        if self.cap is None or not self.cap.isOpened() or self._frame_count <= 0:
            return self._frame_count

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self._frame_count - 1)
        if self.cap.grab():
            return self._frame_count

        return self._find_true_frame_count()

    def is_opened(self) -> bool:
        """Check if the video capture is currently open.

        Returns:
            bool: True if opened, False otherwise.
        """
        return self.cap is not None and bool(self.cap.isOpened())

    def release(self) -> None:
        """Release underlying video capture resources."""
        if self.cap is not None:
            if self.cap.isOpened():
                self.cap.release()
            self.cap = None

    def __enter__(self) -> OpenCVVideoSource:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()
