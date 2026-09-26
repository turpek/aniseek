from abc import ABC, abstractmethod

from numpy import ndarray


class IFrameSource(ABC):
    """Generic interface for frame extraction sources."""

    buffersize: int = 1

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
