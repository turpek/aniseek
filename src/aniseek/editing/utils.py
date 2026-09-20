from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING

from numpy import ndarray

from aniseek.core.interfaces.source import IFrameSource
from aniseek.custom_exceptions import (
    FrameStackError,
    FrameWrapperError,
    SimpleStackError,
)
from aniseek.editing.interfaces.memento import IMementoHandler
from aniseek.editing.memento import Caretaker

if TYPE_CHECKING:
    from aniseek.editing.memento import TrashOriginator
    from aniseek.editing.section import VideoSection
    from aniseek.editing.trash import Trash


class SimpleStack:

    def __init__(self, stack_type):
        self.__stack = deque()
        self.__stack_type = stack_type

    def __len__(self):
        return len(self.__stack)

    def empty(self):
        return len(self.__stack) == 0

    def push(self, item):

        if not isinstance(item, self.__stack_type):
            raise TypeError(
                f'Expected type "{self.__stack_type.__name__}", '
                f'but received "{type(item).__name__}".'
            )
        self.__stack.append(item)

    @property
    def top(self):
        if not self.empty():
            return self.__stack[-1]

    def pop(self):
        if self.empty():
            raise SimpleStackError("Pop failed: Stack is empty.")
        return self.__stack.pop()


class FrameMementoHandler(IMementoHandler):
    def __init__(self, originator: TrashOriginator, caretaker: Caretaker, trash: Trash = None):
        self.__caretaker = caretaker
        self.__originator = originator
        self.__trash = trash

    def store_mementos(self, section: VideoSection):
        if section is not None:
            removed_frames = section.get_trash()
            while self.__caretaker.undo(self.__originator):
                removed_frames.append(self.__originator.get_state())

    def load_mementos(self, section: VideoSection):
        if section is not None:
            removed_frames = section.get_trash()
            while len(removed_frames) > 0:
                self.__originator.set_state(removed_frames.pop())
                self.__caretaker.save(self.__originator)


class FrameWrapper:
    def __init__(self, frame_id: int, frame: ndarray = None):
        self.__frame_id = frame_id
        self.__frame = frame

    def __repr__(self):
        return f"FrameWrapper('{self.__frame_id}')"

    def __eq__(self, obj: FrameWrapper | int) -> bool:
        if isinstance(obj, FrameWrapper):
            return self.id_ == obj.id_
        return self.id_ == obj

    def __lt__(self, obj: FrameWrapper | int) -> bool:
        if isinstance(obj, FrameWrapper):
            return self.id_ < obj.id_
        return self.id_ < obj

    def set_frame(self, frame: ndarray) -> None:
        if isinstance(self.__frame, ndarray):
            raise FrameWrapperError("frame is already defined")
        self.__frame = frame

    @property
    def id_(self):
        return self.__frame_id

    def get_frame(self):
        return self.__frame


class FrameStack:
    def __init__(self, maxlen):
        self.__stack = deque(maxlen=maxlen)
        self.__maxlen = maxlen

    def __len__(self):
        return len(self.__stack)

    @property
    def maxlen(self):
        return self.__maxlen

    def empty(self):
        return len(self) == 0

    def pop(self) -> FrameWrapper:
        if self.empty():
            raise FrameStackError("Pop failed: Stack is empty.")
        return self.__stack.pop()

    def push(self, frame: FrameWrapper) -> None:
        if not isinstance(frame, FrameWrapper):
            raise TypeError(
                f'Expected type "{FrameWrapper.__name__}", '
                f'but received "{type(frame).__name__}".'
            )
        self.__stack.append(frame)

    def can_update_memento(self, trash: Trash) -> bool:
        return trash.can_undo() and len(self) <= self.maxlen // 2

    def _check_update_memento(self, trash: Trash) -> bool:
        return trash.can_undo() and len(self) < self.maxlen

    def _memento_save(self, list_frames: list, trash: Trash) -> None:
        while len(list_frames) > 0:
            trash._memento_save(list_frames.pop())

    def _create_wrapper(self, frame_id: int) -> FrameWrapper:
        frame = FrameWrapper(frame_id, None)
        self.__stack.appendleft(frame)
        return frame

    def update_mementos(self, trash: Trash):
        frames_map = {}
        if self.can_update_memento(trash):
            temp = []
            while self._check_update_memento(trash):
                frame_id = trash._memento_undo()
                temp.append(frame_id)
                if frame_id not in self.__stack:
                    trash._mapping.add(frame_id)
                    frames_map[frame_id] = self._create_wrapper(frame_id)
            self._memento_save(temp, trash)
        return frames_map


class VideoInfo:
    def __init__(self, path: Path, label: str, format_file: str = '.json'):
        self.__path = path
        self.__suffix = path.suffix
        self.__label = label
        self.__fps = None
        self.__frame_count = None
        self.__format_file = format_file

    def __repr__(self):
        return f"VideoInfo('{self.path}')"

    @property
    def path(self) -> Path:
        return self.__path

    @property
    def label(self) -> str:
        return self.__label

    @property
    def suffix(self) -> str:
        return self.__suffix

    @property
    def fps(self) -> float:
        return self.__fps

    @property
    def frame_count(self) -> int:
        return self.__frame_count

    @property
    def format_file(self) -> str:
        return self.__format_file

    def load_video_property(self, source: IFrameSource) -> None:
        if not self.frame_count:
            self.__frame_count = source.frame_count
            self.__fps = source.fps


def partition_by_value(source: list, value_split) -> tuple[list, list]:
    """Função que separa a lista `source` em duas, a partir do valor `value_split`."""
    list_1, list_2 = [], []
    for value in source:
        list_1.append(value) if value < value_split else list_2.append(value)
    return (list_1, list_2)
