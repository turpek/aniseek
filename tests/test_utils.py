
import bisect
from collections import deque
from pathlib import Path
from threading import Semaphore
from unittest.mock import patch

import numpy as np
import pytest
from pytest import fixture, raises

from aniseek.adapter import FakeSectionAdapter
from aniseek.custom_exceptions import (
    FrameStackError,
    FrameWrapperError,
    SimpleStackError,
)
from aniseek.memento import Caretaker, SectionOriginator, TrashOriginator
from aniseek.section import SectionWrapper, VideoSection
from aniseek.trash import Trash
from aniseek.utils import (
    FrameMementoHandler,
    FrameStack,
    FrameWrapper,
    SectionMementoHandler,
    SimpleStack,
    VideoInfo,
    partition_by_value,
)

from .uteis import MyVideoCapture

FAKES = {
    'SECTION_IDS': [1, 2, 4],
    'REMOVED_IDS': [5, 3, 6],
    1: {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
    2: {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134], 'BLACK_LIST': []},
    3: {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [200], 'BLACK_LIST': [210, 211, 212, 213, 214, 215]},
    4: {'RANGE_FRAME_ID': (300, 395), 'REMOVED_FRAMES': [398, 399], 'BLACK_LIST': []},
    5: {'RANGE_FRAME_ID': (403, 497), 'REMOVED_FRAMES': [498, 401, 499, 402], 'BLACK_LIST': [400]},
    6: {'RANGE_FRAME_ID': (500, 599), 'REMOVED_FRAMES': [], 'BLACK_LIST': []},
}


class MockFrameMapper:
    def __init__(self, frame_mapper: list):
        self.__frame_ids = sorted(frame_mapper)

    def __getitem__(self, index):
        if len(self.__frame_ids) > 0:
            return self.__frame_ids[index]

    def add(self, value):
        import bisect
        bisect.insort_left(self.__frame_ids, value)


@fixture
def sections():
    list_sections = [VideoSection(FakeSectionAdapter(FAKES[k])) for k in [1, 2, 3, 4, 5, 6]]
    yield list_sections


@fixture
def removed_sections(request):
    keys = request.param
    removed_sections_ = SimpleStack(SectionWrapper)
    for i, k in keys:
        section_1 = VideoSection(FakeSectionAdapter(FAKES[i]))
        section_2 = None
        if k is not None:
            section_2 = VideoSection(FakeSectionAdapter(FAKES[k]))
        removed_sections_.push(SectionWrapper(section_1, section_2))
    yield removed_sections_


@fixture
def mycap():
    with patch('cv2.VideoCapture', return_value=MyVideoCapture()) as mock:
        yield mock.return_value


@fixture
def trash(mycap):
    semaphore = Semaphore()
    _trash = Trash(mycap, semaphore, frame_count=3000, buffersize=5, bufferlog=False)
    yield _trash
    _trash.join()


@fixture
def video_info(request):
    path, label = request.param
    vinfo = VideoInfo(Path(path), label)
    yield vinfo


def test_SimpleStack_top_sem_push():
    expect = None
    stack = SimpleStack(int)
    result = stack.top
    assert expect == result


def test_SimpleStack_top_com_1x_push():
    expect = 1
    stack = SimpleStack(int)
    stack.push(1)
    result = stack.top
    assert expect == result


def test_SimpleStack_top_com_2x_push():
    expect = 2
    stack = SimpleStack(int)
    stack.push(1)
    stack.push(2)
    result = stack.top
    assert expect == result


def test_SimpleStack_pop_sem_push():
    expect = "Pop failed: Stack is empty."
    stack = SimpleStack(int)
    with raises(SimpleStackError) as excinfo:
        stack.pop()
    result = f'{excinfo.value}'
    assert expect == result


def test_SimpleStack_pop_1x_push():
    expect = 1
    stack = SimpleStack(int)
    stack.push(1)
    result = stack.pop()
    assert expect == result


def test_SimpleStack_pop_2x_push():
    expect = 2
    stack = SimpleStack(int)
    stack.push(1)
    stack.push(2)
    result = stack.pop()
    assert expect == result


def test_SimpleStack_empty_fila_vazia():
    stack = SimpleStack(int)
    assert stack.empty()


def test_SimpleStack_empty_fila_nao_vazia():
    stack = SimpleStack(int)
    stack.push(1)
    assert not stack.empty()


def test_SimpleStack_empty_fila_vazia_apos_push_e_pop():
    stack = SimpleStack(int)
    stack.push(1)
    stack.pop()
    assert stack.empty()


def test_SimplesStack_push_elemento_de_mesmo_tipo():
    stack = SimpleStack(int)
    stack.push(1)


def test_SimplesStack_push_elemento_de_tipo_diferente():
    expect = 'Expected type "int", but received "str".'
    with raises(TypeError) as excinfo:
        stack = SimpleStack(int)
        stack.push('1')
    result = str(excinfo.value)
    assert expect == result


# ############ Testes para a classe FrameMementoHandler ##################

def test_FrameMementoHandler_exportar_dados_para_secao_sem_frames_removidos(sections):
    expect = deque()
    section = sections[5]  # Essa secao não tem frames removidos
    caretaker = Caretaker()
    originator = TrashOriginator(MockFrameMapper([]))
    handler = FrameMementoHandler(originator, caretaker)
    handler.store_mementos(section)
    result = section.get_trash()
    assert expect == result


def test_FrameMementoHandler_exportar_dados_com_1_elemento(sections):
    expect = deque([500])
    section = sections[5]  # Essa secao não tem frames removidos
    caretaker = Caretaker()
    originator = TrashOriginator(MockFrameMapper([]))
    originator.set_state(500)
    caretaker.save(originator)
    handler = FrameMementoHandler(originator, caretaker)
    handler.store_mementos(section)
    result = section.get_trash()
    assert expect == result


def test_FrameMementoHandler_exportar_dados_com_5_elemento(sections):
    frames_id = [503, 505, 502, 501, 504, 500]
    expect = deque(frames_id)
    section = sections[5]  # Essa secao não tem frames removidos
    caretaker = Caretaker()
    originator = TrashOriginator(MockFrameMapper([]))
    for frame_id in frames_id[::-1]:
        originator.set_state(frame_id)
        caretaker.save(originator)
    handler = FrameMementoHandler(originator, caretaker)
    handler.store_mementos(section)
    result = section.get_trash()
    assert expect == result


def test_FrameMementoHandler_importar_dados_de_memento_vazio(sections):
    section = sections[5]  # Essa secao não tem frames removidos
    caretaker = Caretaker()
    originator = TrashOriginator(MockFrameMapper([]))
    handler = FrameMementoHandler(originator, caretaker)
    handler.load_mementos(section)
    assert not caretaker.can_undo()


def test_FrameMementoHandler_importar_dados_de_memento_1_elemento(sections):
    expect = 200
    section = sections[2]  # Essa secao não tem frames removidos
    caretaker = Caretaker()
    originator = TrashOriginator(MockFrameMapper([]))
    handler = FrameMementoHandler(originator, caretaker)
    handler.load_mementos(section)
    assert caretaker.can_undo()

    caretaker.undo(originator)
    result = originator.get_state()
    assert expect == result


def test_FrameMementoHandler_importar_dados_de_memento_2_elemento(sections):
    expect = 399
    section = sections[3]  # Essa secao não tem frames removidos
    caretaker = Caretaker()
    originator = TrashOriginator(MockFrameMapper([]))
    handler = FrameMementoHandler(originator, caretaker)
    handler.load_mementos(section)

    caretaker.undo(originator)
    caretaker.undo(originator)
    originator.get_state()
    result = originator.get_state()
    assert expect == result


def test_FrameMementoHandler_importar_e_exportar_dados(sections):
    expect = deque([150, 149, 148, 147, 136, 135, 134])
    section = sections[1]  # Essa secao não tem frames removidos
    caretaker = Caretaker()
    originator = TrashOriginator(MockFrameMapper([]))
    handler = FrameMementoHandler(originator, caretaker)
    handler.load_mementos(section)
    handler.store_mementos(section)
    result = section.get_trash()
    assert expect == result


def test_FrameMementoHandler_importar_remove_e_exporta_dados(sections):
    expect = deque([199, 150, 149, 148, 147, 136, 135, 134])
    section = sections[1]  # Essa secao não tem frames removidos
    caretaker = Caretaker()
    originator = TrashOriginator(MockFrameMapper([]))
    handler = FrameMementoHandler(originator, caretaker)
    handler.load_mementos(section)

    originator.set_state(199)
    caretaker.save(originator)

    handler.store_mementos(section)
    result = section.get_trash()
    assert expect == result


# ############ Testes para a classe SectionMementoHandler ##################


def test_SectionMementoHandler_exportar_dados_para_secao_1_elemento():
    caretaker = Caretaker()
    originator = SectionOriginator()
    handler = SectionMementoHandler(originator, caretaker)

    removed_sections = SimpleStack(SectionWrapper)
    section = VideoSection(FakeSectionAdapter(FAKES[1]))
    removed_sections.push(SectionWrapper(section, None))
    handler.load_mementos(removed_sections)
    assert removed_sections.empty()
    assert caretaker.can_undo()


@pytest.mark.parametrize('removed_sections', [[(1, None), (2, None)]], indirect=True)
def test_SectionMementoHandler_exportar_dados_para_secao_2_elemento(removed_sections):
    caretaker = Caretaker()
    originator = SectionOriginator()
    handler = SectionMementoHandler(originator, caretaker)

    handler.load_mementos(removed_sections)
    assert removed_sections.empty()


@pytest.mark.parametrize('removed_sections', [[(1, 2)]], indirect=True)
def test_SectionMementoHandler_exportar_dados_para_secao_1_elemento_duplo(removed_sections):
    caretaker = Caretaker()
    originator = SectionOriginator()
    handler = SectionMementoHandler(originator, caretaker)

    handler.load_mementos(removed_sections)
    assert removed_sections.empty()
    assert caretaker.can_undo()


@pytest.mark.parametrize('removed_sections', [[(1, 2), (3, 4)]], indirect=True)
def test_SectionMementoHandler_exportar_dados_para_secao_2_elemento_duplo(removed_sections):
    caretaker = Caretaker()
    originator = SectionOriginator()
    handler = SectionMementoHandler(originator, caretaker)

    handler.load_mementos(removed_sections)
    assert removed_sections.empty()
    assert caretaker.can_undo()


def test_SectionMementoHandler_importar_dados_de_memento_vazio():
    caretaker = Caretaker()
    originator = SectionOriginator()
    handler = SectionMementoHandler(originator, caretaker)

    removed_sections = SimpleStack(SectionWrapper)
    handler.store_mementos(removed_sections)
    assert removed_sections.empty()


@pytest.mark.parametrize('removed_sections', [[(1, None)]], indirect=True)
def test_SectionMementoHandler_importar_dados_de_memento_1(removed_sections):
    expect = None
    expect_id = 0
    caretaker = Caretaker()
    originator = SectionOriginator()
    handler = SectionMementoHandler(originator, caretaker)

    # Carregando o dado no memento
    handler.load_mementos(removed_sections)

    # Agora vem o teste
    handler.store_mementos(removed_sections)
    assert not removed_sections.empty()
    assert not caretaker.can_undo()

    result = removed_sections.top.section_1
    result_id = removed_sections.top.section_2.id_
    assert expect == result
    assert expect_id == result_id


@pytest.mark.parametrize('removed_sections', [[(1, 2)]], indirect=True)
def test_SectionMementoHandler_importar_dados_de_memento_1_elemento_duplo(removed_sections):
    caretaker = Caretaker()
    originator = SectionOriginator()
    handler = SectionMementoHandler(originator, caretaker)

    # Carregando o dado no memento
    handler.load_mementos(removed_sections)

    # Agora vem o teste
    handler.store_mementos(removed_sections)
    assert not removed_sections.empty()
    assert not caretaker.can_undo()


@pytest.mark.parametrize('removed_sections', [[(1, None), (2, 3)]], indirect=True)
def test_SectionMementoHandler_importar_dados_de_memento_2_elementos(removed_sections):
    expect = 2
    expect_id1 = 100
    expect_id2 = 200
    caretaker = Caretaker()
    originator = SectionOriginator()
    handler = SectionMementoHandler(originator, caretaker)

    # Carregando o dado no memento
    handler.load_mementos(removed_sections)

    # Agora vem o teste
    handler.store_mementos(removed_sections)
    result = len(removed_sections)
    assert expect == result

    result_id1 = removed_sections.top.section_1.id_
    result_id2 = removed_sections.top.section_2.id_
    assert expect_id1 == result_id1
    assert expect_id2 == result_id2


@pytest.mark.parametrize('removed_sections', [[(1, None), (2, None), (3, None), (4, 5)]], indirect=True)
def test_SectionMementoHandler_importar_dados_de_memento_4_elementos(removed_sections):
    expect = 4
    caretaker = Caretaker()
    originator = SectionOriginator()
    handler = SectionMementoHandler(originator, caretaker)

    # Carregando o dado no memento
    handler.load_mementos(removed_sections)

    # Agora vem o teste
    handler.store_mementos(removed_sections)
    result = len(removed_sections)
    assert expect == result


@pytest.mark.parametrize('removed_sections', [[(1, None), (2, None), (3, None), (4, 5)]], indirect=True)
def test_SectionMementoHandler_importar_dados_de_memento_4_elementos_e_exportar(removed_sections):
    expect = 0
    caretaker = Caretaker()
    originator = SectionOriginator()
    handler = SectionMementoHandler(originator, caretaker)

    # Carregando o dado no memento
    handler.load_mementos(removed_sections)
    handler.store_mementos(removed_sections)

    # Agora vem o teste
    handler.load_mementos(removed_sections)
    result = len(removed_sections)
    assert expect == result


# ################ Testes para a classe FrameWrapper ######################

def test_FrameWrapper_instanciar_classe_com_frame():
    expect = 0
    frame = FrameWrapper(0, np.zeros((2, 2)))
    result = frame.id_

    assert expect == result


def test_FrameWrapper_instanciar_classe_sem_frame():
    expect = None
    frame = FrameWrapper(0, None)
    result = frame.get_frame()
    assert expect == result


def test_FrameWrapper_set_frame():
    frame = FrameWrapper(0, np.zeros((2, 2)))
    assert isinstance(frame.get_frame(), np.ndarray)


def test_FrameWrapper_set_frame_ja_definido():
    expect = "frame is already defined"
    with raises(FrameWrapperError) as excinfo:
        frame = FrameWrapper(0, np.zeros((2, 2)))
        frame.set_frame(np.zeros((2, 2)))
    result = f'{excinfo.value}'
    assert expect == result


# ################ Testes para o FrameStack ###################

def test_FrameStack_vazia():
    frames = FrameStack(6)
    assert frames.empty()


def test_FrameStack_maxlen():
    expect = 6
    frames = FrameStack(expect)
    result = frames.maxlen
    assert expect == result


def test_FramasStack_colocar_frame():
    frames = FrameStack(6)
    frames.push(FrameWrapper(0, np.zeros((2, 2))))
    assert len(frames) == 1
    assert not frames.empty()


def test_FrameStack_retirar_frame_com_pilha_vazia():
    expect = "Pop failed: Stack is empty."
    with raises(FrameStackError) as excinfo:
        frames = FrameStack(6)
        frames.pop()
    result = str(excinfo.value)
    assert expect == result


def test_FramasStack_retirar_frame():
    expect = 0
    frames = FrameStack(6)
    frames.push(FrameWrapper(0, np.zeros((2, 2))))
    result = frames.pop()
    assert result == expect


def test_FrameStack_can_update_memento_sem_mementos_e_stack_vazia(trash):
    expect = False
    frames = FrameStack(10)
    result = frames.can_update_memento(trash)
    assert expect == result


def test_FrameStack_can_update_memento_com_mementos_maior_que_maxlen_da_stack_e_stack_cheia(trash):
    expect = False
    frames = FrameStack(10)
    [trash.move(frame_id, np.zeros((2, 2))) for frame_id in range(25, 15, -1)]
    [frames.push(FrameWrapper(frame_id, np.zeros((2, 2)))) for frame_id in range(15, 5, -1)]
    result = frames.can_update_memento(trash)
    assert expect == result


def test_FrameStack_can_update_memento_com_mementos_vazios_stack_cheia(trash):
    expect = False
    frames = FrameStack(10)
    [frames.push(FrameWrapper(frame_id, np.zeros((2, 2)))) for frame_id in range(15, 5, -1)]
    result = frames.can_update_memento(trash)
    assert expect == result


def test_FrameStack_can_update_memento_com_mementos_vazios_stack_pela_metade(trash):
    expect = False
    frames = FrameStack(10)
    [frames.push(FrameWrapper(frame_id, np.zeros((2, 2)))) for frame_id in range(15, 10, -1)]
    result = frames.can_update_memento(trash)
    assert expect == result


def test_FrameStack_can_update_memento_com_mementos_vazios_stack_vazia(trash):
    expect = False
    frames = FrameStack(10)
    result = frames.can_update_memento(trash)
    assert expect == result


def test_FrameStack_can_update_memento_com_mementos_maior_que_maxlen_da_stack_e_stack_pela_metade(trash):
    expect = True
    frames = FrameStack(10)
    [trash.move(frame_id, np.zeros((2, 2))) for frame_id in range(25, 15, -1)]
    [frames.push(FrameWrapper(frame_id, np.zeros((2, 2)))) for frame_id in range(15, 10, -1)]
    result = frames.can_update_memento(trash)
    assert expect == result


def test_FrameStack_can_update_memento_com_mementos_maior_que_maxlen_da_stack_e_stack_menor_que_metade(trash):
    expect = True
    frames = FrameStack(10)
    [trash.move(frame_id, np.zeros((2, 2))) for frame_id in range(25, 15, -1)]
    [frames.push(FrameWrapper(frame_id, np.zeros((2, 2)))) for frame_id in range(15, 11, -1)]
    result = frames.can_update_memento(trash)
    assert expect == result


def test_FrameStack_can_update_memento_com_mementos_maior_que_maxlen_da_stack_e_stack_vazia(trash):
    expect = True
    frames = FrameStack(10)
    [trash.move(frame_id, np.zeros((2, 2))) for frame_id in range(25, 15, -1)]
    result = frames.can_update_memento(trash)
    assert expect == result


def test_FrameStack_can_update_memento_com_mementos_vazio_e_stack_na_metade(trash):
    expect = False
    frames = FrameStack(10)
    [frames.push(FrameWrapper(frame_id, np.zeros((2, 2)))) for frame_id in range(15, 10, -1)]
    result = frames.can_update_memento(trash)
    assert expect == result


def test_FrameStack_can_update_memento_com_mementos_vazio_e_stack_menor_que_a_metade(trash):
    expect = False
    frames = FrameStack(10)
    [frames.push(FrameWrapper(frame_id, np.zeros((2, 2)))) for frame_id in range(15, 12, -1)]
    result = frames.can_update_memento(trash)
    assert expect == result


def test_FrameStack_salvando_mementos_retirados(trash):
    expect = [11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
    frames = FrameStack(10)
    frames._memento_save(expect.copy(), trash)
    result = [trash._memento_undo() for _ in range(10)]
    assert expect == result


def test_FrameStack_salvando_mementos_retirados_vazio(trash):
    expect = []
    frames = FrameStack(10)
    frames._memento_save(expect.copy(), trash)
    result = list(filter(None, [trash._memento_undo() for _ in range(10)]))
    assert expect == result


def test_FrameStack_update_mementos_com_stack_e_trash_vazios(trash):
    expect = {}
    frames = FrameStack(10)
    result = frames.update_mementos(trash)
    assert expect == result


def test_FrameStack_update_mementos_com_stack_cheia_e_trash_vazia(trash):
    expect = {}
    frames = FrameStack(10)
    [frames.push(FrameWrapper(frame_id, np.zeros((2, 2)))) for frame_id in range(20, 10, -1)]
    result = frames.update_mementos(trash)
    assert expect == result


def test_FrameStack_check_update_memento_com_stack_e_trash_vazia(trash):
    expect = False
    frames = FrameStack(10)
    result = frames._check_update_memento(trash)
    assert expect == result


def test_FrameStack_check_update_memento_com_stack_cheia_e_trash_vazia(trash):
    expect = False
    frames = FrameStack(10)
    [frames.push(FrameWrapper(frame_id, np.zeros((2, 2)))) for frame_id in range(20, 10, -1)]
    result = frames._check_update_memento(trash)
    assert expect == result


def test_FrameStack_check_update_memento_com_stack_cheia_e_trash_cheio(trash):
    expect = False
    frames = FrameStack(10)
    [frames.push(FrameWrapper(frame_id, np.zeros((2, 2)))) for frame_id in range(20, 10, -1)]
    [trash.move(frame_id, np.zeros((2, 2))) for frame_id in range(40, 10, -1)]
    result = frames._check_update_memento(trash)
    assert expect == result


def test_FrameStack_check_update_memento_com_stack_abaixo_da_metade_de_maxlen_e_trash_vazia(trash):
    expect = False
    frames = FrameStack(10)
    [frames.push(FrameWrapper(frame_id, np.zeros((2, 2)))) for frame_id in range(20, 16, -1)]
    result = frames._check_update_memento(trash)
    assert expect == result


def test_FrameStack_check_update_memento_com_stack_abaixo_da_metade_de_maxlen_e_trash_com_1_elemento(trash):
    expect = True
    frames = FrameStack(10)
    [frames.push(FrameWrapper(frame_id, np.zeros((2, 2)))) for frame_id in range(20, 16, -1)]
    trash.move(21, np.zeros((2, 2)))
    result = frames._check_update_memento(trash)
    assert expect == result


def test_FrameStack_check_update_memento_com_stack_abaixo_da_metade_de_maxlen_e_trash_cheio(trash):
    expect = True
    frames = FrameStack(10)
    [frames.push(FrameWrapper(frame_id, np.zeros((2, 2)))) for frame_id in range(20, 16, -1)]
    [trash.move(frame_id, np.zeros((2, 2))) for frame_id in range(40, 16, -1)]
    result = frames._check_update_memento(trash)
    assert expect == result


def test_FrameStack_check_update_memento_com_stack_com_metade_de_maxlen_e_trash_vazio(trash):
    expect = False
    frames = FrameStack(10)
    [frames.push(FrameWrapper(frame_id, np.zeros((2, 2)))) for frame_id in range(20, 15, -1)]
    result = frames._check_update_memento(trash)
    assert expect == result


def test_FrameStack_check_update_memento_com_stack_com_metade_de_maxlen_e_trash_cheio(trash):
    expect = True
    frames = FrameStack(10)
    [frames.push(FrameWrapper(frame_id, np.zeros((2, 2)))) for frame_id in range(20, 15, -1)]
    [trash.move(frame_id, np.zeros((2, 2))) for frame_id in range(40, 16, -1)]
    result = frames._check_update_memento(trash)
    assert expect == result


def test_FrameStack_check_update_memento_com_stack_com_mais_da_metade_de_maxlen_e_trash_vazio(trash):
    expect = False
    frames = FrameStack(10)
    [frames.push(FrameWrapper(frame_id, np.zeros((2, 2)))) for frame_id in range(20, 14, -1)]
    result = frames._check_update_memento(trash)
    assert expect == result


def test_FrameStack_check_update_memento_com_stack_com_mais_da_metade_de_maxlen_e_trash_cheio(trash):
    expect = True
    frames = FrameStack(10)
    [frames.push(FrameWrapper(frame_id, np.zeros((2, 2)))) for frame_id in range(20, 14, -1)]
    [trash.move(frame_id, np.zeros((2, 2))) for frame_id in range(40, 16, -1)]
    result = frames._check_update_memento(trash)
    assert expect == result


def test_FrameStack_update_mementos_com_stack_cheia_e_trash_maior_que_maxlen(trash):
    expect = {}
    frames = FrameStack(10)
    [frames.push(FrameWrapper(frame_id, np.zeros((2, 2)))) for frame_id in range(20, 10, -1)]
    [trash.move(frame_id, np.zeros((2, 2))) for frame_id in range(40, 20, -1)]
    result = frames.update_mementos(trash)
    assert expect == result


def test_FrameStack_update_mementos_com_stack_igual_a_metade_de_maxlen_e_trash_maior_que_maxlen(trash):
    expect_keys = {21, 22, 23, 24, 25}
    frames = FrameStack(10)
    [frames.push(FrameWrapper(frame_id, np.zeros((2, 2)))) for frame_id in range(20, 15, -1)]
    [trash.move(frame_id, np.zeros((2, 2))) for frame_id in range(40, 15, -1)]
    result = frames.update_mementos(trash)
    assert expect_keys == set(result.keys())


# ############ Teste para a classe `VideoInfo` ################# #

@pytest.mark.parametrize('video_info', [('video-01.mp4', None)], indirect=True)
def test_VideoInfo_path(video_info):
    expect = Path('video-01.mp4')
    result = video_info.path
    assert expect == result


@pytest.mark.parametrize('video_info', [('video-01.mp4', None)], indirect=True)
def test_VideoInfo_label_como_None_sem_ler_dados_de_secao(video_info):
    expect = None
    result = video_info.label
    assert expect == result


@pytest.mark.parametrize('video_info', [('video-01.mp4', 'vid_001')], indirect=True)
def test_VideoInfo_label_sem_ler_dados_de_secao(video_info):
    expect = 'vid_001'
    result = video_info.label
    assert expect == result


@pytest.mark.parametrize('video_info', [('video-01.mp4', None)], indirect=True)
def test_VideoInfo_suffix(video_info):
    expect = '.mp4'
    result = video_info.suffix
    assert expect == result


@pytest.mark.parametrize('video_info', [('video-01.mp4', None)], indirect=True)
def test_VideoInfo_fps_sem_ler_metadados_do_video(video_info):
    expect = None
    result = video_info.fps
    assert expect == result


@pytest.mark.parametrize('video_info', [('video-01.mp4', None)], indirect=True)
def test_VideoInfo_count_frame_sem_ler_metadados_do_video(video_info):
    expect = None
    result = video_info.frame_count
    assert expect == result


@pytest.mark.parametrize('video_info', [('video-01.mp4', None)], indirect=True)
def test_VideoInfo_count_frame_apos_ler_metadados_do_video(video_info, mycap):
    expect = 500
    video_info.load_video_property(mycap)
    result = video_info.frame_count
    assert expect == result


@pytest.mark.parametrize('video_info', [('video-01.mp4', None)], indirect=True)
def test_VideoInfo_fps_apos_ler_metadados_do_video(video_info, mycap):
    expect = 24
    video_info.load_video_property(mycap)
    result = video_info.fps
    assert expect == result


def test_partition_by_value_para_uma_lista_vazia():
    expect_1 = []
    expect_2 = []
    result_1, result_2 = partition_by_value([], 0)

    assert expect_1 == result_1
    assert expect_2 == result_2


def test_partition_by_value_para_uma_lista_ordenda_com_split_no_inicio():
    expect_1 = []
    expect_2 = [0, 1, 2, 3, 4, 5, 6]
    result_1, result_2 = partition_by_value(expect_2, 0)

    assert expect_1 == result_1
    assert expect_2 == result_2


def test_partition_by_value_para_uma_lista_ordenda_com_split_no_final():
    expect_1 = [0, 1, 2, 3, 4, 5]
    expect_2 = [6]
    result_1, result_2 = partition_by_value([0, 1, 2, 3, 4, 5, 6], 6)

    assert expect_1 == result_1
    assert expect_2 == result_2


def test_partition_by_value_para_uma_lista_ordenda_com_split_maior_que_lista():
    expect_1 = [0, 1, 2, 3, 4, 5, 6]
    expect_2 = []
    result_1, result_2 = partition_by_value([0, 1, 2, 3, 4, 5, 6], 7)

    assert expect_1 == result_1
    assert expect_2 == result_2


def test_partition_by_value_para_uma_lista_nao_ordenada():
    expect_1 = [5, 2, 6, 3, 0, 4, 1]
    expect_2 = [13, 9, 11, 8, 12]

    source = [5, 2, 13, 9, 6, 3, 0, 11, 4, 8, 1, 12]
    result_1, result_2 = partition_by_value(source, 7)

    assert expect_1 == result_1
    assert expect_2 == result_2
