from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from threading import Semaphore
from typing import Iterator, Self

from numpy import ndarray

from aniseek.config import config
from aniseek.core.buffer_left import VideoBufferLeft
from aniseek.core.buffer_right import VideoBufferRight
from aniseek.core.frame_mapper import FrameMapper
from aniseek.core.interfaces.source import IFrameSource
from aniseek.core.sources.registry import source_registry
from aniseek.time_utils import resolve_frame_range


class Direction(str, Enum):
    """Direção inicial de leitura do vídeo."""

    FORWARD = "forward"
    REVERSE = "reverse"


class BaseVideoReader(ABC):
    """Classe base abstrata para leitura e amostragem de frames de vídeo."""

    def __init__(
        self,
        source: IFrameSource,
        *,
        start: int | float | str | None = None,
        end: int | float | str | None = None,
        step: int = 1,
        frames: list[int] | None = None,
        buffersize: int = 30,
    ) -> None:
        if not isinstance(source, IFrameSource):
            raise TypeError("source must be an instance of IFrameSource")
        self.source = source
        self.total_frames = self.source.frame_count
        self.fps = self.source.fps

        if frames is not None:
            self.frame_ids = sorted(frames)
        else:
            _start, _end = resolve_frame_range(self.total_frames, start, end, self.fps)
            _step = 1 if step is None or step < 1 else step
            self.frame_ids = list(range(_start, _end, _step))

        self.mapping = FrameMapper(self.frame_ids, self.total_frames)
        self.semaphore = Semaphore()
        self.buffersize = buffersize

    def __len__(self) -> int:
        return len(self.frame_ids)

    @property
    @abstractmethod
    def is_task_complete(self) -> bool:
        """Indica se a leitura alcançou o término do fatiamento configurado."""
        pass

    @property
    @abstractmethod
    def frame_id(self) -> int | None:
        """Retorna o identificador do frame lido mais recentemente."""
        pass

    @abstractmethod
    def read(self) -> tuple[bool, ndarray | None]:
        """Lê o próximo frame e retorna uma tupla (sucesso, frame)."""
        pass

    @abstractmethod
    def set_frame(self, frame_id: int) -> None:
        """Reposiciona o cursor de leitura para o frame indicado."""
        pass

    def set_bounds(self, start: int, end: int) -> None:
        """Redefine os limites de fatiamento da leitura."""
        self.frame_ids = list(range(start, end))
        self.mapping.set_mapping(self.frame_ids, self.total_frames, [])

    @abstractmethod
    def close(self) -> None:
        """Encerra os buffers e libera recursos de captura."""
        pass

    def __iter__(self) -> Iterator[tuple[bool, ndarray | None]]:
        while not self.is_task_complete:
            ret, frame = self.read()
            yield ret, frame

    def __enter__(self) -> BaseVideoReader:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    @classmethod
    def from_default(
        cls,
        path: str | Path,
        *,
        start: int | float | str | None = None,
        end: int | float | str | None = None,
        step: int = 1,
        frames: list[int] | None = None,
        buffersize: int | None = None,
        fps: float | None = None,
    ) -> Self:
        """Create a reader using the default IFrameSource resolved by SourceRegistry."""
        actual_buffersize = buffersize if buffersize is not None else config.buffersize
        source = source_registry.create_source(path, buffersize=actual_buffersize, fps=fps)
        return cls(
            source,
            start=start,
            end=end,
            step=step,
            frames=frames,
            buffersize=actual_buffersize,
        )


class ForwardReader(BaseVideoReader):
    """Leitor unidirecional de alto desempenho focado exclusivamente em avanço (+1)."""

    def __init__(
        self,
        source: IFrameSource,
        *,
        start: int | float | str | None = None,
        end: int | float | str | None = None,
        step: int = 1,
        frames: list[int] | None = None,
        buffersize: int = 30,
    ) -> None:
        super().__init__(
            source,
            start=start,
            end=end,
            step=step,
            frames=frames,
            buffersize=buffersize,
        )
        self.buffer = VideoBufferRight(
            self.source,
            self.mapping,
            self.semaphore,
            buffersize=self.buffersize,
        )
        if len(self.frame_ids) > 0:
            self.buffer.run()
            self.buffer._buffer.wait_task()

    @property
    def is_task_complete(self) -> bool:
        if len(self.frame_ids) == 0:
            return True
        return self.buffer.is_task_complete()

    @property
    def frame_id(self) -> int | None:
        return self.buffer.frame_id

    def read(self) -> tuple[bool, ndarray | None]:
        if self.is_task_complete:
            return False, None
        frame_id, frame = self.buffer.get()
        return frame is not None, frame

    def set_frame(self, frame_id: int) -> None:
        self.buffer.set(frame_id)

    def close(self) -> None:
        self.buffer.join()
        self.source.release()


class ReverseReader(BaseVideoReader):
    """Leitor unidirecional de alto desempenho focado exclusivamente em retrocesso (-1)."""

    def __init__(
        self,
        source: IFrameSource,
        *,
        start: int | float | str | None = None,
        end: int | float | str | None = None,
        step: int = 1,
        frames: list[int] | None = None,
        buffersize: int = 30,
    ) -> None:
        super().__init__(
            source,
            start=start,
            end=end,
            step=step,
            frames=frames,
            buffersize=buffersize,
        )
        self.buffer = VideoBufferLeft(
            self.source,
            self.mapping,
            self.semaphore,
            buffersize=self.buffersize,
        )
        if len(self.frame_ids) > 0:
            self.buffer.set(self.frame_ids[-1] + 1)
            self.buffer.run()
            self.buffer._buffer.wait_task()

    @property
    def is_task_complete(self) -> bool:
        if len(self.frame_ids) == 0:
            return True
        return self.buffer.is_task_complete()

    @property
    def frame_id(self) -> int | None:
        return self.buffer.frame_id

    def read(self) -> tuple[bool, ndarray | None]:
        if self.is_task_complete:
            return False, None
        frame_id, frame = self.buffer.get()
        return frame is not None, frame

    def set_frame(self, frame_id: int) -> None:
        self.buffer.set(frame_id)

    def close(self) -> None:
        self.buffer.join()
        self.source.release()


class VideoReader(BaseVideoReader):
    """Leitor bidirecional com duplo buffer concorrente e cache cooperativo em memória."""

    def __init__(
        self,
        source: IFrameSource,
        *,
        start: int | float | str | None = None,
        end: int | float | str | None = None,
        step: int = 1,
        frames: list[int] | None = None,
        direction: Direction | str = Direction.FORWARD,
        buffersize: int = 30,
    ) -> None:
        super().__init__(
            source,
            start=start,
            end=end,
            step=step,
            frames=frames,
            buffersize=buffersize,
        )
        self.buf_right = VideoBufferRight(
            self.source,
            self.mapping,
            self.semaphore,
            buffersize=self.buffersize,
        )
        self.buf_left = VideoBufferLeft(
            self.source,
            self.mapping,
            self.semaphore,
            buffersize=self.buffersize,
        )
        self._frame_id: int | None = None

        if direction == Direction.REVERSE:
            if len(self.frame_ids) > 0:
                self.buf_left.set(self.frame_ids[-1] + 1)
            self.servant = self.buf_left
            self.master = self.buf_right
        else:
            self.servant = self.buf_right
            self.master = self.buf_left

        if len(self.frame_ids) > 0:
            self.servant.run()
            self.servant._buffer.wait_task()

    @classmethod
    def from_default(
        cls,
        path: str | Path,
        *,
        start: int | float | str | None = None,
        end: int | float | str | None = None,
        step: int = 1,
        frames: list[int] | None = None,
        direction: Direction | str = Direction.FORWARD,
        buffersize: int | None = None,
        fps: float | None = None,
    ) -> Self:
        """Create a VideoReader using the default IFrameSource resolved by SourceRegistry."""
        actual_buffersize = buffersize if buffersize is not None else config.buffersize
        source = source_registry.create_source(path, buffersize=actual_buffersize, fps=fps)
        return cls(
            source,
            start=start,
            end=end,
            step=step,
            frames=frames,
            direction=direction,
            buffersize=actual_buffersize,
        )

    @property
    def is_task_complete(self) -> bool:
        if len(self.frame_ids) == 0:
            return True
        return self.servant.is_task_complete()

    @property
    def frame_id(self) -> int | None:
        return self._frame_id

    @property
    def direction(self) -> Direction:
        """Retorna a direção de reprodução ativa no momento."""
        return Direction.FORWARD if self.is_forward else Direction.REVERSE

    @property
    def is_forward(self) -> bool:
        """Verifica se o sentido de reprodução ativo é avanço (+1)."""
        return isinstance(self.servant, VideoBufferRight)

    @property
    def is_reverse(self) -> bool:
        """Verifica se o sentido de reprodução ativo é retrocesso (-1)."""
        return isinstance(self.servant, VideoBufferLeft)

    def proceed(self) -> None:
        """Alterna o sentido de reprodução para avanço (+1)."""
        if isinstance(self.servant, VideoBufferLeft):
            self.servant, self.master = self.master, self.servant

    def rewind(self) -> None:
        """Alterna o sentido de reprodução para retrocesso (-1)."""
        if isinstance(self.servant, VideoBufferRight):
            self.servant, self.master = self.master, self.servant

    def read(self) -> tuple[bool, ndarray | None]:
        if self.is_task_complete:
            return False, None

        self._frame_id, frame = self.servant.get()
        self.master.put(self._frame_id, frame)
        return frame is not None, frame

    def set_frame(self, frame_id: int) -> None:
        self.servant.set(frame_id)
        self.master.set(frame_id)

    def close(self) -> None:
        self.buf_right.join()
        self.buf_left.join()
        self.source.release()
