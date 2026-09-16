from pytest import fixture
from aniseek.buffer import BufferRight
from threading import Semaphore
import numpy as np


@fixture
def buffer():
    semaphore = Semaphore()
    bf = BufferRight(semaphore, maxsize=25)
    yield bf


def lote(start, end, step):
    return [(frame_id, np.ones((2, 2))) for frame_id in range(start, end, step)]


def test_buffer_right_unqueue_de_1_elemento(buffer):
    expect = False
    [buffer.sput(frame) for frame in lote(0, 1, 1)]
    buffer.unqueue()
    result = buffer.empty()
    assert result == expect


def test_buffer_right_unqueue_da_queue_full(buffer):
    expect = True
    [buffer.sput(frame) for frame in lote(0, 25, 1)]
    buffer.unqueue()
    result = buffer.full()
    assert result == expect


def test_buffer_right_put_1_elemento(buffer):
    expect = 24
    [buffer.sput(frame) for frame in lote(25, 50, 1)]
    buffer.unqueue()
    [buffer.put(frame) for frame in lote(24, 25, 1)]
    result = buffer.get()[0]
    assert result == expect


def test_buffer_right_enchendo_o_buffer_secondary_2_vezes_e_colocando_1_elemento_com_put(buffer):
    expect_block = False
    expect_secondary_empty = True
    expect_frame_id = 24
    [buffer.sput(frame) for frame in lote(25, 50, 1)]
    buffer.unqueue()
    [buffer.sput(frame) for frame in lote(50, 75, 1)]
    [buffer.put(frame) for frame in lote(24, 25, 1)]
    result_block = buffer.no_block_task()
    result_secondary_empty = buffer.secondary_empty()
    result_frame_id = buffer.get()[0]
    assert result_block == expect_block
    assert result_secondary_empty == expect_secondary_empty
    assert result_frame_id == expect_frame_id
