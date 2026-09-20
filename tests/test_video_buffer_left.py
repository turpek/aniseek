from threading import Semaphore
from time import sleep
from unittest.mock import patch

import cv2
import numpy as np
import pytest
from pytest import fixture, raises

from aniseek.core.buffer_left import VideoBufferLeft
from aniseek.core.frame_mapper import FrameMapper
from aniseek.custom_exceptions import VideoBufferError


def lote(start, end, step=1):
    return [(frame_id, np.ones((2, 2))) for frame_id in range(start, end, step)]


from tests.my_mocks import MyVideoCapture


@fixture
def mycap():
    with patch('cv2.VideoCapture', return_value=MyVideoCapture()) as mock:
        yield mock


@fixture
def myvideo(mycap, request):
    lote, buffersize = request.param
    cap = mycap.return_value
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    mapping = FrameMapper(lote, frame_count)
    semaphore = Semaphore()
    buffer = VideoBufferLeft(cap, mapping, semaphore, bufferlog=False, buffersize=buffersize)
    yield buffer

    buffer.join()


@fixture
def myvideo_mapping(mycap, request):
    lote, buffersize = request.param
    cap = mycap.return_value
    semaphore = Semaphore()
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    mapping = FrameMapper(lote, frame_count)
    buffer = VideoBufferLeft(cap, mapping, semaphore, buffersize=buffersize)
    yield (buffer, mapping)

    buffer.join()


# ################### Testes para o VideoBufferLeft sem Frames ##################################333

@pytest.mark.parametrize('myvideo', [([], 5)], indirect=True)
def test_buffer_VideoBufferLeft_is_task_complete(myvideo):
    expect = True
    result = myvideo.is_task_complete()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([], 5)], indirect=True)
def test_buffer_VideoBufferLeft_start_frame_sem_frames(myvideo):
    expect = None
    result = myvideo.start_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([], 5)], indirect=True)
def test_buffer_VideoBufferLeft_end_frame_sem_frames(myvideo):
    expect = None
    result = myvideo.end_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([], 5)], indirect=True)
def test_buffer_VideoBufferLeft__calc_frame_sem_frames(myvideo):
    expect = None
    result = myvideo._VideoBufferLeft__calc_frame(5)
    assert result == expect


@pytest.mark.parametrize('myvideo', [([], 5)], indirect=True)
def test_buffer_VideoBufferLeft_get_com_o_buffer_vazio(myvideo):
    expect = 'get from an empty buffer'
    with raises(VideoBufferError) as excinfo:
        myvideo.get()
    result = f'{excinfo.value}'
    assert result == expect


@pytest.mark.parametrize('myvideo', [([], 5)], indirect=True)
def test_buffer_VideoBufferLeft_put_com_o_buffer_vazio(myvideo):
    frame_id = 5
    expect = f'frame_id "{frame_id}" does not belong to map'
    with raises(VideoBufferError) as excinfo:
        myvideo.put(frame_id, np.zeros((2, 2)))
    result = f'{excinfo.value}'
    assert result == expect


# ##################### Testes para  VideoBufferLeft com 1 Frame ###########################

@pytest.mark.parametrize('myvideo', [([0], 5)], indirect=True)
def test_buffer_VideoBufferLeft_is_task_complete_com_1_frame_sem_ler(myvideo):
    expect = True
    result = myvideo.is_task_complete()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0], 5)], indirect=True)
def test_buffer_VideoBufferLeft_is_task_complete_com_1_frame_com_leitura(myvideo):
    # O VideoBufferLeft` foi construído de forma a não conseguir ler midias que tenham
    # somente 1 frame

    expect = "get from an empty buffer"
    with raises(VideoBufferError) as excinfo:
        myvideo.get()
    result = f'{excinfo.value}'
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0], 5)], indirect=True)
def test_buffer_VideoBufferLeft_start_frame_com_1_frame(myvideo):
    expect = 0
    result = myvideo.start_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0], 5)], indirect=True)
def test_buffer_VideoBufferLeft_end_frame_com_1_frame(myvideo):
    expect = 0
    result = myvideo.end_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0], 5)], indirect=True)
def test_buffer_VideoBufferLeft__calc_frame_com_1_frame(myvideo):
    expect = 0
    result = myvideo._VideoBufferLeft__calc_frame(0)
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0], 5)], indirect=True)
def test_buffer_VideoBufferLeft_get_com_1_frame(myvideo):
    expect = "get from an empty buffer"
    with raises(VideoBufferError) as excinfo:
        myvideo.get()
    result = f'{excinfo.value}'
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1], 5)], indirect=True)
def test_buffer_VideoBufferLeft_put_com_1_frame(myvideo):
    expect = 1
    myvideo.put(1, np.zeros((2, 2)))
    myvideo.get()
    result = myvideo.frame_id
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1], 5)], indirect=True)
def test_buffer_VideoBufferLeft_put_com_1_frame_e_lendo_tudo(myvideo):
    expect = True
    myvideo.put(1, np.zeros((2, 2)))
    [myvideo.get() for _ in range(2)]
    result = myvideo.is_task_complete()
    assert result == expect


# ##################### Testes para  VideoBufferLeft com 2 Frame ###########################

@pytest.mark.parametrize('myvideo', [([0, 1], 5)], indirect=True)
def test_buffer_VideoBufferLeft_is_task_complete_com_2_frame_sem_ler(myvideo):
    expect = True
    result = myvideo.is_task_complete()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1], 5)], indirect=True)
def test_buffer_VideoBufferLeft_is_task_complete_com_2_frame_com_leitura_sem_set(myvideo):
    expect = "get from an empty buffer"
    with raises(VideoBufferError) as excinfo:
        myvideo.get()
    result = f'{excinfo.value}'
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1], 5)], indirect=True)
def test_buffer_VideoBufferLeft_is_task_complete_com_2_frame_com_leitura_com_set(myvideo):
    expect = True
    expect_frame_id = 0
    myvideo.set(1)
    myvideo.get()
    result = myvideo.is_task_complete()
    result_frame_id = myvideo.frame_id
    assert result == expect
    assert result_frame_id == expect_frame_id


@pytest.mark.parametrize('myvideo', [([0, 1], 5)], indirect=True)
def test_buffer_VideoBufferLeft_is_task_complete_com_2_frame_com_leitura_com_set_no_primeiro_frame(myvideo):
    expect = True
    expect_frame_id = 0
    myvideo.set(0)
    result = myvideo.is_task_complete()
    result_frame_id = myvideo.frame_id
    assert result == expect
    assert result_frame_id == expect_frame_id


@pytest.mark.parametrize('myvideo', [([0, 1], 5)], indirect=True)
def test_buffer_VideoBufferLeft_start_frame_com_2_frame_sem_set(myvideo):
    expect = 0
    result = myvideo.start_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1], 5)], indirect=True)
def test_buffer_VideoBufferLeft_start_frame_com_2_frame_com_set(myvideo):
    expect = 0
    myvideo.set(1)
    result = myvideo.start_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1], 5)], indirect=True)
def test_buffer_VideoBufferLeft_end_frame_com_2_frame_sem_set(myvideo):
    expect = 0
    result = myvideo.end_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1], 5)], indirect=True)
def test_buffer_VideoBufferLeft_end_frame_com_2_frame_com_set(myvideo):
    expect = 0

    # Esse teste cai no caso especial descrito no metodo __calc_frame
    myvideo.set(1)
    result = myvideo.end_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1], 5)], indirect=True)
def test_buffer_VideoBufferLeft__calc_frame_com_2_frame(myvideo):
    expect = 0
    result = myvideo._VideoBufferLeft__calc_frame(0)
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1], 5)], indirect=True)
@pytest.mark.skip(reason="pq sim")
def test_buffer_VideoBufferLeft__calc_frame_com_2_frame_com_get_com_set(myvideo):
    expect = 0
    myvideo.set(1)
    myvideo.get()

    result = myvideo._VideoBufferLeft__calc_frame(1)
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1], 5)], indirect=True)
def test_buffer_VideoBufferLeft_get_com_2_frame_sem_set(myvideo):
    expect = "get from an empty buffer"
    with raises(VideoBufferError) as excinfo:
        myvideo.get()
    result = f'{excinfo.value}'
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1], 5)], indirect=True)
def test_buffer_VideoBufferLeft_get_com_2_frame_com_set(myvideo):
    expect = 0
    myvideo.set(1)
    myvideo.get()
    result = myvideo.frame_id
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1, 2], 5)], indirect=True)
def test_buffer_VideoBufferLeft_put_com_2_frame(myvideo):
    expect = 2

    myvideo.put(2, np.zeros((2, 2)))
    myvideo.get()
    result = myvideo.frame_id
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1, 2], 5)], indirect=True)
def test_buffer_VideoBufferLeft_put_com_2_frame_no_block_task(myvideo):
    expect_no_block_task_put = False
    expect_no_block_task_get = True

    myvideo.put(2, np.zeros((2, 2)))
    result_no_block_task_put = myvideo._buffer.no_block_task()

    myvideo.get()
    result_no_block_task_get = myvideo._buffer.no_block_task()

    assert expect_no_block_task_put == result_no_block_task_put
    assert expect_no_block_task_get == result_no_block_task_get


@pytest.mark.parametrize('myvideo', [([0, 1], 5)], indirect=True)
def test_buffer_VideoBufferLeft_put_com_2_frame_com_set_no_block_task(myvideo):
    expect_no_block_task = True

    myvideo.put(0, np.zeros((2, 2)))
    myvideo.put(1, np.zeros((2, 2)))
    myvideo.set(1)
    result_no_block_task = myvideo._buffer.no_block_task()
    assert expect_no_block_task == result_no_block_task


# ##################### Testes para  VideoBufferLeft com 3 Frame ###########################

@pytest.mark.parametrize('myvideo', [([0, 1, 2], 5)], indirect=True)
def test_buffer_VideoBufferLeft_is_task_complete_com_3_frame_sem_ler(myvideo):
    expect = True
    result = myvideo.is_task_complete()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1, 2], 5)], indirect=True)
def test_buffer_VideoBufferLeft_is_task_complete_com_3_frame_com_leitura_com_set(myvideo):
    expect = False
    myvideo.set(3)
    myvideo.get()
    result = myvideo.is_task_complete()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1, 2], 5)], indirect=True)
def test_buffer_VideoBufferLeft_is_task_complete_com_3_frame_com_3_leitura_com_set(myvideo):
    expect = True
    myvideo.set(3)
    [myvideo.get() for _ in range(3)]
    result = myvideo.is_task_complete()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1, 2], 5)], indirect=True)
def test_buffer_VideoBufferLeft_start_frame_com_3_frame_sem_set(myvideo):
    expect = 0
    result = myvideo.start_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1, 2], 5)], indirect=True)
def test_buffer_VideoBufferLeft_start_frame_com_3_frame_com_set(myvideo):
    expect = 0
    myvideo.set(3)
    result = myvideo.start_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1, 2], 5)], indirect=True)
def test_buffer_VideoBufferLeft_end_frame_com_3_frame_sem_set(myvideo):
    expect = 0
    result = myvideo.end_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1, 2], 5)], indirect=True)
def test_buffer_VideoBufferLeft_end_frame_com_3_frame_com_set(myvideo):
    expect = 2
    myvideo.set(3)
    result = myvideo.end_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1, 2], 5)], indirect=True)
def test_buffer_VideoBufferLeft__calc_frame_com_3_frame_sem_set(myvideo):
    expect = 0
    result = myvideo._VideoBufferLeft__calc_frame(0)
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1, 2], 5)], indirect=True)
def test_buffer_VideoBufferLeft__calc_frame_com_3_frame_com_set(myvideo):
    expect = 0
    myvideo.set(3)
    result = myvideo._VideoBufferLeft__calc_frame(0)
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1, 2], 5)], indirect=True)
def test_buffer_VideoBufferLeft__calc_frame_com_3_frame_com_get_sem_set(myvideo):
    expect = "get from an empty buffer"
    with raises(VideoBufferError) as excinfo:
        myvideo.get()
    result = f'{excinfo.value}'
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1, 2], 5)], indirect=True)
def test_buffer_VideoBufferLeft_get_com_3_frame_sem_set(myvideo):
    expect = "get from an empty buffer"
    with raises(VideoBufferError) as excinfo:
        myvideo.get()
    result = f'{excinfo.value}'
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1, 2], 5)], indirect=True)
def test_buffer_VideoBufferLeft_get_com_3_frame_com_set(myvideo):
    expect = 2
    myvideo.set(3)
    myvideo.get()
    result = myvideo.frame_id
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1, 2], 5)], indirect=True)
def test_buffer_VideoBufferLeft_get_com_3_frame_e_3_get_com_set(myvideo):
    expect = True
    myvideo.set(3)
    [myvideo.get() for _ in range(3)]
    result = myvideo.is_task_complete()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1, 2, 3], 5)], indirect=True)
@pytest.mark.skip(reason="pq sim")
def test_buffer_VideoBufferLeft_put_com_3_frame(myvideo):
    expect = 3
    myvideo.put(3, np.zeros((2, 2)))
    myvideo.get()
    result = myvideo.frame_id
    assert result == expect


# ##################### Testes diversos  ###########################

@pytest.mark.parametrize('myvideo', [(list(range(200)), 5)], indirect=True)
def test_buffer_VideoBufferLeft_start_frame_0(myvideo):
    expect = 0
    result = myvideo.start_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(15, 20)), 5)], indirect=True)
def test_buffer_VideoBufferLeft_start_frame_15(myvideo):
    expect = 15
    result = myvideo.start_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(200)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_start_frame_set_sequencia_linear(myvideo):
    expect = 50
    myvideo.set(75)
    result = myvideo.start_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(0, 200, 7)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_start_frame_set_sequencia_nao_linear(myvideo):
    expect = 21
    myvideo.set(195)
    result = myvideo.start_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(200)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_start_frame_buffer_vazio(myvideo):
    expect = 0
    result = myvideo.start_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(200)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_start_frame_buffer_nao_vazio(myvideo):
    expect = 5
    [myvideo._buffer.put(frame) for frame in lote(30, 55, 1)]
    result = myvideo.start_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(0, 500, 7)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_start_frame_buffer_nao_vazio_e_nao_linear(myvideo):
    expect = 35
    [myvideo._buffer.put(frame) for frame in lote(210, 383, 7)]
    result = myvideo.start_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(5, 500, 7)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_start_frame_buffer_vazio_e__frame_id_igual_None(myvideo):
    expect = 5
    myvideo._VideoBufferLeft__frame_id = None
    result = myvideo.start_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo_mapping', [(list(range(20)), 5)], indirect=True)
def test_buffer_VideoBufferLeft_sequence_linear(myvideo_mapping):
    myvvideo, mapping = myvideo_mapping
    lote = list(range(0, 20))
    expect = {key for key in lote}
    result = mapping.get_mapping()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(150)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_metodo_set_frame(myvideo):
    expect_start_frame = 0
    myvideo.set(25)
    result_start_frame = myvideo.start_frame()
    assert result_start_frame == expect_start_frame


@pytest.mark.parametrize('myvideo', [(list(range(200)), 5)], indirect=True)
def test_buffer_VideoBufferLeft_end_frame_com_buffer_vazio_0(myvideo):
    expect = 0
    result = myvideo.end_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(15, 200)), 5)], indirect=True)
def test_buffer_VideoBufferLeft_end_frame_com_buffer_vazio_15(myvideo):
    # CASO ESPECIAL
    expect = 15
    result = myvideo.end_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(15, 200)), 5)], indirect=True)
def test_buffer_VideoBufferLeft_end_frame_com_set_25(myvideo):
    # o valor setado para VideoBuffeLeft é aberto para end_frame!
    expect = 24
    myvideo.set(25)
    result = myvideo.end_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(200)), 5)], indirect=True)
def test_buffer_VideoBufferLeft_end_frame_com_set_0(myvideo):
    expect = 0
    myvideo.set(0)
    result = myvideo.end_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(200)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_end_frame_com_buffer_nao_vazio(myvideo):
    expect = 29
    [myvideo._buffer.put(frame) for frame in lote(30, 55, 1)]
    result = myvideo.end_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(200)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_end_frame_com_end_frame_0(myvideo):
    expect = 0
    [myvideo._buffer.put(frame) for frame in lote(0, 25, 1)]
    result = myvideo.end_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(0, 500, 7)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_end_frame_buffer_nao_vazio_e_nao_linear(myvideo):
    expect = 203
    [myvideo._buffer.put(frame) for frame in lote(210, 383, 7)]
    result = myvideo.end_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(0, 200, 7)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_metodo_set_frame_com_lote_nao_linear(myvideo):
    expect_start_frame = 21
    myvideo.set(195)
    result_start_frame = myvideo.start_frame()
    assert result_start_frame == expect_start_frame


@pytest.mark.parametrize('myvideo', [(list(range(0, 200, 7)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_metodo_set_frame_com_lote_nao_linear_penultimo_frame(myvideo):
    expect_start_frame = 21
    myvideo.set(195)
    result_start_frame = myvideo.start_frame()
    assert result_start_frame == expect_start_frame


@pytest.mark.parametrize('myvideo', [(list(range(0, 200, 1)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_metodo_set_frame_com_lote_linear_ultimo_frame(myvideo):
    expect_start_frame = 174
    myvideo.set(199)
    result_start_frame = myvideo.start_frame()
    assert result_start_frame == expect_start_frame


@pytest.mark.parametrize('myvideo', [(list(range(0, 200, 1)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_metodo_set_frame_com_lote_linear_penultimo_frame(myvideo):
    expect_start_frame = 173
    myvideo.set(198)
    result_start_frame = myvideo.start_frame()
    assert result_start_frame == expect_start_frame


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_enchendo_o_buffer_manualmente(myvideo):
    expect = 10
    [myvideo.put(*frame) for frame in lote(0, 10, 1)]
    result = len(myvideo)
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_is_done_eh_true_com_o_buffer_vazio(myvideo):
    expect = True
    result = myvideo.is_done()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_is_done_eh_false_com_o_buffer_cheio(myvideo):
    expect = False
    [myvideo._buffer.put(frame) for frame in lote(25, 50, 1)]
    result = myvideo.is_done()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_is_done_eh_true(myvideo):
    expect = True
    [myvideo._buffer.put(frame) for frame in lote(0, 25, 1)]
    result = myvideo.is_done()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_do_task_buffer_vazio_sem_set(myvideo):
    expect = False
    result = myvideo.do_task()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_do_task_buffer_vazio_set_0(myvideo):
    expect = False
    myvideo.set(0)
    result = myvideo.do_task()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_do_task_buffer_vazio_set_1(myvideo):
    expect = True
    myvideo.set(1)
    result = myvideo.do_task()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_do_task_buffer_vazio_com_set_50(myvideo):
    expect = True
    myvideo.set(50)
    result = myvideo.do_task()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_do_task_buffer_cheio(myvideo):
    expect = True
    [myvideo._buffer.sput(frame) for frame in lote(50, 75, 1)]
    myvideo._buffer.unqueue()
    result = myvideo.do_task()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_do_task_buffer_cheio_com_frame_id_no_final(myvideo):
    expect = False
    [myvideo._buffer.sput(frame) for frame in lote(0, 15, 1)]
    myvideo._buffer.unqueue()
    result = myvideo.do_task()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_do_task_colocando_dados_manualmente(myvideo):
    expect = False
    [myvideo.put(*frame) for frame in lote(5, 15, 1)]
    result = myvideo.do_task()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_do_task_com_set_0(myvideo):
    expect = False
    myvideo.set(0)
    result = myvideo.do_task()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_do_task_com_set_1(myvideo):
    expect = True
    myvideo.set(1)
    result = myvideo.do_task()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_do_task_com_set_33(myvideo):
    expect = True
    myvideo.set(33)
    result = myvideo.do_task()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_is_task_complete_sem_set(myvideo):
    expect = True
    result = myvideo.is_task_complete()
    assert result == expect


@pytest.mark.skip(reason='Verificar como a mudança do __frame_id no set influencia em is_task_complete')
@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_is_task_complete_set_0(myvideo):
    expect = True
    myvideo.set(0)
    result = myvideo.is_task_complete()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_is_task_complete_colocando_manualmente_de_30_55(myvideo):
    expect = False
    [myvideo._buffer.put(frame) for frame in lote(30, 55, 1)]
    myvideo.get()
    result = myvideo.is_task_complete()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_is_task_complete_colocando_manualmente_de_0_25_consumindo_tudo(myvideo):
    expect = True
    [myvideo._buffer.put(frame) for frame in lote(0, 25, 1)]
    [myvideo.get() for x in range(25)]
    result = myvideo.is_task_complete()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_run_sem_set_e_vazio(myvideo):
    expect = False
    myvideo.run()
    result = myvideo.do_task()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_run_set_50(myvideo):
    expect = False
    myvideo.set(50)
    myvideo.run()
    sleep(0.001)
    result = myvideo._buffer.secondary_empty()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_run_2vezes_set_50(myvideo):
    expect = False
    myvideo.set(50)
    myvideo.run()

    # run é chamado dentro de get
    myvideo.get()
    result = myvideo._buffer.secondary_empty()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_put_e_run(myvideo):
    expect = False
    [myvideo.put(*frame) for frame in lote(50, 75, 1)]
    myvideo.get()
    result = myvideo._buffer.secondary_empty()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_put_e_run_consumindo_tudo_com_get_checando_os_frames_id(myvideo):
    expect = list(range(74, -1, -1))
    [myvideo.put(*frame) for frame in lote(50, 75, 1)]
    result = [myvideo.get()[0] for _ in range(75)]
    assert result == expect


@pytest.mark.parametrize('myvideo_mapping', [(list(range(300)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_set_lot_com_mapping_do_tamanho_do_frame_count(myvideo_mapping):
    myvvideo, mapping = myvideo_mapping
    expect = set(range(300))
    result = mapping.get_mapping()
    assert result == expect


@pytest.mark.parametrize('myvideo_mapping', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_set_lot_com_mapping_menor_que_frame_count(myvideo_mapping):
    myvvideo, mapping = myvideo_mapping
    expect = set(range(100))
    result = mapping.get_mapping()
    assert result == expect


@pytest.mark.parametrize('myvideo_mapping', [(list(range(500)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_set_lot_com_mapping_maior_que_frame_count(myvideo_mapping):
    myvvideo, mapping = myvideo_mapping
    expect = set(range(300))
    result = mapping.get_mapping()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(300)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_colocando_manualmente_o_ultimo_frame(myvideo):
    expect_start_frame = 274
    [myvideo.put(*frame) for frame in lote(299, 300, 1)]
    result_start_frame = myvideo.start_frame()
    assert result_start_frame == expect_start_frame


@pytest.mark.parametrize('myvideo', [(list(range(300)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_colocando_manualmente_o_ultimo_frame_usando_get(myvideo):
    expect_start_frame = 274
    [myvideo.put(*frame) for frame in lote(299, 300, 1)]
    myvideo.get()
    result_start_frame = myvideo.start_frame()
    assert result_start_frame == expect_start_frame


@pytest.mark.parametrize('myvideo', [(list(range(300)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_getitem__com_buffer_vazio(myvideo):
    expect = None
    result = myvideo[0]
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(300)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_getitem__com_buffer_cheio_primeiro_frame_id(myvideo):
    expect = 299
    myvideo.set(300)
    myvideo.run()
    myvideo._buffer.unqueue()
    result = myvideo[0]
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(300)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_getitem__com_buffer_cheio_ultimo_frame_id(myvideo):
    expect = 299 - 24
    myvideo.set(300)
    myvideo.run()
    myvideo._buffer.unqueue()
    result = myvideo[-1]
    assert result == expect


# ##################### TESTANDO OS ERROS NO METODO PUT ########################## #

@pytest.mark.parametrize('myvideo', [(list(range(10, 35)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_colocando_um_frame_id_menor_que_o_ultimo_frame_id_do_buffer(myvideo):
    [myvideo.put(*frame) for frame in lote(10, 35, 1)]

    frame_id = 5
    expect = f'frame_id "{frame_id}" does not belong to map'
    with raises(VideoBufferError) as excinfo:
        myvideo.put(frame_id, np.zeros((2, 2)))
    assert excinfo.value.message == expect


@pytest.mark.parametrize('myvideo', [(list(range(10, 35)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_colocando_um_frame_id_que_ja_esta_presente_no_buffer(myvideo):
    [myvideo.put(*frame) for frame in lote(10, 35, 1)]

    frame_id = 28
    expect = f"Inconsistency in operation: 'frame_id' '{frame_id}' is less than the current frame."
    with raises(VideoBufferError) as excinfo:
        myvideo.put(frame_id, np.zeros((2, 2)))
    assert excinfo.value.message == expect


@pytest.mark.parametrize('myvideo', [(list(range(10, 35)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_colocando_um_frame_id_igual_ao_primeiro_frame_id_do_buffer(myvideo):
    [myvideo.put(*frame) for frame in lote(10, 35, 1)]

    frame_id = 34
    expect = f"The frame_id '{frame_id}' is already present in VideoBufferLeft."
    with raises(VideoBufferError) as excinfo:
        myvideo.put(frame_id, np.zeros((2, 2)))
    assert excinfo.value.message == expect


# ##################### TESTANDO OS ERROS NO METODO SET ########################## #

@pytest.mark.parametrize('myvideo', [(list(range(10, 35)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_setando_o_buffer_com_uma_string(myvideo):
    [myvideo.put(*frame) for frame in lote(10, 35, 1)]

    frame_id = '28'
    expect = 'frame_id must be an integer'
    with raises(TypeError) as excinfo:
        myvideo.set(frame_id)
    result = str(excinfo.value)
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(10, 35)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_setando_o_buffer_com_frame_id_menor_que_zero(myvideo):
    [myvideo.put(*frame) for frame in lote(10, 35, 1)]

    frame_id = -1
    expect = f"frame_id '{frame_id}' must be greater than 0."
    with raises(VideoBufferError) as excinfo:
        myvideo.set(frame_id)
    assert excinfo.value.message == expect


@pytest.mark.parametrize('myvideo', [(list(range(10, 35)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_setando_o_buffer_com_frame_id_maior_que_o_maior_frame_id_no_mapping_com_buffersize_zero(myvideo):
    [myvideo.put(*frame) for frame in lote(10, 35, 1)]

    frame_id = 105
    expect = 'frame_id does not belong to the lot range.'
    myvideo.buffersize = 0
    with raises(IndexError) as excinfo:
        myvideo.set(frame_id)
    result = str(excinfo.value)
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(10, 35)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_setando_o_buffer_com_frame_id_maior_que_o_maior_frame_id_no_mapping(myvideo):
    [myvideo.put(*frame) for frame in lote(10, 35, 1)]

    frame_id = 105
    expect = 'frame_id does not belong to the lot range.'
    myvideo.buffersize = 0
    with patch("aniseek.core.buffer_left.bisect.bisect_left", return_value=50):
        with raises(IndexError) as excinfo:
            myvideo.set(frame_id)
    result = str(excinfo.value)
    assert result == expect


# #################### TESTES EXTRAS PARA START_FRAME##################################

@pytest.mark.parametrize('myvideo', [(list(range(20, 65)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_put_com_buffer_vazio(myvideo):
    frame_id = 45
    expect_start_frame = 20
    expect_end_frame = frame_id - 1
    myvideo.put(frame_id, np.zeros((2, 2)))
    result_start_frame = myvideo.start_frame()
    result_end_frame = myvideo.end_frame()
    assert result_start_frame == expect_start_frame
    assert result_end_frame == expect_end_frame


@pytest.mark.parametrize('myvideo', [(list(range(20, 65)), 25)], indirect=True)
def test_buffer_VideoBufferLeft_com_buffer_vazio_apos_um_get(myvideo):
    # Caso epecial que pode ocorrer no método get do VideoBufferLeft, quando tiramos o
    # ultimo frame do _buffer, o mesmo fica vazio fazendo entrar no segundo run, que chama
    # o método `end_frame` que não trata este caso adequadamente
    frame_id = 45
    expect_start_frame = 20
    expect_end_frame = frame_id - 1

    # Fica dificil de criar esse cenario usando os métodos put e get, então devemos colocar
    # manualmente o valor no atributo __frame_id
    myvideo._VideoBufferLeft__frame_id = frame_id
    result_start_frame = myvideo.start_frame()
    result_end_frame = myvideo.end_frame()
    assert result_start_frame == expect_start_frame
    assert result_end_frame == expect_end_frame
