from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from threading import Semaphore
from typing import Iterator

import cv2
from numpy import ndarray

from aniseek.buffer_left import VideoBufferLeft
from aniseek.buffer_right import VideoBufferRight
from aniseek.frame_mapper import FrameMapper


class BaseVideoReader(ABC):
    """Classe base abstrata para leitura e amostragem de frames de vídeo."""

    def __init__(
        self,
        video: str | Path | cv2.VideoCapture,
        *,
        start: int | None = None,
        end: int | None = None,
        step: int = 1,
        frames: list[int] | None = None,
        buffersize: int = 30,
    ) -> None:
        if isinstance(video, (str, Path)):
            self.cap = cv2.VideoCapture(str(video))
            self._owns_cap = True
        else:
            self.cap = video
            self._owns_cap = False

        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = float(self.cap.get(cv2.CAP_PROP_FPS))

        if frames is not None:
            self.frame_ids = sorted(frames)
        else:
            _start = 0 if start is None else max(0, start)
            _end = self.total_frames if end is None else min(self.total_frames, end)
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
    def close(self) -> None:
        """Encerra os buffers e libera recursos de captura."""
        pass

    def __iter__(self) -> Iterator[tuple[bool, ndarray]]:
        while not self.is_task_complete:
            ret, frame = self.read()
            if not ret or frame is None:
                break
            yield ret, frame

    def __enter__(self) -> BaseVideoReader:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


class ForwardReader(BaseVideoReader):
    """Leitor unidirecional de alto desempenho focado exclusivamente em avanço (+1)."""

    def __init__(
        self,
        video: str | Path | cv2.VideoCapture,
        *,
        start: int | None = None,
        end: int | None = None,
        step: int = 1,
        frames: list[int] | None = None,
        buffersize: int = 30,
    ) -> None:
        super().__init__(
            video,
            start=start,
            end=end,
            step=step,
            frames=frames,
            buffersize=buffersize,
        )
        self.buffer = VideoBufferRight(
            self.cap,
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
        _, frame = self.buffer.get()
        return True, frame

    def close(self) -> None:
        self.buffer.join()
        if self._owns_cap and hasattr(self.cap, "release"):
            self.cap.release()


class ReverseReader(BaseVideoReader):
    """Leitor unidirecional de alto desempenho focado exclusivamente em retrocesso (-1)."""

    def __init__(
        self,
        video: str | Path | cv2.VideoCapture,
        *,
        start: int | None = None,
        end: int | None = None,
        step: int = 1,
        frames: list[int] | None = None,
        buffersize: int = 30,
    ) -> None:
        super().__init__(
            video,
            start=start,
            end=end,
            step=step,
            frames=frames,
            buffersize=buffersize,
        )
        self.buffer = VideoBufferLeft(
            self.cap,
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
        _, frame = self.buffer.get()
        return True, frame

    def close(self) -> None:
        self.buffer.join()
        if self._owns_cap and hasattr(self.cap, "release"):
            self.cap.release()


class VideoReader(BaseVideoReader):
    """Leitor bidirecional com duplo buffer concorrente e cache cooperativo em memória."""

    def __init__(
        self,
        video: str | Path | cv2.VideoCapture,
        *,
        start: int | None = None,
        end: int | None = None,
        step: int = 1,
        frames: list[int] | None = None,
        direction: str = "forward",
        buffersize: int = 30,
    ) -> None:
        super().__init__(
            video,
            start=start,
            end=end,
            step=step,
            frames=frames,
            buffersize=buffersize,
        )
        self.buf_right = VideoBufferRight(
            self.cap,
            self.mapping,
            self.semaphore,
            buffersize=self.buffersize,
        )
        self.buf_left = VideoBufferLeft(
            self.cap,
            self.mapping,
            self.semaphore,
            buffersize=self.buffersize,
        )
        self._frame_id: int | None = None

        if direction == "reverse":
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

    @property
    def is_task_complete(self) -> bool:
        if len(self.frame_ids) == 0:
            return True
        return self.servant.is_task_complete()

    @property
    def frame_id(self) -> int | None:
        return self._frame_id

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
        return True, frame

    def close(self) -> None:
        self.buf_right.join()
        self.buf_left.join()
        if self._owns_cap and hasattr(self.cap, "release"):
            self.cap.release()
