from __future__ import annotations

from pathlib import Path

import av
import numpy as np
import pytest

from aniseek.core.sources.pyav import PyAVBuffer, PyAVFormat, PyAVVideoSource
from aniseek.core.sources.registry import source_registry
from aniseek.core.video_reader import Direction, VideoReader


def test_pyav_format_properties():
    """Valida propriedades semanticas de canais e canal alfa no PyAVFormat."""
    assert PyAVFormat.BGR.channels == 3
    assert PyAVFormat.RGB.channels == 3
    assert PyAVFormat.GRAY.channels == 1
    assert PyAVFormat.BGRA.channels == 4
    assert PyAVFormat.RGBA.channels == 4

    assert PyAVFormat.BGR.has_alpha is False
    assert PyAVFormat.GRAY.has_alpha is False
    assert PyAVFormat.BGRA.has_alpha is True
    assert PyAVFormat.RGBA.has_alpha is True


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
    assert source.size == (64, 48)
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


@pytest.mark.parametrize(
    ("fmt", "dtype", "expected_shape", "expected_dtype"),
    [
        (PyAVFormat.BGR, np.uint8, (48, 64, 3), np.uint8),
        (PyAVFormat.RGB, np.uint8, (48, 64, 3), np.uint8),
        (PyAVFormat.GRAY, np.uint8, (48, 64), np.uint8),
        (PyAVFormat.BGR, np.uint16, (48, 64, 3), np.uint16),
        (PyAVFormat.RGB, np.uint16, (48, 64, 3), np.uint16),
        (PyAVFormat.GRAY, np.uint16, (48, 64), np.uint16),
        ("bgr24", np.uint8, (48, 64, 3), np.uint8),
    ],
    ids=[
        "bgr_uint8",
        "rgb_uint8",
        "gray_uint8",
        "bgr_uint16",
        "rgb_uint16",
        "gray_uint16",
        "raw_string_bgr24",
    ],
)
def test_pyav_source_formats(
    synthetic_video_path: Path,
    fmt: PyAVFormat | str,
    dtype: type,
    expected_shape: tuple[int, ...],
    expected_dtype: type,
):
    """Valida decodificacao nos formatos BGR, RGB e GRAY com diferentes dtypes."""
    with PyAVVideoSource(synthetic_video_path, format=fmt, dtype=dtype) as source:
        ret, frame = source.read()

    assert ret is True
    assert frame is not None
    assert frame.shape == expected_shape
    assert frame.dtype == expected_dtype


def test_pyav_source_readonly_mode(synthetic_video_path: Path):
    """Valida protecao de memoria com array somente-leitura quando readonly=True."""
    with PyAVVideoSource(synthetic_video_path, readonly=True) as source:
        ret, frame = source.read()

    assert ret is True
    assert frame is not None
    assert frame.flags.writeable is False


def test_pyav_source_thread_options(synthetic_video_path: Path):
    """Valida inicializacao com opcoes explicitas de thread no codec."""
    with PyAVVideoSource(synthetic_video_path, thread_type="FRAME", thread_count=2) as source:
        ret, frame = source.read()

    assert ret is True
    assert frame is not None


def test_pyav_source_target_size_and_interpolation(synthetic_video_path: Path):
    """Valida redimensionamento de frames diretamente na decodificacao com target_size."""
    target_size = (32, 24)
    with PyAVVideoSource(synthetic_video_path, target_size=target_size, interpolation="FAST_BILINEAR") as source:
        assert source.size == (32, 24)
        ret, frame = source.read()

    assert ret is True
    assert frame is not None
    assert frame.shape == (24, 32, 3)


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
