from threading import Semaphore
from unittest.mock import patch

import cv2
import numpy as np
import pytest
from pytest import fixture

from aniseek.buffer_left import VideoBufferLeft
from aniseek.buffer_right import VideoBufferRight
from aniseek.frame_mapper import FrameMapper
from aniseek.interfaces.source import IFrameSource
from aniseek.player_control import PlayerControl


def lote(start, end, step=1):
    return [(frame_id, np.ones((2, 2))) for frame_id in range(start, end, step)]


class MyVideoCapture(IFrameSource):
    def __init__(self):
        self.frames = [np.zeros((2, 2)) for x in range(300)]
        self.index = 0
        self.isopened = True

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    @property
    def fps(self) -> float:
        return 24.0

    def seek(self, frame_id: int) -> None:
        self.index = frame_id

    def is_opened(self) -> bool:
        return self.isopened

    def read(self):

        # Para um teste em __opencv_format definimos um retorno como None
        if self.index == 205:
            self.index += 1
        elif self.index < len(self.frames):
            frame = self.frames[self.index]
            self.index += 1
            return True, frame
        return False, None

    def grab(self):
        self.index += 1
        return True

    def set(self, flag, value):
        if cv2.CAP_PROP_POS_FRAMES == flag:
            if len(self.frames) >= value and value >= 0:
                self.index = value
                return True
            else:
                return False
        return False

    def get(self, flag):
        if cv2.CAP_PROP_FRAME_COUNT == flag:
            return len(self.frames)
        elif cv2.CAP_PROP_POS_FRAMES == flag:
            return self.index
        return False

    def isOpened(self):
        return self.isopened

    def release(self):
        self.isopened = False


@fixture
def mycap():
    with patch('cv2.VideoCapture', return_value=MyVideoCapture()) as mock:
        yield mock


@fixture
def player(mycap, request):
    lote, buffersize = request.param
    cap = mycap.return_value
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    mapping = FrameMapper(lote, frame_count)
    semaphore = Semaphore()
    log = False
    vbuffer_right = VideoBufferRight(cap, mapping, semaphore, bufferlog=log, buffersize=buffersize)
    vbuffer_left = VideoBufferLeft(cap, mapping, semaphore, bufferlog=log, buffersize=buffersize)
    player_control = PlayerControl(vbuffer_right, vbuffer_left)
    yield player_control

    vbuffer_left.join()
    vbuffer_right.join()


@fixture
def pm(mycap, request):
    # Fixture para testes do método restore_frame
    lote, buffersize = request.param
    cap = mycap.return_value
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    mapping = FrameMapper(lote, frame_count)
    semaphore = Semaphore()
    log = False
    vbuffer_right = VideoBufferRight(cap, mapping, semaphore, bufferlog=log, buffersize=buffersize)
    vbuffer_left = VideoBufferLeft(cap, mapping, semaphore, bufferlog=log, buffersize=buffersize)
    player_control = PlayerControl(vbuffer_right, vbuffer_left)
    yield player_control, mapping

    vbuffer_left.join()
    vbuffer_right.join()


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_read_com_buffer_right_e_left_vazios_servant_right_no_primeiro_frame(player):
    expect = 0
    player.read()
    result = player.frame_id
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_read_com_buffer_right_e_left_vazios_servant_right_no_ultimo_frame(player):
    expect = None
    player.servant.set(34)
    player.master.set(34)
    player.read()
    player.read()
    result = player.frame_id
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_read_com_buffer_right_e_left_vazios_servant_left_no_ultimo_frame(player):
    expect = 34
    player.servant.set(34)
    player.master.set(34)
    player.read()
    player.rewind()
    result = player.frame_id
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_read_com_buffer_right_e_left_vazios_servant_left_no_primeiro_frame(player):
    expect = None
    player.rewind()
    player.read()
    result = player.frame_id
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_read_com_buffer_right_e_left_vazios_servant_right_com_set_15(player):
    expect = 15
    player.servant.set(15)
    player.master.set(15)
    player.read()
    result = player.frame_id
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_read_com_buffer_right_e_left_vazios_servant_leftt_com_set_15(player):
    expect = 14
    player.servant.set(15)
    player.master.set(15)
    player.rewind()
    player.read()
    result = player.frame_id
    assert expect == result


@pytest.mark.skip(reason='Não lembro o porque, desse teste passar')
@pytest.mark.parametrize('player', [(list(range(205, 300)), 25)], indirect=True)
def test_player__opencv_format_retorna_none(player):
    expect = None
    player.read()
    result = player.frame_id
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_coleta_de_frames_com_buffer_left_vazio_com_buffer_right_nao_vazio(player):
    expect = False
    expect_frame_id = 0
    player.read()
    player.collect_frame()
    result = player.master._buffer.empty()
    result_frame_id = player.frame_id
    assert expect == result
    assert expect_frame_id == result_frame_id


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_coleta_de_frames_com_buffer_left_vazio_com_buffer_right_completo(player):
    expect = False
    expect_frame_id = None
    player.servant.set(34)
    player.master.set(34)
    player.read()
    player.collect_frame()
    result = player.master._buffer.empty()
    result_frame_id = player.frame_id
    assert expect == result
    assert expect_frame_id == result_frame_id


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_coleta_de_frames_com_buffer_left_e_right__vazio_mas__frame_sendo_ndarray(player):
    expect = True
    player._PlayerControl__frame = np.zeros((2, 2))
    player.collect_frame()
    result = player.master._buffer.empty()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_coleta_de_frames_com_buffer_right_e_left__vazio(player):
    expect = True
    player.rewind()
    player.collect_frame()
    result = player.master._buffer.empty()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_coleta_de_frames_com_buffer_right_vazio_com_buffer_left_nao_vazio(player):
    expect = False
    expect_frame_id = 33
    player.servant.set(34)
    player.master.set(34)
    player.rewind()
    player.read()
    player.collect_frame()
    result = player.master._buffer.empty()
    result_frame_id = player.frame_id
    assert expect == result
    assert expect_frame_id == result_frame_id


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_coleta_de_frames_com_buffer_right_vazio_com_buffer_left_completo(player):
    expect = False
    expect_frame_id = None
    player.servant.set(1)
    player.master.set(1)
    player.rewind()
    player.read()
    player.collect_frame()
    result = player.master._buffer.empty()
    result_frame_id = player.frame_id
    assert expect == result
    assert expect_frame_id == result_frame_id


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_rewind_com_servant_como_buffer_right(player):
    expect = VideoBufferLeft
    player.rewind()
    result = player.servant
    assert isinstance(result, expect)


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_rewind_com_servant_como_buffer_left(player):
    expect = VideoBufferLeft
    player.rewind()
    player.rewind()
    result = player.servant
    assert isinstance(result, expect)


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_proceed_com_servant_como_buffer_left(player):
    expect = VideoBufferRight
    player.rewind()
    player.proceed()
    result = player.servant
    assert isinstance(result, expect)


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_proceed_com_servant_como_buffer_right(player):
    expect = VideoBufferRight
    player.proceed()
    result = player.servant
    assert isinstance(result, expect)


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_pause_sem_set_pause(player):
    expect = False
    result = player.pause()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_pause_sem_com_set_pause(player):
    expect = True
    player.set_pause()
    result = player.pause()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_set_pause_2x(player):
    expect = False
    [player.set_pause() for _ in range(2)]
    result = player.pause()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_set_pause_3x(player):
    expect = True
    [player.set_pause() for _ in range(3)]
    result = player.pause()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_quit_sem_set_quit(player):
    expect = False
    result = player.quit()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_quit_com_set_quit(player):
    expect = True
    player.set_quit()
    result = player.quit()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_quit_com_set_quit_2x(player):
    expect = True
    [player.set_quit() for _ in range(2)]
    result = player.quit()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_increase_speed_1x(player):
    expect = player._PlayerControl__default_delay - 1
    player.increase_speed()
    result = player.delay
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_increase_speed_DefaultDelayx(player):
    expect = 1
    default = player._PlayerControl__default_delay
    [player.increase_speed() for _ in range(default)]
    result = player.delay
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_increase_speed_DefaultDelayx_mais_1(player):
    expect = 1
    default = player._PlayerControl__default_delay + 1
    [player.increase_speed() for _ in range(default)]
    result = player.delay
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_decrease_speed_1x(player):
    expect = player._PlayerControl__default_delay + 1
    player.decrease_speed()
    result = player.delay
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_decrease_speed_2x(player):
    expect = player._PlayerControl__default_delay + 2
    [player.decrease_speed() for _ in range(2)]
    result = player.delay
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_decrease_speed_DefaultDelayx(player):
    default = player._PlayerControl__default_delay
    expect = 2 * default
    [player.decrease_speed() for _ in range(default)]
    result = player.delay
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_decrease_speed_DefaultDelayx_mais_1(player):
    default = player._PlayerControl__default_delay
    expect = 2 * default + 1
    [player.decrease_speed() for _ in range(default + 1)]
    result = player.delay
    assert expect == result


# ########## Testes para a remoção de frames com o FrameMapper vazio ############################

@pytest.mark.parametrize('player', [([], 25)], indirect=True)
def test_player_control_remove_frame_sem_frame(player):
    expect = None
    result, _ = player.remove_frame()
    assert expect == result


# ########## Testes para a remoção de frames com o FrameMapper com 1 frame ############################

@pytest.mark.parametrize('player', [([0], 25)], indirect=True)
def test_player_control_remove_frame_com_1_frame(player):
    expect = 0
    result, _ = player.remove_frame()
    assert expect == result


# ########## Testes para a remoção de frames com o FrameMapper com 2 frames ############################

@pytest.mark.parametrize('player', [([0, 1], 25)], indirect=True)
def test_player_control_remove_frame_com_2_frames(player):
    expect = 0
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [([0, 1], 25)], indirect=True)
def test_player_control_remove_frame_com_2_frames_com_1x_read(player):
    expect = 0
    player.read()
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [([0, 1], 25)], indirect=True)
def test_player_control_remove_frame_com_2_frames_com_2x_read(player):
    expect = 1
    [player.read() for _ in range(2)]
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [([0, 1], 25)], indirect=True)
def test_player_control_remove_frame_com_2_frames_com_2x_read_removendo_2x(player):
    expect = [1, None]  # No RemoveFrameCommand é esperado remover [1, 0]
    [player.read() for _ in range(2)]
    result = [player.remove_frame()[0] for _ in range(2)]
    assert expect == result


@pytest.mark.parametrize('player', [([0, 1], 25)], indirect=True)
def test_player_control_remove_frame_com_2_frames_com_2x_read_removendo_2x_com_rewind(player):
    expect = [1, 0]
    expect_is_task_complete = True
    [player.read() for _ in range(2)]
    player.rewind()
    result = [player.remove_frame()[0] for _ in range(2)]
    result_is_task_complete = player.servant.is_task_complete()
    assert expect == result
    assert expect_is_task_complete == result_is_task_complete


# ########## Testes para a remoção de frames com o FrameMapper com 3 frames ############################

@pytest.mark.parametrize('player', [([0, 1], 25)], indirect=True)
def test_player_control_remove_frame_com_3_frames(player):
    expect = 0
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [([0, 1], 25)], indirect=True)
def test_player_control_remove_frame_com_3_frames_com_1x_read(player):
    expect = 0
    player.read()
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [([0, 1, 2], 25)], indirect=True)
def test_player_control_remove_frame_3_com_frames_com_3x_read(player):
    expect = 2
    [player.read() for _ in range(3)]
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [([0, 1, 2], 25)], indirect=True)
def test_player_control_remove_frame_com_3_frames_com_3x_read_removendo_3x(player):
    expect = [2, None, None]  # No RemoveFrameCommand é esperado remover [1, 0]
    [player.read() for _ in range(3)]
    result = [player.remove_frame()[0] for _ in range(3)]
    assert expect == result


@pytest.mark.parametrize('player', [([0, 1, 2], 25)], indirect=True)
def test_player_control_remove_frame_com_3_frames_com_3x_read_removendo_3x_com_rewind(player):
    expect = [2, 1, 0]
    expect_is_task_complete = True
    [player.read() for _ in range(3)]
    player.rewind()
    result = [player.remove_frame()[0] for _ in range(3)]
    result_is_task_complete = player.servant.is_task_complete()
    assert expect == result
    assert expect_is_task_complete == result_is_task_complete


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_remove_frame_com_os_buffers_vazios_com_servant_buffer_right(player):
    expect = 0
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_remove_frame_com_o_servant_buffer_right_cheio_mas_sem_read(player):
    expect = 0
    player.servant.run()
    player.servant._buffer.unqueue()
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_remove_frame_com_o_servant_buffer_right_vazio_mas_com_read(player):
    expect = 0
    player.read()
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_remove_frame_com_o_servant_right_cheio_e_com_read(player):
    expect = 0
    player.servant.run()
    player.servant._buffer.unqueue()
    player.read()
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_remove_frame_com_servant_buffer_right_e_com_set_no_ultimo_frame(player):
    expect = 34
    player.servant.set(34)
    player.master.set(34)
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_remove_frame_servant_buffer_right_e_com_set_no_ultimo_frame_e_read1x(player):
    expect = 34
    player.servant.set(34)
    player.master.set(34)
    player.read()
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_remove_frame_servant_buffer_right_e_com_set_no_ultimo_frame_e_read2x(player):
    expect = None
    player.servant.set(34)
    player.master.set(34)
    [player.read() for _ in range(2)]
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_remove_frame_com_os_buffers_vazios_com_servant_buffer_left(player):
    expect = None
    player.rewind()
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_remove_frame_com_o_servant_buffer_leftt_vazio_mas_com_read(player):
    expect = None
    player.rewind()
    player.read()
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_remove_frame_com_o_servant_buffer_left_cheio_sem_read(player):
    expect = 29
    player.servant.set(30)
    player.master.set(30)
    player.rewind()
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_remove_frame_com_o_servant_buffer_left_cheio_com_read(player):
    expect = 29
    player.servant.set(30)
    player.master.set(30)
    player.rewind()
    player.read()
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_remove_frame_com_o_servant_buffer_left_set_1_com_read1x(player):
    expect = 0
    player.servant.set(1)
    player.master.set(1)
    player.rewind()
    player.read()
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_remove_frame_com_o_servant_buffer_left_set_1_com_read2x(player):
    expect = None
    player.servant.set(1)
    player.master.set(1)
    player.rewind()
    [player.read() for _ in range(2)]
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_remove_frame_com_o_servant_buffer_left_set_1_sem_read(player):
    expect = 0
    player.servant.set(1)
    player.master.set(1)
    player.rewind()
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_remove_frame_com_o_servant_buffer_left_set_no_ultimo_frame_com_read(player):
    expect = 33
    player.servant.set(34)
    player.master.set(34)
    player.rewind()
    player.read()
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_remove_frame_com_o_servant_buffer_left_set_no_ultimo_frame_sem_read(player):
    expect = 33
    player.servant.set(34)
    player.master.set(34)
    player.rewind()
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_remove_frame_com_o_servant_buffer_left_set_no_ultimo_frame_read_com_right_e_depois_rewind(player):
    expect = 34
    player.servant.set(34)
    player.master.set(34)
    player.read()
    player.rewind()
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_remove_frame_com_o_servant_buffer_left_set_no_ultimo_frame_read2x_com_right_e_depois_rewind(player):
    expect = 34
    player.servant.set(34)
    player.master.set(34)
    [player.read() for _ in range(2)]
    player.rewind()
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_remove_frame_com_o_servant_buffer_right_set_no_frame_1_read1x_com_left_e_depois_proceed(player):
    expect = 0
    player.servant.set(1)
    player.master.set(1)
    player.rewind()
    [player.read() for _ in range(1)]
    player.proceed()
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_remove_frame_com_o_servant_buffer_right_set_no_frame_1_read2x_com_left_e_depois_proceed(player):
    expect = 0
    player.servant.set(1)
    player.master.set(1)
    player.rewind()
    [player.read() for _ in range(2)]
    player.proceed()
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_remove_frame_com_o_servant_right_com_read2x(player):
    expect = 1
    [player.read() for _ in range(2)]
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_remove_frame_com_o_servant_right_com_read35x(player):
    expect = 34
    [player.read() for _ in range(35)]
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_remove_frame_com_o_servant_right_com_read36x(player):
    expect = None
    [player.read() for _ in range(36)]
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_remove_frame_com_o_servant_left_com_read2x(player):
    expect = 32
    player.servant.set(34)
    player.master.set(34)
    player.rewind()
    [player.read() for _ in range(2)]
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_remove_frame_com_o_servant_left_com_read34x(player):
    expect = 0
    player.servant.set(34)
    player.master.set(34)
    player.rewind()
    [player.read() for _ in range(34)]
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_remove_frame_com_o_servant_left_com_read35x(player):
    expect = None
    player.servant.set(34)
    player.master.set(34)
    player.rewind()
    [player.read() for _ in range(35)]
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_remove_frame_com_o_servant_left_com_read35x_mais_proceed(player):
    expect = 0
    player.servant.set(34)
    player.master.set(34)
    player.rewind()
    [player.read() for _ in range(35)]
    player.proceed()
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_remove_frame_com_o_servant_right_com_read36x_mais_rewind(player):
    expect = 34
    [player.read() for _ in range(36)]
    player.rewind()
    result, _ = player.remove_frame()
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_pause_delay(player):
    expect = 0
    player.pause_delay()
    result = player.delay
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_pause_delay2x_despausa(player):
    expect = player._PlayerControl__default_delay
    [player.pause_delay() for _ in range(2)]
    result = player.delay
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_pause_delay3x_pausa(player):
    expect = 0
    [player.pause_delay() for _ in range(3)]
    result = player.delay
    assert expect == result


# ######### Testes para o rewind sem frames ##############################

@pytest.mark.parametrize('player', [([], 25)], indirect=True)
def test_player_control_rewind_sem_frames(player):
    expect = True
    player.rewind()
    result = isinstance(player.servant, VideoBufferLeft)
    assert expect == result


@pytest.mark.parametrize('player', [([], 25)], indirect=True)
def test_player_control_rewind_sem_frames_com_read(player):
    expect = False
    player.rewind()
    result, _ = player.read()
    assert expect == result


# ######### Testes para o restore delay ##############################

@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_restore_delay_com_o_valor_padrao(player):
    expect = player._PlayerControl__default_delay
    player.restore_delay()
    result = player.delay
    assert expect == result


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_restore_delay_com_o_pause_delay_ativado(player):
    expect_delay = 0
    expect_current_delay = player.current_delay
    player.pause_delay()
    player.restore_delay()
    result_delay = player.delay

    result_current_delay = player.current_delay
    assert expect_delay == result_delay
    assert expect_current_delay == result_current_delay


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_restore_delay_antes_de_desativar_o_pause_delay(player):
    expect_delay = player._PlayerControl__default_delay
    player.pause_delay()
    player.restore_delay()
    player.pause_delay()
    result_delay = player.delay

    assert expect_delay == result_delay


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_restore_delay_com_increase_delay(player):
    expect_delay = player._PlayerControl__default_delay
    [player.increase_speed() for _ in range(10)]
    player.restore_delay()
    result_delay = player.delay

    assert expect_delay == result_delay


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_restore_delay_com_decrease_delay(player):
    expect_delay = player._PlayerControl__default_delay
    [player.decrease_speed() for _ in range(10)]
    player.restore_delay()
    result_delay = player.delay

    assert expect_delay == result_delay


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_restore_delay_com_increase_delay_e_pause_delay_ativado(player):
    [player.increase_speed() for _ in range(10)]
    player.pause_delay()

    expect_delay = 0
    player.restore_delay()
    result_delay = player.delay

    assert expect_delay == result_delay


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_restore_delay_com_increase_delay_e_desativando_o_pause_delay(player):
    [player.increase_speed() for _ in range(10)]
    player.pause_delay()

    expect_delay = player._PlayerControl__default_delay
    player.restore_delay()
    player.pause_delay()
    result_delay = player.delay

    assert expect_delay == result_delay


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_restore_delay_com_decrease_delay_e_pause_delay_ativado(player):
    [player.decrease_speed() for _ in range(10)]
    player.pause_delay()

    expect_delay = 0
    player.restore_delay()
    result_delay = player.delay

    assert expect_delay == result_delay


@pytest.mark.parametrize('player', [(list(range(0, 35)), 25)], indirect=True)
def test_player_control_restore_delay_com_decrease_delay_e_desativando_o_pause_delay(player):
    [player.decrease_speed() for _ in range(10)]
    player.pause_delay()

    expect_delay = player._PlayerControl__default_delay
    player.restore_delay()
    player.pause_delay()
    result_delay = player.delay

    assert expect_delay == result_delay


# ################## Teste do set_frame para FrameMapper vazio ######################### #
@pytest.mark.parametrize('player', [([], 25)], indirect=True)
def test_player_control_set_frame_com_0_frames(player):
    expect = None
    player.set_frame(0)
    result = player.frame_id
    assert expect == result


# ################## Teste do set_frame para 1 frame ######################### #
@pytest.mark.parametrize('player', [([1], 25)], indirect=True)
def test_player_control_set_frame_com_1_frames(player):
    expect = 1
    player.set_frame(1)
    player.read()
    result = player.frame_id
    assert expect == result


@pytest.mark.parametrize('player', [([1], 25)], indirect=True)
def test_player_control_set_frame_com_1_frames_com_rewind(player):
    expect = None
    player.rewind()
    player.set_frame(1)
    player.read()
    result = player.frame_id
    assert expect == result


# ################## Teste do set_frame para 2 frames ######################### #
@pytest.mark.parametrize('player', [([0, 1], 25)], indirect=True)
def test_player_control_set_frame_com_2_frames_no_ultimo_frame(player):
    expect = 1
    player.set_frame(1)
    player.read()
    result = player.frame_id
    assert expect == result


@pytest.mark.parametrize('player', [([0, 1], 25)], indirect=True)
def test_player_control_set_frame_com_2_frames_no_primeiro_frame(player):
    expect = 0
    player.set_frame(0)
    player.read()
    result = player.frame_id
    assert expect == result


@pytest.mark.parametrize('player', [([0, 1], 25)], indirect=True)
def test_player_control_set_frame_com_2_frames_no_ultimo_frame_com_rewind(player):
    expect = 0  # O VideoBufferLeft lé a partir de frame_id - 1
    player.rewind()
    player.set_frame(1)
    player.read()
    result = player.frame_id
    assert expect == result


@pytest.mark.parametrize('player', [([0, 1], 25)], indirect=True)
def test_player_control_set_frame_com_2_frames_no_primeiro_frame_com_rewind(player):
    expect = None
    player.rewind()
    player.set_frame(0)
    player.read()
    result = player.frame_id
    assert expect == result


# ################## Teste do set_frame para 3 frames ######################### #
@pytest.mark.parametrize('player', [([0, 1, 2], 25)], indirect=True)
def test_player_control_set_frame_com_3_frames_no_ultimo_frame(player):
    expect = 2
    player.set_frame(2)
    player.read()
    result = player.frame_id
    assert expect == result


@pytest.mark.parametrize('player', [([0, 1, 2], 25)], indirect=True)
def test_player_control_set_frame_com_3_frames_no_primeiro_frame(player):
    expect = 0
    player.set_frame(0)
    player.read()
    result = player.frame_id
    assert expect == result


@pytest.mark.parametrize('player', [([0, 1, 2], 25)], indirect=True)
def test_player_control_set_frame_com_3_frames_no_frame_do_meio(player):
    expect = 1
    player.set_frame(1)
    player.read()
    result = player.frame_id
    assert expect == result


@pytest.mark.parametrize('player', [([0, 1, 2], 25)], indirect=True)
def test_player_control_set_frame_com_3_frames_no_frame_do_meio_com_read_2x(player):
    expect = 2
    player.set_frame(1)
    [player.read() for _ in range(2)]
    result = player.frame_id
    assert expect == result


@pytest.mark.parametrize('player', [([0, 1, 2], 25)], indirect=True)
def test_player_control_set_frame_com_3_frames_no_frame_do_meio_com_read_3x(player):
    expect = None
    expect_is_complete = True
    player.set_frame(1)
    [player.read() for _ in range(3)]
    result = player.frame_id
    result_is_complete = player.servant.is_task_complete()
    assert expect == result
    assert expect_is_complete == result_is_complete


@pytest.mark.parametrize('player', [([0, 1, 2], 25)], indirect=True)
def test_player_control_set_frame_com_3_frames_no_ultimo_frame_com_rewind(player):
    expect = 1
    player.rewind()
    player.set_frame(2)
    player.read()
    result = player.frame_id
    assert expect == result


@pytest.mark.parametrize('player', [([0, 1, 2], 25)], indirect=True)
def test_player_control_set_frame_com_3_frames_no_ultimo_frame_com_rewind_com_read_2x(player):
    expect = 0
    player.rewind()
    player.set_frame(2)
    [player.read() for _ in range(2)]
    result = player.frame_id
    assert expect == result


@pytest.mark.parametrize('player', [([0, 1, 2], 25)], indirect=True)
def test_player_control_set_frame_com_3_frames_no_ultimo_frame_com_rewind_com_read_3x(player):
    expect = 0
    expect_is_complete = True
    player.rewind()
    player.set_frame(2)
    [player.read() for _ in range(2)]
    result = player.frame_id
    result_is_complete = player.servant.is_task_complete()
    assert expect == result
    assert expect_is_complete == result_is_complete


@pytest.mark.parametrize('player', [([0, 1, 2], 25)], indirect=True)
def test_player_control_set_frame_com_3_frames_no_primeiro_frame_com_rewind(player):
    expect = None
    player.rewind()
    player.set_frame(0)
    player.read()
    result = player.frame_id
    assert expect == result


# ######### Teste para o método restore_frame para o FrameMapper vazio ####################### #

@pytest.mark.undo
@pytest.mark.parametrize('pm', [([], 25)], indirect=True)
def test_player_control_restore_frame_com_o_FrameMapper_vazio_proceed(pm):
    player, mapping = pm
    frame_id, frame = (0, np.zeros((2, 2)))
    mapping.add(frame_id)

    expect = frame_id
    player.restore_frame(frame_id, frame)
    player.read()
    result = player.frame_id
    assert expect == result


@pytest.mark.undo
@pytest.mark.parametrize('pm', [([], 25)], indirect=True)
def test_player_control_restore_frame_com_o_FrameMapper_vazio_rewind(pm):
    player, mapping = pm
    frame_id, frame = (0, np.zeros((2, 2)))
    mapping.add(frame_id)

    expect = frame_id
    player.rewind()
    player.restore_frame(frame_id, frame)
    result = player.frame_id
    assert expect == result


# ######### Teste para o método restore_frame para 1 frame ####################### #

@pytest.mark.undo
@pytest.mark.parametrize('pm', [([0], 25)], indirect=True)
def test_player_control_restore_frame_com_1_frame_proceed_ultimo_frame(pm):
    player, mapping = pm
    frame_id, frame = (1, np.zeros((2, 2)))
    mapping.add(frame_id)

    expect = frame_id
    player.restore_frame(frame_id, frame)
    result = player.frame_id
    assert expect == result


@pytest.mark.undo
@pytest.mark.parametrize('pm', [([0], 25)], indirect=True)
def test_player_control_restore_frame_com_1_frame_rewind_ultimo_frame(pm):
    player, mapping = pm
    frame_id, frame = (1, np.zeros((2, 2)))
    mapping.add(frame_id)

    expect = frame_id
    player.rewind()
    player.restore_frame(frame_id, frame)
    result = player.frame_id
    assert expect == result


@pytest.mark.undo
@pytest.mark.parametrize('pm', [([1], 25)], indirect=True)
def test_player_control_restore_frame_com_1_frame_proceed_primeiro_frame(pm):
    player, mapping = pm
    frame_id, frame = (0, np.zeros((2, 2)))
    mapping.add(frame_id)

    expect = frame_id
    player.restore_frame(frame_id, frame)
    result = player.frame_id
    assert expect == result


@pytest.mark.undo
@pytest.mark.parametrize('pm', [([1], 25)], indirect=True)
def test_player_control_restore_frame_com_1_frame_rewind_primeiro_frame(pm):
    player, mapping = pm
    frame_id, frame = (0, np.zeros((2, 2)))
    mapping.add(frame_id)

    expect = frame_id
    player.rewind()
    player.restore_frame(frame_id, frame)
    result = player.frame_id
    assert expect == result


# ######### Teste para o método restore_frame para 2 frame ####################### #

@pytest.mark.undo
@pytest.mark.parametrize('pm', [([0, 1], 25)], indirect=True)
def test_player_control_restore_frame_com_2_frames_proceed_ultimo_frame(pm):
    player, mapping = pm
    frame_id, frame = (2, np.zeros((2, 2)))
    mapping.add(frame_id)

    expect = frame_id
    player.restore_frame(frame_id, frame)
    result = player.frame_id
    assert expect == result


@pytest.mark.undo
@pytest.mark.parametrize('pm', [([0, 1], 25)], indirect=True)
def test_player_control_restore_frame_com_2_frames_rewind_ultimo_frame(pm):
    player, mapping = pm
    frame_id, frame = (2, np.zeros((2, 2)))
    mapping.add(frame_id)

    expect = frame_id
    player.rewind()
    player.restore_frame(frame_id, frame)
    result = player.frame_id
    assert expect == result


@pytest.mark.undo
@pytest.mark.parametrize('pm', [([0, 2], 25)], indirect=True)
def test_player_control_restore_frame_com_2_frames_proceed_frame_do_meio(pm):
    player, mapping = pm
    frame_id, frame = (1, np.zeros((2, 2)))
    mapping.add(frame_id)

    expect = frame_id
    player.restore_frame(frame_id, frame)
    result = player.frame_id
    assert expect == result


@pytest.mark.undo
@pytest.mark.parametrize('pm', [([0, 2], 25)], indirect=True)
def test_player_control_restore_frame_com_2_frames_rewind_frame_do_meio(pm):
    player, mapping = pm
    frame_id, frame = (1, np.zeros((2, 2)))
    mapping.add(frame_id)

    expect = frame_id
    player.rewind()
    player.restore_frame(frame_id, frame)
    result = player.frame_id
    assert expect == result


@pytest.mark.undo
@pytest.mark.parametrize('pm', [([1, 2], 25)], indirect=True)
def test_player_control_restore_frame_com_2_frames_proceed_primeiro_frame(pm):
    player, mapping = pm
    frame_id, frame = (0, np.zeros((2, 2)))
    mapping.add(frame_id)

    expect = frame_id
    player.restore_frame(frame_id, frame)
    result = player.frame_id
    assert expect == result


@pytest.mark.undo
@pytest.mark.parametrize('pm', [([1, 2], 25)], indirect=True)
def test_player_control_restore_frame_com_2_frames_rewind_primeiro_frame(pm):
    player, mapping = pm
    frame_id, frame = (0, np.zeros((2, 2)))
    mapping.add(frame_id)

    expect = frame_id
    player.rewind()
    player.restore_frame(frame_id, frame)
    result = player.frame_id
    assert expect == result


# ######## Teste para o backward com FrameMapper sem frames ############### #
# Os testes para o _backward devem ser feitos em relação ao VideoBufferLeft
# usando o valor do fid

@pytest.mark.backward
@pytest.mark.parametrize('player', [([], 25)], indirect=True)
def test_player_control__backward_com_0_frames(player):
    expect = None
    player.read()
    player._backward(1)
    result = player.master[0]
    assert expect == result


# ######## Teste para o backward com 1 frames ############### #

@pytest.mark.backward
@pytest.mark.parametrize('player', [([0], 25)], indirect=True)
def test_player_control__backward_com_1_frames_com_proceed_frame_id_maior(player):
    expect = 0
    expect_servant = VideoBufferRight
    frame_id = 1

    [player.read() for _ in range(2)]
    player.proceed()
    player._backward(frame_id)
    result = player.master[0]
    assert expect == result
    assert isinstance(player.servant, expect_servant)


@pytest.mark.backward
@pytest.mark.parametrize('player', [([0], 25)], indirect=True)
def test_player_control__backward_com_1_frames_com_rewind_frame_id_maior(player):
    expect = 0  # Eh None pois nesse cenario a task já acabou
    expect_servant = VideoBufferLeft
    frame_id = 1

    [player.read() for _ in range(2)]
    player.rewind()
    player._backward(frame_id)
    result = player.servant[0]
    assert expect == result
    assert isinstance(player.servant, expect_servant)


@pytest.mark.backward
@pytest.mark.parametrize('player', [([0], 25)], indirect=True)
def test_player_control__backward_com_1_frames_com_rewind_frame_id_igual(player):
    expect = None  # Eh None pois nesse cenario a task já acabou
    expect_servant = VideoBufferLeft
    frame_id = 0

    [player.read() for _ in range(2)]
    player.rewind()
    player._backward(frame_id)
    result = player.servant[0]
    assert expect == result
    assert isinstance(player.servant, expect_servant)


@pytest.mark.backward
@pytest.mark.parametrize('player', [([0], 25)], indirect=True)
def test_player_control__backward_com_1_frames_com_proceed_frame_id_igual(player):
    expect = None
    expect_servant = VideoBufferRight
    frame_id = 0

    [player.read() for _ in range(2)]
    player.proceed()
    player._backward(frame_id)
    result = player.master[0]
    assert expect == result
    assert isinstance(player.servant, expect_servant)


# ######## Teste para o backward com 2 frames ############### #

@pytest.mark.backward
@pytest.mark.parametrize('player', [([0, 1], 25)], indirect=True)
def test_player_control__backward_com_2_frames_com_proceed_frame_id_maior(player):
    expect = 1
    expect_servant = VideoBufferRight
    frame_id = 2

    player.proceed()
    [player.read() for _ in range(3)]
    player._backward(frame_id)
    result = player.master[0]
    assert expect == result
    assert isinstance(player.servant, expect_servant)


@pytest.mark.backward
@pytest.mark.parametrize('player', [([0, 1], 25)], indirect=True)
def test_player_control__backward_com_2_frames_com_rewind_frame_id_maior(player):
    expect = 1
    expect_servant = VideoBufferLeft
    frame_id = 2

    [player.read() for _ in range(3)]
    player.rewind()
    player._backward(frame_id)
    result = player.servant[0]
    assert expect == result
    assert isinstance(player.servant, expect_servant)


@pytest.mark.backward
@pytest.mark.parametrize('player', [([0, 1], 25)], indirect=True)
def test_player_control__backward_com_2_frames_com_proceed_frame_id_igual(player):
    expect = None
    expect_servant = VideoBufferRight
    frame_id = 0

    player.proceed()
    [player.read() for _ in range(2)]
    player._backward(frame_id)
    result = player.master[0]
    assert expect == result
    assert isinstance(player.servant, expect_servant)


@pytest.mark.backward
@pytest.mark.parametrize('player', [([0, 1], 25)], indirect=True)
def test_player_control__backward_com_2_frames_com_rewind_frame_id_igual(player):
    expect = None
    expect_servant = VideoBufferLeft
    frame_id = 0

    [player.read() for _ in range(2)]
    player.rewind()
    player._backward(frame_id)
    result = player.servant[0]
    assert expect == result
    assert isinstance(player.servant, expect_servant)


@pytest.mark.backward
@pytest.mark.parametrize('player', [([1, 2], 25)], indirect=True)
def test_player_control__backward_com_2_frames_com_proceed_frame_id_menor(player):
    expect = None
    expect_servant = VideoBufferRight
    frame_id = 0

    player.proceed()
    [player.read() for _ in range(2)]
    player._backward(frame_id)
    result = player.master[0]
    assert expect == result
    assert isinstance(player.servant, expect_servant)


@pytest.mark.backward
@pytest.mark.parametrize('player', [([1, 2], 25)], indirect=True)
def test_player_control__backward_com_2_frames_com_rewind_frame_id_menor(player):
    expect = None
    expect_servant = VideoBufferLeft
    frame_id = 0

    [player.read() for _ in range(2)]
    player.rewind()
    player._backward(frame_id)
    result = player.servant[0]
    assert expect == result
    assert isinstance(player.servant, expect_servant)


# ######## Teste para o backward com 3 frames ############### #

@pytest.mark.backward
@pytest.mark.parametrize('player', [([0, 1, 2], 25)], indirect=True)
def test_player_control__backward_com_3_frames_com_proceed_frame_id_maior(player):
    expect = 2
    expect_servant = VideoBufferRight
    frame_id = 3

    player.proceed()
    [player.read() for _ in range(4)]
    player._backward(frame_id)
    result = player.master[0]
    assert expect == result
    assert isinstance(player.servant, expect_servant)


@pytest.mark.backward
@pytest.mark.parametrize('player', [([0, 1, 2], 25)], indirect=True)
def test_player_control__backward_com_3_frames_com_rewind_frame_id_maior(player):
    expect = 2
    expect_servant = VideoBufferLeft
    frame_id = 3

    [player.read() for _ in range(4)]
    player.rewind()
    player._backward(frame_id)
    result = player.servant[0]
    assert expect == result
    assert isinstance(player.servant, expect_servant)


@pytest.mark.backward
@pytest.mark.parametrize('player', [([0, 1, 2], 25)], indirect=True)
def test_player_control__backward_com_3_frames_com_proceed_frame_id_igual(player):
    expect = None
    expect_servant = VideoBufferRight
    frame_id = 0

    player.proceed()
    [player.read() for _ in range(3)]
    player._backward(frame_id)
    result = player.master[0]
    assert expect == result
    assert isinstance(player.servant, expect_servant)


@pytest.mark.backward
@pytest.mark.parametrize('player', [([0, 1, 2], 25)], indirect=True)
def test_player_control__backward_com_3_frames_com_rewind_frame_id_igual(player):
    expect = None
    expect_servant = VideoBufferLeft
    frame_id = 0

    [player.read() for _ in range(3)]
    player.rewind()
    player._backward(frame_id)
    result = player.servant[0]
    assert expect == result
    assert isinstance(player.servant, expect_servant)


@pytest.mark.backward
@pytest.mark.parametrize('player', [([1, 2, 3], 25)], indirect=True)
def test_player_control__backward_com_3_frames_com_proceed_frame_id_menor(player):
    expect = None
    expect_servant = VideoBufferRight
    frame_id = 0

    player.proceed()
    [player.read() for _ in range(3)]
    player._backward(frame_id)
    result = player.master[0]
    assert expect == result
    assert isinstance(player.servant, expect_servant)


@pytest.mark.backward
@pytest.mark.parametrize('player', [([1, 2, 3], 25)], indirect=True)
def test_player_control__backward_com_3_frames_com_rewind_frame_id_menor(player):
    expect = None
    expect_servant = VideoBufferLeft
    frame_id = 0

    [player.read() for _ in range(3)]
    player.rewind()
    player._backward(frame_id)
    result = player.servant[0]
    assert expect == result
    assert isinstance(player.servant, expect_servant)


@pytest.mark.backward
@pytest.mark.parametrize('player', [([1, 3, 4], 25)], indirect=True)
def test_player_control__backward_com_3_frames_com_rewind_frame_id_meio(player):
    expect = 1
    expect_servant = VideoBufferLeft
    frame_id = 2

    [player.read() for _ in range(3)]
    player.rewind()
    player._backward(frame_id)
    result = player.servant[0]
    assert expect == result
    assert isinstance(player.servant, expect_servant)


@pytest.mark.backward
@pytest.mark.parametrize('player', [([1, 3, 4], 25)], indirect=True)
def test_player_control__backward_com_3_frames_com_proceed_frame_id_meio(player):
    expect = 1
    expect_servant = VideoBufferRight
    frame_id = 2

    player.proceed()
    [player.read() for _ in range(3)]
    player._backward(frame_id)
    result = player.master[0]
    assert expect == result
    assert isinstance(player.servant, expect_servant)


# ############# Testes para o método _forward 0 frames ################### #
# Usar o VideoBufferLeft para fazer o testes de valores

@pytest.mark.forward
@pytest.mark.parametrize('player', [([], 25)], indirect=True)
def test_player_control__forward_com_0_frames(player):
    expect = None
    frame_id = 0

    player.read()
    player.proceed()
    player._forward(frame_id)
    result = player.master[0]
    assert expect == result


# ############# Testes para o método _forward 1 frames ################### #

@pytest.mark.forward
@pytest.mark.parametrize('player', [([0], 25)], indirect=True)
def test_player_control__forward_com_1_frames_com_frame_id_maior(player):
    expect = 0
    frame_id = 1

    player.servant.run()
    player.servant._buffer.unqueue()
    player._forward(frame_id)
    result = player.master[0]
    assert expect == result


@pytest.mark.forward
@pytest.mark.parametrize('player', [([1], 25)], indirect=True)
def test_player_control__forward_com_1_frames_com_frame_id_menor(player):
    expect = None
    frame_id = 0

    player.servant.run()
    player.servant._buffer.unqueue()
    player._forward(frame_id)
    result = player.master[0]
    assert expect == result


@pytest.mark.forward
@pytest.mark.parametrize('player', [([0], 25)], indirect=True)
def test_player_control__forward_com_1_frames_com_frame_id_igual(player):
    expect = 0
    frame_id = 0

    player.servant.run()
    player.servant._buffer.unqueue()
    player._forward(frame_id)
    result = player.master[0]
    assert expect == result


# ############# Testes para o método _forward 2 frames ################### #

@pytest.mark.forward
@pytest.mark.parametrize('player', [([0, 1], 25)], indirect=True)
def test_player_control__forward_com_2_frames_com_frame_id_maior(player):
    expect = 1
    frame_id = 2

    player.servant.run()
    player.servant._buffer.unqueue()
    player._forward(frame_id)
    result = player.master[0]
    assert expect == result


@pytest.mark.forward
@pytest.mark.parametrize('player', [([1, 2], 25)], indirect=True)
def test_player_control__forward_com_2_frames_com_frame_id_menor(player):
    expect = None
    frame_id = 0

    player.servant.run()
    player.servant._buffer.unqueue()
    player._forward(frame_id)
    result = player.master[0]
    assert expect == result


@pytest.mark.dev0
@pytest.mark.forward
@pytest.mark.parametrize('player', [([0, 1], 25)], indirect=True)
def test_player_control__forward_com_2_frames_com_frame_id_igual(player):
    expect = 1
    frame_id = 1

    player.servant.run()
    player.servant._buffer.unqueue()
    player._forward(frame_id)
    result = player.master[0]
    assert expect == result


# ############# Testes para o método _forward 3 frames ################### #

@pytest.mark.forward
@pytest.mark.parametrize('player', [([0, 1, 2], 25)], indirect=True)
def test_player_control__forward_com_3_frames_com_frame_id_maior(player):
    expect = 2
    frame_id = 3

    player.servant.run()
    player.servant._buffer.unqueue()
    player._forward(frame_id)
    result = player.master[0]
    assert expect == result


@pytest.mark.forward
@pytest.mark.parametrize('player', [([1, 2, 3], 25)], indirect=True)
def test_player_control__forward_com_3_frames_com_frame_id_menor(player):
    expect = None
    frame_id = 0

    player.servant.run()
    player.servant._buffer.unqueue()
    player._forward(frame_id)
    result = player.master[0]
    assert expect == result


@pytest.mark.forward
@pytest.mark.parametrize('player', [([0, 1, 2], 25)], indirect=True)
def test_player_control__forward_com_3_frames_com_frame_id_igual(player):
    expect = 2
    frame_id = 2

    player.servant.run()
    player.servant._buffer.unqueue()
    player._forward(frame_id)
    result = player.master[0]
    assert expect == result


@pytest.mark.forward
@pytest.mark.parametrize('player', [([0, 1, 3], 25)], indirect=True)
def test_player_control__forward_com_3_frames_com_frame_id_meio(player):
    expect = 1
    frame_id = 2

    player.servant.run()
    player.servant._buffer.unqueue()
    player._forward(frame_id)
    result = player.master[0]
    assert expect == result


# ############# Testes para o método _forward 10 frames ################### #

@pytest.mark.forward
@pytest.mark.parametrize('player', [([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 25)], indirect=True)
def test_player_control__forward_com_10_frames_com_frame_id_maior(player):
    expect = 10
    frame_id = 11

    player.servant.run()
    player.servant._buffer.unqueue()
    player._forward(frame_id)
    result = player.master[0]
    assert expect == result


@pytest.mark.forward
@pytest.mark.parametrize('player', [([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 25)], indirect=True)
def test_player_control__forward_com_10_frames_com_frame_id_igual(player):
    expect = 8
    frame_id = 8

    player.servant.run()
    player.servant._buffer.unqueue()
    player._forward(frame_id)
    result = player.master[0]
    assert expect == result


@pytest.mark.forward
@pytest.mark.parametrize('player', [([0, 1, 2, 3, 4, 5, 6, 8, 9, 10], 25)], indirect=True)
def test_player_control__forward_com_10_frames_com_frame_id_meio(player):
    expect = 6
    frame_id = 7

    player.servant.run()
    player.servant._buffer.unqueue()
    player._forward(frame_id)
    result = player.master[0]
    assert expect == result


# ########### Testes do _is_valid_backward para 0 frames ############ #

@pytest.mark.backward
@pytest.mark.parametrize('player', [([], 25)], indirect=True)
def test_player_control__is_valid_backward_com_0_frames(player):
    expect = False

    result = player._is_valid_backward(0)
    assert expect == result


# ########### Testes do _is_valid_backward para 1 frame ############ #

@pytest.mark.backward
@pytest.mark.parametrize('player', [([1], 25)], indirect=True)
def test_player_control__is_valid_backward_com_1_frame_com_frame_id_menor(player):
    expect = True

    [player.read() for _ in range(2)]
    result = player._is_valid_backward(0)
    assert expect == result


@pytest.mark.backward
@pytest.mark.parametrize('player', [([1], 25)], indirect=True)
def test_player_control__is_valid_backward_com_1_frame_com_frame_id_igual(player):
    expect = False

    [player.read() for _ in range(2)]
    result = player._is_valid_backward(1)
    assert expect == result


@pytest.mark.backward
@pytest.mark.parametrize('player', [([1], 25)], indirect=True)
def test_player_control__is_valid_backward_com_1_frame_com_frame_id_maior(player):
    expect = False

    [player.read() for _ in range(2)]
    result = player._is_valid_backward(2)
    assert expect == result


# ########### Testes do _is_valid_backward para 2 frame ############ #

@pytest.mark.backward
@pytest.mark.parametrize('player', [([1, 2], 25)], indirect=True)
def test_player_control__is_valid_backward_com_2_frames_com_frame_id_menor(player):
    expect = True

    [player.read() for _ in range(3)]
    result = player._is_valid_backward(0)
    assert expect == result


@pytest.mark.backward
@pytest.mark.parametrize('player', [([1, 2], 25)], indirect=True)
def test_player_control__is_valid_backward_com_2_frames_com_frame_id_igual(player):
    expect = True

    [player.read() for _ in range(3)]
    result = player._is_valid_backward(1)
    assert expect == result


@pytest.mark.backward
@pytest.mark.parametrize('player', [([1, 2], 25)], indirect=True)
def test_player_control__is_valid_backward_com_2_frames_com_frame_id_maior(player):
    expect = False

    [player.read() for _ in range(3)]
    result = player._is_valid_backward(3)
    assert expect == result


# ########### Testes do _is_valid_backward para 2 frame ############ #

@pytest.mark.backward
@pytest.mark.parametrize('player', [([1, 2, 3], 25)], indirect=True)
def test_player_control__is_valid_backward_com_3_frames_com_frame_id_menor(player):
    expect = True

    [player.read() for _ in range(4)]
    result = player._is_valid_backward(0)
    assert expect == result


@pytest.mark.backward
@pytest.mark.parametrize('player', [([1, 2, 3], 25)], indirect=True)
def test_player_control__is_valid_backward_com_3_frames_com_frame_id_igual(player):
    expect = True

    [player.read() for _ in range(4)]
    result = player._is_valid_backward(1)
    assert expect == result


@pytest.mark.backward
@pytest.mark.parametrize('player', [([1, 2, 3], 25)], indirect=True)
def test_player_control__is_valid_backward_com_3_frames_com_frame_id_maior(player):
    expect = False

    [player.read() for _ in range(4)]
    result = player._is_valid_backward(3)
    assert expect == result


@pytest.mark.backward
@pytest.mark.parametrize('player', [([1, 3, 4], 25)], indirect=True)
def test_player_control__is_valid_backward_com_3_frames_com_frame_id_meio(player):
    expect = True

    [player.read() for _ in range(4)]
    result = player._is_valid_backward(3)
    assert expect == result
