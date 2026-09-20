from array import array
from unittest.mock import patch

import pytest
from pytest import fixture

from aniseek.view.video import VideoCon
from tests.uteis import MyVideoCapture


@fixture
def mycap():
    with patch('aniseek.core.sources.opencv.cv2.VideoCapture', return_value=MyVideoCapture(frame_count=300)) as mock:
        yield mock


@fixture
def creating_window():
    with patch('aniseek.view.video.VideoCon._VideoCon__creating_window', return_value=None) as mock:
        yield mock


@fixture
def myvideo(mycap, creating_window):
    with patch('aniseek.editing.section.SectionManager.get_mapping', return_value=list(range(300))):
        video = VideoCon('model.mp4')
        yield video
        video.join()


@pytest.mark.skip('deprecado')
def test_Video_set_mapping(myvideo):
    expect = 300
    result = len(myvideo._mapping.get_mapping())
    assert result == expect


@pytest.mark.skip('deprecado')
def test_Video_set_mapping_manualmente(myvideo):
    expect = array('l', [0, 1, 2, 3, 4])
    myvideo.set_mapping([1, 2, 0, 3, 4])
    resultd = myvideo._mapping.frame_ids
    assert resultd == expect


def test_Video_read_verificando_se_a_leitura_foi_bem_sucedida(myvideo):
    expect = True
    result, _ = myvideo.read()
    assert result == expect


def test_Video_read_frame_0(myvideo):
    expect_frame_id = 0
    myvideo.read()
    result_frame_id = myvideo.frame_id
    assert result_frame_id == expect_frame_id


def test_Video_read_60_frames(myvideo):
    expect_frames_id = list(range(60))
    result_frames_id = []
    for _ in range(60):
        myvideo.read()
        result_frames_id.append(myvideo.frame_id)
    assert result_frames_id == expect_frames_id


def test_Video_read_300_frames(myvideo):
    expect_frames_id = list(range(300))
    result_frames_id = []
    for _ in range(300):
        myvideo.read()
        result_frames_id.append(myvideo.frame_id)
    assert result_frames_id == expect_frames_id


def test_Video_read_verificando_se_a_leitura_resume_foi_bem_sucedida_e_falhando(myvideo):
    expect = False
    for _ in range(300):
        myvideo.read()
    result, _ = myvideo.read()
    assert result == expect


def test_Video_read_300_frames_e_voltando_1(myvideo):
    expect = 298
    for _ in range(300):
        myvideo.read()
    myvideo.control(ord('a'))
    myvideo.read()
    result = myvideo.frame_id
    assert result == expect


@pytest.mark.skip(reason='Por equanto o programa esta definido para receber None quando chega ao final')
def test_Video_read_300_frames_e_voltando_tudo(myvideo):
    expect = 0
    for _ in range(300):
        myvideo.read()
    myvideo.control(ord('a'))
    for _ in range(300):
        myvideo.read()
    result = myvideo.frame_id
    assert result == expect


def test_Video_read_verificando_se_a_leitura_rewind_foi_bem_sucedida_e_falhando(myvideo):
    expect = False
    myvideo.control(ord('a'))
    result, _ = myvideo.read()
    assert result == expect


def test_Video_read_300_frames_e_voltando_tudo_teste_se_foi_bem_sucedida_e_falhando(myvideo):
    expect = False
    for _ in range(300):
        myvideo.read()
    myvideo.control(ord('a'))
    for _ in range(300):
        myvideo.read()
    result, _ = myvideo.read()
    assert result == expect


@pytest.mark.skip(reason='Fica para depois')
def test_Video_set_150_e_read_tudo(myvideo):
    expect = 299
    myvideo.set(150)
    for _ in range(150):
        myvideo.read()
    result = myvideo.frame_id
    assert result == expect
