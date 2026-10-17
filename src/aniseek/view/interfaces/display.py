from __future__ import annotations

from abc import ABC, abstractmethod

from numpy import ndarray


class IFrameDisplay(ABC):
    """Abstract interface for video frame display and window lifecycle."""

    @abstractmethod
    def create_window(self, name: str = "videoseq", width: int = 720, height: int = 420) -> None:
        """Initialize and configure the display window.

        Args:
            name: Window title or identifier.
            width: Initial window width in pixels.
            height: Initial window height in pixels.
        """
        ...

    @abstractmethod
    def show_frame(self, frame: ndarray) -> None:
        """Render a single frame on the display.

        Args:
            frame: Image array to display.
        """
        ...

    @abstractmethod
    def set_title(self, title: str) -> None:
        """Update window title with dynamic status or metadata.

        Args:
            title: Formatted title string.
        """
        ...

    @abstractmethod
    def close(self) -> None:
        """Destroy the display window and release underlying graphics resources."""
        ...
