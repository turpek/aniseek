from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pytest

from aniseek.core.sources.opencv import OpenCVVideoSource
from aniseek.view.display import (
    CV2Display,
    NullDisplay,
    resolve_display,
)
from aniseek.view.interfaces.display import IFrameDisplay
from aniseek.view.video import FrameViewer
from tests.uteis import MyVideoCapture


def test_resolve_display_with_none_returns_cv2_display():
    """Verifica que None resolve para a classe CV2Display por padrão."""
    result = resolve_display(None)
    assert result is CV2Display


@pytest.mark.parametrize(
    "name,expected_cls",
    [
        ("cv2", CV2Display),
        ("opencv", CV2Display),
        ("null", NullDisplay),
        ("headless", NullDisplay),
    ],
    ids=["cv2", "opencv", "null", "headless"],
)
def test_resolve_display_with_valid_strings(name: str, expected_cls: type[IFrameDisplay]):
    """Verifica resolução de classes IFrameDisplay a partir de identificadores string válidos."""
    result = resolve_display(name)
    assert result is expected_cls


def test_resolve_display_with_subclass_returns_same_class():
    """Verifica que uma subclasse válida de IFrameDisplay é retornada diretamente."""
    result = resolve_display(NullDisplay)
    assert result is NullDisplay


def test_resolve_display_with_unknown_string_raises_value_error():
    """Verifica que strings não reconhecidas disparam ValueError."""
    with pytest.raises(ValueError, match="Unknown display 'invalid'"):
        resolve_display("invalid")


def test_resolve_display_with_invalid_type_raises_type_error():
    """Verifica que tipos incompatíveis disparam TypeError."""
    with pytest.raises(TypeError, match="Expected display to be a subclass of IFrameDisplay"):
        resolve_display(123)  # type: ignore[arg-type]


def test_cv2_display_lifecycle():
    """Verifica o ciclo de vida completo de criação, exibição e fechamento no CV2Display."""
    display = CV2Display(name="test_window")
    dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)

    with (
        patch("cv2.namedWindow") as mock_named,
        patch("cv2.resizeWindow") as mock_resize,
        patch("cv2.imshow") as mock_imshow,
        patch("cv2.setWindowTitle") as mock_set_title,
        patch("cv2.destroyWindow") as mock_destroy,
    ):
        display.create_window(name="test_window", width=800, height=600)
        assert display.is_open is True
        mock_named.assert_called_once()
        mock_resize.assert_called_once_with("test_window", 800, 600)

        display.show_frame(dummy_frame)
        mock_imshow.assert_called_once_with("test_window", dummy_frame)

        display.set_title("New Title")
        mock_set_title.assert_called_once_with("test_window", "New Title")

        display.close()
        assert display.is_open is False
        mock_destroy.assert_called_once_with("test_window")


def test_null_display_lifecycle():
    """Verifica que NullDisplay captura frames e títulos em memória sem invocar janelas."""
    display = NullDisplay(name="headless")
    dummy_frame = np.zeros((50, 50, 3), dtype=np.uint8)

    display.create_window(name="headless", width=640, height=480)
    assert display.is_open is True

    display.show_frame(dummy_frame)
    assert display.last_frame is dummy_frame

    display.set_title("Headless Mode")
    assert display.last_title == "Headless Mode"

    display.close()
    assert display.is_open is False


def test_frame_viewer_with_null_display(tmp_path):
    """Verifica que FrameViewer funciona em modo headless sem tocar no OpenCV HighGUI."""
    video_path = tmp_path / "clip.mp4"
    video_path.touch()

    with patch("cv2.VideoCapture") as mock_cap_cls:
        mock_cap_cls.return_value = MyVideoCapture(frame_count=100)
        source = OpenCVVideoSource(video_path)
        viewer = FrameViewer(source, display="null")

        assert isinstance(viewer.display, NullDisplay)
        assert viewer.display.is_open is True
        assert viewer.controller is viewer.video_controller
        assert viewer.video_manager is viewer._video_manager

        flag, frame = viewer.read()
        viewer.show(flag, frame)
        assert viewer.display.last_frame is not None

        viewer.quit()
        assert viewer.display.is_open is False
