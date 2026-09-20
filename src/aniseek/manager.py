from array import array
from pathlib import Path
from threading import Semaphore

from aniseek.buffer_left import VideoBufferLeft
from aniseek.buffer_right import VideoBufferRight
from aniseek.frame_mapper import FrameMapper
from aniseek.player_control import PlayerControl
from aniseek.section import SectionManager
from aniseek.section_service import SectionService
from aniseek.sources.opencv import OpenCVVideoSource
from aniseek.trash import Trash
from aniseek.utils import VideoInfo


class VideoManager:

    def __init__(self, buffersize, log):
        self.__log = log
        self.__buffersize = buffersize
        self.mapping = None
        self.path = None
        self.trash = None
        self.frame_count = None
        self.semaphore = Semaphore()
        self.player = PlayerControl()
        self.__section_manager = None

    def set_mapping(self, frame_ids: list = None) -> None:
        """
        Define o mapping de frames que serão lidos e armazenados no buffer.

        Returns:
            None
        """

        frame_count = self.frame_count
        if not isinstance(frame_ids, (list, tuple, array)):
            frame_ids = list(range(frame_count))

        if isinstance(self.mapping, FrameMapper):
            self.mapping.set_mapping(frame_ids, frame_count, [])
            return self.mapping
        else:
            return FrameMapper(frame_ids, frame_count)

    def load_capture(self, file_path: str | Path) -> None:
        self.path = Path(file_path)
        self.source = OpenCVVideoSource(self.path)
        self.frame_count = self.source.frame_count

    def load_section_manager(self, file_path: Path, label: str, file_format: str):
        frame_count = self.frame_count
        file_data = file_path.with_suffix(file_format)
        return SectionService.load_section_manager(file_data, label, frame_count)

    def load_mapping(self, frames_mapping: list):
        self.mapping = self.set_mapping(frames_mapping)

    def load_trash(self, section_manager: SectionManager):
        args = (self.source, self.semaphore, self.frame_count)
        if isinstance(self.trash, Trash):
            self.trash._buffer.join_like()
        self.trash = Trash(*args, buffersize=20)
        section_manager.load_mementos_frames(self.trash)

    def load_player(self, servant: VideoBufferRight, master: VideoBufferLeft):
        self.player.set_buffers(servant, master)

    def load_buffers(self):
        args = (self.source, self.mapping, self.semaphore)
        bsize, log = self.__buffersize, self.__log
        self.servant = VideoBufferRight(*args, buffersize=bsize, bufferlog=log)
        self.master = VideoBufferLeft(*args, buffersize=bsize, bufferlog=log)
        self.load_player(self.servant, self.master)

    def create(self, section_manager: SectionManager):

        section_manager.load_mementos_frames(self.trash)
        self.player.servant.join_like()
        self.player.master.join_like()
        self.load_mapping(section_manager.get_mapping())
        self.load_buffers()

    def open(self, file_path: Path, label: str, file_format: str) -> SectionManager:
        self.load_capture(file_path)
        section_manager = self.load_section_manager(file_path, label, file_format)
        self.load_mapping(section_manager.get_mapping())
        self.load_trash(section_manager)
        self.load_buffers()

        # Iniciando a task e esperando que a mesma esteja concluida.
        self.servant.run()
        self.servant._buffer.wait_task()
        return section_manager

    def load_video_info(self, video_info: VideoInfo):
        video_info.load_video_property(self.source)

    def save_section(self,
                     section_manager: SectionManager,
                     file_path: Path,
                     label: str) -> None:
        data_section = section_manager.to_dict(self.trash)
        SectionService.save_section_manager(file_path, label, data_section)

    def get(self):
        return (self.player, self.mapping, self.trash)
