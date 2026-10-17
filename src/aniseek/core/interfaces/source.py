from __future__ import annotations

import bisect
from abc import ABC, abstractmethod
from collections.abc import Callable

from loguru import logger
from numpy import ndarray


def _noop_callback(old_count: int, new_count: int) -> None:
    pass


class IFrameSource(ABC):
    """Generic interface for frame extraction sources."""

    buffersize: int = 1
    _callback: Callable[[int, int], None] = _noop_callback
    _is_resolving_eof: bool = False

    @property
    @abstractmethod
    def frame_count(self) -> int:
        """Total number of frames available."""
        ...

    @property
    @abstractmethod
    def fps(self) -> float:
        """Frame rate of the video source in frames per second."""
        ...

    @abstractmethod
    def seek(self, frame_id: int) -> None:
        """Position cursor at frame_id.

        Args:
            frame_id (int): Target frame index (0-based).
        """
        ...

    @abstractmethod
    def read(self) -> tuple[bool, ndarray | None]:
        """Read and decode the next frame.

        Returns:
            tuple[bool, ndarray | None]: (success, frame).
        """
        ...

    @abstractmethod
    def grab(self) -> bool:
        """Advance cursor without decoding the frame.

        Returns:
            bool: True if next frame could be grabbed/skipped, False otherwise.
        """
        ...

    @abstractmethod
    def is_opened(self) -> bool:
        """Check if the source is currently open and accessible.

        Returns:
            bool: True if open, False otherwise.
        """
        ...

    @abstractmethod
    def release(self) -> None:
        """Release any resources held by the source."""
        ...

    def get_keyframes(self) -> list[int] | None:
        """Return list of keyframe frame indices if available.

        Returns:
            list[int] | None: Sorted list of keyframe indices, or None.
        """
        return None

    def on_frame_count_changed(self, old_count: int, new_count: int) -> None:
        """Hook called when the decodable frame count is adjusted."""
        self._callback(old_count, new_count)

    def probe(self, frame_id: int) -> bool:
        """Test if a frame at frame_id can be positioned and grabbed without failure.

        Args:
            frame_id (int): Target frame index to test.

        Returns:
            bool: True if decodable/accessible, False otherwise.
        """
        if not self.is_opened() or frame_id < 0:
            return False
        self.seek(frame_id)
        return self.grab()

    def _set_frame_count(self, new_count: int) -> None:
        """Internal helper to update the backing frame count attribute."""
        self._frame_count = new_count

    def validate_frame_count(self) -> int:
        """Validate and adjust frame_count on-demand via binary search.

        Returns:
            int: The actual decodable frame count.
        """
        if not self.is_opened() or self.frame_count <= 0:
            return self.frame_count

        if self.probe(self.frame_count - 1):
            return self.frame_count

        return self._find_true_frame_count()

    def _find_true_frame_count(self) -> int:
        """Locate the exact last decodable frame using keyframe candidates or binary search.

        Returns:
            int: The actual decodable frame count.
        """
        if not self.is_opened() or self.frame_count <= 0:
            return self.frame_count

        was_resolving = self._is_resolving_eof
        self._is_resolving_eof = True
        try:
            kfs = self.get_keyframes()
            if kfs:
                candidates = [k for k in kfs if k < self.frame_count]
                if candidates:
                    last_good = -1
                    if self.probe(candidates[-1]):
                        last_good = candidates[-1]
                    else:
                        low_idx = 0
                        high_idx = len(candidates) - 2
                        while low_idx <= high_idx:
                            mid_idx = (low_idx + high_idx) // 2
                            target = candidates[mid_idx]
                            if self.probe(target):
                                last_good = target
                                low_idx = mid_idx + 1
                            else:
                                high_idx = mid_idx - 1

                    if last_good >= 0:
                        self.seek(last_good)
                        self.grab()
                        curr = last_good
                        while self.grab():
                            curr += 1
                        new_count = curr + 1
                        if 0 < new_count != self.frame_count:
                            logger.info(
                                f"Adjusted frame count from nominal {self.frame_count} "
                                f"to actual decodable {new_count} via keyframe candidates."
                            )
                            old_count = self.frame_count
                            self._set_frame_count(new_count)
                            self.on_frame_count_changed(old_count, new_count)
                        return self.frame_count

            # Fallback sem keyframes: busca binaria
            low = 0
            high = self.frame_count - 1
            last_good = -1
            while low <= high:
                mid = (low + high) // 2
                if self.probe(mid):
                    last_good = mid
                    low = mid + 1
                else:
                    high = mid - 1

            if last_good >= 0:
                new_count = last_good + 1
                if 0 < new_count != self.frame_count:
                    logger.info(
                        f"Adjusted frame count from nominal {self.frame_count} "
                        f"to actual decodable {new_count} via binary search."
                    )
                    old_count = self.frame_count
                    self._set_frame_count(new_count)
                    self.on_frame_count_changed(old_count, new_count)

            return self.frame_count
        finally:
            self._is_resolving_eof = was_resolving

    def _handle_read_failure(self, current_pos: int, probe_window: int = 5) -> None:
        """Handle unexpected read or grab failure with tail probe and EOF resolution.

        Args:
            current_pos (int): Frame position where the failure occurred.
            probe_window (int): Number of trailing frames to check before EOF resolution.
        """
        if self._is_resolving_eof or not self.is_opened() or self.frame_count <= 0:
            return

        if current_pos >= self.frame_count:
            return

        self._is_resolving_eof = True
        try:
            # 1. Reverse tail probe se a falha ocorreu proximo a cauda do stream
            if current_pos >= self.frame_count - probe_window:
                for target in range(current_pos - 1, max(-1, current_pos - probe_window - 1), -1):
                    if self.probe(target):
                        new_count = target + 1
                        logger.info(
                            f"Adjusted frame count from nominal {self.frame_count} "
                            f"to actual decodable {new_count} via tail probe."
                        )
                        old_count = self.frame_count
                        self._set_frame_count(new_count)
                        self.on_frame_count_changed(old_count, new_count)
                        return
                self._find_true_frame_count()
                return

            # 2. Tentativas exponenciais 2^N para N de 0 a 4 (passos 1, 2, 4, 8, 16)
            last_failed = current_pos
            for n in range(5):
                target = current_pos + (1 << n)
                if target >= self.frame_count:
                    break
                if self.probe(target):
                    logger.warning(
                        f"Corrupted frame detected at index {current_pos}; "
                        f"recovered decodable stream at index {target}."
                    )
                    self.seek(target + 1)
                    return
                last_failed = target

            # 3. Se o video possui keyframes, busca galopante nos keyframes a frente
            kfs = self.get_keyframes()
            if kfs:
                start_idx = bisect.bisect_right(kfs, last_failed)
                step_kf = 1
                curr_idx = start_idx
                b_low = start_idx
                b_high = None

                while curr_idx < len(kfs) and kfs[curr_idx] < self.frame_count:
                    target = kfs[curr_idx]
                    if self.probe(target):
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
                        if self.probe(kfs[mid]):
                            best_kf_idx = mid
                            high = mid - 1
                        else:
                            low = mid + 1
                    first_valid_kf = kfs[best_kf_idx]
                    logger.warning(
                        f"Stream hole detected starting at index {current_pos}; "
                        f"recovered decodable stream at keyframe {first_valid_kf}."
                    )
                    self.seek(first_valid_kf + 1)
                    return
            else:
                # 4. Se NAO possui keyframes, continua galope 2^N para N >= 5 (32, 64, 128...)
                n = 5
                first_valid = None
                while True:
                    step = 1 << n
                    target = current_pos + step
                    if target >= self.frame_count:
                        break
                    if self.probe(target):
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
                        if self.probe(mid):
                            exact_recovery = mid
                            high = mid - 1
                        else:
                            low = mid + 1

                    logger.warning(
                        f"Stream hole detected starting at index {current_pos}; "
                        f"recovered decodable stream at index {exact_recovery}."
                    )
                    self.seek(exact_recovery + 1)
                    return

            # 5. Nenhum frame decodifica ate o fim: arquivo acabou ali
            self._find_true_frame_count()
        finally:
            self._is_resolving_eof = False
