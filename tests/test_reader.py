from __future__ import annotations

from threading import Semaphore

import numpy as np
import pytest

from aniseek.core.buffer import FakeBuffer
from aniseek.core.interfaces.source import IFrameSource
from aniseek.core.reader import reader_task


class FakeFrameSource(IFrameSource):
    def __init__(self, frame_count: int = 10) -> None:
        self._frame_count = frame_count
        self.cursor = 0
        self.grabbed = 0
        self.frames = [np.ones((2, 2)) * i for i in range(frame_count)]

    @property
    def frame_count(self) -> int:
        return self._frame_count

    @property
    def fps(self) -> float:
        return 24.0

    def seek(self, frame_id: int) -> None:
        self.cursor = frame_id

    def read(self) -> tuple[bool, np.ndarray | None]:
        if 0 <= self.cursor < self._frame_count:
            frame = self.frames[self.cursor]
            self.cursor += 1
            return True, frame
        return False, None

    def grab(self) -> bool:
        self.cursor += 1
        self.grabbed += 1
        return True

    def is_opened(self) -> bool:
        return True

    def release(self) -> None:
        pass


def test_reader_task_reads_mapped_frames():
    """Valida leitura e inserção de frames mapeados na fila secundária do buffer."""
    buffer = FakeBuffer(Semaphore(), maxsize=5)
    source = FakeFrameSource(frame_count=10)
    mapping = {0, 1, 2}

    reader_task(buffer, (source, 0, 2, mapping))

    assert buffer._secondary.qsize() == 3
    assert buffer._secondary.get()[0] == 0
    assert buffer._secondary.get()[0] == 1
    assert buffer._secondary.get()[0] == 2


def test_reader_task_skips_unmapped_frames_via_grab():
    """Verifica se frames não mapeados são pulados através do método grab."""
    buffer = FakeBuffer(Semaphore(), maxsize=5)
    source = FakeFrameSource(frame_count=10)
    mapping = {0, 2}

    reader_task(buffer, (source, 0, 2, mapping))

    assert buffer._secondary.qsize() == 2
    assert source.grabbed == 1
    assert buffer._secondary.get()[0] == 0
    assert buffer._secondary.get()[0] == 2


def test_reader_task_raises_on_start_frame_out_of_bounds():
    """Garante que IndexError é levantado quando start_frame excede frame_count."""
    buffer = FakeBuffer(Semaphore(), maxsize=5)
    source = FakeFrameSource(frame_count=5)

    with pytest.raises(IndexError):
        reader_task(buffer, (source, 10, 15, {10, 11}))
