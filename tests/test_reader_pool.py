import pytest

from aniseek import ReaderPool
from aniseek.core.frame_mapper import FrameMapper
from aniseek.core.reader_pool import FrameSync
from aniseek.core.sources.opencv import OpenCVVideoSource
from aniseek.core.video_reader import (
    Direction,
    ForwardReader,
    ReverseReader,
    VideoReader,
)
from tests.uteis import MyVideoCapture


@pytest.fixture
def mock_video_capture():
    return MyVideoCapture()


@pytest.fixture
def synthetic_cap(tmp_path, monkeypatch, mock_video_capture):
    dummy_video = tmp_path / "video.mp4"
    dummy_video.touch()
    monkeypatch.setattr(
        "aniseek.core.sources.opencv.cv2.VideoCapture",
        lambda _: mock_video_capture,
    )
    return OpenCVVideoSource(dummy_video)


@pytest.mark.parametrize(
    ("reader_cls", "kwargs", "expected_reverse"),
    [
        (ForwardReader, {}, False),
        (ReverseReader, {}, True),
        (VideoReader, {"direction": Direction.FORWARD}, False),
        (VideoReader, {"direction": Direction.REVERSE}, True),
    ],
    ids=["forward", "reverse", "video_forward", "video_reverse"],
)
def test_reader_is_reverse_contract(synthetic_cap, reader_cls, kwargs, expected_reverse):
    """Valida a propriedade is_reverse no contrato de todos os leitores."""
    with reader_cls(synthetic_cap, start=0, end=5, lazy=True, **kwargs) as reader:
        result = reader.is_reverse

    assert result == expected_reverse


def test_reader_contains_operator(synthetic_cap):
    """Verifica se o operador in identifica frames carregados no buffer do leitor."""
    with ForwardReader(synthetic_cap, start=0, end=10, buffersize=5, lazy=True) as reader:
        before_start = 0 in reader
        reader.read()
        in_buffer = 1 in reader
        out_of_range = 99 in reader

    assert before_start is False
    assert in_buffer is True
    assert out_of_range is False


def test_frame_sync_direction_swapping():
    """Valida empilhamento e inversao de sentido entre proceed e rewind no FrameSync."""
    mapper = FrameMapper([0, 1, 2, 3, 4], 10)
    sync = FrameSync(mapper)

    f1 = sync.get()
    f2 = sync.get()
    sync.rewind()
    f3 = sync.get()
    sync.proceed()
    f4 = sync.get()

    assert [f1, f2, f3, f4] == [0, 1, 1, 1]


def test_frame_sync_set_partitions_stacks():
    """Verifica se o metodo set reparte corretamente os frames entre as pilhas direita e esquerda."""
    mapper = FrameMapper([3, 8, 15, 29], 50)
    sync = FrameSync(mapper)

    sync.set(15)
    fwd_id = sync.get()
    sync.set(15)
    sync.rewind()
    rev_id = sync.get()

    assert fwd_id == 15
    assert rev_id == 8


def test_reader_pool_cache_hit_avoids_buffer_decoding(synthetic_cap):
    """Consome frames do cache de outro reader no pool sem iniciar decodificacao no segundo reader."""
    pool = ReaderPool(maxsize=50)
    r1 = pool.get_reader(ForwardReader, synthetic_cap, start=0, end=5)
    r2 = pool.get_reader(ForwardReader, synthetic_cap, start=0, end=5)

    frames_r1 = [r1.frame_id for _, _ in r1]
    frames_r2 = [r2.frame_id for _, _ in r2]
    r2_buffer_len = len(r2._reader.buffer)
    pool.close()

    assert frames_r1 == [0, 1, 2, 3, 4]
    assert frames_r2 == [0, 1, 2, 3, 4]
    assert r2_buffer_len == 0


def test_reader_pool_cache_miss_after_hit_syncs_seamlessly(synthetic_cap):
    """Sincroniza o reader real automaticamente quando ocorre cache miss apos leituras em cache."""
    pool = ReaderPool(maxsize=50)
    r1 = pool.get_reader(ForwardReader, synthetic_cap, start=0, end=5)
    r2 = pool.get_reader(ForwardReader, synthetic_cap, start=3, end=8)

    _ = list(r1)
    frames_r2 = [r2.frame_id for _, _ in r2]
    pool.close()

    assert frames_r2 == [3, 4, 5, 6, 7]


def test_reader_pool_proxy_set_frame_and_direction_swap(synthetic_cap):
    """Valida set_frame, rewind e proceed atraves do ReaderProxy no ReaderPool."""
    pool = ReaderPool(maxsize=50)
    proxy = pool.get_reader(VideoReader, synthetic_cap, start=0, end=20)

    proxy.set_frame(10)
    proxy.read()
    f1 = proxy.frame_id
    proxy.read()
    f2 = proxy.frame_id
    proxy.rewind()
    proxy.read()
    f3 = proxy.frame_id
    proxy.proceed()
    proxy.read()
    f4 = proxy.frame_id
    pool.close()

    assert [f1, f2, f3, f4] == [10, 11, 11, 11]


def test_reader_pool_maxsize_eviction(synthetic_cap):
    """Descarta os frames mais antigos do cache quando o limite maxsize for atingido."""
    pool = ReaderPool(maxsize=3)
    proxy = pool.get_reader(ForwardReader, synthetic_cap, start=0, end=5)

    _ = list(proxy)
    hit_0, _ = pool.read(0)
    hit_1, _ = pool.read(1)
    hit_2, _ = pool.read(2)
    hit_4, _ = pool.read(4)
    pool.close()

    assert hit_0 is False
    assert hit_1 is False
    assert hit_2 is True
    assert hit_4 is True


def test_reader_pool_clear_and_close(synthetic_cap):
    """Verifica se clear esvazia os caches e close encerra todos os leitores registrados."""
    pool = ReaderPool(maxsize=20)
    proxy = pool.get_reader(ForwardReader, synthetic_cap, start=0, end=5)

    proxy.read()
    hit_before_clear, _ = pool.read(0)
    pool.clear()
    hit_after_clear, _ = pool.read(0)
    pool.close()

    assert hit_before_clear is True
    assert hit_after_clear is False
    assert len(pool._cache) == 0
