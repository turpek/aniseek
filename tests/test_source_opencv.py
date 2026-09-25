from __future__ import annotations

import pytest

from aniseek.core.sources.opencv import OpenCVVideoSource
from tests.uteis import MyVideoCapture


def test_opencv_source_raises_on_missing_file(tmp_path):
    """Verifica se RuntimeError é levantado quando o arquivo de vídeo não pode ser aberto."""
    missing_file = tmp_path / "non_existent.mp4"

    with pytest.raises(RuntimeError):
        OpenCVVideoSource(missing_file)


def test_opencv_source_raises_when_cannot_open(tmp_path, monkeypatch):
    """Verifica se RuntimeError é levantado quando o OpenCV não consegue abrir o arquivo."""
    dummy_file = tmp_path / "video.mp4"
    dummy_file.touch()

    monkeypatch.setattr("cv2.VideoCapture", lambda _: MyVideoCapture(isopened=False))

    with pytest.raises(RuntimeError):
        OpenCVVideoSource(dummy_file)


def test_opencv_source_read_and_seek(tmp_path, monkeypatch):
    """Valida leitura, seek e propriedades básicas de frame_count e fps."""
    dummy_file = tmp_path / "video.mp4"
    dummy_file.touch()

    mock_cap = MyVideoCapture(isopened=True)
    monkeypatch.setattr("cv2.VideoCapture", lambda _: mock_cap)

    source = OpenCVVideoSource(dummy_file)

    assert source.frame_count == 500
    assert source.fps == 24.0

    ret, frame = source.read()
    assert ret is True
    assert frame is not None

    source.seek(10)
    assert mock_cap.index == 10

    source.grab()
    assert mock_cap.index == 11

    source.release()
    assert source.is_opened() is False


def test_opencv_source_context_manager(tmp_path, monkeypatch):
    """Valida liberação de recursos ao utilizar o context manager."""
    dummy_file = tmp_path / "video.mp4"
    dummy_file.touch()

    mock_cap = MyVideoCapture(isopened=True)
    monkeypatch.setattr("cv2.VideoCapture", lambda _: mock_cap)

    with OpenCVVideoSource(dummy_file) as source:
        assert source.is_opened() is True

    assert source.is_opened() is False


def test_opencv_source_adjusts_inflated_frame_count(tmp_path, monkeypatch):
    """Ajusta frame_count quando o container reporta mais frames do que os realmente decodificáveis."""
    dummy_file = tmp_path / "video.mp4"
    dummy_file.touch()

    class InflatedVideoCapture(MyVideoCapture):
        def grab(self) -> bool:
            if self.index >= 498:
                return False
            self.index += 1
            return True

    mock_cap = InflatedVideoCapture(isopened=True, frame_count=500)
    monkeypatch.setattr("cv2.VideoCapture", lambda _: mock_cap)

    source = OpenCVVideoSource(dummy_file)
    assert source.frame_count == 498
    assert mock_cap.index == 0


def test_opencv_source_custom_buffersize_and_fps(tmp_path, monkeypatch):
    """Permite sobrescrever buffersize e fps na inicializacao."""
    dummy_file = tmp_path / "video.mp4"
    dummy_file.touch()

    mock_cap = MyVideoCapture(isopened=True)
    monkeypatch.setattr("cv2.VideoCapture", lambda _: mock_cap)

    source = OpenCVVideoSource(dummy_file, buffersize=45, fps=60.0)
    assert source.buffersize == 45
    assert source.fps == 60.0
