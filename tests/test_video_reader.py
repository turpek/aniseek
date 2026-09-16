from __future__ import annotations

import pytest

from aniseek.video_reader import ForwardReader, ReverseReader, VideoReader
from tests.uteis import MyVideoCapture


@pytest.fixture
def synthetic_cap():
    return MyVideoCapture()


@pytest.mark.parametrize(
    ("start", "end", "step", "expected_ids"),
    [
        (0, 10, 1, list(range(0, 10, 1))),
        (10, 30, 2, list(range(10, 30, 2))),
        (0, 5, 1, list(range(0, 5, 1))),
    ],
    ids=["slice_0_10_step1", "slice_10_30_step2", "slice_0_5_step1"],
)
def test_forward_reader_slice(synthetic_cap, start, end, step, expected_ids):
    """Valida leitura direta fatiada com diferentes parâmetros de start, end e step."""
    reader = ForwardReader(
        synthetic_cap,
        start=start,
        end=end,
        step=step,
        buffersize=5,
    )

    result_ids = [reader.frame_id for _, _ in reader]
    reader.close()

    assert result_ids == expected_ids


def test_forward_reader_explicit_frames(synthetic_cap):
    """Valida leitura direta informando lista explícita de frames arbitrários."""
    target_frames = [2, 5, 11, 24, 37]
    reader = ForwardReader(
        synthetic_cap,
        frames=target_frames,
        buffersize=5,
    )

    result_ids = [reader.frame_id for _, _ in reader]
    reader.close()

    assert result_ids == target_frames


def test_forward_reader_is_task_complete_on_finish(synthetic_cap):
    """Verifica se a propriedade is_task_complete retorna True após consumir todos os frames."""
    reader = ForwardReader(
        synthetic_cap,
        start=0,
        end=4,
        step=1,
        buffersize=5,
    )

    _ = list(reader)
    is_complete = reader.is_task_complete
    extra_read_status, extra_frame = reader.read()
    reader.close()

    assert is_complete is True
    assert extra_read_status is False
    assert extra_frame is None


def test_forward_reader_empty_slice(synthetic_cap):
    """Verifica comportamento do leitor direto com intervalo vazio."""
    reader = ForwardReader(
        synthetic_cap,
        start=10,
        end=10,
        buffersize=5,
    )

    is_complete = reader.is_task_complete
    ret, frame = reader.read()
    reader.close()

    assert is_complete is True
    assert ret is False
    assert frame is None


@pytest.mark.parametrize(
    ("start", "end", "step", "expected_ids"),
    [
        (0, 10, 1, list(reversed(range(0, 10, 1)))),
        (10, 30, 2, list(reversed(range(10, 30, 2)))),
        (0, 5, 1, list(reversed(range(0, 5, 1)))),
    ],
    ids=["reverse_0_10_step1", "reverse_10_30_step2", "reverse_0_5_step1"],
)
def test_reverse_reader_slice(synthetic_cap, start, end, step, expected_ids):
    """Valida leitura reversa fatiada em ordem decrescente."""
    reader = ReverseReader(
        synthetic_cap,
        start=start,
        end=end,
        step=step,
        buffersize=5,
    )

    result_ids = [reader.frame_id for _, _ in reader]
    reader.close()

    assert result_ids == expected_ids


def test_reverse_reader_explicit_frames(synthetic_cap):
    """Valida leitura reversa com lista explícita de frames em ordem decrescente."""
    target_frames = [3, 8, 15, 29]
    reader = ReverseReader(
        synthetic_cap,
        frames=target_frames,
        buffersize=5,
    )

    result_ids = [reader.frame_id for _, _ in reader]
    reader.close()

    assert result_ids == list(reversed(target_frames))


def test_reverse_reader_is_task_complete_on_finish(synthetic_cap):
    """Verifica se is_task_complete retorna True após término da leitura reversa."""
    reader = ReverseReader(
        synthetic_cap,
        start=0,
        end=4,
        step=1,
        buffersize=5,
    )

    _ = list(reader)
    is_complete = reader.is_task_complete
    extra_read_status, extra_frame = reader.read()
    reader.close()

    assert is_complete is True
    assert extra_read_status is False
    assert extra_frame is None


def test_video_reader_initial_forward(synthetic_cap):
    """Valida VideoReader inicializado com avanço padrão."""
    with VideoReader(synthetic_cap, start=0, end=5, buffersize=5) as reader:
        result_ids = [reader.frame_id for _, _ in reader]

    assert result_ids == [0, 1, 2, 3, 4]


def test_video_reader_initial_reverse(synthetic_cap):
    """Valida VideoReader inicializado em modo reverso."""
    with VideoReader(
        synthetic_cap,
        start=0,
        end=5,
        direction="reverse",
        buffersize=5,
    ) as reader:
        result_ids = [reader.frame_id for _, _ in reader]

    assert result_ids == [4, 3, 2, 1, 0]


def test_video_reader_direction_swapping(synthetic_cap):
    """Valida troca dinâmica de direção entre proceed e rewind."""
    with VideoReader(synthetic_cap, start=0, end=10, buffersize=5) as reader:
        ret_1, _ = reader.read()
        f1 = reader.frame_id
        ret_2, _ = reader.read()
        f2 = reader.frame_id

        reader.rewind()
        is_rev = reader.is_reverse
        ret_3, _ = reader.read()
        f3 = reader.frame_id

        reader.proceed()
        is_fwd = reader.is_forward
        ret_4, _ = reader.read()
        f4 = reader.frame_id

    assert f1 == 0
    assert f2 == 1
    assert is_rev is True
    assert f3 == 1
    assert is_fwd is True
    assert f4 == 1


def test_forward_reader_continues_on_none_frame(synthetic_cap):
    """Verifica se o iterador continua até o término da tarefa mesmo quando um frame falha."""
    synthetic_cap.frames[2] = None

    with ForwardReader(synthetic_cap, start=0, end=5, buffersize=5) as reader:
        results = [(ret, f is not None, reader.frame_id) for ret, f in reader]
        is_complete = reader.is_task_complete

    expected = [
        (True, True, 0),
        (True, True, 1),
        (False, False, 2),
        (True, True, 3),
        (True, True, 4),
    ]
    assert results == expected
    assert is_complete is True
