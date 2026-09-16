from __future__ import annotations

from collections import deque
from copy import deepcopy

from loguru import logger

from aniseek.adapter import (
    ISectionAdapter,
    ISectionManagerAdapter,
    SectionSplitProcess,
    SectionUnionAdapter,
)
from aniseek.custom_exceptions import SectionManagerError
from aniseek.frame_mapper import FrameMapper
from aniseek.memento import Caretaker, SectionOriginator
from aniseek.trash import Trash
from aniseek.utils import FrameMementoHandler, SectionMementoHandler, SimpleStack


class VideoSection:
    def __init__(self, adapter: ISectionAdapter):
        self.__start = adapter.start()
        self.__end = adapter.end()
        self.__removed_frame = adapter.removed_frames()
        self.black_list_frames = adapter.black_list_frames()
        self.__id = self.__calculate_id()
        self.__mapping = self._calculate_mapping(self.__removed_frame)

    def __repr__(self):
        return f"VideoSection('{self.id_}')"

    def __add__(self, obj: VideoSection) -> VideoSection:
        return VideoSection(SectionUnionAdapter(self, obj))

    def __eq__(self, obj: int | VideoSection) -> bool:
        if isinstance(obj, VideoSection):
            return self.id_ == obj.id_
        return self.id_ == obj

    def __lt__(self, obj: VideoSection) -> bool:
        return self.id_ < obj.id_

    def __le__(self, obj: VideoSection) -> bool:
        return self.id_ <= obj.id_

    def __truediv__(self, frame_id: int) -> tuple[VideoSection, VideoSection]:
        return self.split_section(frame_id)

    def __calculate_id(self):
        if len(self.get_trash()) > 0:
            removed = min(self.get_trash())
            return min(self.start, removed)
        return self.start

    def _calculate_mapping(self, removed):
        if self.start is None:
            return []
        frames_id = set(range(self.start, self.end))
        removeds = set(list(removed) + self.black_list_frames)
        return list(frames_id - removeds)

    @property
    def start(self):
        return self.__start

    @property
    def end(self):
        return self.__end

    @property
    def id_(self):
        return self.__id

    def update_range(self, frame_map: FrameMapper):
        """Atualiza o range da seção, ou seja, o start e end dos frames"""
        self.__start = frame_map[0]
        self.__end = frame_map[-1]

    def get_trash(self) -> deque:
        """
        Devolve uma pilha dos frames removidos, portanto os elementos
        no topo do deque foram os primeiros removidos
        """
        return self.__removed_frame

    def get_mapping(self):
        return self.__mapping

    def split_section(self, frame_id: int) -> tuple[VideoSection, VideoSection]:
        """Método para dividir a seção em duas a partir do frame de indice `frame_id`."""
        process = SectionSplitProcess(self, frame_id)
        section_1, section_2 = process.split()
        return (
            VideoSection(section_1),
            VideoSection(section_2)
        )

    def to_dict(self) -> dict:
        """ Retorna o estado atual da `VideoSection` como um dicionário."""
        data_section = dict()
        data_section['RANGE_FRAME_ID'] = (self.start, self.end)
        data_section['REMOVED_FRAMES'] = list(self.get_trash())
        data_section['BLACK_LIST'] = self.black_list_frames
        return data_section


class SectionWrapper:
    def __init__(self, section_1: VideoSection, section_2: VideoSection = None):
        self.__check_section(section_1)
        if section_2 is not None:
            self.__check_section(section_2)

        self.__lower = section_1
        self.__upper = section_2
        if section_2 is None or section_2 < section_1:
            self.__lower = section_2
            self.__upper = section_1

    def __check_section(self, section):
        if not isinstance(section, VideoSection):
            raise TypeError(f' section expected "{VideoSection.__name__}" but received "{type(section).__name__}"!')

    @property
    def section_1(self) -> VideoSection | None:
        """Devolve a seção com o meno ID ou None caso uma da seções não esteja definida."""
        return self.__lower

    @property
    def section_2(self) -> VideoSection:
        """Devolve a seção com o maior ID."""
        return self.__upper

    def to_dict(self) -> dict:
        """Método que retorna os estados atuais das seções como um dicionário."""
        data_2 = self.section_2.to_dict()
        if self.section_1 is None:
            return [data_2, None]
        data_1 = self.section_1.to_dict()
        return [data_1, data_2]


class SectionManager:
    def __init__(self, manager_adapter: ISectionManagerAdapter):
        self._right = SimpleStack(VideoSection)
        self._left = SimpleStack(VideoSection)
        self.removed_sections = SimpleStack(SectionWrapper)

        self._caretaker = Caretaker()
        self._originator = SectionOriginator()
        self.__memento_handler = SectionMementoHandler(self._originator, self._caretaker)
        self.__frame_memento_handler = None

        # O ISectionManagerAdapter deve retorna uma lista ordenada, além disso
        # devemos considerar está lista como uma "pilha", portando a remoção
        # deve ser feita no topo!
        section_adapter = manager_adapter.section_adapter
        datas = manager_adapter.get_sections()
        while len(datas):
            self._right.push(VideoSection(section_adapter(datas.pop())))

        self.__load_removed_sections(manager_adapter, section_adapter)

        if self._right.empty() and self.removed_sections.empty():
            raise SectionManagerError('there are no sections id to work with')

        self.load_mementos()

    def __len__(self):
        return len(self._right) + len(self._left)

    def __load_removed_sections(
        self,
        manager_adapter: ISectionManagerAdapter,
        section_adapter: ISectionAdapter
    ) -> None:

        # Devemos considerar a lista retornada pelo removed_sections como uma pilha,
        # portanto a remoção deve ser feita no topo, além disso a lista deve seguir o
        # seguinte padrão list[VideoSection, VideoSection | None]
        rdatas = manager_adapter.removed_sections()
        while len(rdatas):
            section_1, section_2 = rdatas.pop()
            data = [VideoSection(section_adapter(section_1)), section_2]
            if section_2 is not None:
                data[1] = VideoSection(section_adapter(section_2))
            self.removed_sections.push(SectionWrapper(*data))

    def load_mementos_frames(self, trash: Trash):
        trash_originator = trash.get_originator()
        trash_caretaker = trash.get_caretaker()
        self._right.top._calculate_mapping(self._right.top.get_trash())
        frame_handler = FrameMementoHandler(trash_originator, trash_caretaker)
        frame_handler.load_mementos(self._right.top)

    def store_mementos_frames(self, trash: Trash):
        trash_originator = trash.get_originator()
        trash_caretaker = trash.get_caretaker()
        frame_handler = FrameMementoHandler(trash_originator, trash_caretaker, trash)
        frame_handler.store_mementos(self._right.top)

    def load_mementos(self):
        self.__memento_handler.load_mementos(self.removed_sections)

    def store_mementos(self):
        self.__memento_handler.store_mementos(self.removed_sections)

    @property
    def section_id(self) -> int:
        if not self._right.empty():
            return self._right.top.id_

    def get_section(self) -> VideoSection:
        return self._right.top

    def get_mapping(self) -> list:
        return self._right.top.get_mapping()

    def update_mapping(self) -> None:
        self._right.top.update_mapping()

    def __next_section(self, min_size: int) -> bool:
        if len(self._right) > min_size:
            self._left.push(self._right.pop())
            return True
        return False

    def _next_section(self) -> bool:
        """Passa para a próxima seção se existir."""

        # Como a seção atual está sempre no topo da pilha não
        # podemos remover a última seção da mesma, pois ficariamos
        # sem seção para consultar
        return self.__next_section(1)

    def _prev_section(self) -> bool:
        """Retorna para a seção anterior."""
        if not self._left.empty():
            self._right.push(self._left.pop())
            return True
        return False

    def __check_right(self):
        """Para o caso do última frame ser removido, devemos voltar para a seção anterior."""
        if self._right.empty() and not self._left.empty():
            self._prev_section()

    def __remove_section(
        self,
        section_1: VideoSection,
        section_2: VideoSection = None
    ) -> None:
        data = SectionWrapper(section_1, section_2)
        self._originator.set_state(data)
        self._caretaker.save(self._originator)

    def remove_section(self, trash: Trash) -> bool:
        if self._right.empty():
            logger.debug('there are no more sections to remove')
            return False
        self.store_mementos_frames(trash)
        self.__remove_section(self._right.pop())
        self.__check_right()
        return True

    def __restore_right(self, section) -> None:
        while self.__next_section(0):
            if self._right.empty():
                break
            elif section < self._right.top:
                break

    def __restore_left(self, section) -> None:
        while self._prev_section():
            if self._left.empty():
                break
            elif self._left.top <= section:
                break

    def restore_section(self):
        """Restaura a última seção excluida."""
        if self._caretaker.undo(self._originator):
            data = self._originator.get_state()
            section_1 = data.section_1
            section_2 = data.section_2

            if not self._left.empty() and section_2 < self._left.top:
                self.__restore_left(section_2)
            elif not self._right.empty() and self._right.top <= section_2:
                self.__restore_right(section_2)

            # A escolha de poder fazer section_1 ser None, nos permite
            # simplificar a `restore_section`, já que section_2 sempre deve
            # ser sempre maior que section_1, portando ficar na pilha _right.
            if isinstance(section_1, VideoSection):
                self._left.pop()
                self._left.push(section_1)
            elif not self._left.empty() and self._left.top == section_2:
                self._left.pop()
                self._right.pop()

            self._right.push(section_2)
            return True
        return False

    def join_section(self, trash: Trash) -> bool:
        if self._left.empty():
            return False
        self.store_mementos_frames(trash)
        lower = self._left.pop()
        upper = self._right.pop()
        self._right.push(lower + upper)
        self.__remove_section(lower, upper)
        return True

    def split_section(self, frame_id: int, trash: Trash):
        try:
            self.store_mementos_frames(trash)
            section = self._right.pop()
            section_1, section_2 = section / frame_id
        except Exception:
            self._right.push(section)
            self.load_mementos_frames(trash)
            return False
        self._left.push(section_1)
        self._right.push(section_2)
        self.__remove_section(section)
        return True

    def next_section(self, trash: Trash):
        self.store_mementos_frames(trash)
        self._next_section()
        self.load_mementos()
        trash.reset(None)
        self.load_mementos_frames(trash)

    def prev_section(self, trash: Trash):
        self.store_mementos_frames(trash)
        self._prev_section()
        self.load_mementos()
        trash.reset(None)
        self.load_mementos_frames(trash)

    def load_trash(self, trash: Trash):
        self.load_mementos()
        trash.reset(None)
        self.load_mementos_frames(trash)

    def set_mapping(self, mapping):
        self._right

    def to_dict(self, trash: Trash):
        self.store_mementos_frames(trash)
        right = deepcopy(self._right)
        left = deepcopy(self._left)
        self.load_mementos_frames(trash)

        data_sections = list()
        while not left.empty():
            right.push(left.pop())
        while not right.empty():
            data = right.pop()
            data_sections.append(data.to_dict())

        self.store_mementos()
        removed_sections = deepcopy(self.removed_sections)
        self.load_mementos()

        data_removed = list()
        while not removed_sections.empty():
            data_wrapper = removed_sections.pop()
            data_removed.append(data_wrapper.to_dict())

        return {
            'SECTIONS': data_sections,
            'REMOVED': data_removed
        }
