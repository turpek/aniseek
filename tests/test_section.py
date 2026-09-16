import pytest
from collections import deque
from aniseek.adapter import FakeSectionAdapter, FakeSectionManagerAdapter
from aniseek.section import SectionManager, VideoSection, SectionWrapper
from aniseek.custom_exceptions import SectionManagerError
from aniseek.trash import Trash
from pytest import fixture, raises
from threading import Semaphore
from unittest.mock import patch
import numpy as np
import cv2


black_list_100 = [200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273, 274, 275, 276, 277, 278, 279, 280, 281, 282, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296, 297, 298]


FAKES = {
    'SECTION_IDS': [1, 2, 4],
    'REMOVED_IDS': [5, 3, 6],
    1: {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
    2: {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134], 'BLACK_LIST': []},
    3: {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [201, 200], 'BLACK_LIST': [210, 211, 212, 213, 214, 215]},
    4: {'RANGE_FRAME_ID': (300, 395), 'REMOVED_FRAMES': [396, 397, 398, 399], 'BLACK_LIST': []},
    5: {'RANGE_FRAME_ID': (403, 497), 'REMOVED_FRAMES': [498, 401, 499, 402], 'BLACK_LIST': [400]},
    6: {'RANGE_FRAME_ID': (500, 599), 'REMOVED_FRAMES': [], 'BLACK_LIST': []},
}


FAKEMAN0 = {
    'SECTIONS': [
        {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
        {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134], 'BLACK_LIST': []},
        {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [201, 200], 'BLACK_LIST': [210, 211, 212, 213, 214, 215]},
        {'RANGE_FRAME_ID': (300, 395), 'REMOVED_FRAMES': [396, 397, 398, 399], 'BLACK_LIST': []},
        {'RANGE_FRAME_ID': (403, 497), 'REMOVED_FRAMES': [498, 401, 499, 402], 'BLACK_LIST': [400]},
        {'RANGE_FRAME_ID': (500, 599), 'REMOVED_FRAMES': [], 'BLACK_LIST': []}
    ],
    'REMOVED': []
}

FAKEMAN = {
    'SECTIONS': [
        {
            'RANGE_FRAME_ID': (100, 497),
            'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134, 396, 397, 398, 399, 498, 401, 499, 402],
            'BLACK_LIST': black_list_100 + [400]},
        {
            'RANGE_FRAME_ID': (500, 599),
            'REMOVED_FRAMES': [],
            'BLACK_LIST': []}
    ],
    'REMOVED': [
        [
            {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
            None
        ],
        [
            {
                'RANGE_FRAME_ID': (100, 399),
                'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134, 396, 397, 398, 399],
                'BLACK_LIST': black_list_100
            },
            {
                'RANGE_FRAME_ID': (403, 497),
                'REMOVED_FRAMES': [498, 401, 499, 402],
                'BLACK_LIST': [400]
            }
        ],
        [
            {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134], 'BLACK_LIST': black_list_100},
            {'RANGE_FRAME_ID': (300, 395), 'REMOVED_FRAMES': [396, 397, 398, 399], 'BLACK_LIST': []},
        ],
        [
            {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [201, 200], 'BLACK_LIST': [210, 211, 212, 213, 214, 215]},
            None
        ]

    ]
}


# FAKEMAN1 tem os casos de split_section, de forma linear, ou seja, a seções foram divididas
# de forma em que os frames iriam avançandos
FAKEMAN1 = {
    "SECTIONS": [
        {"RANGE_FRAME_ID": [0, 363], "REMOVED_FRAMES": [], "BLACK_LIST": []},
        {"RANGE_FRAME_ID": [364, 655], "REMOVED_FRAMES": [], "BLACK_LIST": []},
        {"RANGE_FRAME_ID": [656, 946], "REMOVED_FRAMES": [], "BLACK_LIST": []},
        {"RANGE_FRAME_ID": [947, 1273], "REMOVED_FRAMES": [], "BLACK_LIST": []},
        {"RANGE_FRAME_ID": [1274, 1492], "REMOVED_FRAMES": [], "BLACK_LIST": []},
        {"RANGE_FRAME_ID": [1493, 2640], "REMOVED_FRAMES": [], "BLACK_LIST": []}
    ],
    "REMOVED": [
        [
            {"RANGE_FRAME_ID": [0, 2640], "REMOVED_FRAMES": [], "BLACK_LIST": []},
            None
        ],
        [
            {"RANGE_FRAME_ID": [364, 2640], "REMOVED_FRAMES": [], "BLACK_LIST": []},
            None
        ],
        [
            {"RANGE_FRAME_ID": [656, 2640], "REMOVED_FRAMES": [], "BLACK_LIST": []},
            None
        ],
        [
            {"RANGE_FRAME_ID": [947, 2640], "REMOVED_FRAMES": [], "BLACK_LIST": []},
            None
        ],
        [
            {"RANGE_FRAME_ID": [1274, 2640], "REMOVED_FRAMES": [], "BLACK_LIST": []},
            None
        ]
    ]
}

class MyVideoCapture():
    def __init__(self):
        self.frames = [np.zeros((2, 2)) for x in range(5000)]
        self.index = 0
        self.isopened = True

    def read(self):
        if self.index < len(self.frames):
            frame = self.frames[self.index]
            self.index += 1
            return True, frame
        return False, None

    def grab(self):
        self.index += 1

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
        ...


@fixture
def mycap():
    with patch('cv2.VideoCapture', return_value=MyVideoCapture()) as mock:
        yield mock


@fixture
def trash(mycap):
    cap = mycap.return_value
    semaphore = Semaphore()
    _trash = Trash(cap, semaphore, frame_count=3000, buffersize=5, bufferlog=False)
    yield _trash
    _trash.join()


class MockPlayer:
    def __init__(self):
        ...


class MockTrash:
    def __init__(self):
        self._stack = deque()

    def _set_data(self, dados: deque()):
        self._stack = dados.copy()

    def undo(self) -> tuple[bool | np.ndarray]:
        return (True, np.zeros((2, 2)))

    def import_frames_id(self, frames_id: deque):
        while len(frames_id):
            self._stack.put(frames_id.pop())

    def export_frames_id(self, frames_id: deque):
        while len(self._stack):
            frames_id.append(self._stack.pop())


class MockFrameMapper:
    def __init__(self, frame_mapper: list):
        self.__frame_ids = sorted(frame_mapper)

    def __getitem__(self, index):
        if len(self.__frame_ids) > 0:
            return self.__frame_ids[index]


def gera_mock(frames_mapping, removed):
    frame_mapping = sorted(set(frames_mapping) - set(removed))
    mapping = MockFrameMapper(frame_mapping)
    trash = MockTrash()
    trash._set_data(deque(removed))
    return mapping, trash


def gera_mock_com_fake(index):
    start, end = FAKES[index]['RANGE_FRAME_ID']
    frame_mapping = list(range(start, end + 1))
    removed = FAKES[index]['REMOVED_FRAMES']
    return gera_mock(frame_mapping, removed)


@fixture
def sections():
    section_manager = SectionManager(FAKES)
    yield section_manager


@fixture
def mock_config(request):
    frames_mapping, removed = request.param
    mapping, trash = gera_mock(frames_mapping, removed)
    yield mapping, trash


def test_VideoSection_start_frame():
    expect = 0
    secion = VideoSection(FakeSectionAdapter(FAKES[1]))
    result = secion.start
    assert expect == result


def test_VideoSection_end_frame():
    expect = 99
    secion = VideoSection(FakeSectionAdapter(FAKES[1]))
    result = secion.end
    assert expect == result


def test_VideoSection_removed_frames():
    expect = deque([14, 13, 12, 11, 10])
    secion = VideoSection(FakeSectionAdapter(FAKES[1]))
    result = secion.get_trash()
    assert expect == result


def test_VideoSection_black_list_frames():
    expect = set([210, 211, 212, 213, 214, 215])
    secion = VideoSection(FakeSectionAdapter(FAKES[3]))
    result = set(secion.black_list_frames)
    assert expect == result


def test_VideoSection_update_range():
    expect_start_frame = 15
    expect_end_frame = 78

    mock_mapper = list(range(15, 79))
    section = VideoSection(FakeSectionAdapter(FAKES[1]))
    section.update_range(mock_mapper)
    result_start_frame = section.start
    result_end_frame = section.end

    assert expect_start_frame == result_start_frame
    assert expect_end_frame == result_end_frame


def test_VideoSection_section_id_sem_frames_removidos():
    expect = 500
    section = VideoSection(FakeSectionAdapter(FAKES[6]))
    result = section.id_
    assert expect == result


def test_VideoSection_section_id_com_frames_removidos_maiores_que_section_start():
    expect = 300
    section = VideoSection(FakeSectionAdapter(FAKES[4]))
    result = section.id_
    assert expect == result


def test_VideoSection_section_id_com_frames_removidos_menores_que_section_start():
    expect = 200
    section = VideoSection(FakeSectionAdapter(FAKES[3]))
    result = section.id_
    assert expect == result


def test_VideoSection_uniao_de_duas_secoes_vizinhas():
    expect_start = 100
    expect_end = 299
    expect_trash = deque([150, 149, 148, 147, 136, 135, 134, 201, 200])

    section_1 = VideoSection(FakeSectionAdapter(FAKES[2]))
    section_2 = VideoSection(FakeSectionAdapter(FAKES[3]))
    section = section_1 + section_2
    result_start = section.start
    result_end = section.end
    result_trash = section.get_trash()

    assert expect_start == result_start
    assert expect_end == result_end
    assert expect_trash == result_trash


def test_VideoSection_uniao_de_duas_secoes_vizinhas_invertendo_ah_soma():
    expect_start = 100
    expect_end = 299
    expect_trash = deque([150, 149, 148, 147, 136, 135, 134, 201, 200])
    expect_black_list = set([210, 211, 212, 213, 214, 215])

    section_1 = VideoSection(FakeSectionAdapter(FAKES[2]))
    section_2 = VideoSection(FakeSectionAdapter(FAKES[3]))
    section = section_2 + section_1
    result_start = section.start
    result_end = section.end
    result_trash = section.get_trash()
    result_black_list = set(section.black_list_frames)

    assert expect_start == result_start
    assert expect_end == result_end
    assert expect_trash == result_trash
    assert expect_black_list == result_black_list


def test_VideoSection_uniao_de_duas_secoes_nao_vizinhas():
    expect_id = 200
    black_list_3 = [210, 211, 212, 213, 214, 215]
    expect_black_list = set(list(range(300, 500)) + black_list_3)

    section_1 = VideoSection(FakeSectionAdapter(FAKES[3]))
    section_2 = VideoSection(FakeSectionAdapter(FAKES[6]))
    section = section_1 + section_2
    result_id = section.id_
    result_black_list = set(section.black_list_frames)

    assert expect_id == result_id
    assert expect_black_list == result_black_list


def test_VideoSection_uniao_de_duas_secoes_nao_vizinhas_invertendo_soma():
    expect_id = 200
    black_list_3 = [210, 211, 212, 213, 214, 215]
    expect_black_list = set(list(range(300, 500)) + black_list_3)

    section_1 = VideoSection(FakeSectionAdapter(FAKES[3]))
    section_2 = VideoSection(FakeSectionAdapter(FAKES[6]))
    section = section_2 + section_1
    result_id = section.id_
    result_black_list = set(section.black_list_frames)

    assert expect_id == result_id
    assert expect_black_list == result_black_list


def test_VideoSection_dividindo_a_secao_em_duas_no_segundo_frame():
    expect_1 = 0
    expect_2 = 1
    section = VideoSection(FakeSectionAdapter(FAKES[1]))
    section_1, section_2 = section.split_section(1)
    result_1 = section_1.start
    result_2 = section_2.start

    assert expect_1 == result_1
    assert expect_2 == result_2


def test_VideoSection_dividindo_a_secao_em_duas_no_ultimo_frame():
    expect_1 = 0
    expect_2 = 98
    section = VideoSection(FakeSectionAdapter(FAKES[1]))
    section_1, section_2 = section.split_section(98)
    result_1 = section_1.start
    result_2 = section_2.start

    assert expect_1 == result_1
    assert expect_2 == result_2


def test_VideoSection_dividindo_a_secao_em_duas_remove_frame():
    expect_1 = deque([136, 135, 134])
    expect_2 = deque([150, 149, 148, 147])
    section = VideoSection(FakeSectionAdapter(FAKES[2]))
    section_1, section_2 = section.split_section(140)
    result_1 = section_1.get_trash()
    result_2 = section_2.get_trash()

    assert expect_1 == result_1
    assert expect_2 == result_2


def test_VideoSection_dividindo_a_secao_em_duas_black_list():
    expect_1 = [210, 211, 212, 213, 214, 215]
    expect_2 = []

    section = VideoSection(FakeSectionAdapter(FAKES[3]))
    section_1, section_2 = section.split_section(250)
    result_1 = section_1.black_list_frames
    result_2 = section_2.black_list_frames

    assert expect_1 == result_1
    assert expect_2 == result_2


def test_VideoSection_dividindo_a_secao_em_duas_id_():
    expect_1 = 200
    expect_2 = 250

    section = VideoSection(FakeSectionAdapter(FAKES[3]))
    section_1, section_2 = section / 250
    result_1 = section_1.id_
    result_2 = section_2.id_

    assert expect_1 == result_1
    assert expect_2 == result_2


def test_VideoSection_comparacao_secao1_menor_que_secao2():
    section_1 = VideoSection(FakeSectionAdapter(FAKES[3]))
    section_2 = VideoSection(FakeSectionAdapter(FAKES[6]))
    assert section_1 < section_2


def test_VideoSection_comparacao_secao2_nao_eh_menor_que_secao1():
    section_1 = VideoSection(FakeSectionAdapter(FAKES[3]))
    section_2 = VideoSection(FakeSectionAdapter(FAKES[6]))
    assert not section_2 < section_1


def test_VideoSection_comparacao_secao2_igual_secao1_usando_objeto():
    section_1 = VideoSection(FakeSectionAdapter(FAKES[3]))
    section_2 = VideoSection(FakeSectionAdapter(FAKES[3]))
    assert section_2 == section_1


def test_VideoSection_comparacao_secao2_nao_igual_secao1_usando_objeto():
    section_1 = VideoSection(FakeSectionAdapter(FAKES[3]))
    section_2 = VideoSection(FakeSectionAdapter(FAKES[4]))
    assert not section_2 == section_1


def test_VideoSection_comparacao_secao2_igual_secao1_usando_int():
    section_1 = VideoSection(FakeSectionAdapter(FAKES[3]))
    section_2 = VideoSection(FakeSectionAdapter(FAKES[3]))
    assert section_2 == section_1.id_


def test_VideoSection_comparacao_secao2_nao_igual_secao1_usando_int():
    section_1 = VideoSection(FakeSectionAdapter(FAKES[3]))
    section_2 = VideoSection(FakeSectionAdapter(FAKES[4]))
    assert not section_2 == section_1.id_


def test_VideoSection_to_dict():
    expect_range = (202, 299)
    expect_removed = [201, 200]
    expect_black = [210, 211, 212, 213, 214, 215]

    section = VideoSection(FakeSectionAdapter(FAKES[3]))
    data = section.to_dict()
    result_range = data['RANGE_FRAME_ID']
    result_removed = data['REMOVED_FRAMES']
    result_black = data['BLACK_LIST']

    assert expect_range == result_range
    assert expect_removed == result_removed
    assert expect_black == result_black


# ############### Teste para `SectionWrapper` ####################

def test_SectionWrapper_to_dict():
    expect = [
        {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [201, 200], 'BLACK_LIST': [210, 211, 212, 213, 214, 215]},
        {'RANGE_FRAME_ID': (300, 395), 'REMOVED_FRAMES': [396, 397, 398, 399], 'BLACK_LIST': []}
    ]
    section_1 = VideoSection(FakeSectionAdapter(FAKES[3]))
    section_2 = VideoSection(FakeSectionAdapter(FAKES[4]))
    wrapper = SectionWrapper(section_1, section_2)
    result = wrapper.to_dict()
    assert expect == result


def test_SectionWrapper_to_dict_com_None():
    expect = [
        {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [201, 200], 'BLACK_LIST': [210, 211, 212, 213, 214, 215]},
        None
    ]
    section_1 = VideoSection(FakeSectionAdapter(FAKES[3]))
    wrapper = SectionWrapper(section_1)
    result = wrapper.to_dict()
    assert expect == result


# ################ Testes para o SectionManager #####################33

def test_SectionManager_com_dados_vazios():
    expect = 'there are no sections id to work with'
    with pytest.raises(SectionManagerError) as excinfo:
        data = {'SECTIONS': [], 'REMOVED': []}
        SectionManager(FakeSectionManagerAdapter(data))
    result = f'{excinfo.value}'
    assert expect == result


def test_SectionManager_com_sections_vazios():
    data = {
        'SECTIONS': [],
        'REMOVED':
        [
            [
                {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
                None
            ]
        ]
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    assert secman.removed_sections.empty()


def test_SectionManager_primeira_section():
    result = 0
    data = {
        'SECTIONS': [{'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []}],
        'REMOVED': []
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    expect = secman.section_id
    assert expect == result


def test_SectionManager_next_section_1x():
    result = 100
    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN0))
    secman._next_section()
    expect = secman.section_id
    assert expect == result


def test_SectionManager_next_section_2x():
    result = 200
    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN0))
    [secman._next_section() for _ in range(2)]
    expect = secman.section_id
    assert expect == result


def test_SectionManager_next_section_ate_o_final_5x():
    result = 500
    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN0))
    [secman._next_section() for _ in range(5)]
    expect = secman.section_id
    assert expect == result


def test_SectionManager_next_section_no_final():
    result = 500
    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN0))
    [secman._next_section() for _ in range(5)]
    secman._next_section()
    expect = secman.section_id
    assert expect == result


def test_SectionManager_prev_section_no_inicio():
    result = 0
    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN0))
    secman._prev_section()
    expect = secman.section_id
    assert expect == result


def test_SectionManager_prev_section_1x_apos_2x_next_section():
    result = 100
    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN0))
    [secman._next_section() for _ in range(2)]
    secman._prev_section()
    expect = secman.section_id
    assert expect == result


def test_SectionManager_prev_section_1x_no_final():
    result = 401
    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN0))
    [secman._next_section() for _ in range(5)]
    secman._prev_section()
    expect = secman.section_id
    assert expect == result


def test_SectionManager_prev_section_2x_no_final():
    result = 300
    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN0))
    [secman._next_section() for _ in range(5)]
    [secman._prev_section() for _ in range(2)]
    expect = secman.section_id
    assert expect == result


def test_SectionManager_prev_section_5x_voltando_para_o_inicio():
    result = 0
    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN0))
    [secman._next_section() for _ in range(5)]
    [secman._prev_section() for _ in range(5)]
    expect = secman.section_id
    assert expect == result


def test_SectionManager_remove_section_com_removed_section_vazia(trash):
    data = {
        'SECTIONS': [{'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []}],
        'REMOVED': []
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    secman.remove_section(trash)
    assert secman.removed_sections.empty()


def test_SectionManager_remove_section_com_removed_sections_vazia(trash):
    data = {
        'SECTIONS': [],
        'REMOVED':
        [
            [
                {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
                None
            ]
        ]
    }

    secman = SectionManager(FakeSectionManagerAdapter(data))
    secman.remove_section(trash)
    assert secman.removed_sections.empty()


def test_SectionManager_remove_section_1_secao(trash):
    expect = 100
    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN0))
    secman.remove_section(trash)
    result = secman.section_id
    assert expect == result


def test_SectionManager_remove_section_2_secao(trash):
    expect = 200
    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN0))
    [secman.remove_section(trash) for _ in range(2)]
    result = secman.section_id
    assert expect == result


def test_SectionManager_remove_section_ultimo_secao(trash):
    expect = 401
    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN0))
    [secman._next_section() for _ in range(5)]
    secman.remove_section(trash)
    result = secman.section_id
    assert expect == result


def test_SectionManager_remove_section_todas_as_secoes(trash):
    expect = None
    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN0))
    [secman.remove_section(trash) for _ in range(6)]
    result = secman.section_id
    assert expect == result


def test_SectionManager_remove_section_todas_as_secoes_a_partir_do_ultima(trash):
    expect = None
    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN0))
    [secman._next_section() for _ in range(5)]
    [secman.remove_section(trash) for _ in range(6)]
    result = secman.section_id
    assert expect == result


def test_SectionManager_restore_section_sem_nenhuma_secao_excluida():
    expect = False
    data = {
        'SECTIONS': [{'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []}],
        'REMOVED': []
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    result = secman.restore_section()
    assert expect == result


def test_SectionManager_restore_section_excluida_pela_importacao_dos_dados_e_secao_vazia_insercao_pilha_atual():
    # Caso zero a inserção ocorre na posição atual da pilha superior, pois as dua pilha estão vazias
    expect = 100
    data = {
        'SECTIONS': [],
        'REMOVED':
        [
            [
                {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134], 'BLACK_LIST': []},
                None
            ]
        ]
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    assert secman.restore_section()

    result = secman.section_id
    assert expect == result


# ############ Inserção ocorre na pilha superior #############

def test_SectionManager_restore_section_excluida_pela_importacao_dos_dados_insercao_na_pilha_atual():
    # Caso 1a a inserção ocorre na pilha superior, pois a pilha inferior está vazia
    expect = 0
    data = {
        'SECTIONS': [
            {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [201, 200], 'BLACK_LIST': [210, 211, 212, 213, 214, 215]},
            {'RANGE_FRAME_ID': (300, 395), 'REMOVED_FRAMES': [396, 397, 398, 399], 'BLACK_LIST': []}
        ],
        'REMOVED':
        [
            [
                {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
                None
            ]
        ]
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    secman.restore_section()
    result = secman.section_id
    assert expect == result


def test_SectionManager_restore_section_excluida_pela_importacao_dos_dados_pilha_inferior_vazia_insercao_pilha_atual():
    # Caso 1a a inserção ocorre na pilha superior, pois a pilha inferior está vazia
    expect = 0
    data = {
        'SECTIONS': [
            {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [201, 200], 'BLACK_LIST': [210, 211, 212, 213, 214, 215]},
            {'RANGE_FRAME_ID': (300, 395), 'REMOVED_FRAMES': [396, 397, 398, 399], 'BLACK_LIST': []}
        ],
        'REMOVED':
        [
            [
                {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
                None
            ]
        ]
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    secman.restore_section()
    result = secman.section_id
    assert expect == result


def test_SectionManager_restore_section_excluida_pela_importacao_dos_dados_pilha_inferior_vazia_insercao_pilha_superior():
    # Caso 1b a inserção ocorre na pilha superior, pois a pilha inferior está vazia
    expect = 300
    data = {
        'SECTIONS': [
            {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (300, 395), 'REMOVED_FRAMES': [396, 397, 398, 399], 'BLACK_LIST': []}
        ],
        'REMOVED':
        [
            [
                {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [201, 200], 'BLACK_LIST': [210, 211, 212, 213, 214, 215]},
                None
            ]
        ]
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    secman.restore_section()

    # Devemos checar o id da próxima seção para verificar se a seção restaurada
    # está no lugar certo
    secman._next_section()
    result = secman.section_id

    assert expect == result


def test_SectionManager_restore_section_excluida_pela_importacao_dos_dados_pilha_inferior_vazia_insercao_pilha_superior_ultimo_elemento():
    # Caso 1b a inserção ocorre na pilha superior, pois a pilha inferior está vazia
    expect = 300
    data = {
        'SECTIONS': [
            {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [201, 200], 'BLACK_LIST': [210, 211, 212, 213, 214, 215]}
        ],
        'REMOVED':
        [
            [
                {'RANGE_FRAME_ID': (300, 395), 'REMOVED_FRAMES': [396, 397, 398, 399], 'BLACK_LIST': []},
                None
            ]
        ]
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    secman.restore_section()

    # Devemos checar o id da próxima seção para verificar se a seção restaurada
    # está no lugar certo
    secman._next_section()
    result = secman.section_id

    assert expect == result


def test_SectionManager_restore_section_excluida_pela_importacao_dos_dados_pilha_inferior_nao_vazia_insercao_pilha_superior():
    # Caso 1b a inserção ocorre na pilha superior, pois a pilha inferior está vazia
    expect = 300
    data = {
        'SECTIONS': [
            {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (300, 395), 'REMOVED_FRAMES': [396, 397, 398, 399], 'BLACK_LIST': []}
        ],
        'REMOVED':
        [
            [
                {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [201, 200], 'BLACK_LIST': [210, 211, 212, 213, 214, 215]},
                None
            ]
        ]
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    secman._next_section()
    secman.restore_section()

    # Devemos checar o id da próxima seção para verificar se a seção restaurada
    # está no lugar certo
    secman._next_section()
    result = secman.section_id

    assert expect == result


# ####### Inserção ocorre na pilha inferior

def test_SectionManager_restore_section_excluida_pela_importacao_dos_dados_insercao_na_pilha_atual_com_pilha_inferior_nao_vazia():
    # Caso 2b a inserção ocorre na pilha atual, pois o elemento esta na posicao correta
    expect = 200
    data = {
        'SECTIONS': [
            {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [201, 200], 'BLACK_LIST': [210, 211, 212, 213, 214, 215]},
            {'RANGE_FRAME_ID': (300, 395), 'REMOVED_FRAMES': [396, 397, 398, 399], 'BLACK_LIST': []}
        ],
        'REMOVED':
        [
            [
                {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134], 'BLACK_LIST': []},
                None
            ]
        ]
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    secman._next_section()
    secman.restore_section()
    secman._next_section()
    result = secman.section_id
    assert expect == result


def test_SectionManager_restore_section_excluida_pela_importacao_dos_dados_pilha_inferior_nao_vazia_insercao_pilha_inferior():
    # Caso 1b a inserção ocorre na pilha superior, pois a pilha inferior está vazia
    expect = 200
    data = {
        'SECTIONS': [
            {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [201, 200], 'BLACK_LIST': [210, 211, 212, 213, 214, 215]},
            {'RANGE_FRAME_ID': (300, 395), 'REMOVED_FRAMES': [396, 397, 398, 399], 'BLACK_LIST': []}
        ],
        'REMOVED':
        [
            [
                {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134], 'BLACK_LIST': []},
                None
            ]
        ]
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    [secman._next_section() for _ in range(2)]

    secman.restore_section()

    # Devemos checar o id da próxima seção para verificar se a seção restaurada
    # está no lugar certo
    secman._next_section()
    result = secman.section_id

    assert expect == result


def test_SectionManager_restore_section_excluida_pela_importacao_dos_dados_pilha_inferior_nao_vazia_insercao_pilha_inferior_no_inicio():
    # Caso 1b a inserção ocorre na pilha superior, pois a pilha inferior está vazia
    expect = 100
    data = {
        'SECTIONS': [
            {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [201, 200], 'BLACK_LIST': [210, 211, 212, 213, 214, 215]},
            {'RANGE_FRAME_ID': (300, 395), 'REMOVED_FRAMES': [396, 397, 398, 399], 'BLACK_LIST': []},
        ],
        'REMOVED':
        [
            [
                {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
                None
            ]
        ]
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    [secman._next_section() for _ in range(3)]
    secman.restore_section()

    # Devemos checar o id da próxima seção para verificar se a seção restaurada
    # está no lugar certo
    secman._next_section()
    result = secman.section_id

    assert expect == result


def test_SectionManager_restore_section_excluida_manual_do_1_elemento_e_insercao_na_posicao_atual(trash):
    expect = 100
    data = {
        'SECTIONS': [
            {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [201, 200], 'BLACK_LIST': [210, 211, 212, 213, 214, 215]},
            {'RANGE_FRAME_ID': (300, 395), 'REMOVED_FRAMES': [396, 397, 398, 399], 'BLACK_LIST': []}
        ],
        'REMOVED': []
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    secman.remove_section(trash)
    secman.restore_section()

    # Devemos checar o id da próxima seção para verificar se a seção restaurada
    # está no lugar certo
    secman._next_section()
    result = secman.section_id

    assert expect == result


def test_SectionManager_restore_section_excluida_manual_do_elemento_ao_meio_e_insercao_na_pilha_superior(trash):
    expect = 300
    data = {
        'SECTIONS': [
            {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [201, 200], 'BLACK_LIST': [210, 211, 212, 213, 214, 215]},
            {'RANGE_FRAME_ID': (300, 395), 'REMOVED_FRAMES': [396, 397, 398, 399], 'BLACK_LIST': []}
        ],
        'REMOVED': []
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    [secman._next_section() for _ in range(2)]
    secman.remove_section(trash)

    secman._prev_section()
    secman.restore_section()

    # Devemos checar o id da próxima seção para verificar se a seção restaurada
    # está no lugar certo
    secman._next_section()
    result = secman.section_id

    assert expect == result


def test_SectionManager_restore_section_excluida_manual_do_elemento_ao_meio_e_insercao_na_pilha_inferior(trash):
    expect = 200
    data = {
        'SECTIONS': [
            {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [201, 200], 'BLACK_LIST': [210, 211, 212, 213, 214, 215]},
            {'RANGE_FRAME_ID': (300, 395), 'REMOVED_FRAMES': [396, 397, 398, 399], 'BLACK_LIST': []}
        ],
        'REMOVED': []
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    secman._next_section()
    secman.remove_section(trash)
    [secman._next_section() for _ in range(2)]

    secman._prev_section()
    secman.restore_section()

    # Devemos checar o id da próxima seção para verificar se a seção restaurada
    # está no lugar certo
    secman._next_section()
    result = secman.section_id

    assert expect == result


def test_SectionManager_restore_section_excluida_manual_do_ultimo_elemento_e_insercao_sem_prev_section(trash):
    expect = 300
    data = {
        'SECTIONS': [
            {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [201, 200], 'BLACK_LIST': [210, 211, 212, 213, 214, 215]},
            {'RANGE_FRAME_ID': (300, 395), 'REMOVED_FRAMES': [396, 397, 398, 399], 'BLACK_LIST': []}
        ],
        'REMOVED': []
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    [secman._next_section() for _ in range(3)]
    secman.remove_section(trash)
    secman.restore_section()

    # Devemos checar o id da próxima seção para verificar se a seção restaurada
    # está no lugar certo
    secman._next_section()
    result = secman.section_id

    assert expect == result


def test_SectionManager_restore_section_excluida_manual_do_ultimo_elemento_e_insercao_com_prev_section(trash):
    expect = 300
    data = {
        'SECTIONS': [
            {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [201, 200], 'BLACK_LIST': [210, 211, 212, 213, 214, 215]},
            {'RANGE_FRAME_ID': (300, 395), 'REMOVED_FRAMES': [396, 397, 398, 399], 'BLACK_LIST': []}
        ],
        'REMOVED': []
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    [secman._next_section() for _ in range(3)]
    secman.remove_section(trash)
    secman._prev_section()
    secman.restore_section()

    # Devemos checar o id da próxima seção para verificar se a seção restaurada
    # está no lugar certo
    secman._next_section()
    result = secman.section_id

    assert expect == result


def test_SectionManager_restore_section_excluida_todos_os_elementos_manualmente_a_partir_do_1_e_restaurando_1_elemento(trash):
    expect = 300
    data = {
        'SECTIONS': [
            {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [201, 200], 'BLACK_LIST': [210, 211, 212, 213, 214, 215]},
            {'RANGE_FRAME_ID': (300, 395), 'REMOVED_FRAMES': [396, 397, 398, 399], 'BLACK_LIST': []}
        ],
        'REMOVED': []
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    [secman.remove_section(trash) for _ in range(4)]
    secman.restore_section()

    # Devemos checar o id da próxima seção para verificar se a seção restaurada
    # está no lugar certo
    secman._next_section()
    result = secman.section_id

    assert expect == result


def test_SectionManager_restore_section_excluida_todos_os_elementos_manualmente_a_partir_do_ultimo_e_restaurando_1_elemento(trash):
    expect = 0
    data = {
        'SECTIONS': [
            {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [201, 200], 'BLACK_LIST': [210, 211, 212, 213, 214, 215]},
            {'RANGE_FRAME_ID': (300, 395), 'REMOVED_FRAMES': [396, 397, 398, 399], 'BLACK_LIST': []}
        ],
        'REMOVED': []
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    [secman._next_section() for _ in range(3)]
    [secman.remove_section(trash) for _ in range(4)]
    secman.restore_section()

    # Devemos checar o id da próxima seção para verificar se a seção restaurada
    # está no lugar certo
    secman._next_section()
    result = secman.section_id

    assert expect == result


def test_SectionManager_restore_section_excluida_todos_os_elementos_manualmente_a_partir_do_1_e_restaurando_todos(trash):
    expect = 100
    data = {
        'SECTIONS': [
            {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [201, 200], 'BLACK_LIST': [210, 211, 212, 213, 214, 215]},
            {'RANGE_FRAME_ID': (300, 395), 'REMOVED_FRAMES': [396, 397, 398, 399], 'BLACK_LIST': []}
        ],
        'REMOVED': []
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    [secman.remove_section(trash) for _ in range(4)]
    [secman.restore_section() for _ in range(4)]

    # Devemos checar o id da próxima seção para verificar se a seção restaurada
    # está no lugar certo
    secman._next_section()
    result = secman.section_id

    assert expect == result


def test_SectionManager_restore_section_excluida_todos_os_elementos_manualmente_a_partir_do_ultimo_e_restaurando_todos(trash):
    expect = 300
    data = {
        'SECTIONS': [
            {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [201, 200], 'BLACK_LIST': [210, 211, 212, 213, 214, 215]},
            {'RANGE_FRAME_ID': (300, 395), 'REMOVED_FRAMES': [396, 397, 398, 399], 'BLACK_LIST': []}
        ],
        'REMOVED': []
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    [secman._next_section() for _ in range(4)]
    [secman.remove_section(trash) for _ in range(4)]
    [secman.restore_section() for _ in range(4)]

    # Devemos checar o id da próxima seção para verificar se a seção restaurada
    # está no lugar certo
    secman._next_section()
    result = secman.section_id

    assert expect == result


# ###################### Unindo a seção atual com a seção anterior #####################

def test_SectionManager_unindo_a_primeira_secao_com_a_anterior(trash):
    expect = 100
    data = {
        'SECTIONS': [
            {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [201, 200], 'BLACK_LIST': [210, 211, 212, 213, 214, 215]},
            {'RANGE_FRAME_ID': (300, 395), 'REMOVED_FRAMES': [396, 397, 398, 399], 'BLACK_LIST': []}
        ],
        'REMOVED': []
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    secman.join_section(trash)

    # Devemos checar o id da próxima seção para verificar se a seção foi
    # unida corretamente
    secman._next_section()
    result = secman.section_id

    assert expect == result


def test_SectionManager_unindo_a_segunda_secao_com_a_anterior(trash):
    expect = 0
    expect_next = 200
    data = {
        'SECTIONS': [
            {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [201, 200], 'BLACK_LIST': [210, 211, 212, 213, 214, 215]},
            {'RANGE_FRAME_ID': (300, 395), 'REMOVED_FRAMES': [396, 397, 398, 399], 'BLACK_LIST': []}
        ],
        'REMOVED': []
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    secman._next_section()
    secman.join_section(trash)

    result = secman.section_id
    secman._next_section()
    result_next = secman.section_id

    assert expect == result
    assert expect_next == result_next


def test_SectionManager_unindo_a_ultima_secao_com_a_anterior(trash):
    expect = 200
    expect_next = 200
    data = {
        'SECTIONS': [
            {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [201, 200], 'BLACK_LIST': [210, 211, 212, 213, 214, 215]},
            {'RANGE_FRAME_ID': (300, 395), 'REMOVED_FRAMES': [396, 397, 398, 399], 'BLACK_LIST': []}
        ],
        'REMOVED': []
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    [secman._next_section() for _ in range(3)]
    secman.join_section(trash)

    result = secman.section_id
    secman._next_section()
    result_next = secman.section_id

    assert expect == result
    assert expect_next == result_next


def test_SectionManager_unindo_todas_as_secoes_a_partir_da_ultima(trash):
    expect = 0
    data = {
        'SECTIONS': [
            {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [201, 200], 'BLACK_LIST': [210, 211, 212, 213, 214, 215]},
            {'RANGE_FRAME_ID': (300, 395), 'REMOVED_FRAMES': [396, 397, 398, 399], 'BLACK_LIST': []}
        ],
        'REMOVED': []
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    [secman._next_section() for _ in range(3)]
    [secman.join_section(trash) for _ in range(3)]

    result = secman.section_id

    assert expect == result


def test_SectionManager_restaura_a_1_secao_unida_com_2_elementos(trash):
    expect_prev = 0
    expect = 100
    data = {
        'SECTIONS': [
            {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134], 'BLACK_LIST': []},
        ],
        'REMOVED': []
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    secman._next_section()
    secman.join_section(trash)
    secman.restore_section()
    result = secman.section_id
    secman._prev_section()
    result_prev = secman.section_id

    assert expect == result
    assert expect_prev == result_prev


def test_SectionManager_restaura_a_1_secao_unida(trash):
    expect_prev = 0
    expect = 100
    data = {
        'SECTIONS': [
            {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [201, 200], 'BLACK_LIST': [210, 211, 212, 213, 214, 215]},
            {'RANGE_FRAME_ID': (300, 395), 'REMOVED_FRAMES': [396, 397, 398, 399], 'BLACK_LIST': []}
        ],
        'REMOVED': []
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    secman._next_section()
    secman.join_section(trash)
    secman.restore_section()
    result = secman.section_id
    secman._prev_section()
    result_prev = secman.section_id

    assert expect == result
    assert expect_prev == result_prev


def test_SectionManager_restaura_a_secao_do_meio_unida(trash):
    expect_prev = 100
    expect = 200
    data = {
        'SECTIONS': [
            {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [201, 200], 'BLACK_LIST': [210, 211, 212, 213, 214, 215]},
            {'RANGE_FRAME_ID': (300, 395), 'REMOVED_FRAMES': [396, 397, 398, 399], 'BLACK_LIST': []}
        ],
        'REMOVED': []
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    [secman._next_section() for _ in range(2)]
    secman.join_section(trash)
    secman.restore_section()
    result = secman.section_id
    secman._prev_section()
    result_prev = secman.section_id

    assert expect == result
    assert expect_prev == result_prev


def test_SectionManager_restaura_a_ultima_secao_unida(trash):
    expect_prev = 200
    expect = 300
    data = {
        'SECTIONS': [
            {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [201, 200], 'BLACK_LIST': [210, 211, 212, 213, 214, 215]},
            {'RANGE_FRAME_ID': (300, 395), 'REMOVED_FRAMES': [396, 397, 398, 399], 'BLACK_LIST': []}
        ],
        'REMOVED': []
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    [secman._next_section() for _ in range(3)]
    secman.join_section(trash)
    secman.restore_section()
    result = secman.section_id
    secman._prev_section()
    result_prev = secman.section_id

    assert expect == result
    assert expect_prev == result_prev


def test_SectionManager_restaura_a_ultima_secao_unida_quando_unimos_todas_as_secoes(trash):
    expect_prev = 0
    expect = 100
    data = {
        'SECTIONS': [
            {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [201, 200], 'BLACK_LIST': [210, 211, 212, 213, 214, 215]},
            {'RANGE_FRAME_ID': (300, 395), 'REMOVED_FRAMES': [396, 397, 398, 399], 'BLACK_LIST': []}
        ],
        'REMOVED': []
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    [secman._next_section() for _ in range(3)]
    [secman.join_section(trash) for _ in range(3)]
    secman.restore_section()
    result = secman.section_id
    secman._prev_section()
    result_prev = secman.section_id

    assert expect == result
    assert expect_prev == result_prev


def test_SectionManager_restaura_todas_as_secao_unida_quando_unimos_todas_as_secoes(trash):
    expect_prev = 200
    expect = 300
    data = {
        'SECTIONS': [
            {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [201, 200], 'BLACK_LIST': [210, 211, 212, 213, 214, 215]},
            {'RANGE_FRAME_ID': (300, 395), 'REMOVED_FRAMES': [396, 397, 398, 399], 'BLACK_LIST': []}
        ],
        'REMOVED': []
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    [secman._next_section() for _ in range(3)]
    [secman.join_section(trash) for _ in range(3)]
    [secman.restore_section() for _ in range(3)]
    result = secman.section_id
    secman._prev_section()
    result_prev = secman.section_id

    assert expect == result
    assert expect_prev == result_prev


def test_SectionManager_restaura_todas_as_secao_unida_quando_unimos_todas_as_secoes_e_removemos_a_ultima_secao(trash):
    expect_prev = 200
    expect = 300
    data = {
        'SECTIONS': [
            {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 149, 148, 147, 136, 135, 134], 'BLACK_LIST': []},
            {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [201, 200], 'BLACK_LIST': [210, 211, 212, 213, 214, 215]},
            {'RANGE_FRAME_ID': (300, 395), 'REMOVED_FRAMES': [396, 397, 398, 399], 'BLACK_LIST': []}
        ],
        'REMOVED': []
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    [secman._next_section() for _ in range(3)]
    [secman.join_section(trash) for _ in range(3)]
    secman.remove_section(trash)
    [secman.restore_section() for _ in range(4)]
    result = secman.section_id
    secman._prev_section()
    result_prev = secman.section_id

    assert expect == result
    assert expect_prev == result_prev


def test_SectionManager_restaura_caso_geral():
    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN))
    secman.restore_section()
    secman.restore_section()
    secman.restore_section()
    secman.restore_section()


# ############## Teste de integração entre o `Trash` e `SectionManager`

def test_SectionManager_carregar_frames_no_memento_do_trash(trash):
    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN0))
    secman.load_mementos_frames(trash)
    assert trash.can_undo()

    expect = 14
    result, _ = trash.undo()
    assert expect == result


def test_SectionManager_proxima_secao_atualizando_o_trash(trash):
    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN0))
    secman.load_mementos_frames(trash)

    secman.next_section(trash)
    expect = 150
    result, _ = trash.undo()
    assert expect == result


def test_SectionManager_secao_anterior_atualizando_o_trash(trash):
    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN0))
    secman.load_mementos_frames(trash)
    secman.next_section(trash)

    secman.prev_section(trash)
    expect = 14
    result, _ = trash.undo()
    assert expect == result


def test_SectionManager_remover_1o_frame_mover_proxima_secao_e_voltar(trash):
    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN0))
    secman.load_mementos_frames(trash)
    trash.move(0, np.zeros((2, 2)))
    secman.next_section(trash)
    secman.prev_section(trash)
    expect = 0
    result, _ = trash.undo()
    assert expect == result


def test_SectionManager_to_dict_SECTIONS(trash):
    expect = FAKEMAN['SECTIONS']
    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN))
    result = secman.to_dict(trash)
    assert expect == result['SECTIONS']


def test_SectionManager_to_dict_SECTIONS_com_next_3x(trash):
    expect = FAKEMAN['SECTIONS']
    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN))
    [secman.next_section(trash) for _ in range(3)]
    result = secman.to_dict(trash)
    assert expect == result['SECTIONS']


def test_SectionManager_to_dict_REMOVED_sections(trash):
    expect = FAKEMAN['REMOVED']
    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN))
    result = secman.to_dict(trash)
    assert expect == result['REMOVED']


def test_SectionManager_to_dict_sections(trash):
    expect = FAKEMAN
    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN))
    result = secman.to_dict(trash)
    assert expect == result


# ################# Testes para dividir a seção em duas ###################### #

def test_SectionManager_split_section_no_1o_frame_da_1o_secao(trash):
    expect = False
    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN0))
    result = secman.split_section(0, trash)
    assert expect == result


def test_SectionManager_split_section_no_2o_frame_da_1o_secao(trash):
    expect = True
    expect_id = 1
    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN0))
    result = secman.split_section(1, trash)
    section = secman.get_section()
    result_id = section.id_
    assert expect == result
    assert expect_id == result_id


def test_SectionManager_split_section_sem_load_memento_frames(trash):
    expect_1 = deque([396, 397, 398, 399, 498, 401, 499, 402])
    expect_2 = deque([150, 149, 148, 147, 136, 135, 134, ])

    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN))
    secman.split_section(199, trash)

    section_1 = secman.get_section()
    result_1 = section_1.get_trash()
    secman.prev_section(trash)
    section_2 = secman.get_section()
    result_2 = section_2.get_trash()
    secman.store_mementos_frames(trash)

    assert expect_1 == result_1
    assert expect_2 == result_2


def test_SectionManager_split_section_com_load_memento_frame_antes(trash):
    expect = deque([396, 397, 398, 399, 498, 401, 499, 402])

    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN))
    secman.load_mementos_frames(trash)
    secman.split_section(199, trash)

    section = secman.get_section()
    result = section.get_trash()

    assert expect == result


def test_SectionManager_split_section_mal_sucedida(trash):
    expect_id = 200

    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN0))
    secman.load_mementos_frames(trash)
    [secman.next_section(trash) for _ in range(2)]
    secman.split_section(159, trash)

    section = secman.get_section()
    result_id = section.id_

    assert expect_id == result_id


def test_SectionManager_split_section_mal_sucedida_checar_frames_removidos(trash):
    expect = deque([])

    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN0))
    secman.load_mementos_frames(trash)
    [secman.next_section(trash) for _ in range(2)]
    secman.split_section(159, trash)

    section = secman.get_section()
    result = section.get_trash()

    assert expect == result


def test_SectionManager_restore_section_apos_split_na_primeira_secao(trash):
    data = {
        "SECTIONS": [
            {"RANGE_FRAME_ID": [0, 891], "REMOVED_FRAMES": [], "BLACK_LIST": []},
            {"RANGE_FRAME_ID": [892, 2640], "REMOVED_FRAMES": [], "BLACK_LIST": []}
        ],
        "REMOVED": [[
            {"RANGE_FRAME_ID": [0, 2640], "REMOVED_FRAMES": [], "BLACK_LIST": []},
            None
        ]]
    }
    expect = 1
    secman = SectionManager(FakeSectionManagerAdapter(data))
    secman.restore_section()
    result = len(secman)
    assert expect == result


def test_SectionManager_restore_section_apos_split_e_na_utlima_secao(trash):
    data = {
        "SECTIONS": [
            {"RANGE_FRAME_ID": [0, 891], "REMOVED_FRAMES": [], "BLACK_LIST": []},
            {"RANGE_FRAME_ID": [892, 2640], "REMOVED_FRAMES": [], "BLACK_LIST": []}
        ],
        "REMOVED": [[
            {"RANGE_FRAME_ID": [0, 2640], "REMOVED_FRAMES": [], "BLACK_LIST": []},
            None
        ]]
    }
    expect = 1
    secman = SectionManager(FakeSectionManagerAdapter(data))
    secman.next_section(trash)
    secman.restore_section()
    result = len(secman)
    assert expect == result


def test_SectionManager_restore_section_apos_5x_split_na_primeira_secao(trash):
    expect = 5
    expect_id = 1274
    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN1))
    secman.restore_section()
    result = len(secman)

    section = secman.get_section()
    result_id = section.id_
    assert expect == result
    assert expect_id == result_id


def test_SectionManager_restore_section_apos_5x_split_na_ultima_secao(trash):
    expect = 5
    expect_id = 1274
    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN1))
    [secman.next_section(trash) for _ in range(5)]
    secman.restore_section()
    result = len(secman)

    section = secman.get_section()
    result_id = section.id_
    assert expect == result
    assert expect_id == result_id


def test_SectionManager_restore_section_2x_apos_5x_split_na_primeira_secao(trash):
    expect = 4
    expect_id = 947
    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN1))
    secman.restore_section()
    secman.restore_section()
    result = len(secman)

    section = secman.get_section()
    result_id = section.id_
    assert expect == result
    assert expect_id == result_id


def test_SectionManager_restore_section_2x_apos_5x_split_na_segunda_secao(trash):
    expect = 4
    expect_id = 947
    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN1))
    [secman.next_section(trash) for _ in range(2)]
    secman.restore_section()
    secman.restore_section()
    result = len(secman)

    section = secman.get_section()
    result_id = section.id_
    assert expect == result
    assert expect_id == result_id


def test_SectionManager_restore_section_2x_apos_5x_split_na_ultima_secao(trash):
    expect = 4
    expect_id = 947
    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN1))
    [secman.next_section(trash) for _ in range(5)]
    secman.restore_section()
    secman.restore_section()
    result = len(secman)

    section = secman.get_section()
    result_id = section.id_
    assert expect == result
    assert expect_id == result_id


def test_SectionManager_restore_section_tudo_apartir_da_primeira_secao(trash):
    expect = 1
    secman = SectionManager(FakeSectionManagerAdapter(FAKEMAN1))
    [secman.restore_section() for _ in range(5)]
    result = len(secman)
    assert expect == result


def test_SectionManager_restore_section_nao_linear_a_partir_da_primeira_secao(trash):
    expect = 2
    expect_id = 0
    data = {
        "SECTIONS": [
            {"RANGE_FRAME_ID": [0, 511], "REMOVED_FRAMES": [], "BLACK_LIST": []},
            {"RANGE_FRAME_ID": [512, 1080], "REMOVED_FRAMES": [], "BLACK_LIST": []},
            {"RANGE_FRAME_ID": [1081, 2640], "REMOVED_FRAMES": [], "BLACK_LIST": []}
        ],
        "REMOVED": [
            [
                {"RANGE_FRAME_ID": [0, 2640], "REMOVED_FRAMES": [], "BLACK_LIST": []},
                None
            ],
            [
                {"RANGE_FRAME_ID": [0, 1080], "REMOVED_FRAMES": [], "BLACK_LIST": []},
                None
            ]
        ]
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    secman.restore_section()
    result = len(secman)

    section = secman.get_section()
    result_id = section.id_
    assert expect == result
    assert expect_id == result_id


def test_SectionManager_restore_section_nao_linear_a_partir_da_ultima_secao(trash):
    expect = 2
    expect_id = 0
    data = {
        "SECTIONS": [
            {"RANGE_FRAME_ID": [0, 511], "REMOVED_FRAMES": [], "BLACK_LIST": []},
            {"RANGE_FRAME_ID": [512, 1080], "REMOVED_FRAMES": [], "BLACK_LIST": []},
            {"RANGE_FRAME_ID": [1081, 2640], "REMOVED_FRAMES": [], "BLACK_LIST": []}
        ],
        "REMOVED": [
            [
                {"RANGE_FRAME_ID": [0, 2640], "REMOVED_FRAMES": [], "BLACK_LIST": []},
                None
            ],
            [
                {"RANGE_FRAME_ID": [0, 1080], "REMOVED_FRAMES": [], "BLACK_LIST": []},
                None
            ]
        ]
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    [secman.next_section(trash) for _ in range(2)]
    secman.restore_section()
    result = len(secman)
    section = secman.get_section()
    result_id = section.id_
    assert expect == result
    assert expect_id == result_id


def test_SectionManager_restore_section_tudo_nao_linear_a_partir_da_primeira_secao(trash):
    expect = 1
    expect_id = 0
    data = {
        "SECTIONS": [
            {"RANGE_FRAME_ID": [0, 511], "REMOVED_FRAMES": [], "BLACK_LIST": []},
            {"RANGE_FRAME_ID": [512, 1080], "REMOVED_FRAMES": [], "BLACK_LIST": []},
            {"RANGE_FRAME_ID": [1081, 2640], "REMOVED_FRAMES": [], "BLACK_LIST": []}
        ],
        "REMOVED": [
            [
                {"RANGE_FRAME_ID": [0, 2640], "REMOVED_FRAMES": [], "BLACK_LIST": []},
                None
            ],
            [
                {"RANGE_FRAME_ID": [0, 1080], "REMOVED_FRAMES": [], "BLACK_LIST": []},
                None
            ]
        ]
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    [secman.restore_section() for _ in range(2)]
    result = len(secman)

    section = secman.get_section()
    result_id = section.id_
    assert expect == result
    assert expect_id == result_id


def test_SectionManager_restore_section_tudo_nao_linear_a_partir_da_ultima_secao(trash):
    expect = 1
    expect_id = 0
    data = {
        "SECTIONS": [
            {"RANGE_FRAME_ID": [0, 511], "REMOVED_FRAMES": [], "BLACK_LIST": []},
            {"RANGE_FRAME_ID": [512, 1080], "REMOVED_FRAMES": [], "BLACK_LIST": []},
            {"RANGE_FRAME_ID": [1081, 2640], "REMOVED_FRAMES": [], "BLACK_LIST": []}
        ],
        "REMOVED": [
            [
                {"RANGE_FRAME_ID": [0, 2640], "REMOVED_FRAMES": [], "BLACK_LIST": []},
                None
            ],
            [
                {"RANGE_FRAME_ID": [0, 1080], "REMOVED_FRAMES": [], "BLACK_LIST": []},
                None
            ]
        ]
    }
    secman = SectionManager(FakeSectionManagerAdapter(data))
    [secman.next_section(trash) for _ in range(2)]
    [secman.restore_section() for _ in range(2)]

    result = len(secman)
    section = secman.get_section()
    result_id = section.id_
    assert expect == result
    assert expect_id == result_id
