from threading import Semaphore
from unittest.mock import patch

import cv2
import numpy as np
import pytest
from pytest import fixture, raises

from aniseek.core.buffer_right import VideoBufferRight
from aniseek.core.frame_mapper import FrameMapper
from aniseek.custom_exceptions import VideoBufferError
from tests.uteis import MyVideoCapture


def lote(start, end, step=1):
    return [(frame_id, np.ones((2, 2))) for frame_id in range(start, end, step)]


@fixture
def mycap():
    with patch('cv2.VideoCapture', return_value=MyVideoCapture()) as mock:
        yield mock


@fixture
def myvideo(mycap, request):
    lote, buffersize = request.param
    cap = mycap.return_value
    semaphore = Semaphore()
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    mapping = FrameMapper(lote, frame_count)
    buffer = VideoBufferRight(cap, mapping, semaphore, buffersize=buffersize)
    yield buffer

    buffer.join()


@fixture
def myvideo_mapping(mycap, request):
    lote, buffersize = request.param
    cap = mycap.return_value
    semaphore = Semaphore()
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    mapping = FrameMapper(lote, frame_count)
    buffer = VideoBufferRight(cap, mapping, semaphore, buffersize=buffersize)
    yield (buffer, mapping)

    buffer.join()


# ################### Testes para o VideoBufferRight sem Frames ##################################333

@pytest.mark.parametrize('myvideo', [([], 5)], indirect=True)
def test_buffer_VideoBufferRight_is_task_complete(myvideo):
    expect = True
    result = myvideo.is_task_complete()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([], 5)], indirect=True)
def test_buffer_VideoBufferRight_start_frame_sem_frames(myvideo):
    expect = None
    result = myvideo.start_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([], 5)], indirect=True)
def test_buffer_VideoBufferRight_end_frame_sem_frames(myvideo):
    expect = None
    result = myvideo.end_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([], 5)], indirect=True)
def test_buffer_VideoBufferRight__calc_frame_sem_frames(myvideo):
    expect = None
    result = myvideo._VideoBufferRight__calc_frame(5)
    assert result == expect


@pytest.mark.parametrize('myvideo', [([], 5)], indirect=True)
def test_buffer_VideoBufferRight_get_com_o_buffer_vazio(myvideo):
    expect = 'get from an empty buffer'
    with raises(VideoBufferError) as excinfo:
        myvideo.get()
    result = f'{excinfo.value}'
    assert result == expect


@pytest.mark.parametrize('myvideo', [([], 5)], indirect=True)
def test_buffer_VideoBufferRight_put_com_o_buffer_vazio(myvideo):
    expect = 'frame_id does not belong to map'
    with raises(VideoBufferError) as excinfo:
        myvideo.put(5, np.zeros((2, 2)))
    result = f'{excinfo.value}'
    assert result == expect


# ##################### Testes para  VideoBufferRight com 1 Frame ###########################

@pytest.mark.parametrize('myvideo', [([0], 5)], indirect=True)
def test_buffer_VideoBufferRight_is_task_complete_com_1_frame_sem_ler(myvideo):
    expect = False
    result = myvideo.is_task_complete()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0], 5)], indirect=True)
def test_buffer_VideoBufferRight_is_task_complete_com_1_frame_com_leitura(myvideo):
    expect = True
    myvideo.get()
    result = myvideo.is_task_complete()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0], 5)], indirect=True)
def test_buffer_VideoBufferRight_start_frame_com_1_frame(myvideo):
    expect = 0
    result = myvideo.start_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0], 5)], indirect=True)
def test_buffer_VideoBufferRight_end_frame_com_1_frame(myvideo):
    expect = 0
    result = myvideo.end_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0], 5)], indirect=True)
def test_buffer_VideoBufferRight__calc_frame_com_1_frame(myvideo):
    expect = 0
    result = myvideo._VideoBufferRight__calc_frame(0)
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0], 5)], indirect=True)
def test_buffer_VideoBufferRight__calc_frame_com_1_frame_com_get(myvideo):
    expect = 'frame_id does not belong to the lot range.'
    myvideo.get()

    with raises(IndexError) as excinfo:
        myvideo._VideoBufferRight__calc_frame(1)
    result = f'{excinfo.value}'
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0], 5)], indirect=True)
def test_buffer_VideoBufferRight_get_com_1_frame(myvideo):
    expect = 0
    myvideo.get()
    result = myvideo.frame_id
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1], 5)], indirect=True)
def test_buffer_VideoBufferRight_put_com_1_frame(myvideo):
    expect = 1
    myvideo.put(1, np.zeros((2, 2)))
    myvideo.get()
    result = myvideo.frame_id
    assert result == expect


# ##################### Testes para  VideoBufferRight com 2 Frame ###########################

@pytest.mark.parametrize('myvideo', [([0, 1], 5)], indirect=True)
def test_buffer_VideoBufferRight_is_task_complete_com_2_frame_sem_ler(myvideo):
    expect = False
    result = myvideo.is_task_complete()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1], 5)], indirect=True)
def test_buffer_VideoBufferRight_is_task_complete_com_2_frame_com_leitura(myvideo):
    expect = False
    myvideo.get()
    result = myvideo.is_task_complete()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1], 5)], indirect=True)
def test_buffer_VideoBufferRight_start_frame_com_2_frame(myvideo):
    expect = 0
    result = myvideo.start_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1], 5)], indirect=True)
def test_buffer_VideoBufferRight_end_frame_com_2_frame(myvideo):
    expect = 1
    result = myvideo.end_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1], 5)], indirect=True)
def test_buffer_VideoBufferRight__calc_frame_com_2_frame(myvideo):
    expect = 0
    result = myvideo._VideoBufferRight__calc_frame(0)
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1], 5)], indirect=True)
def test_buffer_VideoBufferRight__calc_frame_com_2_frame_com_get(myvideo):
    expect = 1
    myvideo.get()

    result = myvideo._VideoBufferRight__calc_frame(1)
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1], 5)], indirect=True)
def test_buffer_VideoBufferRight_get_com_2_frame(myvideo):
    expect = 0
    myvideo.get()
    result = myvideo.frame_id
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1, 2], 5)], indirect=True)
def test_buffer_VideoBufferRight_put_com_2_frame(myvideo):
    expect = 2
    expect_no_block_task = True
    myvideo.put(2, np.zeros((2, 2)))
    myvideo.get()
    result = myvideo.frame_id
    result_no_block_task = myvideo._buffer.no_block_task()
    assert result == expect
    assert expect_no_block_task == result_no_block_task


@pytest.mark.parametrize('myvideo', [([0, 1, 2], 5)], indirect=True)
def test_buffer_VideoBufferRight_put_com_2_frame_no_block_task(myvideo):
    expect_no_block_task_put = False
    expect_no_block_task_get = True

    myvideo.put(2, np.zeros((2, 2)))
    result_no_block_task_put = myvideo._buffer.no_block_task()

    myvideo.get()
    result_no_block_task_get = myvideo._buffer.no_block_task()

    assert expect_no_block_task_put == result_no_block_task_put
    assert expect_no_block_task_get == result_no_block_task_get


@pytest.mark.parametrize('myvideo', [([0, 1], 5)], indirect=True)
def test_buffer_VideoBufferRight_put_com_2_frame_com_set_no_block_task(myvideo):
    expect_no_block_task = True

    myvideo.put(1, np.zeros((2, 2)))
    myvideo.put(0, np.zeros((2, 2)))
    myvideo.set(1)
    result_no_block_task = myvideo._buffer.no_block_task()
    assert expect_no_block_task == result_no_block_task


# ##################### Testes para  VideoBufferRight com 3 Frame ###########################

@pytest.mark.parametrize('myvideo', [([0, 1, 2], 5)], indirect=True)
def test_buffer_VideoBufferRight_is_task_complete_com_3_frame_sem_ler(myvideo):
    expect = False
    result = myvideo.is_task_complete()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1, 2], 5)], indirect=True)
def test_buffer_VideoBufferRight_is_task_complete_com_3_frame_com_leitura(myvideo):
    expect = False
    myvideo.get()
    result = myvideo.is_task_complete()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1, 2], 5)], indirect=True)
def test_buffer_VideoBufferRight_is_task_complete_com_3_frame_com_3_leitura(myvideo):
    expect = True
    [myvideo.get() for _ in range(3)]
    result = myvideo.is_task_complete()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1, 2], 5)], indirect=True)
def test_buffer_VideoBufferRight_start_frame_com_3_frame(myvideo):
    expect = 0
    result = myvideo.start_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1, 2], 5)], indirect=True)
def test_buffer_VideoBufferRight_end_frame_com_3_frame(myvideo):
    expect = 2
    result = myvideo.end_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1, 2], 5)], indirect=True)
def test_buffer_VideoBufferRight__calc_frame_com_3_frame(myvideo):
    expect = 0
    result = myvideo._VideoBufferRight__calc_frame(0)
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1, 2], 5)], indirect=True)
def test_buffer_VideoBufferRight__calc_frame_com_3_frame_com_get(myvideo):
    expect = 1
    myvideo.get()

    result = myvideo._VideoBufferRight__calc_frame(1)
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1, 2], 5)], indirect=True)
def test_buffer_VideoBufferRight_get_com_3_frame(myvideo):
    expect = 0
    myvideo.get()
    result = myvideo.frame_id
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1, 2], 5)], indirect=True)
def test_buffer_VideoBufferRight_get_com_3_frame_e_3_get(myvideo):
    expect = True
    [myvideo.get() for _ in range(3)]
    result = myvideo.is_task_complete()
    assert result == expect


@pytest.mark.parametrize('myvideo', [([0, 1, 2, 3], 5)], indirect=True)
def test_buffer_VideoBufferRight_put_com_3_frame(myvideo):
    expect = 3
    myvideo.put(3, np.zeros((2, 2)))
    myvideo.get()
    result = myvideo.frame_id
    assert result == expect


# ##################### Testes diversos  ###########################


@pytest.mark.parametrize('myvideo', [(list(range(200)), 5)], indirect=True)
def test_buffer_VideoBufferRight_start_frame_0(myvideo):
    expect = 0
    result = myvideo.start_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(15, 20)), 5)], indirect=True)
def test_buffer_VideoBufferRight_start_frame_15(myvideo):
    expect = 15
    result = myvideo.start_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(200)), 25)], indirect=True)
def test_buffer_VideoBufferRight_start_frame_set_sequencia_linear(myvideo):
    expect = 75
    myvideo.set(75)
    result = myvideo.start_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(0, 200, 7)), 25)], indirect=True)
def test_buffer_VideoBufferRight_start_frame_set_sequencia_nao_linear(myvideo):
    expect = 196
    myvideo.set(195)
    result = myvideo.start_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(200)), 25)], indirect=True)
def test_buffer_VideoBufferRight_start_frame_buffer_vazio(myvideo):
    expect = 0
    result = myvideo.start_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(200)), 25)], indirect=True)
def test_buffer_VideoBufferRight_start_frame_buffer_nao_vazio(myvideo):
    expect = 55
    [myvideo._buffer.put(frame) for frame in lote(54, 29, -1)]
    result = myvideo.start_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(0, 500, 7)), 25)], indirect=True)
def test_buffer_VideoBufferRight_start_frame_buffer_nao_vazio_e_nao_linear(myvideo):
    expect = 392
    [myvideo._buffer.put(frame) for frame in lote(385, 215, -7)]
    result = myvideo.start_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo_mapping', [(list(range(20)), 5)], indirect=True)
def test_buffer_VideoBufferRight_sequence_linear(myvideo_mapping):
    myvideo, mapping = myvideo_mapping
    lote = list(range(0, 20))
    expect = {key for key in lote}
    result = mapping.get_mapping()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(150)), 25)], indirect=True)
def test_buffer_VideoBufferRight_metodo_set_frame(myvideo):
    expect_start_frame = 25
    myvideo.set(25)
    result_start_frame = myvideo.start_frame()
    assert result_start_frame == expect_start_frame


@pytest.mark.parametrize('myvideo', [(list(range(200)), 5)], indirect=True)
def test_buffer_VideoBufferRight_end_frame_com_buffer_vazio_0(myvideo):
    expect = 5
    result = myvideo.end_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(15, 200)), 5)], indirect=True)
def test_buffer_VideoBufferRight_end_frame_com_buffer_vazio_15(myvideo):
    expect = 20
    result = myvideo.end_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(15, 200)), 5)], indirect=True)
def test_buffer_VideoBufferRight_end_frame_com_set_25(myvideo):
    expect = 30
    myvideo.set(25)
    result = myvideo.end_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(200)), 5)], indirect=True)
def test_buffer_VideoBufferRight_end_frame_com_set_0(myvideo):
    expect = 5
    myvideo.set(0)
    result = myvideo.end_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(200)), 25)], indirect=True)
def test_buffer_VideoBufferRight_end_frame_com_buffer_nao_vazio(myvideo):
    expect = 79
    [myvideo._buffer.put(frame) for frame in lote(54, 29, -1)]
    result = myvideo.end_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(200)), 25)], indirect=True)
def test_buffer_VideoBufferRight_end_frame_com_end_frame_0(myvideo):
    expect = 49
    [myvideo._buffer.put(frame) for frame in lote(24, -1, -1)]
    result = myvideo.end_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(0, 500, 7)), 25)], indirect=True)
def test_buffer_VideoBufferRight_end_frame_buffer_nao_vazio_e_nao_linear_atingindo_o_limite(myvideo):
    expect = 497
    [myvideo._buffer.put(frame) for frame in lote(385, 215, -7)]
    result = myvideo.end_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(0, 500, 7)), 5)], indirect=True)
def test_buffer_VideoBufferRight_end_frame_buffer_nao_vazio_e_nao_linear(myvideo):
    expect = 420
    [myvideo._buffer.put(frame) for frame in lote(385, 355, -7)]
    result = myvideo.end_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(0, 500, 1)), 25)], indirect=True)
def test_buffer_VideoBufferRight_end_frame_buffer_vazio_e_com__freme_id_nao_none_index_error(myvideo):
    expect = 499
    myvideo._VideoBufferRight__frame_id = 490
    result = myvideo.end_frame()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(0, 200, 7)), 25)], indirect=True)
def test_buffer_VideoBufferRight_metodo_set_frame_com_lote_nao_linear(myvideo):
    expect_start_frame = 196
    myvideo.set(195)
    result_start_frame = myvideo.start_frame()
    assert result_start_frame == expect_start_frame


@pytest.mark.parametrize('myvideo', [(list(range(0, 212, 7)), 25)], indirect=True)
def test_buffer_VideoBufferRight_metodo_set_frame_com_lote_nao_linear_penultimo_frame(myvideo):
    expect_start_frame = 196
    myvideo.set(195)
    result_start_frame = myvideo.start_frame()
    assert result_start_frame == expect_start_frame


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferRight_enchendo_o_buffer_manualmente(myvideo):
    expect = 10
    [myvideo._buffer.put(frame) for frame in lote(10, 0, -1)]
    result = len(myvideo)
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferRight_is_done_eh_true_com_o_buffer_vazio(myvideo):
    expect = False
    result = myvideo.is_done()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferRight_is_done_eh_false_com_o_buffer_cheio(myvideo):
    expect = False
    [myvideo._buffer.put(frame) for frame in lote(49, 24, -1)]
    result = myvideo.is_done()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferRight_is_done_eh_true(myvideo):
    expect = True
    [myvideo._buffer.put(frame) for frame in lote(100, 74, -1)]
    result = myvideo.is_done()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferRight_do_task_buffer_vazio_sem_set(myvideo):
    expect = True
    result = myvideo.do_task()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferRight_do_task_buffer_vazio_set_0(myvideo):
    expect = True
    myvideo.set(0)
    result = myvideo.do_task()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferRight_do_task_buffer_vazio_set_1(myvideo):
    expect = True
    myvideo.set(1)
    result = myvideo.do_task()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferRight_do_task_buffer_vazio_com_set_50(myvideo):
    expect = True
    myvideo.set(50)
    result = myvideo.do_task()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferRight_do_task_buffer_cheio(myvideo):
    expect = True
    [myvideo._buffer.sput(frame) for frame in lote(50, 75, 1)]
    myvideo._buffer.unqueue()
    result = myvideo.do_task()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferRight_do_task_buffer_cheio_com_frame_id_no_final(myvideo):
    expect = False
    [myvideo._buffer.sput(frame) for frame in lote(75, 100, 1)]
    myvideo._buffer.unqueue()
    result = myvideo.do_task()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferRight_do_task_colocando_dados_manualmente(myvideo):
    expect = False
    [myvideo.put(*frame) for frame in lote(99, 74, -1)]
    result = myvideo.do_task()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferRight_do_task_com_set_0(myvideo):
    expect = True
    myvideo.set(0)
    result = myvideo.do_task()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferRight_do_task_com_set_1(myvideo):
    expect = True
    myvideo.set(1)
    result = myvideo.do_task()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferRight_do_task_com_set_33(myvideo):
    expect = True
    myvideo.set(33)
    result = myvideo.do_task()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferRight_is_task_complete_sem_set(myvideo):
    expect = False
    result = myvideo.is_task_complete()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferRight_is_task_complete_set_0(myvideo):
    expect = False
    myvideo.set(0)
    result = myvideo.is_task_complete()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferRight_is_task_complete_colocando_manualmente_de_30_55(myvideo):
    expect = False
    [myvideo._buffer.put(frame) for frame in lote(55, 29, -1)]
    myvideo.get()
    result = myvideo.is_task_complete()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferRight_is_task_complete_colocando_manualmente_de_75_99_consumindo_tudo(myvideo):
    expect = True
    [myvideo._buffer.put(frame) for frame in lote(99, 74, -1)]
    [myvideo.get() for x in range(25)]
    result = myvideo.is_task_complete()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferRight_run_sem_set_e_vazio(myvideo):
    expect = False
    myvideo.run()
    result = myvideo.do_task()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferRight_run_set_50(myvideo):
    expect = False
    myvideo.set(50)
    myvideo.run()
    result = myvideo._buffer.secondary_empty()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferRight_run_2vezes_set_50(myvideo):
    expect = False
    myvideo.set(50)
    myvideo.run()

    # run é chamado dentro de get
    myvideo.get()
    result = myvideo._buffer.secondary_empty()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferRight_put_e_run(myvideo):
    expect = False
    [myvideo.put(*frame) for frame in lote(75, 49, -1)]
    myvideo.get()
    result = myvideo._buffer.secondary_empty()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferRight_put_e_run_consumindo_tudo_com_get_checando_os_frames_id(myvideo):
    expect = list(range(50, 100, 1))
    [myvideo.put(*frame) for frame in lote(75, 49, -1)]
    result = [myvideo.get()[0] for _ in range(50)]
    assert result == expect

# ##################### NOVOS TESTES #############################################


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferRight_is_task_complete_set_99_sem_ler_do_buffer(myvideo):
    expect = False
    myvideo.set(99)
    result = myvideo.is_task_complete()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferRight_is_task_complete_set_99_lendo_do_buffer(myvideo):
    expect = True
    myvideo.set(99)
    myvideo.run()  # Deve-se usar run apos o set
    myvideo.get()
    result = myvideo.is_task_complete()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferRight_is_done_com_set_no_ultimo_frame(myvideo):
    expect = True
    myvideo.set(99)
    myvideo.run()  # Deve-se usar run apos o set
    myvideo._buffer.unqueue()  # Movendo o frame para o buffer primario
    result = myvideo.is_done()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferRight_get_com_o_set_no_ultimo_frame(myvideo):
    expect = 99
    myvideo.set(99)
    myvideo.run()  # Deve-se usar run apos o set
    result, _ = myvideo.get()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferRight_do_task_com_set_no_ultimo_frame(myvideo):
    expect = True
    myvideo.set(99)
    result = myvideo.do_task()
    assert result == expect

# ################### TESTES SOBRE O SET_MAPPING ###############################


@pytest.mark.parametrize('myvideo_mapping', [(list(range(500)), 25)], indirect=True)
def test_buffer_VideoBufferRight_set_lot_com_mapping_do_tamanho_do_frame_count(myvideo_mapping):
    myvideo, mapping = myvideo_mapping
    expect = set(range(500))
    result = mapping.get_mapping()
    assert result == expect


@pytest.mark.parametrize('myvideo_mapping', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferRight_set_lot_com_mapping_menor_que_frame_count(myvideo_mapping):
    myvideo, mapping = myvideo_mapping
    expect = set(range(100))
    result = mapping.get_mapping()
    assert result == expect


@pytest.mark.parametrize('myvideo_mapping', [(list(range(900)), 25)], indirect=True)
def test_buffer_VideoBufferRight_set_lot_com_mapping_maior_que_frame_count(myvideo_mapping):
    myvideo, mapping = myvideo_mapping
    expect = set(range(500))
    result = mapping.get_mapping()
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(300)), 25)], indirect=True)
def test_buffer_VideoBufferRight_colocando_manualmente_o_primeiro_frame(myvideo):
    expect_end_frame = 25
    [myvideo.put(*frame) for frame in lote(0, 1, 1)]
    result_end_frame = myvideo.end_frame()
    assert result_end_frame == expect_end_frame


@pytest.mark.parametrize('myvideo', [(list(range(300)), 25)], indirect=True)
def test_buffer_VideoBufferRight_colocando_manualmente_o_primeiro_frame_e_usando_get(myvideo):
    expect_end_frame = 25
    [myvideo.put(*frame) for frame in lote(0, 1, 1)]
    myvideo.get()
    result_end_frame = myvideo.end_frame()
    assert result_end_frame == expect_end_frame


# ##################### TESTANDO OS ERROS NO METODO PUT ########################## #

@pytest.mark.parametrize('myvideo', [(list(range(10, 36)), 25)], indirect=True)
def test_buffer_VideoBufferRight_colocando_um_frame_id_maior_que_o_primeiro_frame_id_do_buffer(myvideo):
    [myvideo.put(*frame) for frame in lote(35, 10, -1)]

    frame_id = 12
    expect = f"Inconsistency in operation: 'frame_id' '{frame_id}' is greater than the current frame."
    with raises(VideoBufferError) as excinfo:
        myvideo.put(frame_id, np.zeros((2, 2)))
    assert excinfo.value.message == expect


@pytest.mark.parametrize('myvideo', [(list(range(10, 36)), 25)], indirect=True)
def test_buffer_VideoBufferRight_colocando_um_frame_id_que_ja_esta_presente_no_buffer(myvideo):
    [myvideo.put(*frame) for frame in lote(30, 10, -1)]

    frame_id = 34
    expect = f"Inconsistency in operation: 'frame_id' '{frame_id}' is greater than the current frame."
    with raises(VideoBufferError) as excinfo:
        myvideo.put(frame_id, np.zeros((2, 2)))
    assert excinfo.value.message == expect


@pytest.mark.parametrize('myvideo', [(list(range(10, 36)), 25)], indirect=True)
def test_buffer_VideoBufferRight_colocando_um_frame_id_igual_ao_primeiro_frame_id_do_buffer(myvideo):
    [myvideo.put(*frame) for frame in lote(35, 10, -1)]

    frame_id = 11
    expect = f"The frame_id '{frame_id}' is already present in VideoBufferRight."
    with raises(VideoBufferError) as excinfo:
        myvideo.put(frame_id, np.zeros((2, 2)))
    assert excinfo.value.message == expect


# ##################### TESTANDO OS ERROS NO METODO SET ########################## #


@pytest.mark.parametrize('myvideo', [(list(range(10, 36)), 25)], indirect=True)
def test_buffer_VideoBufferRight_setando_o_buffer_com_uma_string(myvideo):
    [myvideo.put(*frame) for frame in lote(35, 10, -1)]

    frame_id = '8'
    expect = 'frame_id must be an integer.'
    with raises(TypeError) as excinfo:
        myvideo.set(frame_id)
    result = str(excinfo.value)
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(10, 36)), 25)], indirect=True)
def test_buffer_VideoBufferRight_setando_o_buffer_com_frame_id_menor_que_zero(myvideo):
    [myvideo.put(*frame) for frame in lote(35, 10, -1)]

    frame_id = -5
    expect = f"frame_id '{frame_id}' must be greater than 0."
    with raises(VideoBufferError) as excinfo:
        myvideo.set(frame_id)
    result = str(excinfo.value)
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(10, 36)), 25)], indirect=True)
def test_buffer_VideoBufferRight_setando_o_buffer_com_frame_id_maior_que_o_maior_frame_id_no_buffer(myvideo):
    [myvideo.put(*frame) for frame in lote(35, 10, -1)]

    frame_id = 45
    expect = 'frame_id does not belong to the lot range.'
    with raises(IndexError) as excinfo:
        myvideo.set(frame_id)
    result = str(excinfo.value)
    assert result == expect


@pytest.mark.parametrize('myvideo', [(list(range(10, 60)), 25)], indirect=True)
def test_buffer_VideoBufferRight_setando_o_buffer_com_idx_do_set_end_frame_maior_que_o_indice_maximo_do_mapping(myvideo):
    frame_id = 50
    expect = 59
    myvideo.buffersize = 60
    myvideo.set(frame_id)
    result = myvideo.end_frame()
    assert result == expect


# #################### TESTES EXTRAS PARA START_FRAME##################################

@pytest.mark.parametrize('myvideo', [(list(range(20, 65)), 25)], indirect=True)
def test_buffer_VideoBufferRight_put_com_buffer_vazio(myvideo):
    frame_id = 30
    expect_start_frame = 31
    expect_end_frame = 55
    myvideo.put(frame_id, np.zeros((2, 2)))
    result_start_frame = myvideo.start_frame()
    result_end_frame = myvideo.end_frame()
    assert result_start_frame == expect_start_frame
    assert result_end_frame == expect_end_frame


@pytest.mark.parametrize('myvideo', [(list(range(20, 65)), 25)], indirect=True)
def test_buffer_VideoBufferRight_com_buffer_vazio_apos_um_get(myvideo):
    # Caso epecial que pode ocorrer no método get do VideoBufferRight, quando tiramos o
    # ultimo frame do _buffer, o mesmo fica vazio fazendo entrar no segundo run, que chama
    # o método `end_frame` que não trata este caso adequadamente
    frame_id = 35
    expect_start_frame = 36
    expect_end_frame = 60

    # Fica dificil de criar esse cenario usando os métodos put e get, então devemos colocar
    # manualmente o valor no atributo __frame_id
    myvideo._VideoBufferRight__frame_id = frame_id
    result_start_frame = myvideo.start_frame()
    result_end_frame = myvideo.end_frame()
    assert result_start_frame == expect_start_frame
    assert result_end_frame == expect_end_frame
