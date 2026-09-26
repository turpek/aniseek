from __future__ import annotations

from pathlib import Path
from time import sleep

import cv2
from loguru import logger

from aniseek.config import config
from aniseek.core.interfaces.source import IFrameSource
from aniseek.core.sources.registry import source_registry
from aniseek.editing.manager import VideoManager
from aniseek.editing.section import SectionManager
from aniseek.view.input_handler import PynputKeyReader
from aniseek.view.interfaces.command import ButtonState, Command
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
    PauseCommand,
    PauseDelayCommand,
    PrevSectionCommand,
    PrevVideoCommand,
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


class FrameViewer:
    def __init__(
            self,
            source: IFrameSource, *,
            sections: SectionManager | dict | Path | str | None = None,
            shortcuts: dict[int, str] | None = None,
            buffersize: int = 60,
            key_reader: type[InputHandler] = PynputKeyReader,
            log: bool = False
    ):
        if not isinstance(source, IFrameSource):
            raise TypeError(
                f"Expected source to be an instance of IFrameSource, got {type(source).__name__}. "
                "Use FrameViewer.from_default(path) if passing a file path or directory."
            )

        self.__source = source
        self.__log = log
        self.__buffersize = buffersize
        self.__creating_window()
        self.__key_reader = key_reader()
        kr = type(self.__key_reader)
        base_shortcuts = SHORTCUTS.get(kr, PYNPUT_SHORTCUTS)
        self.__shortcuts = dict(base_shortcuts)
        if shortcuts is not None:
            self.__shortcuts.update(shortcuts)

        self.__last_title: str | None = None
        self.__video_manager = VideoManager(buffersize, log)
        self.__video_controller = VideoController.from_source(
            source=source,
            video_manager=self.__video_manager,
            sections=sections,
        )

        self.command = Invoker()
        self.set_commands(self.__video_controller)

    @classmethod
    def from_default(
        cls,
        path: str | Path,
        *,
        sections: SectionManager | dict | Path | str | None = None,
        shortcuts: dict[int, str] | None = None,
        buffersize: int = 60,
        key_reader: type[InputHandler] = PynputKeyReader,
        log: bool = False,
    ) -> FrameViewer:
        if isinstance(path, IFrameSource):
            raise TypeError(
                "from_default() expects a file path (str or Path), not an IFrameSource instance. "
                "Use FrameViewer(source) directly."
            )
        source = source_registry.create_source(path)
        return cls(
            source,
            sections=sections,
            shortcuts=shortcuts,
            buffersize=buffersize,
            key_reader=key_reader,
            log=log,
        )

    def bind(self, key: int, command: Command) -> None:
        """Associa uma tecla diretamente a uma instância de Command."""
        if not isinstance(command, Command):
            raise TypeError(
                f"Expected command to be an instance of Command, got {type(command).__name__}"
            )
        self.__shortcuts[key] = key
        self.command.set_command(key, command)

    def save(self, file_path: Path | str | None = None) -> None:
        """Salva o estado das seções explicitamente."""
        self.__video_controller.save(file_path)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        sleep(1)
        self.join()
        cv2.destroyWindow('videoseq')

    def __creating_window(self) -> None:
        """
        Cria a janela onde os frames serão exibidos.

        Returns:
            None
        """
        cv2.namedWindow('videoseq', cv2.WINDOW_NORMAL | cv2.WINDOW_GUI_NORMAL)
        cv2.resizeWindow('videoseq', 720, 420)

    def join(self):
        self.__video_controller.join()
        self.__key_reader.join()

    @property
    def frame_id(self):
        return self.__video_controller.frame_id

    def set(self, frame_id) -> None:
        """
        Define o vídeo para o frame especificado pelo índice 'frame_id'.

        Posiciona o vídeo no frame correspondente ao índice fornecido.
        O índice deve ser um valor inteiro maior ou igual a 0.

        Args:
            frame_id (int): O índice do frame para o qual o vídeo deve ser posicionado.
                            Deve ser um valor maior ou igual a 0.

        Returns:
            None
        """
        self.__video_controller.set_frame(frame_id)

    def _show(self, frame):
        cv2.imshow('videoseq', frame)

    def _update_title(self) -> None:
        try:
            frame_id = self.frame_id if self.frame_id is not None else '-'
            direction_str = '<<' if self.__video_manager.player.is_rewind else '>>'
            paused_str = ' (PAUSADO)' if self.__video_manager.player.delay == 0 else ''
            if self.__video_controller.is_preview:
                title = f'videoseq - [PREVIEW | Frame: {frame_id}] [{direction_str}]{paused_str}'
            else:
                sec_man = self.__video_controller.section_manager
                sec_idx = sec_man.current_index + 1
                sec_total = len(sec_man.sections)
                sec = sec_man.current_section
                title = f'videoseq - [Seção {sec_idx}/{sec_total} | Frames {sec.start}-{sec.end - 1} | Frame: {frame_id}] [{direction_str}]{paused_str}'
            if title != self.__last_title:
                cv2.setWindowTitle('videoseq', title)
                self.__last_title = title
        except Exception as err:
            logger.debug(f'_update_title error: {err}')

    def show(self, flag, frame):
        if flag is True:
            logger.info(f'exibindo o frame de id {self.frame_id}')
            self._show(frame)
        self._update_title()
        delay = self.__video_manager.player.delay
        event = self.__key_reader.get_event(delay)
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
        command.set_command('PrevVideoCommand', PrevVideoCommand(video_controller, delay=delay, interval=interval))
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
        shortcut_key = self.__shortcuts.get(key, key)
        self.command.executor_command(shortcut_key, state)
        return key

    def read(self):
        return self.__video_controller.read()

    def quit(self):
        return self.__video_controller.quit()
