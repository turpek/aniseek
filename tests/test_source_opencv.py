from __future__ import annotations

import pytest

from aniseek.core.sources.opencv import OpenCVVideoSource
from aniseek.editing.manager import VideoManager
from aniseek.editing.section import SectionManager, VideoSection
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


def test_opencv_source_instant_init_without_seeks(tmp_path, monkeypatch):
    """Garante abertura instantanea sem executar seeks antecipados no construtor."""
    dummy_file = tmp_path / "video.mp4"
    dummy_file.touch()

    mock_cap = MyVideoCapture(isopened=True, frame_count=500)
    monkeypatch.setattr("cv2.VideoCapture", lambda _: mock_cap)

    source = OpenCVVideoSource(dummy_file)

    assert source.frame_count == 500
    assert mock_cap.index == 0


def test_opencv_source_lazy_adjusts_inflated_frame_count_on_read(tmp_path, monkeypatch):
    """Ajusta frame_count de forma lazy durante a leitura quando container contem frames fantasmas."""
    dummy_file = tmp_path / "video.mp4"
    dummy_file.touch()

    class InflatedVideoCapture(MyVideoCapture):
        def grab(self) -> bool:
            if self.index >= 498:
                return False
            self.index += 1
            return True

        def read(self, image=None):
            if self.index >= 498:
                return False, None
            return super().read(image)

    mock_cap = InflatedVideoCapture(isopened=True, frame_count=500)
    monkeypatch.setattr("cv2.VideoCapture", lambda _: mock_cap)

    source = OpenCVVideoSource(dummy_file)
    source.seek(496)
    ret1, _ = source.read()
    ret2, _ = source.read()
    ret3, _ = source.read()

    assert ret1 is True
    assert ret2 is True
    assert ret3 is False
    assert source.frame_count == 498


def test_opencv_source_validate_frame_count_on_demand(tmp_path, monkeypatch):
    """Permite validar e ajustar a contagem de frames sob demanda via busca binaria."""
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
    actual_count = source.validate_frame_count()

    assert actual_count == 498
    assert source.frame_count == 498


def test_opencv_source_recovers_from_corrupted_frame_via_probe(tmp_path, monkeypatch):
    """Recupera fluxo de decodificacao apos frame corrompido sem truncar frame_count."""
    dummy_file = tmp_path / "video.mp4"
    dummy_file.touch()

    class CorruptVideoCapture(MyVideoCapture):
        def read(self, image=None):
            if self.index == 10:
                self.index += 1
                return False, None
            return super().read(image)

    mock_cap = CorruptVideoCapture(isopened=True, frame_count=100)
    monkeypatch.setattr("cv2.VideoCapture", lambda _: mock_cap)

    source = OpenCVVideoSource(dummy_file)
    source.seek(10)
    corrupted_ret, corrupted_frame = source.read()
    recovered_ret, recovered_frame = source.read()

    assert corrupted_ret is False
    assert corrupted_frame is None
    assert recovered_ret is True
    assert recovered_frame is not None
    assert source.frame_count == 100


def test_opencv_source_custom_buffersize_and_fps(tmp_path, monkeypatch):
    """Permite sobrescrever buffersize e fps na inicializacao."""
    dummy_file = tmp_path / "video.mp4"
    dummy_file.touch()

    mock_cap = MyVideoCapture(isopened=True)
    monkeypatch.setattr("cv2.VideoCapture", lambda _: mock_cap)

    source = OpenCVVideoSource(dummy_file, buffersize=45, fps=60.0)

    assert source.buffersize == 45
    assert source.fps == 60.0


def test_opencv_source_finds_frame_count_via_keyframe_candidates(tmp_path, monkeypatch):
    """Localiza o ultimo frame decodificavel atraves de candidatos de keyframes."""
    dummy_file = tmp_path / "video.mp4"
    dummy_file.touch()

    class TruncatedVideoCapture(MyVideoCapture):
        def grab(self) -> bool:
            if self.index >= 350:
                return False
            self.index += 1
            return True

    mock_cap = TruncatedVideoCapture(isopened=True, frame_count=500)
    monkeypatch.setattr("cv2.VideoCapture", lambda _: mock_cap)

    source = OpenCVVideoSource(dummy_file)
    monkeypatch.setattr(source, "get_keyframes", lambda: [0, 100, 200, 300, 400])

    actual = source.validate_frame_count()
    assert actual == 350
    assert source.frame_count == 350


def test_opencv_source_tail_probe_adjusts_frame_count_immediately(tmp_path, monkeypatch):
    """Ajusta frame count diretamente via probe reverso na cauda do stream."""
    dummy_file = tmp_path / "video.mp4"
    dummy_file.touch()

    class OffByOneVideoCapture(MyVideoCapture):
        def read(self, image=None):
            if self.index >= 99:
                return False, None
            return super().read(image)

        def grab(self) -> bool:
            if self.index >= 99:
                return False
            return super().grab()

    mock_cap = OffByOneVideoCapture(isopened=True, frame_count=100)
    monkeypatch.setattr("cv2.VideoCapture", lambda _: mock_cap)

    source = OpenCVVideoSource(dummy_file)
    source.seek(99)
    ret, frame = source.read()

    assert ret is False
    assert frame is None
    assert source.frame_count == 99


def test_opencv_source_calls_on_frame_count_changed(tmp_path, monkeypatch):
    """Verifica que on_frame_count_changed e chamado quando o final real e detectado."""
    dummy_file = tmp_path / "video.mp4"
    dummy_file.touch()

    class OffByTwoVideoCapture(MyVideoCapture):
        def read(self, image=None):
            if self.index >= 98:
                return False, None
            return super().read(image)

        def grab(self) -> bool:
            if self.index >= 98:
                return False
            return super().grab()

    mock_cap = OffByTwoVideoCapture(isopened=True, frame_count=100)
    monkeypatch.setattr("cv2.VideoCapture", lambda _: mock_cap)

    source = OpenCVVideoSource(dummy_file)
    recorded_changes = []
    source._callback = lambda old, new: recorded_changes.append((old, new))

    source.seek(99)
    source.read()

    assert source.frame_count == 98
    assert recorded_changes == [(100, 98)]


def test_video_manager_updates_section_and_mapping_when_frame_count_changes(tmp_path, monkeypatch):
    """Verifica que o VideoManager atualiza SectionManager e FrameMapper apos ajuste de frame count."""
    dummy_file = tmp_path / "video.mp4"
    dummy_file.touch()

    class TruncatedCap(MyVideoCapture):
        def read(self, image=None):
            if self.index >= 98:
                return False, None
            return super().read(image)

        def grab(self) -> bool:
            if self.index >= 98:
                return False
            return super().grab()

    mock_cap = TruncatedCap(isopened=True, frame_count=100)
    monkeypatch.setattr("cv2.VideoCapture", lambda _: mock_cap)

    source = OpenCVVideoSource(dummy_file)
    manager = VideoManager(25, False)
    sec = VideoSection(0, 100)
    sec_man = SectionManager([sec])
    manager.open_source(source, sections=sec_man)

    assert manager.frame_count == 100
    assert sec.end == 100
    assert len(manager.mapping) == 100

    source.seek(99)
    source.read()

    assert manager.frame_count == 98
    assert sec.end == 98
    assert len(manager.mapping) == 98
    manager.player.servant.join_like()
    manager.player.master.join_like()
    manager.trash.join()


def test_opencv_source_progressive_hole_recovery(tmp_path, monkeypatch):
    """Recupera fluxo de decodificacao apos buraco de frames sem alterar frame_count."""
    dummy_file = tmp_path / "video.mp4"
    dummy_file.touch()

    class HoleCap(MyVideoCapture):
        def read(self, image=None):
            if 10 <= self.index <= 20:
                self.index += 1
                return False, None
            return super().read(image)

        def grab(self) -> bool:
            if 10 <= self.index <= 20:
                self.index += 1
                return False
            return super().grab()

    mock_cap = HoleCap(isopened=True, frame_count=100)
    monkeypatch.setattr("cv2.VideoCapture", lambda _: mock_cap)

    source = OpenCVVideoSource(dummy_file)
    monkeypatch.setattr(source, "get_keyframes", lambda: [0, 24, 48, 72])

    source.seek(10)
    failed_ret, failed_frame = source.read()
    recovered_ret, recovered_frame = source.read()

    assert failed_ret is False
    assert failed_frame is None
    assert recovered_ret is True
    assert recovered_frame is not None
    assert source.frame_count == 100
