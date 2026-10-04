from array import array
from unittest.mock import patch

import pytest
from pytest import fixture

from aniseek.core.sources.opencv import OpenCVVideoSource
from aniseek.editing.section import SectionManager, VideoSection
from aniseek.view import (
    ViewerTitleContext,
    default_title_formatter,
    truncate_middle,
)
from aniseek.view.interfaces.command import ButtonState, Command
from aniseek.view.shortcuts import IP
from aniseek.view.video import FrameViewer
from aniseek.view.video_command import MacroCommand
from tests.uteis import MyVideoCapture


@fixture
def mycap():
    with patch('aniseek.core.sources.opencv.cv2.VideoCapture', return_value=MyVideoCapture(frame_count=300)) as mock:
        yield mock


@fixture
def creating_window():
    with patch('aniseek.view.video.FrameViewer._FrameViewer__creating_window', return_value=None) as mock:
        yield mock


@fixture
def myvideo(mycap, creating_window):
    with patch('aniseek.editing.section.SectionManager.get_mapping', return_value=list(range(300))):
        video = FrameViewer.from_default('model.mp4')
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
    myvideo.control(ord('a'), ButtonState.PRESS)
    myvideo.read()
    result = myvideo.frame_id
    assert result == expect


@pytest.mark.skip(reason='Por equanto o programa esta definido para receber None quando chega ao final')
def test_Video_read_300_frames_e_voltando_tudo(myvideo):
    expect = 0
    for _ in range(300):
        myvideo.read()
    myvideo.control(ord('a'), ButtonState.PRESS)
    for _ in range(300):
        myvideo.read()
    result = myvideo.frame_id
    assert result == expect


def test_Video_read_verificando_se_a_leitura_rewind_foi_bem_sucedida_e_falhando(myvideo):
    expect = False
    myvideo.control(ord('a'), ButtonState.PRESS)
    result, _ = myvideo.read()
    assert result == expect


def test_Video_read_300_frames_e_voltando_tudo_teste_se_foi_bem_sucedida_e_falhando(myvideo):
    expect = False
    for _ in range(300):
        myvideo.read()
    myvideo.control(ord('a'), ButtonState.PRESS)
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


def test_frame_viewer_init_with_iframe_source(mycap, creating_window):
    """Verifica instanciação direta do FrameViewer com IFrameSource."""
    source = OpenCVVideoSource('test_video.mp4')
    viewer = FrameViewer(source)
    assert viewer.frame_id is None
    success, frame = viewer.read()
    assert success is True
    assert viewer.frame_id == 0
    viewer.join()


def test_frame_viewer_init_raises_type_error_for_invalid_type(creating_window):
    """Verifica que FrameViewer rejeita caminhos str ou tipos não-IFrameSource no construtor."""
    with pytest.raises(TypeError, match='Expected source to be an instance of IFrameSource'):
        FrameViewer('model.mp4')


def test_frame_viewer_from_default_raises_type_error_for_source_instance(mycap, creating_window):
    """Verifica que from_default rejeita instâncias de IFrameSource."""
    source = OpenCVVideoSource('model.mp4')
    with pytest.raises(TypeError, match='from_default.*expects a file path'):
        FrameViewer.from_default(source)


def test_frame_viewer_init_with_injected_dict_sections(mycap, creating_window):
    """Verifica injeção de seções como dicionário no FrameViewer."""
    source = OpenCVVideoSource('test_video.mp4')
    sections_dict = {
        'SECTIONS': [
            {'RANGE_FRAME_ID': (10, 50), 'REMOVED_FRAMES': [], 'BLACK_LIST': []},
        ],
        'REMOVED': [],
    }
    viewer = FrameViewer(source, sections=sections_dict)
    success, frame = viewer.read()
    assert success is True
    assert viewer.frame_id == 10
    viewer.join()


def test_frame_viewer_init_with_injected_section_manager(mycap, creating_window):
    """Verifica injeção de instância de SectionManager no FrameViewer."""
    source = OpenCVVideoSource('test_video.mp4')
    sec = VideoSection(20, 80)
    secman = SectionManager([sec])
    viewer = FrameViewer(source, sections=secman)
    success, frame = viewer.read()
    assert success is True
    assert viewer.frame_id == 20
    viewer.join()


def test_frame_viewer_save_method(mycap, creating_window, tmp_path):
    """Verifica que o método save persiste as seções no arquivo especificado."""
    source = OpenCVVideoSource('test_video.mp4')
    viewer = FrameViewer(source)
    save_file = tmp_path / 'saved_sections.json'
    viewer.save(save_file)
    assert save_file.exists()
    viewer.join()


def test_frame_viewer_save_command_via_shortcut(mycap, creating_window):
    """Verifica execução do SaveCommand através do atalho Ctrl+w."""
    source = OpenCVVideoSource('test_video.mp4')
    viewer = FrameViewer(source)
    with patch.object(viewer._FrameViewer__video_controller, 'save') as mock_save:
        viewer.control(IP.CTRL_BIT | ord('w'), ButtonState.PRESS)
        mock_save.assert_called_once()
    viewer.join()


def test_frame_viewer_custom_shortcuts_in_init(mycap, creating_window):
    """Verifica sobrescrita de atalhos através do parâmetro shortcuts."""
    source = OpenCVVideoSource('test_video.mp4')
    viewer = FrameViewer(source, shortcuts={ord('k'): 'PauseCommand'})
    with patch.object(viewer._FrameViewer__video_controller, 'set_pause') as mock_pause:
        viewer.control(ord('k'), ButtonState.PRESS)
        mock_pause.assert_called_once()
    viewer.join()


def test_frame_viewer_bind_command(mycap, creating_window):
    """Verifica registro e execução de comando personalizado via método bind."""
    source = OpenCVVideoSource('test_video.mp4')
    viewer = FrameViewer(source)
    executed = []

    class CustomCommand(Command):
        def on_press(self) -> None:
            executed.append(True)

    viewer.bind(ord('m'), CustomCommand())
    viewer.control(ord('m'), ButtonState.PRESS)
    assert executed == [True]
    viewer.join()


def test_frame_viewer_bind_raises_type_error_for_non_command(mycap, creating_window):
    """Verifica que o método bind rejeita objetos que não herdam de Command."""
    source = OpenCVVideoSource('test_video.mp4')
    viewer = FrameViewer(source)
    with pytest.raises(TypeError, match='Expected command to be an instance of Command'):
        viewer.bind(ord('m'), lambda: None)
    viewer.join()


def test_macro_command_executes_sequence_in_order():
    """Verifica que MacroCommand executa comandos sequencialmente na ordem fornecida."""
    call_order = []

    class StepCommand(Command):
        def __init__(self, step_id: int):
            self.step_id = step_id

        def on_press(self) -> None:
            call_order.append(self.step_id)

    macro = MacroCommand([StepCommand(1), StepCommand(2), StepCommand(3)])
    macro.executor(ButtonState.PRESS)
    assert call_order == [1, 2, 3]


def test_macro_command_add_appends_commands():
    """Verifica que o método add anexa comandos adicionais ao MacroCommand."""
    call_order = []

    class StepCommand(Command):
        def __init__(self, step_id: int):
            self.step_id = step_id

        def on_press(self) -> None:
            call_order.append(self.step_id)

    macro = MacroCommand([StepCommand(1)])
    macro.add(StepCommand(2))
    macro.executor(ButtonState.PRESS)
    assert call_order == [1, 2]


def test_macro_command_raises_type_error_for_invalid_command():
    """Verifica que MacroCommand rejeita objetos que não herdam de Command."""
    with pytest.raises(TypeError, match='Expected command to be an instance of Command'):
        MacroCommand([lambda: None])


def test_macro_command_bound_to_viewer(mycap, creating_window):
    """Verifica execução de MacroCommand vinculado ao FrameViewer via método bind."""
    source = OpenCVVideoSource('test_video.mp4')
    viewer = FrameViewer(source)
    executed = []

    class ActionCommand(Command):
        def __init__(self, name: str):
            self.name = name

        def on_press(self) -> None:
            executed.append(self.name)

    macro = MacroCommand([ActionCommand('step_1'), ActionCommand('step_2')])
    viewer.bind(ord('z'), macro)
    viewer.control(ord('z'), ButtonState.PRESS)
    assert executed == ['step_1', 'step_2']
    viewer.join()


def test_frame_viewer_directional_right_triggers_dynamic_proceed(mycap, creating_window):
    """Verifica que a tecla direcional direita dispara o DynamicProceedCommand."""
    source = OpenCVVideoSource('test_video.mp4')
    viewer = FrameViewer(source)
    with patch.object(viewer._FrameViewer__video_controller, 'proceed') as mock_proceed:
        viewer.control(IP.KEY_RIGHT, ButtonState.PRESS)
        mock_proceed.assert_called_once()
    viewer.join()


def test_frame_viewer_directional_left_triggers_dynamic_rewind(mycap, creating_window):
    """Verifica que a tecla direcional esquerda dispara o DynamicRewindCommand."""
    source = OpenCVVideoSource('test_video.mp4')
    viewer = FrameViewer(source)
    with patch.object(viewer._FrameViewer__video_controller, 'rewind') as mock_rewind:
        viewer.control(IP.KEY_LEFT, ButtonState.PRESS)
        mock_rewind.assert_called_once()
    viewer.join()


def test_truncate_middle_with_short_and_long_strings():
    """Verifica que truncate_middle preserva strings curtas e resume strings longas no meio."""
    short = "video_01"
    assert truncate_middle(short, 10, 10) == "video_01"
    long_str = "1_vertical_394_kimi_no_koto_ga_dai_dai_dai_dai_daisuki_na_100-nin_no_kanojo_08_1439_1"
    expected = "1_vertical..._08_1439_1"
    assert truncate_middle(long_str, 10, 10) == expected


def test_default_title_formatter_normal_mode():
    """Verifica formatação padrão de título no modo normal com contagem relativa e id global."""
    ctx = ViewerTitleContext(
        frame_id=21055,
        relative_frame=5,
        section_frames=34,
        section_index=1,
        total_sections=6,
        is_preview=False,
        is_rewind=False,
        is_paused=False,
        playlist_index=1,
        playlist_total=15,
        label="1_vertical_394_kimi_no_koto_ga_dai_dai_dai_dai_daisuki_na_100-nin_no_kanojo_08_1439_1",
    )
    title = default_title_formatter(ctx)
    assert title == "videoseq - [1/15] [1_vertical..._08_1439_1] [Seção 1/6 | Frame 5/34 (#21055)] [>>]"


def test_default_title_formatter_preview_and_paused():
    """Verifica formatação padrão no modo preview com reprodução pausada e direção rewind."""
    ctx = ViewerTitleContext(
        frame_id=100,
        relative_frame=1,
        section_frames=50,
        section_index=1,
        total_sections=1,
        is_preview=True,
        is_rewind=True,
        is_paused=True,
        playlist_index=None,
        playlist_total=None,
        label=None,
    )
    title = default_title_formatter(ctx)
    assert title == "videoseq - [PREVIEW | Frame: 100] [<<] (PAUSADO)"


def test_frame_viewer_custom_title_formatter(mycap, creating_window):
    """Verifica que FrameViewer delega a formatação do título da janela ao formatador customizado."""
    source = OpenCVVideoSource('test_video.mp4')
    received_contexts = []

    def custom_formatter(ctx: ViewerTitleContext) -> str:
        received_contexts.append(ctx)
        return f"custom - {ctx.frame_id}"

    with patch('aniseek.view.video.cv2.setWindowTitle') as mock_set_title:
        viewer = FrameViewer(source, title_formatter=custom_formatter)
        viewer.read()
        viewer._update_title()
        mock_set_title.assert_called_with('videoseq', 'custom - 0')
        assert len(received_contexts) >= 1
        assert received_contexts[-1].frame_id == 0
        viewer.join()
