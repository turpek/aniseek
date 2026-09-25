from __future__ import annotations

from pathlib import Path

import cv2
from numpy import ndarray

from aniseek.core.interfaces.source import IFrameSource

SUPPORTED_EXTENSIONS: tuple[str, ...] = (
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
)


class ImageSource(IFrameSource):
    """Frame source implementation backed by a directory of image files."""

    def __init__(
        self,
        path: str | Path,
        *,
        buffersize: int = 30,
        fps: float = 24.0,
        extensions: tuple[str, ...] = SUPPORTED_EXTENSIONS,
    ) -> None:
        self.path = Path(path)
        if not self.path.exists() or not self.path.is_dir():
            raise RuntimeError(
                f"Directory does not exist or is not a directory: {self.path}"
            )

        self._image_paths = sorted(
            f for f in self.path.iterdir()
            if f.is_file() and f.suffix.lower() in extensions
        )
        self._frame_count = len(self._image_paths)
        self._fps = float(fps if fps > 0.0 else 24.0)
        self.buffersize = max(1, buffersize)
        self._cursor = 0
        self._is_opened = True

    @property
    def frame_count(self) -> int:
        """Total number of images available in the directory."""
        return self._frame_count

    @property
    def fps(self) -> float:
        """Configured frames per second of the image source."""
        return self._fps

    def seek(self, frame_id: int) -> None:
        """Position the cursor at the specified frame ID.

        Args:
            frame_id (int): Target frame index (0-based).
        """
        self._cursor = max(0, frame_id)

    def read(self) -> tuple[bool, ndarray | None]:
        """Read and decode the next image.

        Returns:
            tuple[bool, ndarray | None]: (success, frame).
        """
        if not self._is_opened or self._cursor >= self._frame_count:
            return False, None

        image_path = self._image_paths[self._cursor]
        frame = cv2.imread(str(image_path))
        self._cursor += 1

        if frame is not None:
            return True, frame
        return False, None

    def grab(self) -> bool:
        """Advance cursor without decoding the image.

        Returns:
            bool: True if next image could be grabbed, False otherwise.
        """
        if not self._is_opened or self._cursor >= self._frame_count:
            return False

        self._cursor += 1
        return True

    def is_opened(self) -> bool:
        """Check if the image source is currently open and accessible.

        Returns:
            bool: True if opened, False otherwise.
        """
        return self._is_opened

    def release(self) -> None:
        """Release any resources held by the source."""
        self._is_opened = False

    def __enter__(self) -> ImageSource:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()
