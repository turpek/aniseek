from array import array
from pathlib import Path
from threading import Semaphore

from aniseek.core.buffer_left import VideoBufferLeft
from aniseek.core.buffer_right import VideoBufferRight
from aniseek.core.frame_mapper import FrameMapper
from aniseek.core.interfaces.buffer import IVideoBuffer
from aniseek.core.interfaces.source import IFrameSource
from aniseek.core.sources.registry import source_registry
from aniseek.editing.player_control import PlayerControl
from aniseek.editing.section import SectionManager, VideoSection
from aniseek.editing.section_service import SectionService
from aniseek.editing.trash import Trash
from aniseek.editing.utils import VideoInfo


class VideoManager:

    def __init__(self, buffersize, log):
        self.__log = log
        self.__buffersize = buffersize
        self.mapping = None
        self.path = None
        self.source = None
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
        self.source = source_registry.create_source(self.path)
        self.frame_count = self.source.frame_count

    def load_source(self, source: IFrameSource) -> None:
        if not isinstance(source, IFrameSource):
            raise TypeError(
                f"Expected source to be an instance of IFrameSource, got {type(source).__name__}"
            )
        self.source = source
        self.path = None
        self.frame_count = source.frame_count

    def resolve_section_manager(
        self,
        sections: SectionManager | dict | Path | str | None = None,
        label: str = 'video_01',
        file_format: str = '.json',
    ) -> SectionManager:
        if isinstance(sections, SectionManager):
            return sections
        if isinstance(sections, dict):
            if 'SECTIONS' in sections:
                return SectionManager.from_dict(sections)
            if label in sections:
                return SectionManager.from_dict(sections[label])
            for val in sections.values():
                if isinstance(val, dict) and 'SECTIONS' in val:
                    return SectionManager.from_dict(val)
            return SectionManager.from_dict(sections)
        if isinstance(sections, (str, Path)):
            return SectionService.load_section_manager(Path(sections), label, self.frame_count)
        if sections is None:
            if self.path is not None:
                file_data = self.path.with_suffix(file_format)
                if file_data.exists():
                    return SectionService.load_section_manager(file_data, label, self.frame_count)
            return SectionManager([VideoSection(0, self.frame_count)])
        raise TypeError(f"Unsupported type for sections: {type(sections).__name__}")

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

    def load_player(self, servant: IVideoBuffer, master: IVideoBuffer):
        self.player.set_buffers(servant, master)

    def load_buffers(self):
        args = (self.source, self.mapping, self.semaphore)
        bsize, log = self.__buffersize, self.__log
        right = VideoBufferRight(*args, buffersize=bsize, bufferlog=log)
        left = VideoBufferLeft(*args, buffersize=bsize, bufferlog=log)

        if self.player is not None and self.player.is_rewind:
            self.servant, self.master = left, right
        else:
            self.servant, self.master = right, left

        self.load_player(self.servant, self.master)

    def create(self, section_manager: SectionManager, mapping: list[int] | None = None):

        section_manager.load_mementos_frames(self.trash)
        self.player.servant.join_like()
        self.player.master.join_like()
        map_frames = mapping if mapping is not None else section_manager.get_mapping()
        self.load_mapping(map_frames)
        self.load_buffers()

    def open_source(
        self,
        source: IFrameSource,
        sections: SectionManager | dict | Path | str | None = None,
        label: str = 'video_01',
        file_format: str = '.json',
    ) -> SectionManager:
        self.load_source(source)
        section_manager = self.resolve_section_manager(sections, label, file_format)
        self.__section_manager = section_manager
        self.load_mapping(section_manager.get_mapping())
        self.load_trash(section_manager)
        self.load_buffers()

        # Iniciando a task e esperando que a mesma esteja concluida.
        self.servant.run()
        self.servant._buffer.wait_task()
        return section_manager

    def open(
        self,
        file_path: Path,
        label: str,
        file_format: str,
        sections: SectionManager | dict | Path | str | None = None,
    ) -> SectionManager:
        self.load_capture(file_path)
        section_manager = self.resolve_section_manager(sections, label, file_format)
        self.__section_manager = section_manager
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
