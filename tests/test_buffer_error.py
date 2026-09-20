"""
from src.buffer import VideoBufferLeft, VideoBufferRight
from src.buffer_error import VideoBufferError
from pytest import fixture, raises
from unittest.mock import MagicMock, patch


import cv2
import numpy as np
import ipdb


from tests.my_mocks import MyVideoCapture


@fixture
def mycap():
    with patch('cv2.VideoCapture', return_value=MyVideoCapture()) as mock:
        yield mock


def test_buffer_metodo_end_frame_com_o_video_no_inicio(mycap):
    cap = mycap.return_value
    with raises(VideoBufferError) as excinfo:
        VideoBufferLeft(cap, list(range(300)), buffersize=25, name='buffer0')
    assert excinfo.value.message == 'the current frame index is not a valid index'


def test_buffer_VideoBuffer_Right_mount_sequence_indice_do_frame_maior_que_o_maior_indice_do_lot(mycap):
    seq = [90, 91, 95, 98, 100, 101, 102, 103, 104, 105, 106, 107, 108]
    cap = mycap.return_value
    cap.set(cv2.CAP_PROP_POS_FRAMES, 231)

    with raises(VideoBufferError) as excinfo:
        VideoBufferRight(cap, seq, buffersize=10)
    assert excinfo.value.message == 'the current frame index is greater than maximum frame index'


def test_buffer_mount_sequence_VideoBufferRight_com_frame_atual_nao_pertencendo_ao_lot_de_frames_nao_continuo(mycap):
    seq = [90, 91, 95, 98, 103, 104, 107, 108]

    cap = mycap.return_value
    cap.set(cv2.CAP_PROP_POS_FRAMES, 100)

    with raises(VideoBufferError) as excinfo:
        VideoBufferRight(cap, seq, buffersize=10)
    assert excinfo.value.message == 'current frame index is not in batch'


def test_buffer_mount_sequence_VideoBufferRight_com_lote_vazio(mycap):
    seq = []

    cap = mycap.return_value
    cap.set(cv2.CAP_PROP_POS_FRAMES, 100)

    with raises(VideoBufferError) as excinfo:
        VideoBufferRight(cap, seq, buffersize=10)
    assert excinfo.value.message == 'the last batch is empty'


def test_buffer_mount_sequence_VideoBufferRight_preencher_o_buffer_com_a_fila_nao_vazi(mycap):

    cap = mycap.return_value
    cap.set(cv2.CAP_PROP_POS_FRAMES, 100)
    ret, frame = cap.read()

    with raises(VideoBufferError) as excinfo:
        buffer = VideoBufferRight(cap, sorted(range(300)), buffersize=10)
        buffer.put((100, frame))
        buffer.start()
        buffer.join()
    assert excinfo.value.message == 'buffer is not empty'


def test_buffer_VideoBufferRight_metodo_end_frame_com_start_frame_mais_buffer_maior_que_o_tamanho_do_lote(mycap):
    lote = list(range(0, 20))
    expect = 19
    buffer = VideoBufferRight('path', lote, buffersize=5)
    buffer.set(16)
    result = buffer.end_frame()
    assert result == expect

@pytest.mark.parametrize('myvideo', [(list(range(100)), 25)], indirect=True)
def test_buffer_VideoBufferRight_enchendo_o_buffer_manualmente_com_o_buffer_lotado(myvideo, seq):
    expect_start_frame = False
    buffer = myvideo
    buffer.bufferlog = True
    [buffer.queue.append((frame_id, np.zeros((2, 2)))) for frame_id in range(25, 50)]
    buffer._old_frame = 25
    buffer._frame_id = 50
    [buffer.put(*seq.pop(0)) for _ in range(3)]
    ipdb.set_trace()
    result_start_frame = buffer.start_frame()
    assert result_start_frame == expect_start_frame

    # Consumindo os frames para testar se start_frame() deixa de estar bloqueado
    expect_start_frame = 0
    [buffer.read() for _ in range(25)]
    try:
        buffer.read()
    except TimeoutError:
        ...
    result_start_frame = buffer.start_frame()
    assert result_start_frame == expect_start_frame
"""
