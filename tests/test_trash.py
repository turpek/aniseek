from threading import Semaphore
from unittest.mock import patch

import numpy as np
from pytest import fixture

from aniseek.editing.trash import Trash
from tests.uteis import MyVideoCapture


def lote(start, end, step=1):
    return [(frame_id, np.zeros((2, 2))) for frame_id in range(start, end, step)]


@fixture
def mycap():
    with patch('cv2.VideoCapture', return_value=MyVideoCapture()) as mock:
        yield mock


@fixture
def trash(mycap):
    cap = mycap.return_value
    semaphore = Semaphore()
    _trash = Trash(cap, semaphore, frame_count=3000, buffersize=5)
    yield _trash
    _trash.join()


def test_trash_empty(trash):
    expect = True
    result = trash.empty()
    assert expect == result


def test_trash_not_empty(trash):
    expect = False
    trash.move(0, np.zeros((2, 2)))
    result = trash.empty()
    assert expect == result


def test_adicionando_o_frame_excluido(trash):
    expect_frame_id = 0
    trash.move(0, np.zeros((2, 2)))
    result_frame_id = trash._stack.pop()
    assert expect_frame_id == result_frame_id


def test_adicionando_10_frame_excluido(trash):
    expect_frames = 10
    [trash.move(frame_id, frame) for frame_id, frame in lote(0, 10)]
    result_frames = len(trash._stack)
    assert expect_frames == result_frames


def test_adicionando_11_frame_excluido(trash):
    expect_frames_id = [frame_id for frame_id in range(10, 0, -1)]
    [trash.move(frame_id, frame) for frame_id, frame in lote(0, 11)]

    result_frames_id = []
    while not trash._stack.empty():
        result_frames_id.append(trash._stack.pop().id_)
    trash._memento_undo()
    assert expect_frames_id == result_frames_id


def test_trash_not_full(trash):
    expect = False
    result = trash.full()
    assert expect == result


def test_trash_not_full_com_1_frame(trash):
    expect = False
    trash.move(0, np.zeros((2, 2)))
    result = trash.full()
    assert expect == result


def test_trash_full(trash):
    expect = True
    [trash.move(frame_id, frame) for frame_id, frame in lote(0, 10)]
    result = trash.full()
    assert expect == result


def test_trash_vazio_com_undo(trash):
    expect = (None, None)
    result = trash.undo()
    assert expect == result


def test_trash_com_1_frame_undo(trash):
    expect_frame_id = 0
    trash.move(0, np.zeros((2, 2)))
    result_frame_id, _ = trash.undo()
    assert expect_frame_id == result_frame_id


def test_trash_com_10_frame_undo(trash):
    expect_frames_id = list(range(9, -1, -1))
    [trash.move(frame_id, frame) for frame_id, frame in lote(0, 10)]
    result_frames_id = [trash.undo()[0] for _ in range(10)]
    assert expect_frames_id == result_frames_id


def test_trash_com_11_frame_undo(trash):
    expect_frames_id = list(range(11, 0, -1))
    [trash.move(frame_id, frame) for frame_id, frame in lote(1, 12)]
    result_frames_id = [trash.undo()[0] for _ in range(11)]
    assert expect_frames_id == result_frames_id


def test_trash_com_20_frame_undo(trash):
    expect_frames_id = list(range(20, 0, -1))
    [trash.move(frame_id, frame) for frame_id, frame in lote(1, 21)]
    result_frames_id = [trash.undo()[0] for _ in range(20)]
    assert expect_frames_id == result_frames_id


# def test_trash_import_frames_id_vazia(trash):
#     frames_id = deque()
#     expect = False
#     trash.import_frames_id(frames_id)
#     result = trash.can_undo()
#     assert expect == result
#
#
# def test_trash_import_frames_id_com_1_elemento(trash):
#     frames_id = deque()
#     frames_id.append(0)
#     expect = True
#
#     trash.import_frames_id(frames_id)
#     result = trash.can_undo()
#     assert expect == result
#
#
# def test_trash_undo_apos_import_frames_id_com_1_elemento(trash):
#     frames_id = deque()
#     frames_id.append(0)
#     expect = 0
#
#     trash.import_frames_id(frames_id)
#     result = trash.undo()[0]
#     assert expect == result
#
#
# def test_trash_undo_apos_import_frames_id_com_20_elemento(trash):
#     frames_id = deque()
#     [frames_id.append(fid) for fid in range(19, -1, -1)]
#     expect = list(range(19, -1, -1))
#
#     trash.import_frames_id(frames_id)
#     result = [trash.undo()[0] for _ in range(20)]
#     assert expect == result
#
#
# def test_trash_export_frames_id_vazia(trash):
#     frames_id = deque()
#     expect = True
#
#     trash.export_frames_id(frames_id)
#     result = len(frames_id) == 0
#     assert expect == result
#
#
# def test_trash_export_frames_id_com_20_elemento_sem_undo(trash):
#     frames_id = deque()
#     [frames_id.append(fid) for fid in range(19, -1, -1)]
#     expect = frames_id.copy()
#
#     result = deque()
#     trash.import_frames_id(frames_id)
#     trash.export_frames_id(result)
#
#     assert expect == result
#
#
# def test_trash_export_frames_id_com_20_elemento_com_undo(trash):
#     frames_id = deque()
#     [frames_id.append(fid) for fid in range(19, -1, -1)]
#     frames_id.appendleft(20)  # Será removido ao restaurar, então não entra no valor experado!
#     expect = frames_id.copy()
#     expect.popleft()
#
#     result = deque()
#     trash.import_frames_id(frames_id)
#     trash.undo()
#     trash.export_frames_id(result)
#
#     assert expect == result
