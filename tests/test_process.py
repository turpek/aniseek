from collections import deque

from pytest import raises

from aniseek.custom_exceptions import SectionSplitProcessError
from aniseek.editing.adapter import FakeSectionAdapter, SectionSplitProcess
from aniseek.editing.section import VideoSection

FAKES = {
    'SECTION_IDS': [1, 2, 4],
    'REMOVED_IDS': [5, 3, 6],
    1: {'RANGE_FRAME_ID': (0, 99), 'REMOVED_FRAMES': [14, 13, 12, 11, 10], 'BLACK_LIST': []},
    2: {'RANGE_FRAME_ID': (100, 199), 'REMOVED_FRAMES': [150, 136, 148, 147, 135, 149, 134], 'BLACK_LIST': []},
    3: {'RANGE_FRAME_ID': (202, 299), 'REMOVED_FRAMES': [201, 200], 'BLACK_LIST': [210, 258, 212, 253, 254, 215]},
    4: {'RANGE_FRAME_ID': (300, 395), 'REMOVED_FRAMES': [396, 397, 398, 399], 'BLACK_LIST': []},
    5: {'RANGE_FRAME_ID': (403, 497), 'REMOVED_FRAMES': [498, 401, 499, 402], 'BLACK_LIST': [400]},
    6: {'RANGE_FRAME_ID': (500, 599), 'REMOVED_FRAMES': [], 'BLACK_LIST': []},
}


def test_SectionSplitProcess_com_frame_id_igual_ao_start():
    expect = 'cannot split section from start frame'
    with raises(SectionSplitProcessError) as excinfo:
        section = VideoSection(FakeSectionAdapter(FAKES[1]))
        SectionSplitProcess(section, 0)
    result = str(excinfo.value)
    assert expect == result


def test_SectionSplitProcess_com_frame_id_nao_pertencente_a_secao():
    frame_id = 200
    expect = f'Cannot split at position "{frame_id}": frame is either deleted or not in the current section.'
    with raises(SectionSplitProcessError) as excinfo:
        section = VideoSection(FakeSectionAdapter(FAKES[1]))
        SectionSplitProcess(section, frame_id)
    result = str(excinfo.value)
    assert expect == result


def test_SectionSplitProcess_dividir_lista_sem_frames_removidos():
    frame_id = 550

    expect_1 = (500, 549)
    expect_2 = (550, 599)

    section = VideoSection(FakeSectionAdapter(FAKES[6]))
    secsplit = SectionSplitProcess(section, frame_id)
    section_1, section_2 = secsplit.split()

    result_1 = (section_1.start(), section_1.end())
    result_2 = (section_2.start(), section_2.end())

    assert expect_1 == result_1
    assert expect_2 == result_2


def test_SectionSplitProcess_dividir_lista_com_frames_removidos():
    frame_id = 146
    [150, 136, 148, 147, 135, 149, 134]
    expect_1 = deque([136, 135, 134])
    expect_2 = deque([150, 148, 147, 149])

    section = VideoSection(FakeSectionAdapter(FAKES[2]))
    secsplit = SectionSplitProcess(section, frame_id)
    section_1, section_2 = secsplit.split()

    result_1 = section_1.removed_frames()
    result_2 = section_2.removed_frames()

    assert expect_1 == result_1
    assert expect_2 == result_2


def test_SectionSplitProcess_dividir_lista_black_list():
    frame_id = 230
    [210, 258, 212, 253, 254, 215]
    expect_1 = [210, 212, 215]
    expect_2 = [258, 253, 254]

    section = VideoSection(FakeSectionAdapter(FAKES[3]))
    secsplit = SectionSplitProcess(section, frame_id)
    (section_1, section_2) = secsplit.split()

    result_1 = section_1.black_list_frames()
    result_2 = section_2.black_list_frames()

    assert expect_1 == result_1
    assert expect_2 == result_2
