from pytest import fixture, raises
from aniseek.custom_exceptions import InvalidFrameIdError
from aniseek.frame_mapper import FrameMapper
from aniseek.interfaces import IFakeVideoBuffer
import pytest


@fixture
def frame_map(request):
    frame_id, frame_count = request.param
    yield FrameMapper(frame_id, frame_count)


@pytest.mark.parametrize('frame_map', [([], 300)], indirect=True)
def test_FrameMapper_com_lista_vazia_get_mapping(frame_map):
    expect = set()
    result = frame_map.get_mapping()
    assert result == expect


@pytest.mark.parametrize('frame_map', [([], 300)], indirect=True)
def test_FrameMapper_com_lista_vazia__getitems__(frame_map):
    expect = None
    result = frame_map[0]
    assert result == expect


@pytest.mark.parametrize('frame_map', [(list(range(300)), 300)], indirect=True)
def test_FrameMapper_com_lista_igual_ao_count_frame(frame_map):
    expect = set(range(300))
    result = frame_map.get_mapping()
    assert result == expect


@pytest.mark.parametrize('frame_map', [(list(range(300)), 300)], indirect=True)
def test_FrameMapper_com_lista_igual_ao_count_frame_checando_ultimo_frame(frame_map):
    expect = 299
    result = frame_map[-1]
    assert result == expect


@pytest.mark.parametrize('frame_map', [(list(range(150)), 300)], indirect=True)
def test_FrameMapper_com_lista_menor_que_count_frame(frame_map):
    expect = 149
    result = frame_map[-1]
    assert result == expect


@pytest.mark.parametrize('frame_map', [(list(range(600)), 300)], indirect=True)
def test_FrameMapper_com_lista_maior_que_count_frame(frame_map):
    expect = 299
    result = frame_map[-1]
    assert result == expect


@pytest.mark.parametrize('frame_map', [(list(range(100)), 300)], indirect=True)
def test_FrameMapper_set_mapping_com_lista_igual_ao_count_frame(frame_map):
    expect = set(range(200))
    frame_map.set_mapping(list(range(200)), 200, [IFakeVideoBuffer()])
    result = frame_map.get_mapping()
    assert result == expect


@pytest.mark.parametrize('frame_map', [(list(range(300)), 300)], indirect=True)
def test_FrameMapper_set_mapping_com_lista_igual_ao_count_frame_checando_ultimo_frame(frame_map):
    expect = 199
    frame_map.set_mapping(list(range(200)), 200, [IFakeVideoBuffer()])
    result = frame_map[-1]
    assert result == expect


@pytest.mark.parametrize('frame_map', [(list(range(150)), 300)], indirect=True)
def test_FrameMapper_set_mapping_com_lista_menor_que_count_frame(frame_map):
    expect = 99
    frame_map.set_mapping(list(range(100)), 200, [IFakeVideoBuffer()])
    result = frame_map[-1]
    assert result == expect


@pytest.mark.parametrize('frame_map', [(list(range(600)), 300)], indirect=True)
def test_FrameMapper_set_mapping_com_lista_maior_que_count_frame(frame_map):
    expect = 199
    frame_map.set_mapping(list(range(600)), 200, [IFakeVideoBuffer()])
    result = frame_map[-1]
    assert result == expect


@pytest.mark.parametrize('frame_map', [(list(range(300)), 300)], indirect=True)
def test_FrameMapper_frame_id_esta_no_mapping(frame_map):
    expect = True
    expect_id = 2
    result = 2 in frame_map
    result_id = frame_map[2]
    assert result == expect
    assert result_id == expect_id


@pytest.mark.parametrize('frame_map', [(list(range(0, 300, 4)), 300)], indirect=True)
def test_FrameMapper_frame_id_nao_esta_no_mapping(frame_map):
    expect = False
    expect_id = 2
    result = 2 in frame_map
    result_id = frame_map[2]
    assert result == expect
    assert result_id != expect_id


@pytest.mark.parametrize('frame_map', [(list(range(0, 300, 4)), 300)], indirect=True)
def test_FrameMapper_add_frame_id_que_nao_esta_no_mapping(frame_map):
    expect = True
    expect_id = 2
    frame_map.add(2)
    result_id = frame_map[1]
    result = 2 in frame_map
    assert result == expect
    assert result_id == expect_id


@pytest.mark.parametrize('frame_map', [(list(range(0, 300, 4)), 300)], indirect=True)
def test_FrameMapper_add_frame_id_menor_que_zero(frame_map):
    with raises(InvalidFrameIdError) as excinfo:
        frame_map.add(-1)
    assert excinfo.value.message == 'frame_id must be greater than zero'


@pytest.mark.parametrize('frame_map', [(list(range(0, 300, 4)), 300)], indirect=True)
def test_FrameMapper_add_frame_id_maior_que_frame_count(frame_map):
    with raises(InvalidFrameIdError) as excinfo:
        frame_map.add(300)
    assert excinfo.value.message == 'frame_id must be less than frame_count'


@pytest.mark.parametrize('frame_map', [(list(range(10)), 10)], indirect=True)
def test_FrameMapper_remove_frame_id(frame_map):
    expect = False
    frame_map.remove(2)
    result = 2 in frame_map
    assert result == expect


@pytest.mark.parametrize('frame_map', [(list(range(10)), 10)], indirect=True)
def test_FrameMapper_add_frame_id_ja_existente(frame_map):
    frame_id = 5
    expect = f'frame_id "{frame_id}" is already in the mapping'
    with raises(InvalidFrameIdError) as excinfo:
        frame_map.add(frame_id)
    assert excinfo.value.message == expect
