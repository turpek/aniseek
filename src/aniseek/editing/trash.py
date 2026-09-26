from collections import deque
from threading import Semaphore

from loguru import logger
from numpy import ndarray

from aniseek.core.buffer_right import VideoBufferRight
from aniseek.core.frame_mapper import FrameMapper
from aniseek.core.interfaces.source import IFrameSource
from aniseek.editing.memento import Caretaker, TrashOriginator
from aniseek.editing.utils import FrameStack, FrameWrapper


class Trash():
    def __init__(self, source: IFrameSource, semaphore: Semaphore, frame_count: int, buffersize=5, bufferlog=False):
        self.__buffersize = buffersize
        self.__frame_count = frame_count
        self._stack = FrameStack(2 * buffersize)
        self._dframes = dict()
        self._mapping = FrameMapper([], frame_count)
        self._buffer = VideoBufferRight(source, self._mapping, semaphore, buffersize=buffersize, bufferlog=bufferlog)
        self._state = None
        self.__caretaker = Caretaker()
        self.__originator = TrashOriginator(self._mapping)
        self._history = list()

    def reset(self, frame_count):
        self._stack = FrameStack(2 * self.__buffersize)
        self._mapping.set_mapping([], self.__frame_count, [])
        self._state = None
        self.__caretaker = Caretaker()
        self.__originator = TrashOriginator(self._mapping)
        self._history = list()

    def join(self):
        self._buffer.join()

    def _memento_save(self, frame_id: int) -> None:
        self.__originator.set_state(frame_id)
        self.__caretaker.save(self.__originator)

    def _memento_undo(self) -> int:
        self.__caretaker.undo(self.__originator)
        return self.__originator.get_state()

    def empty(self) -> bool:
        return len(self._stack) == 0

    def full(self) -> bool:
        return len(self._stack) == self._stack.maxlen

    def move(self, frame_id, frame) -> None:
        if isinstance(frame, ndarray):
            self._memento_save(frame_id)
            self._stack.push(FrameWrapper(frame_id, frame))

    def undo(self) -> tuple[int, ndarray] | None:
        logger.debug('Starting frame restoration')
        if self.can_undo():
            frames = self._stack.update_mementos(self)
            frame = self._stack.pop()
            self._memento_undo()
            if frames:
                self._buffer.set(self._mapping[0])
                self._buffer.run()
                while not self._buffer.is_task_complete():
                    fid, update_frame = self._buffer.get()
                    # print(f'RESTAURADO {fid}')
                    self._mapping.remove(fid)
                    frames[fid].set_frame(update_frame)
            return frame.id_, frame.get_frame()
        return None, None

    def can_undo(self) -> bool:
        """
        Método que verifica se há frames para restaurar.

        Returns:
            True: se tiver frames
            False: se não houver frames
        """
        return self.__caretaker.can_undo()

    def get_originator(self) -> TrashOriginator:
        return self.__originator

    def get_caretaker(self) -> Caretaker:
        return self.__caretaker

    def import_frames_id(self, frames_id: deque) -> None:
        """
        Importar os frames_id de uma pilha para uma outra pilha

        Args:
            frames_id (deque): uma fila que contém números inteiros que representam o
                os frame_id excluidos, e que podem ser restaurados.

        Returns:
            None
        """
        while len(frames_id):
            self._memento_save(frames_id.pop())

    def export_frames_id(self, frames_id: deque) -> None:
        """
        Exporta os frames_id de uma pilha para uma queue

        Args:
            frames_id (Queue): uma fila que contém números inteiros que representam o
                os frame_id excluidos, e que podem ser restaurados.

        Returns:
            None
        """
        while self.__caretaker.can_undo():
            frames_id.append(self._memento_undo())

        while self.can_undo():
            frames_id.appendleft(self._stack.popleft())
