from __future__ import annotations

import cv2
from numpy import ndarray

from aniseek.view.interfaces.display import IFrameDisplay


class CV2Display(IFrameDisplay):
    """OpenCV HighGUI implementation of IFrameDisplay."""

    def __init__(self, name: str = "aniseek") -> None:
        self._name = name
        self._is_open = False

    @property
    def name(self) -> str:
        """Window name or identifier."""
        return self._name

    @property
    def is_open(self) -> bool:
        """True if the window has been created and not yet destroyed."""
        return self._is_open

    def create_window(self, name: str = "aniseek", width: int = 720, height: int = 420) -> None:
        """Create and configure an OpenCV window."""
        self._name = name
        cv2.namedWindow(self._name, cv2.WINDOW_NORMAL | cv2.WINDOW_GUI_NORMAL)
        cv2.resizeWindow(self._name, width, height)
        self._is_open = True

    def show_frame(self, frame: ndarray) -> None:
        """Render frame in the OpenCV window."""
        if self._is_open:
            cv2.imshow(self._name, frame)

    def set_title(self, title: str) -> None:
        """Set window title."""
        if self._is_open:
            cv2.setWindowTitle(self._name, title)

    def close(self) -> None:
        """Destroy the OpenCV window."""
        if self._is_open:
            cv2.destroyWindow(self._name)
            self._is_open = False


class NullDisplay(IFrameDisplay):
    """Headless no-op display implementation useful for tests, batch jobs, and CI/CD."""

    def __init__(self, name: str = "aniseek") -> None:
        self._name = name
        self._is_open = False
        self.last_frame: ndarray | None = None
        self.last_title: str | None = None

    @property
    def name(self) -> str:
        """Window name or identifier."""
        return self._name

    @property
    def is_open(self) -> bool:
        """True if window is considered active."""
        return self._is_open

    def create_window(self, name: str = "aniseek", width: int = 720, height: int = 420) -> None:
        """Simulate creating a window."""
        self._name = name
        self._is_open = True

    def show_frame(self, frame: ndarray) -> None:
        """Capture the frame in memory without rendering."""
        self.last_frame = frame

    def set_title(self, title: str) -> None:
        """Capture the title in memory."""
        self.last_title = title

    def close(self) -> None:
        """Mark display as closed."""
        self._is_open = False


AVAILABLE_DISPLAYS: dict[str, type[IFrameDisplay]] = {
    "cv2": CV2Display,
    "opencv": CV2Display,
    "null": NullDisplay,
    "headless": NullDisplay,
}


def resolve_display(display: type[IFrameDisplay] | str | None) -> type[IFrameDisplay]:
    """Resolve display class from string identifier or class type.

    Args:
        display: Display class, string identifier ('cv2', 'null'), or None for default.

    Returns:
        type[IFrameDisplay]: Resolved concrete display class.

    Raises:
        ValueError: If string identifier is not recognized.
        TypeError: If display is not a subclass of IFrameDisplay.
    """
    if display is None:
        return CV2Display
    if isinstance(display, str):
        key = display.strip().lower()
        if key in AVAILABLE_DISPLAYS:
            return AVAILABLE_DISPLAYS[key]
        raise ValueError(
            f"Unknown display '{display}'. Expected one of: {list(AVAILABLE_DISPLAYS.keys())}"
        )
    if isinstance(display, type) and issubclass(display, IFrameDisplay):
        return display
    raise TypeError(
        f"Expected display to be a subclass of IFrameDisplay or one of {list(AVAILABLE_DISPLAYS.keys())}, got {display}"
    )
