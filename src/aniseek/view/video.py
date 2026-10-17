from __future__ import annotations

from bisect import bisect_left
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from time import sleep

from loguru import logger

from aniseek.config import config
from aniseek.core.interfaces.source import IFrameSource
from aniseek.core.sources.registry import source_registry
from aniseek.editing.manager import VideoManager
from aniseek.editing.playlist import Playlist
from aniseek.editing.section import SectionManager
from aniseek.view.display import CV2Display, resolve_display
from aniseek.view.input_handler import PynputKeyReader
from aniseek.view.interfaces.command import ButtonState, Command
from aniseek.view.interfaces.display import IFrameDisplay
from aniseek.view.interfaces.input import InputHandler
from aniseek.view.shortcuts import PYNPUT_SHORTCUTS, SHORTCUTS
from aniseek.view.video_command import (
    DecreaseSpeedCommand,
    DynamicProceedCommand,
    DynamicRewindCommand,
    IncreaseSpeedCommand,
    Invoker,
    JoinSectionCommand,
    JumpSectionEndCommand,
    JumpSectionStartCommand,
    NextSectionCommand,
    NextVideoCommand,
    NextVideoEndCommand,
    PauseCommand,
    PauseDelayCommand,
    PrevSectionCommand,
    PrevVideoCommand,
    PrevVideoEndCommand,
    ProceesCommand,
    QuitCommand,
    RemoveFrameCommand,
    RemoveSectionCommand,
    RestoreDelayCommand,
    RewindCommand,
    SaveCommand,
    SplitSectionCommand,
    TogglePreviewCommand,
    UndoFrameCommand,
    UndoSectionCommand,
)
from aniseek.view.video_controller import VideoController


@dataclass(frozen=True)
class ViewerTitleContext:
    frame_id: int | None
    relative_frame: int
    section_frames: int
    section_index: int
    total_sections: int
    is_preview: bool
    is_rewind: bool
    is_paused: bool
    playlist_index: int | None
    playlist_total: int | None
    label: str | None


TitleFormatter = Callable[[ViewerTitleContext], str]


def truncate_middle(text: str, head: int = 10, tail: int = 10) -> str:
    """Encurta textos longos preservando o início e o fim separados por reticências."""
    if len(text) <= head + tail + 3:
        return text
    return f"{text[:head]}...{text[-tail:]}"


def default_title_formatter(ctx: ViewerTitleContext) -> str:
    """Formatador padrão exibindo contagem relativa e identificador global."""
    direction_str = '<<' if ctx.is_rewind else '>>'
    paused_str = ' (PAUSADO)' if ctx.is_paused else ''

    prefix = ''
    if ctx.playlist_index is not None and ctx.playlist_total is not None:
        label_str = f'[{truncate_middle(ctx.label)}] ' if ctx.label else ''
        prefix = f'[{ctx.playlist_index}/{ctx.playlist_total}] {label_str}'

    if ctx.is_preview:
        fid_str = str(ctx.frame_id) if ctx.frame_id is not None else '-'
        return f'{prefix}[PREVIEW | Frame: {fid_str}] [{direction_str}]{paused_str}'

    fid_str = f' (#{ctx.frame_id})' if ctx.frame_id is not None else ''
    return (
        f'{prefix}[Seção {ctx.section_index}/{ctx.total_sections} | '
        f'Frame {ctx.relative_frame}/{ctx.section_frames}{fid_str}] '
        f'[{direction_str}]{paused_str}'
    )


class FrameViewer:
    def __init__(
        self,
        source: IFrameSource,
        *,
        sections: SectionManager | dict | Path | str | None = None,
        shortcuts: dict[int, str] | None = None,
        buffersize: int = 60,
        key_reader: type[InputHandler] = PynputKeyReader,
        display: type[IFrameDisplay] | str = CV2Display,
        log: bool = False,
        title_formatter: TitleFormatter | None = None,
    ):
        if not isinstance(source, IFrameSource):
            raise TypeError(
                f"Expected source to be an instance of IFrameSource, got {type(source).__name__}. "
                "Use FrameViewer.from_default(path) if passing a file path or directory."
            )

        self._source = source
        self._log = log
        self._buffersize = buffersize
        display_cls = resolve_display(display)
        self._display: IFrameDisplay = display_cls()
        self._creating_window()

        self._key_reader = key_reader()
        kr = type(self._key_reader)
        base_shortcuts = SHORTCUTS.get(kr, PYNPUT_SHORTCUTS)
        self._shortcuts = dict(base_shortcuts)
        if shortcuts is not None:
            self._shortcuts.update(shortcuts)

        self._last_title: str | None = None
        self._title_formatter: TitleFormatter = title_formatter or default_title_formatter
        self._video_manager = VideoManager(buffersize, log)
        self._video_controller = VideoController.from_source(
            source=source,
            video_manager=self._video_manager,
            sections=sections,
        )

        self.command = Invoker()
        self.set_commands(self._video_controller)

    @classmethod
    def from_default(
        cls,
        path: str | Path,
        *,
        sections: SectionManager | dict | Path | str | None = None,
        shortcuts: dict[int, str] | None = None,
        buffersize: int = 60,
        key_reader: type[InputHandler] = PynputKeyReader,
        display: type[IFrameDisplay] | str = CV2Display,
        backend: type[IFrameSource] | str | None = None,
        log: bool = False,
        title_formatter: TitleFormatter | None = None,
    ) -> FrameViewer:
        if isinstance(path, IFrameSource):
            raise TypeError(
                "from_default() expects a file path (str or Path), not an IFrameSource instance. "
                "Use FrameViewer(source) directly."
            )
        source = source_registry.create_source(
            path, buffersize=buffersize, backend=backend
        )
        return cls(
            source,
            sections=sections,
            shortcuts=shortcuts,
            buffersize=buffersize,
            key_reader=key_reader,
            display=display,
            log=log,
            title_formatter=title_formatter,
        )

    @classmethod
    def from_playlist(
        cls,
        playlist: Playlist,
        *,
        sections: SectionManager | dict | Path | str | None = None,
        shortcuts: dict[int, str] | None = None,
        buffersize: int = 60,
        key_reader: type[InputHandler] = PynputKeyReader,
        display: type[IFrameDisplay] | str = CV2Display,
        log: bool = False,
        title_formatter: TitleFormatter | None = None,
    ) -> FrameViewer:
        if not isinstance(playlist, Playlist):
            raise TypeError(
                f"Expected playlist to be an instance of Playlist, got {type(playlist).__name__}."
            )
        viewer = cls.__new__(cls)
        viewer._source = None
        viewer._log = log
        viewer._buffersize = buffersize
        display_cls = resolve_display(display)
        viewer._display = display_cls()
        viewer._creating_window()

        viewer._key_reader = key_reader()
        kr = type(viewer._key_reader)
        base_shortcuts = SHORTCUTS.get(kr, PYNPUT_SHORTCUTS)
        viewer._shortcuts = dict(base_shortcuts)
        if shortcuts is not None:
            viewer._shortcuts.update(shortcuts)

        viewer._last_title = None
        viewer._title_formatter = title_formatter or default_title_formatter
        viewer._video_manager = VideoManager(buffersize, log)
        viewer._video_controller = VideoController(
            playlist=playlist,
            video_manager=viewer._video_manager,
            sections=sections,
        )
        viewer.command = Invoker()
        viewer.set_commands(viewer._video_controller)
        return viewer

    def bind(self, key: int, command: Command) -> None:
        """Associa uma tecla diretamente a uma instância de Command."""
        if not isinstance(command, Command):
            raise TypeError(
                f"Expected command to be an instance of Command, got {type(command).__name__}"
            )
        self._shortcuts[key] = key
        self.command.set_command(key, command)

    def save(self, file_path: Path | str | None = None) -> None:
        """Salva o estado das seções explicitamente."""
        self._video_controller.save(file_path)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        sleep(1)
        self.join()
        self._display.close()

    def _creating_window(self) -> None:
        """Cria a janela onde os frames serão exibidos."""
        self._display.create_window(name="aniseek", width=720, height=420)

    # Backward compatibility alias
    _FrameViewer__creating_window = _creating_window

    def join(self):
        self._video_controller.join()
        self._key_reader.join()

    @property
    def display(self) -> IFrameDisplay:
        return self._display

    @property
    def video_controller(self) -> VideoController:
        return self._video_controller

    @property
    def controller(self) -> VideoController:
        return self._video_controller

    @property
    def video_manager(self) -> VideoManager:
        return self._video_manager

    # Backward compatibility alias
    @property
    def _FrameViewer__video_controller(self) -> VideoController:
        return self._video_controller

    @property
    def frame_id(self):
        return self._video_controller.frame_id

    def set(self, frame_id) -> None:
        """Define o vídeo para o frame especificado pelo índice 'frame_id'.

        Posiciona o vídeo no frame correspondente ao índice fornecido.
        O índice deve ser um valor inteiro maior ou igual a 0.

        Args:
            frame_id (int): O índice do frame para o qual o vídeo deve ser posicionado.
                            Deve ser um valor maior ou igual a 0.
        """
        self._video_controller.set_frame(frame_id)

    def _show(self, frame):
        self._display.show_frame(frame)

    def set_title_formatter(self, formatter: TitleFormatter) -> None:
        """Define uma função customizada para formatação do título da janela."""
        self._title_formatter = formatter
        self._last_title = None
        self._update_title()

    @property
    def title_formatter(self) -> TitleFormatter:
        return self._title_formatter

    def _update_title(self) -> None:
        try:
            frame_id = self.frame_id
            is_rewind = self._video_manager.player.is_rewind
            is_paused = self._video_manager.player.delay == 0
            is_preview = self._video_controller.is_preview

            pl_idx: int | None = None
            pl_total: int | None = None
            label: str | None = None

            if self._video_controller.playlist is not None:
                playlist = self._video_controller.playlist
                vinfo = playlist.get_video_info()
                if vinfo is not None:
                    pl_idx = playlist.current_index
                    pl_total = len(playlist)
                    label = vinfo.label

            sec_man = self._video_controller.section_manager
            if sec_man is not None and len(sec_man.sections) > 0:
                sec_idx = sec_man.current_index + 1
                sec_total = len(sec_man.sections)
                sec = sec_man.current_section
                mapping = sec.mapping
                sec_frames = len(mapping)

                if frame_id is not None and sec_frames > 0:
                    pos = bisect_left(mapping, frame_id)
                    if pos < sec_frames and mapping[pos] == frame_id:
                        rel_frame = pos + 1
                    else:
                        rel_frame = min(pos + 1, sec_frames)
                else:
                    rel_frame = 1 if sec_frames > 0 else 0
            else:
                sec_idx = 0
                sec_total = 0
                sec_frames = 0
                rel_frame = 0

            ctx = ViewerTitleContext(
                frame_id=frame_id,
                relative_frame=rel_frame,
                section_frames=sec_frames,
                section_index=sec_idx,
                total_sections=sec_total,
                is_preview=is_preview,
                is_rewind=is_rewind,
                is_paused=is_paused,
                playlist_index=pl_idx,
                playlist_total=pl_total,
                label=label,
            )

            title = self._title_formatter(ctx)
            if title != self._last_title:
                self._display.set_title(title)
                self._last_title = title
        except Exception as err:
            logger.debug(f'_update_title error: {err}')

    def show(self, flag, frame):
        if flag is True:
            logger.trace(f'Displaying frame {self.frame_id}')
            self._show(frame)
        self._update_title()
        delay = self._video_manager.player.delay
        event = self._key_reader.get_event(delay)
        if event is not None:
            key, state = event
            return self.control(key, state)
        return -1

    def set_commands(self, video_controller: VideoController) -> None:
        delay = config.hold_delay
        interval = config.hold_interval

        command = self.command
        command.set_command('PauseCommand', PauseCommand(video_controller))
        command.set_command('QuitCommand', QuitCommand(video_controller))
        command.set_command('RewindCommand', RewindCommand(video_controller, delay=delay, interval=interval))
        command.set_command('ProceesCommand', ProceesCommand(video_controller, delay=delay, interval=interval))
        command.set_command('IncreaseSpeedCommand', IncreaseSpeedCommand(video_controller, delay=delay, interval=interval))
        command.set_command('DecreaseSpeedCommand', DecreaseSpeedCommand(video_controller, delay=delay, interval=interval))
        command.set_command('PauseDelayCommand', PauseDelayCommand(video_controller))
        command.set_command('RestoreDelayCommand', RestoreDelayCommand(video_controller))
        command.set_command('RemoveFrameCommand', RemoveFrameCommand(video_controller, delay=delay, interval=interval))
        command.set_command('UndoFrameCommand', UndoFrameCommand(video_controller, delay=delay, interval=interval))
        command.set_command('NextVideoCommand', NextVideoCommand(video_controller, delay=delay, interval=interval))
        command.set_command('NextVideoEndCommand', NextVideoEndCommand(video_controller, delay=delay, interval=interval))
        command.set_command('PrevVideoCommand', PrevVideoCommand(video_controller, delay=delay, interval=interval))
        command.set_command('PrevVideoEndCommand', PrevVideoEndCommand(video_controller, delay=delay, interval=interval))
        command.set_command('NextSectionCommand', NextSectionCommand(video_controller, delay=delay, interval=interval))
        command.set_command('PrevSectionCommand', PrevSectionCommand(video_controller, delay=delay, interval=interval))
        command.set_command('SplitSectionCommand', SplitSectionCommand(video_controller, delay=delay, interval=interval))
        command.set_command('UndoSectionCommand', UndoSectionCommand(video_controller, delay=delay, interval=interval))
        command.set_command('JoinSectionCommand', JoinSectionCommand(video_controller, delay=delay, interval=interval))
        command.set_command('RemoveSectionCommand', RemoveSectionCommand(video_controller, delay=delay, interval=interval))
        command.set_command('JumpSectionStartCommand', JumpSectionStartCommand(video_controller, delay=delay, interval=interval))
        command.set_command('JumpSectionEndCommand', JumpSectionEndCommand(video_controller, delay=delay, interval=interval))
        command.set_command('TogglePreviewCommand', TogglePreviewCommand(video_controller))
        command.set_command('SaveCommand', SaveCommand(video_controller))
        command.set_command('DynamicProceedCommand', DynamicProceedCommand(video_controller))
        command.set_command('DynamicRewindCommand', DynamicRewindCommand(video_controller))

    def control(self, key, state: ButtonState):
        shortcut_key = self._shortcuts.get(key, key)
        self.command.executor_command(shortcut_key, state)
        return key

    def read(self):
        return self._video_controller.read()

    def quit(self):
        self.join()
        self._display.close()
        return self._video_controller.quit()
