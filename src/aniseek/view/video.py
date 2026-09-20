from time import sleep

import cv2
from loguru import logger

from aniseek.editing.interfaces.section import ISectionManagerAdapter
from aniseek.editing.manager import VideoManager
from aniseek.editing.playlist import Playlist
from aniseek.view.input_handler import PynputKeyReader
from aniseek.view.interfaces.input import InputHandler
from aniseek.view.shortcuts import PYNPUT_SHORTCUTS, SHORTCUTS
from aniseek.view.video_command import (
    DecreaseSpeedCommand,
    IncreaseSpeedCommand,
    Invoker,
    JoinSectionCommand,
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
    SplitSectionCommand,
    UndoFrameCommand,
    UndoSectionCommand,
)
from aniseek.view.video_controller import VideoController


class VideoCon:
    def __init__(
            self,
            video: str | Playlist, *,
            frames_mapping: list[int] = None,
            section: ISectionManagerAdapter = None,
            buffersize: int = 60,
            key_reader: type[InputHandler] = PynputKeyReader,
            log: bool = False
    ):

        self.__playlist = video if isinstance(video, Playlist) else Playlist([video])
        self.__log = log
        self.__buffersize = buffersize
        self.__creating_window()
        self.__key_reader = key_reader()
        kr = type(self.__key_reader)
        self.__shortcuts = SHORTCUTS.get(kr, PYNPUT_SHORTCUTS)

        self.__video_manager = VideoManager(buffersize, log)
        self.__video_controller = VideoController(self.__playlist,
                                                  frames_mapping,
                                                  self.__video_manager)

        self.command = Invoker()
        self.set_commands(self.__video_controller)

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

    def show(self, flag, frame):
        if flag is True:
            logger.info(f'exibindo o frame de id {self.frame_id}')
            self._show(frame)
        delay = self.__video_manager.player.delay
        return self.control(self.__key_reader.get_code(delay))

    def set_commands(self, video_controller: VideoController) -> None:

        command = self.command
        command.set_command('PauseCommand', PauseCommand(video_controller))
        command.set_command('QuitCommand', QuitCommand(video_controller))
        command.set_command('RewindCommand', RewindCommand(video_controller))
        command.set_command('ProceesCommand', ProceesCommand(video_controller))
        command.set_command('IncreaseSpeedCommand', IncreaseSpeedCommand(video_controller))
        command.set_command('DecreaseSpeedCommand', DecreaseSpeedCommand(video_controller))
        command.set_command('PauseDelayCommand', PauseDelayCommand(video_controller))
        command.set_command('RestoreDelayCommand', RestoreDelayCommand(video_controller))
        command.set_command('RemoveFrameCommand', RemoveFrameCommand(video_controller))
        command.set_command('UndoFrameCommand', UndoFrameCommand(video_controller))
        command.set_command('NextVideoCommand', NextVideoCommand(video_controller))
        command.set_command('PrevVideoCommand', PrevVideoCommand(video_controller))
        command.set_command('NextSectionCommand', NextSectionCommand(video_controller))
        command.set_command('PrevSectionCommand', PrevSectionCommand(video_controller))
        command.set_command('SplitSectionCommand', SplitSectionCommand(video_controller))
        command.set_command('UndoSectionCommand', UndoSectionCommand(video_controller))
        command.set_command('JoinSectionCommand', JoinSectionCommand(video_controller))
        command.set_command('RemoveSectionCommand', RemoveSectionCommand(video_controller))

    def control(self, key):
        shortcut_key = self.__shortcuts.get(key, key)
        self.command.executor_command(shortcut_key)
        return key

    def read(self):
        return self.__video_controller.read()

    def quit(self):
        return self.__video_controller.quit()
