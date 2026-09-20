from __future__ import annotations

from unittest.mock import patch

import pytest

from aniseek.core.interfaces.source import IFrameSource
from aniseek.core.sources.image import ImageSource
from aniseek.core.sources.opencv import OpenCVVideoSource
from aniseek.core.sources.registry import SourceRegistry, source_registry
from tests.uteis import MyVideoCapture


@pytest.fixture(autouse=True)
def reset_registry():
    """Garante estado limpo do registry antes e depois de cada teste."""
    source_registry.reset()
    yield
    source_registry.reset()


def test_registry_singleton():
    """Verifica que instâncias de SourceRegistry compartilham o mesmo estado."""
    reg1 = SourceRegistry()
    reg2 = SourceRegistry()

    assert reg1 is reg2
    assert reg1 is source_registry


def test_registry_resolves_image_directory(tmp_path):
    """Resolve diretório existente para instância de ImageSource."""
    img_dir = tmp_path / "images"
    img_dir.mkdir()

    source = source_registry.create_source(img_dir)

    assert isinstance(source, ImageSource)
    assert source.path == img_dir


def test_registry_resolves_video_file(tmp_path):
    """Resolve arquivo de vídeo para instância de OpenCVVideoSource."""
    video_file = tmp_path / "clip.mp4"
    video_file.touch()

    with patch("cv2.VideoCapture", return_value=MyVideoCapture(isopened=True)):
        source = source_registry.create_source(video_file)

    assert isinstance(source, OpenCVVideoSource)
    assert source.path == video_file


def test_registry_raises_on_unopenable_video_path(tmp_path):
    """Verifica se RuntimeError é levantado pelo backend quando o vídeo não pode ser aberto."""
    missing = tmp_path / "non_existent.mp4"

    with pytest.raises(RuntimeError, match="Could not open video file"):
        source_registry.create_source(missing)


def test_registry_raises_on_unsupported_extension(tmp_path):
    """Verifica se ValueError é levantado para extensões de arquivo não suportadas."""
    unsupported = tmp_path / "document.pdf"
    unsupported.touch()

    with pytest.raises(ValueError):
        source_registry.create_source(unsupported)


def test_registry_allows_custom_video_source(tmp_path):
    """Permite registrar classe customizada de IFrameSource para vídeo."""
    video_file = tmp_path / "clip.mkv"
    video_file.touch()

    class CustomVideoSource(IFrameSource):
        def __init__(self, path, **kwargs):
            self.path = path

        @property
        def frame_count(self) -> int:
            return 100

        def seek(self, frame_id: int) -> None:
            pass

        def read(self):
            return True, None

        def grab(self) -> bool:
            return True

        def is_opened(self) -> bool:
            return True

        def release(self) -> None:
            pass

    source_registry.video_source = CustomVideoSource
    source = source_registry.create_source(video_file)

    assert isinstance(source, CustomVideoSource)


def test_registry_validates_source_class_type():
    """Verifica se TypeError é levantado ao tentar registrar classe que não herda de IFrameSource."""
    class InvalidSource:
        pass

    with pytest.raises(TypeError):
        source_registry.video_source = InvalidSource

    with pytest.raises(TypeError):
        source_registry.image_source = InvalidSource


def test_registry_context_manager_use(tmp_path):
    """Verifica se o context manager use altera temporariamente o backend e restaura o original."""
    video_file = tmp_path / "clip.mp4"
    video_file.touch()

    class TempSource(IFrameSource):
        def __init__(self, path, **kwargs):
            self.path = path

        @property
        def frame_count(self) -> int:
            return 10

        def seek(self, frame_id: int) -> None:
            pass

        def read(self):
            return True, None

        def grab(self) -> bool:
            return True

        def is_opened(self) -> bool:
            return True

        def release(self) -> None:
            pass

    original_video_source = source_registry.video_source
    with source_registry.use(video=TempSource):
        assert source_registry.video_source is TempSource
        source = source_registry.create_source(video_file)
        assert isinstance(source, TempSource)

    assert source_registry.video_source is original_video_source
