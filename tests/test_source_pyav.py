from __future__ import annotations

from pathlib import Path

import av
import numpy as np
import pytest

from aniseek.core.sources.pyav import PyAVBuffer, PyAVVideoSource
from aniseek.core.sources.registry import source_registry
from aniseek.core.video_reader import Direction, VideoReader


@pytest.fixture
def synthetic_video_path(tmp_path: Path) -> Path:
    video_file = tmp_path / "synthetic_test.mp4"
    container = av.open(str(video_file), mode="w")
    stream = container.add_stream("libx264", rate=24)
    stream.width = 64
    stream.height = 48
    stream.pix_fmt = "yuv420p"
    stream.options = {"g": "5"}

    for i in range(20):
        img = np.full((48, 64, 3), i * 10, dtype=np.uint8)
        frame = av.VideoFrame.from_ndarray(img, format="bgr24")
        for packet in stream.encode(frame):
            container.mux(packet)
    for packet in stream.encode():
        container.mux(packet)
    container.close()
    return video_file


def test_pyav_source_raises_on_missing_file(tmp_path: Path):
    """Verifica se RuntimeError e levantado quando o arquivo de video nao existe."""
    missing_file = tmp_path / "non_existent.mp4"

    with pytest.raises(RuntimeError):
        PyAVVideoSource(missing_file)


def test_pyav_source_raises_when_path_is_a_directory(tmp_path: Path):
    """Verifica se RuntimeError e levantado quando o caminho fornecido e um diretorio."""
    dummy_dir = tmp_path / "folder"
    dummy_dir.mkdir()

    with pytest.raises(RuntimeError):
        PyAVVideoSource(dummy_dir)


def test_pyav_source_reads_and_seeks(synthetic_video_path: Path):
    """Valida leitura sequencial, seek arbitrario e propriedades basicas de frames."""
    source = PyAVVideoSource(synthetic_video_path)

    assert source.frame_count == 20
    assert abs(source.fps - 24.0) < 0.1
    assert source.is_opened() is True

    ret, frame = source.read()
    assert ret is True
    assert frame is not None
    assert frame.shape == (48, 64, 3)
    assert frame.dtype == np.uint8

    source.seek(10)
    ret_seek, frame_seek = source.read()
    assert ret_seek is True
    assert frame_seek is not None

    grab_ok = source.grab()
    assert grab_ok is True

    source.release()
    assert source.is_opened() is False


def test_pyav_source_context_manager(synthetic_video_path: Path):
    """Valida liberacao de recursos ao utilizar o context manager."""
    with PyAVVideoSource(synthetic_video_path) as source:
        is_opened_inside = source.is_opened()

    assert is_opened_inside is True
    assert source.is_opened() is False


def test_pyav_source_validate_frame_count(synthetic_video_path: Path):
    """Valida deteccao e ajuste do total de frames decodificaveis via validate_frame_count."""
    with PyAVVideoSource(synthetic_video_path) as source:
        valid_count = source.validate_frame_count()

    assert valid_count == 20


def test_pyav_source_integration_with_video_reader(synthetic_video_path: Path):
    """Valida integracao cooperativa bidirecional entre PyAVVideoSource e VideoReader."""
    source = PyAVVideoSource(synthetic_video_path)
    with VideoReader(source, start=0, end=10, direction=Direction.FORWARD, buffersize=5) as reader:
        first_ret, first_frame = reader.read()
        reader.rewind()
        rev_ret, rev_frame = reader.read()

    assert first_ret is True
    assert first_frame is not None
    assert rev_ret is True
    assert rev_frame is not None


def test_pyav_source_registry_override(synthetic_video_path: Path):
    """Valida sobreposicao de backend de video usando SourceRegistry."""
    with source_registry.use(video=PyAVVideoSource):
        source = source_registry.create_source(synthetic_video_path)
        ret, frame = source.read()
        source.release()

    assert isinstance(source, PyAVVideoSource)
    assert ret is True
    assert frame is not None


def test_pyav_buffer_caching_and_eviction(synthetic_video_path: Path):
    """Valida retencao de frames intermediarios e politica de descarte por max_size."""
    container = av.open(str(synthetic_video_path))
    stream = container.streams.video[0]
    buffer = PyAVBuffer(container, stream, fps=24.0, max_size=5)

    buffer.seek(4)
    frame4 = buffer.decode(4)

    assert frame4 is not None
    assert len(buffer.cache) <= 5
    assert buffer.probe(2) is True

    cached_frame2 = buffer.decode(2)
    assert cached_frame2 is not None

    buffer.release()
    container.close()


AV1_SAMPLE_PATH = Path(
    "/mnt/Dados/Downloads/Animes/2026/1-winter-2026/Osananajimi to wa Love Comedy ni Naranai 04.mkv"
)


@pytest.mark.skipif(not AV1_SAMPLE_PATH.exists(), reason="Arquivo AV1 nao encontrado no disco")
def test_pyav_source_av1_file_if_available():
    """Valida decodificacao real e resolucao da cauda de arquivo AV1 10-bit."""
    with PyAVVideoSource(AV1_SAMPLE_PATH) as source:
        assert source.frame_count == 34296
        true_count = source.validate_frame_count()
        assert true_count == 34287
        source.seek(34286)
        ret, frame = source.read()

    assert ret is True
    assert frame is not None
    assert frame.shape == (1080, 1920, 3)
    assert frame.dtype == np.uint8
