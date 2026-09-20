from threading import Semaphore
from unittest.mock import patch

import numpy as np
import pytest
from pytest import fixture

from aniseek.core.buffer_left import VideoBufferLeft
from aniseek.core.buffer_right import VideoBufferRight
from aniseek.core.frame_mapper import FrameMapper
from aniseek.editing.manager import VideoManager
from aniseek.editing.player_control import PlayerControl
from aniseek.editing.playlist import Playlist
from aniseek.editing.trash import Trash
from aniseek.view.video_command import (
    ProceesCommand,
    RemoveFrameCommand,
    RewindCommand,
    UndoFrameCommand,
)
from aniseek.view.video_controller import FakeVideoController as VideoController
from tests.uteis import MyVideoCapture


def lote(start, end, step=1):
    return [(frame_id, np.zeros((2, 2))) for frame_id in range(start, end, step)]


@fixture
def mycap():
    with patch('cv2.VideoCapture', return_value=MyVideoCapture()) as mock:
        yield mock


@fixture
def video(mycap, request):
    frames_mapping, buffersize, frame_count, log = request.param
    log = False
    with patch('aniseek.core.sources.opencv.cv2.VideoCapture', return_value=MyVideoCapture()) as _:
        with patch('aniseek.editing.section.SectionManager.get_mapping', return_value=frames_mapping) as _:
            manager = VideoManager(buffersize, log)
            playlist = Playlist(['video-01.mp4'])
            video = VideoController(playlist, frames_mapping, manager)
            yield video

    video.join()


@fixture
def orch_100(mycap, frame_count=100, buffersize=25, log=False):
    cap = mycap.return_value
    semaphore = Semaphore()

    mapping = FrameMapper(list(range(frame_count)), frame_count=frame_count)
    master = VideoBufferLeft(cap, mapping, semaphore, buffersize=buffersize, bufferlog=log, name='left')
    servant = VideoBufferRight(cap, mapping, semaphore, buffersize=buffersize, bufferlog=log, name='right')
    player_control = PlayerControl(servant, master)
    _trash = Trash(cap, semaphore, frame_count=frame_count, buffersize=5)
    yield (player_control, mapping, _trash)
    _trash.join()
    master.join()
    servant.join()


@fixture
def orch_200(mycap, frame_count=200, buffersize=25, log=False):
    cap = mycap.return_value
    semaphore = Semaphore()

    mapping = FrameMapper(list(range(frame_count)), frame_count=frame_count)
    master = VideoBufferLeft(cap, mapping, semaphore, buffersize=buffersize, bufferlog=log, name='left')
    servant = VideoBufferRight(cap, mapping, semaphore, buffersize=buffersize, bufferlog=log, name='right')
    player_control = PlayerControl(servant, master)
    _trash = Trash(cap, semaphore, frame_count=frame_count, buffersize=5)
    yield (player_control, mapping, _trash)
    _trash.join()
    master.join()
    servant.join()


# ######### Teste do RewindCommand Sem frames ###################################

@pytest.mark.parametrize('video', [([], 25, 100, False)], indirect=True)
def test_RewindCommand_sem_frames(video):
    rewind = RewindCommand(video)
    rewind.executor()
    assert isinstance(video.player.servant, VideoBufferLeft)


@pytest.mark.parametrize('video', [([], 25, 100, False)], indirect=True)
def test_RewindCommand_sem_frames_com_read(video):
    rewind = RewindCommand(video)

    expect = False
    rewind.executor()
    result, _ = video.read()
    assert expect == result


@pytest.mark.parametrize('video', [([], 25, 100, False)], indirect=True)
def test_RewindCommand_sem_frames_com_a_seguinte_sequencia_rewind_proceed_rewind(video):
    rewind = RewindCommand(video)
    procees = ProceesCommand(video)

    expect = False
    rewind.executor()
    procees.executor()
    rewind.executor()
    result, _ = video.read()
    assert expect == result


# ######### Teste do RewindCommand com 1 frame #####################################

@pytest.mark.parametrize('video', [([], 25, 100, False)], indirect=True)
def test_RewindCommand_com_1_frame(video):
    RewindCommand(video)
    video.rewind()
    assert isinstance(video.player.servant, VideoBufferLeft)


@pytest.mark.parametrize('video', [([0], 25, 100, False)], indirect=True)
def test_RewindCommand_com_1_frame_com_read(video):
    rewind = RewindCommand(video)
    expect = False
    rewind.executor()
    result, _ = video.read()
    assert expect == result


@pytest.mark.parametrize('video', [([0], 25, 100, False)], indirect=True)
def test_RewindCommand_com_1_frame_com_a_seguinte_sequencia_rewind_proceed_rewind(video):
    rewind = RewindCommand(video)
    procees = ProceesCommand(video)

    expect = False
    rewind.executor()
    procees.executor()
    rewind.executor()
    result, _ = video.read()
    assert expect == result


# ######### Teste do RewindCommand com 2 frame #####################################

@pytest.mark.parametrize('video', [([0, 1], 25, 100, False)], indirect=True)
def test_RewindCommand_com_2_frames(video):
    RewindCommand(video)
    video.rewind()
    assert isinstance(video.player.servant, VideoBufferLeft)


@pytest.mark.parametrize('video', [([0, 1], 25, 100, False)], indirect=True)
def test_RewindCommand_com_2_frames_com_read(video):
    rewind = RewindCommand(video)
    expect = False
    rewind.executor()
    result, _ = video.read()
    assert expect == result


@pytest.mark.parametrize('video', [([0, 1], 25, 100, False)], indirect=True)
def test_RewindCommand_com_2_frames_com_a_seguinte_sequencia_rewind_proceed_rewind(video):
    rewind = RewindCommand(video)
    procees = ProceesCommand(video)

    expect = False
    rewind.executor()
    procees.executor()
    rewind.executor()
    result, _ = video.read()
    assert expect == result


@pytest.mark.parametrize('video', [([0, 1], 25, 100, False)], indirect=True)
def test_RewindCommand_com_2_frames_com_set_antes_do_executor(video):
    rewind = RewindCommand(video)
    procees = ProceesCommand(video)
    video.player.servant.set(1)
    video.player.master.set(1)

    expect = True
    rewind.executor()
    procees.executor()
    rewind.executor()
    result, _ = video.read()
    assert expect == result


@pytest.mark.parametrize('video', [([0, 1], 25, 100, False)], indirect=True)
def test_RewindCommand_com_2_frames_com_set_antes_do_executor_com_read(video):
    rewind = RewindCommand(video)
    procees = ProceesCommand(video)
    video.player.servant.set(1)
    video.player.master.set(1)

    expect = False
    rewind.executor()
    procees.executor()
    rewind.executor()
    result, _ = video.read()
    result, _ = video.read()
    assert expect == result


# ######### Teste do RewindCommand com 3 frames #####################################

@pytest.mark.parametrize('video', [([0, 1, 2], 25, 100, False)], indirect=True)
def test_RewindCommand_com_3_frames(video):
    RewindCommand(video)
    video.rewind()
    assert isinstance(video.player.servant, VideoBufferLeft)


@pytest.mark.parametrize('video', [([0, 1, 2], 25, 100, False)], indirect=True)
def test_RewindCommand_com_3_frames_com_read(video):
    rewind = RewindCommand(video)
    expect = False
    rewind.executor()
    result, _ = video.read()
    assert expect == result


@pytest.mark.parametrize('video', [([0, 1, 2], 25, 100, False)], indirect=True)
def test_RewindCommand_com_3_frames_com_a_seguinte_sequencia_rewind_proceed_rewind(video):
    rewind = RewindCommand(video)
    procees = ProceesCommand(video)

    rewind.executor()
    procees.executor()
    rewind.executor()
    assert isinstance(video.player.servant, VideoBufferLeft)


@pytest.mark.parametrize('video', [([0, 1, 2], 25, 100, False)], indirect=True)
def test_RewindCommand_com_3_frames_com_set_antes_do_executor(video):
    rewind = RewindCommand(video)
    procees = ProceesCommand(video)
    video.player.servant.set(2)
    video.player.master.set(2)

    expect = True
    rewind.executor()
    procees.executor()
    rewind.executor()
    result, _ = video.read()
    assert expect == result


@pytest.mark.parametrize('video', [([0, 1, 2], 25, 100, False)], indirect=True)
def test_RewindCommand_com_3_frames_com_set_antes_do_executor_com_2_read(video):
    rewind = RewindCommand(video)
    procees = ProceesCommand(video)
    video.player.servant.set(2)
    video.player.master.set(2)

    expect = True
    rewind.executor()
    procees.executor()
    rewind.executor()
    result, _ = video.read()
    result, _ = video.read()
    assert expect == result


@pytest.mark.parametrize('video', [([0, 1, 2], 25, 100, False)], indirect=True)
def test_RewindCommand_com_3_frames_com_set_antes_do_executor_com_3_read(video):
    rewind = RewindCommand(video)
    procees = ProceesCommand(video)
    video.player.servant.set(2)
    video.player.master.set(2)

    expect = False
    rewind.executor()
    procees.executor()
    rewind.executor()
    result, _ = video.read()
    result, _ = video.read()
    result, _ = video.read()
    assert expect == result


# ####### Testes do RemoveFrameCommand com servant VideoBufferRight como padrão ###### #

# ####### Teste para o FrameMapper vazio ####################################

#  lote, buffersize, frame_count, log = request.param
@pytest.mark.parametrize('video', [([], 25, 100, False)], indirect=True)
def test_RemoveFrameCommand_removendo_frame_com_frame_mapper_vazio(video):
    remove = RemoveFrameCommand(video)
    video.read()
    remove.executor()

    expect_frame_id = None
    video.read()
    result_frame_id = video.frame_id
    assert expect_frame_id == result_frame_id


# ####### Teste para o FrameMapper com 1 frame ####################################

@pytest.mark.parametrize('video', [([0], 25, 100, False)], indirect=True)
def test_RemoveFrameCommand_removendo_frame_com_1_frame_no_frame_mapper(video):
    remove = RemoveFrameCommand(video)
    video.read()
    remove.executor()

    expect_frame_id = None
    expect_VideoBufferLeft_servant = True

    # Como é o último frame deve ocorrer um swap entre os buffers
    video.read()
    result_frame_id = video.frame_id
    result_VideoBufferLeft = isinstance(video.player.servant, VideoBufferLeft)
    assert expect_frame_id == result_frame_id
    assert expect_VideoBufferLeft_servant == result_VideoBufferLeft


@pytest.mark.parametrize('video', [([0], 25, 100, False)], indirect=True)
def test_RemoveFrameCommand_removendo_frame_com_1_frame_no_frame_mapper_com_rewind(video):
    remove = RemoveFrameCommand(video)
    video.player.read()
    video.player.rewind()
    remove.executor()

    expect_frame_id = None
    expect_VideoBufferLeft_servant = False

    # Como é o último frame deve ocorrer um swap entre os buffers
    video.read()
    result_frame_id = video.frame_id
    result_VideoBufferLeft = isinstance(video.player.servant, VideoBufferLeft)
    assert expect_frame_id == result_frame_id
    assert expect_VideoBufferLeft_servant == result_VideoBufferLeft


# ####### Teste para o FrameMapper com 2 frames ####################################

@pytest.mark.parametrize('video', [([0, 1], 25, 100, False)], indirect=True)
def test_RemoveFrameCommand_removendo_frame_com_2_frame_no_frame_mapper(video):
    remove = RemoveFrameCommand(video)
    video.read()
    remove.executor()

    expect_frame_id = 1
    expect_VideoBufferLeft_servant = True

    video.read()
    result_frame_id = video.frame_id
    result_VideoBufferRight = isinstance(video.player.servant, VideoBufferRight)
    assert expect_frame_id == result_frame_id
    assert expect_VideoBufferLeft_servant == result_VideoBufferRight


@pytest.mark.parametrize('video', [([0, 1], 25, 100, False)], indirect=True)
def test_RemoveFrameCommand_removendo_frame_com_2_frame_no_frame_mapper_removendo_2x(video):
    remove = RemoveFrameCommand(video)
    for _ in range(2):
        video.read()
        remove.executor()

    expect_frame_id = None
    expect_servant = True

    video.read()
    result_frame_id = video.player.frame_id
    result_servant = isinstance(video.player.servant, VideoBufferLeft)
    assert expect_frame_id == result_frame_id
    assert expect_servant == result_servant


@pytest.mark.parametrize('video', [([0, 1], 25, 100, False)], indirect=True)
def test_RemoveFrameCommand_removendo_frame_com_2_frame_no_frame_mapper_removendo_1x_com_rewind(video):
    remove = RemoveFrameCommand(video)
    [video.read() for _ in range(3)]
    video.rewind()

    video.read()
    remove.executor()

    expect_frame_id = 0

    video.read()
    result_frame_id = video.frame_id
    assert expect_frame_id == result_frame_id
    assert isinstance(video.player.servant, VideoBufferLeft)


@pytest.mark.parametrize('video', [([0, 1], 25, 100, False)], indirect=True)
def test_RemoveFrameCommand_removendo_frame_com_2_frame_no_frame_mapper_removendo_2x_com_rewind(video):
    remove = RemoveFrameCommand(video)
    [video.read() for _ in range(3)]
    video.rewind()
    for _ in range(2):
        video.read()
        remove.executor()

    expect_frame_id = None
    expect_servant = False

    video.read()
    result_frame_id = video.frame_id
    result_servant = isinstance(video.player.servant, VideoBufferLeft)
    assert expect_frame_id == result_frame_id
    assert expect_servant == result_servant


# ####### Teste para o FrameMapper com 3 frames ####################################

@pytest.mark.parametrize('video', [([0, 1, 2], 25, 100, False)], indirect=True)
def test_RemoveFrameCommand_removendo_frame_com_3_frame_no_frame_mapper(video):
    remove = RemoveFrameCommand(video)
    video.read()
    remove.executor()

    video.read()
    expect_frame_id = 1
    result_frame_id = video.frame_id

    assert expect_frame_id == result_frame_id
    assert isinstance(video.player.servant, VideoBufferRight)


@pytest.mark.parametrize('video', [([0, 1, 2], 25, 100, False)], indirect=True)
def test_RemoveFrameCommand_removendo_frame_com_3_frame_no_frame_mapper_removendo_2x(video):
    remove = RemoveFrameCommand(video)
    for _ in range(2):
        video.read()
        remove.executor()

    video.read()
    expect_frame_id = 2
    result_frame_id = video.frame_id

    assert expect_frame_id == result_frame_id
    assert isinstance(video.player.servant, VideoBufferRight)


@pytest.mark.parametrize('video', [([0, 1, 2], 25, 100, False)], indirect=True)
def test_RemoveFrameCommand_removendo_frame_com_3_frame_no_frame_mapper_removendo_3x(video):
    remove = RemoveFrameCommand(video)
    for _ in range(3):
        video.read()
        remove.executor()

    video.read()
    expect_frame_id = None
    result_frame_id = video.frame_id

    assert expect_frame_id == result_frame_id
    assert isinstance(video.player.servant, VideoBufferLeft)


@pytest.mark.parametrize('video', [([0, 1, 2], 25, 100, False)], indirect=True)
def test_RemoveFrameCommand_removendo_frame_com_3_frame_no_frame_mapper_removendo_1x_com_rewind(video):
    remove = RemoveFrameCommand(video)
    [video.read() for _ in range(4)]
    video.rewind()

    video.read()
    remove.executor()

    video.read()
    expect_frame_id = 1
    result_frame_id = video.frame_id

    assert expect_frame_id == result_frame_id
    assert isinstance(video.player.servant, VideoBufferLeft)


@pytest.mark.parametrize('video', [([0, 1, 2], 25, 100, False)], indirect=True)
def test_RemoveFrameCommand_removendo_frame_com_3_frame_no_frame_mapper_removendo_2x_com_rewind(video):

    remove = RemoveFrameCommand(video)
    [video.read() for _ in range(4)]
    video.rewind()
    for _ in range(2):
        video.read()
        remove.executor()

    video.read()
    expect_frame_id = 0
    result_frame_id = video.frame_id

    assert expect_frame_id == result_frame_id
    assert isinstance(video.player.servant, VideoBufferLeft)


@pytest.mark.parametrize('video', [([0, 1, 2], 25, 100, False)], indirect=True)
def test_RemoveFrameCommand_removendo_frame_com_3_frame_no_frame_mapper_removendo_3x_com_rewind(video):
    remove = RemoveFrameCommand(video)
    [video.read() for _ in range(4)]
    video.rewind()
    for _ in range(3):
        video.read()
        remove.executor()

    video.read()
    expect_frame_id = None
    result_frame_id = video.frame_id

    assert expect_frame_id == result_frame_id
    assert isinstance(video.player.servant, VideoBufferRight)


@pytest.mark.parametrize('video', [([0, 1, 2], 25, 100, False)], indirect=True)
def test_RemoveFrameCommand_removendo_frame_com_3_frame_no_frame_mapper_removendo_frame_do_meio_1x(video):
    remove = RemoveFrameCommand(video)
    [video.read() for _ in range(2)]
    remove.executor()

    video.read()
    expect_frame_id = 2
    result_frame_id = video.frame_id

    assert expect_frame_id == result_frame_id
    assert isinstance(video.player.servant, VideoBufferRight)


@pytest.mark.parametrize('video', [([0, 1, 2], 25, 100, False)], indirect=True)
def test_RemoveFrameCommand_removendo_frame_com_3_frame_no_frame_mapper_removendo_frame_do_meio_2x(video):
    remove = RemoveFrameCommand(video)
    video.read()
    for _ in range(2):
        video.read()
        remove.executor()

    video.read()
    expect_frame_id = 0
    result_frame_id = video.frame_id

    assert expect_frame_id == result_frame_id
    assert isinstance(video.player.servant, VideoBufferLeft)


@pytest.mark.parametrize('video', [([0, 1, 2], 25, 100, False)], indirect=True)
def test_RemoveFrameCommand_removendo_frame_com_3_frame_no_frame_mapper_removendo_frame_do_meio_3x(video):

    remove = RemoveFrameCommand(video)
    video.read()
    for _ in range(3):
        video.read()
        remove.executor()

    video.read()
    expect_frame_id = None
    result_frame_id = video.frame_id

    assert expect_frame_id == result_frame_id
    assert isinstance(video.player.servant, VideoBufferRight)


@pytest.mark.parametrize('video', [([0, 1, 2], 25, 100, False)], indirect=True)
def test_RemoveFrameCommand_removendo_frame_com_3_frame_no_frame_mapper_removendo_frame_do_meio_1x_com_rewind(video):
    remove = RemoveFrameCommand(video)
    [video.read() for _ in range(2)]
    video.rewind()
    remove.executor()

    video.read()
    expect_frame_id = 0
    result_frame_id = video.frame_id

    assert expect_frame_id == result_frame_id
    assert isinstance(video.player.servant, VideoBufferLeft)


@pytest.mark.parametrize('video', [([0, 1, 2], 25, 100, False)], indirect=True)
def test_RemoveFrameCommand_removendo_frame_com_3_frame_no_frame_mapper_removendo_frame_do_meio_2x_com_rewind(video):
    remove = RemoveFrameCommand(video)
    [video.read() for _ in range(2)]
    video.rewind()
    for _ in range(2):
        video.read()
        remove.executor()

    video.read()
    expect_frame_id = 2
    result_frame_id = video.frame_id

    assert expect_frame_id == result_frame_id
    assert isinstance(video.player.servant, VideoBufferRight)


@pytest.mark.parametrize('video', [([0, 1, 2], 25, 100, False)], indirect=True)
def test_RemoveFrameCommand_removendo_frame_com_3_frame_no_frame_mapper_removendo_frame_do_meio_3x_com_rewind(video):

    remove = RemoveFrameCommand(video)
    [video.read() for _ in range(2)]
    video.rewind()
    for _ in range(3):
        video.read()
        remove.executor()

    video.read()
    expect_frame_id = None
    result_frame_id = video.frame_id

    assert expect_frame_id == result_frame_id
    assert isinstance(video.player.servant, VideoBufferLeft)


@pytest.mark.parametrize('video', [(list(range(100)), 25, 100, False)], indirect=True)
def test_RemoveFrameCommand_removendo_frame_0_com_servant_VideoBufferRight(video):
    video.read()
    remove = RemoveFrameCommand(video)
    remove.executor()

    video.read()
    expect_frame_id = 1
    result_frame_id = video.frame_id

    assert expect_frame_id == result_frame_id


@pytest.mark.parametrize('video', [(list(range(100)), 25, 100, False)], indirect=True)
def test_RemoveFrameCommand_removendo_ultimo_frame_com_servant_VideoBufferRight(video):

    video.player.servant.set(99)
    video.player.master.set(99)
    video.read()
    remove = RemoveFrameCommand(video)
    remove.executor()

    video.read()
    expect_frame_id = 98
    result_frame_id = video.frame_id

    assert expect_frame_id == result_frame_id
    assert isinstance(video.player.servant, VideoBufferLeft)


@pytest.mark.parametrize('video', [(list(range(100)), 25, 100, False)], indirect=True)
def test_RemoveFrameCommand_removendo_frame_do_meio_com_servant_VideoBufferRight(video):
    video.player.servant.set(50)
    video.player.master.set(50)
    video.read()
    remove = RemoveFrameCommand(video)
    remove.executor()

    video.read()
    expect_frame_id = 51
    result_frame_id = video.frame_id

    assert expect_frame_id == result_frame_id
    assert isinstance(video.player.servant, VideoBufferRight)


@pytest.mark.parametrize('video', [(list(range(100)), 25, 100, False)], indirect=True)
def test_RemoveFrameCommand_removendo_todos_os_frames_desde_o_inicio_com_servant_VideoBufferRight(video):
    remove = RemoveFrameCommand(video)
    video.player.servant.set(50)
    video.player.master.set(50)
    while not video.player.servant.is_task_complete():
        video.read()
        remove.executor()

    # Aqui ocorre duas trocas de buffers, a primeira ao atingir a extremidade direita,
    # a segunda ao atingir a extremidade da esquerda, portanto o buffer do final é o da direita
    # por isso o expect_buffer deve ser falso
    video.read()
    expect_is_task_complete = True
    result_is_task_complet = video.player.servant.is_task_complete()
    assert expect_is_task_complete == result_is_task_complet
    assert isinstance(video.player.servant, VideoBufferRight)


@pytest.mark.parametrize('video', [(list(range(100)), 25, 100, False)], indirect=True)
def test_RemoveFrameCommand_removendo_todos_os_frames_a_partir_da_metade_com_servant_VideoBufferRight(video):
    remove = RemoveFrameCommand(video)
    while not video.player.servant.is_task_complete():
        video.read()
        remove.executor()

    video.read()
    expect_is_task_complete = True
    result_is_task_complet = video.player.servant.is_task_complete()

    assert expect_is_task_complete == result_is_task_complet
    assert isinstance(video.player.servant, VideoBufferLeft)


# ####### Testes do RemoveFrameCommand com servant VideoBufferRight como padrão ###### #

@pytest.mark.parametrize('video', [(list(range(100)), 25, 100, False)], indirect=True)
def test_RemoveFrameCommand_removendo_frame_0_com_servant_VideoBufferLeft(video):
    video.rewind()

    video.player.servant.set(1)
    video.player.master.set(1)
    video.read()

    remove = RemoveFrameCommand(video)
    remove.executor()

    expect_frame_id = 1
    video.read()
    result_frame_id = video.frame_id
    assert expect_frame_id == result_frame_id


@pytest.mark.parametrize('video', [(list(range(100)), 25, 100, False)], indirect=True)
def test_RemoveFrameCommand_removendo_ultimo_frame_com_servant_VideoBufferLeft(video):
    video.player.servant.set(99)
    video.player.master.set(99)
    video.read()
    video.rewind()

    remove = RemoveFrameCommand(video)
    remove.executor()

    video.read()
    expect_frame_id = 98
    result_frame_id = video.frame_id

    assert expect_frame_id == result_frame_id
    assert isinstance(video.player.servant, VideoBufferLeft)


@pytest.mark.parametrize('video', [(list(range(100)), 25, 100, False)], indirect=True)
def test_RemoveFrameCommand_removendo_frame_do_meio_com_servant_VideoBufferLeft(video):
    video.rewind()
    video.player.servant.set(50)  # seta o frame_id 49
    video.player.master.set(50)
    video.read()

    remove = RemoveFrameCommand(video)
    remove.executor()  # Remove o frame_id 49

    video.read()
    expect_frame_id = 48
    result_frame_id = video.frame_id

    assert expect_frame_id == result_frame_id
    assert isinstance(video.player.servant, VideoBufferLeft)


@pytest.mark.parametrize('video', [(list(range(100)), 25, 100, False)], indirect=True)
def test_RemoveFrameCommand_removendo_todos_os_frames_a_partir_da_metade_com_servant_VideoBufferLeft(video):
    remove = RemoveFrameCommand(video)

    video.rewind()
    video.player.servant.set(50)
    video.player.master.set(50)

    while not video.player.servant.is_task_complete():
        video.read()
        remove.executor()

    # Aqui ocorre duas trocas de buffers, a primeira ao atingir a extremidade esquerda,
    # a segunda ao atingir a extremidade da direita, portanto o buffer do final é o da esquerda
    # por isso o expect_buffer deve ser falso
    video.read()
    expect_is_task_complete = True
    result_is_task_complet = video.player.servant.is_task_complete()

    assert expect_is_task_complete == result_is_task_complet
    assert isinstance(video.player.servant, VideoBufferLeft)


@pytest.mark.parametrize('video', [(list(range(100)), 25, 100, False)], indirect=True)
def test_RemoveFrameCommand_removendo_todos_os_frames_desde_o_inicio_com_servant_VideoBufferLeft(video):
    remove = RemoveFrameCommand(video)

    video.rewind()
    while not video.player.servant.is_task_complete():
        video.read()
        remove.executor()

    video.read()
    result_is_task_complet = video.player.servant.is_task_complete()
    expect_is_task_complete = True

    assert expect_is_task_complete == result_is_task_complet


@pytest.mark.parametrize('video', [(list(range(100)), 25, 100, False)], indirect=True)
def test_RemoveFrameCommand_removendo_todos_os_frames_desde_o_final_com_servant_VideoBufferLeft(video):
    remove = RemoveFrameCommand(video)

    video.player.servant.set(99)
    video.player.master.set(99)
    video.read()
    video.rewind()

    while not video.player.servant.is_task_complete():
        remove.executor()
        video.read()

    expect_is_task_complete = True
    result_is_task_complet = video.player.servant.is_task_complete()
    assert expect_is_task_complete == result_is_task_complet


@pytest.mark.parametrize('video', [(list(range(100)), 25, 100, False)], indirect=True)
def test_RemoveFrameCommand_removendo_o_primeiro_frame_com_servant_buffer_leftt_e_depois_rewind_e_read_novamente(video):
    remove = RemoveFrameCommand(video)

    video.player.servant.set(1)
    video.rewind()

    video.read()
    remove.executor()
    video.rewind()
    video.read()

    expect_is_task_complete = True
    result_is_task_complet = video.player.servant.is_task_complete()
    assert expect_is_task_complete == result_is_task_complet


@pytest.mark.parametrize('video', [(list(range(100)), 25, 100, False)], indirect=True)
def test_RemoveFrameCommand_removendo_o_ultimos_frame_e_depois_proceed_e_read_novamente(video):
    remove = RemoveFrameCommand(video)

    video.player.servant.set(99)
    video.player.master.set(99)

    video.read()
    remove.executor()
    video.proceed()
    video.read()

    expect_is_task_complete = True
    result_is_task_complet = video.player.servant.is_task_complete()
    assert expect_is_task_complete == result_is_task_complet


@pytest.mark.parametrize('video', [(list(range(100)), 25, 100, False)], indirect=True)
def test_RemoveFrameCommand_removendo_o_ultimo_frame_com_servant_buffer_left(video):
    remove = RemoveFrameCommand(video)

    video.player.servant.set(99)
    video.player.master.set(99)

    video.read()
    video.rewind()
    remove.executor()
    video.proceed()
    video.read()

    expect_is_task_complete = True
    result_is_task_complet = video.player.servant.is_task_complete()
    assert expect_is_task_complete == result_is_task_complet


@pytest.mark.parametrize('video', [(list(range(100)), 25, 100, False)], indirect=True)
def test_UndoFrameCommand_restaurando_o_frame_com_os_dois_buffers_vazios_exclusao_linear_para_a_direita(video):
    remove = RemoveFrameCommand(video)
    undo = UndoFrameCommand(video)

    # Removendo o frame de indice 15
    video.player.servant.run()
    video.read()
    [remove.executor() for _ in range(100)]

    expect_frame_id = 0
    undo.executor()
    result_frame_id = video.frame_id
    assert result_frame_id == expect_frame_id


@pytest.mark.parametrize('video', [(list(range(100)), 25, 100, False)], indirect=True)
def test_UndoFrameCommand_restaurando_o_frame_com_o_indice_no_buffer_primario_do_buffer_da_direita_e_VideoBufferRight_como_servant(video):
    remove = RemoveFrameCommand(video)
    undo = UndoFrameCommand(video)

    # Removendo o frame de indice 15
    [video.read() for _ in range(16)]
    remove.executor()

    # Retornando para o frame de indice 0
    video.rewind()
    [video.read() for _ in range(16)]
    video.proceed()

    expect_frame_id = 15
    undo.executor()
    result_frame_id = video.frame_id
    assert result_frame_id == expect_frame_id


@pytest.mark.parametrize('video', [(list(range(100)), 25, 100, False)], indirect=True)
def test_UndoFrameCommand_recuperando_o_frame_do_50_com_servant_VideoBufferRight_no_frame_60(video):
    remove = RemoveFrameCommand(video)
    undo = UndoFrameCommand(video)
    expect = 50

    video.player.servant.set(50)
    video.player.master.set(50)
    video.player.servant.run()
    video.read()
    remove.executor()
    [video.read() for _ in range(10)]
    undo.executor()
    video.read()
    result = video.frame_id
    assert expect == result


@pytest.mark.parametrize('video', [(list(range(100)), 25, 100, False)], indirect=True)
def test_player_control_simulando_o_bug_ao_remover_o_1o_frame(video):
    """
    ### Descrição do Problema

        <!-- Explique claramente o que está acontecendo. -->
        Logo que abrimos ativamos o modo `pause_delay` , logo em seguida mudamos para o modo `rewind`,
        removemos o 1o. f rame e apertamos `rewind` 2x seguidas, com isso o erro VideoBufferError:
        Inconsistency in operation: 'frame_id' '25' is greater than the current frame é levantado.

    ### Passos para Reproduzir (1)
        1. Enquanto a janela do opencv carrega, apertamos a tecla de barra de espaço.
        2. Apertamos a tecla "a" para entrar no modo `rewind`.
        3. Apertamos a tacla "x" para remover o 1o. frame
        4. Apertamos a tecla "a" 2x.

    ### Passos para Reproduzir (2)

        1. Enquanto a janela do opencv abre, apetamos a tecla de barra de espaço, para ativar o pause por delay
        2. Apertamos o botão 'a' 2x para o modo `rewind`
        3. Apertamos o botão 'd' para ativar o modo `proceed`
        4. Apertamos o botão 'a' 2x novamente para o modo `rewind`

    Para a simulação o passo 1. não é necessario, já que podemos controlar frame por frame, já o 2x rewind é
    simulado por 1x rewind seguido de 2x read
    """
    remove = RemoveFrameCommand(video)
    expect = None

    video.player.servant.run()
    video.player.servant._buffer.wait_task()

    video.read()
    video.read()

    video.rewind()
    video.read()

    remove.executor()
    video.read()

    video.rewind()
    video.read()
    video.read()

    result = video.frame_id
    assert expect == result


@pytest.mark.parametrize('video', [(list(range(100)), 25, 100, False)], indirect=True)
def test_player_control_simulando_o_bug_ao_remover_o_1o_frame_versao_2(video):
    """
    ### Descrição do Problema

        <!-- Explique claramente o que está acontecendo. -->
        Ao dar o pause_dalay e excluir o 1o frame o seguinte erro é levantado
        "VideoBufferError: Inconsistency in operation: 'frame_id' '1' is less than the current frame."

    ### Passos para Reproduzir

        1. Enquanto a janela do opencv abre, aperto o botão para o `pause_delay` com a tecla barra de espaço
        2. Logo em seguida aperto o 'd' 2x para mudar o modo para `rewind`
        3. Aperto o 'a' 1x para mudar o modo para `proceed`
        4. Aperto a tecla `x` para remover o 1o. frame
        5. Aperto a tecla 'd' 1x para o modo `rewind`
        6. Por último aperto 2x 'a' para o modo `proceed`

    Para a simulação o passo 1. não é necessario, já que podemos controlar frame por frame, já o 2x rewind é
    simulado por 1x rewind seguido de 2x read
    """
    remove = RemoveFrameCommand(video)
    expect = 2

    video.player.servant.run()
    video.player.servant._buffer.wait_task()

    video.rewind()
    video.read()
    video.read()

    video.proceed()
    video.read()

    remove.executor()
    video.read()

    video.rewind()
    video.read()

    video.proceed()
    video.read()
    video.read()

    result = video.frame_id
    assert expect == result
