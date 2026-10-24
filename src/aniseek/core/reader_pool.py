from __future__ import annotations

import bisect
from collections import OrderedDict, deque
from typing import Any, Iterator

from numpy import ndarray

from aniseek.core.frame_mapper import FrameMapper
from aniseek.core.video_reader import BaseVideoReader, VideoReader


class FrameSync:
    """Sincronizador de cursores em pilha dupla sobre o FrameMapper."""

    def __init__(self, mapping: FrameMapper, *, reverse: bool = False) -> None:
        self._mapping = mapping
        self._right: deque[int] = deque()
        self._left: deque[int] = deque()
        self.frame_id: int | None = None
        self.seek_id: int = 0

        if reverse:
            self._left.extend(reversed(mapping.frame_ids))
            self.servant = self._left
            self.master = self._right
        else:
            self._right.extend(mapping.frame_ids)
            self.servant = self._right
            self.master = self._left

    @property
    def is_complete(self) -> bool:
        return len(self.servant) == 0

    def get(self) -> int:
        self.seek_id = (
            self._right[0] if len(self._right) > 0 else self._mapping.frame_ids[-1] + 1
        )
        frame_id = self.servant.popleft()
        self.master.appendleft(frame_id)
        self.frame_id = frame_id
        return frame_id

    def proceed(self) -> None:
        if self.servant is self._left:
            self.servant, self.master = self.master, self.servant

    def rewind(self) -> None:
        if self.servant is self._right:
            self.servant, self.master = self.master, self.servant

    def set(self, frame_id: int) -> None:
        frame_ids = self._mapping.frame_ids
        idx = bisect.bisect_left(frame_ids, frame_id)
        self._right.clear()
        self._left.clear()
        self._right.extend(frame_ids[idx:])
        self._left.extend(reversed(frame_ids[:idx]))
        self.frame_id = None


class ReaderProxy:
    """Proxy que vincula um leitor de vídeo ao cache compartilhado do ReaderPool."""

    def __init__(self, reader: BaseVideoReader, pool: ReaderPool) -> None:
        self._reader = reader
        self._pool = pool
        self._sync = FrameSync(reader.mapping, reverse=reader.is_reverse)

    def __len__(self) -> int:
        return len(self._reader)

    def __contains__(self, frame_id: int) -> bool:
        return frame_id in self._reader

    def __iter__(self) -> Iterator[tuple[bool, ndarray | None]]:
        while not self.is_task_complete:
            ret, frame = self.read()
            yield ret, frame

    def __enter__(self) -> ReaderProxy:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._reader, name)

    @property
    def frame_id(self) -> int | None:
        return self._sync.frame_id

    @property
    def is_task_complete(self) -> bool:
        return self._sync.is_complete

    @property
    def is_reverse(self) -> bool:
        return self._reader.is_reverse

    def read(self) -> tuple[bool, ndarray | None]:
        if self._sync.is_complete:
            return False, None

        target_id = self._sync.get()
        hit, frame = self._pool.read(target_id)
        if hit:
            return True, frame

        if target_id not in self._reader:
            self._reader.set_frame(self._sync.seek_id)

        ret, frame = False, None
        while not self._reader.is_task_complete:
            ret, frame = self._reader.read()
            if not ret or frame is None:
                break
            if self._reader.frame_id is not None:
                self._pool.put(self._reader, self._reader.frame_id, frame)
            if self._reader.frame_id == target_id:
                break

        return ret, frame

    def set_frame(self, frame_id: int) -> None:
        self._sync.set(frame_id)

    def set_bounds(self, start: int, end: int) -> None:
        self._reader.set_bounds(start, end)
        self._sync = FrameSync(self._reader.mapping, reverse=self._reader.is_reverse)

    def proceed(self) -> None:
        self._sync.proceed()
        self._reader.proceed()  # type: ignore[attr-defined]

    def rewind(self) -> None:
        self._sync.rewind()
        self._reader.rewind()  # type: ignore[attr-defined]

    def clear(self) -> None:
        self._reader.clear()

    def close(self) -> None:
        self._reader.close()


class ReaderPool:
    """Fábrica e gerenciador de múltiplos leitores com cache de frames compartilhado."""

    def __init__(self, maxsize: int = 100) -> None:
        self.maxsize = maxsize
        self._cache: dict[BaseVideoReader, OrderedDict[int, ndarray]] = {}

    def get_reader(
        self,
        cls: type[BaseVideoReader] = VideoReader,
        *args: Any,
        **kwargs: Any,
    ) -> ReaderProxy:
        kwargs.setdefault("lazy", True)
        reader = cls(*args, **kwargs)
        self._cache[reader] = OrderedDict()
        return ReaderProxy(reader, self)

    def read(self, frame_id: int) -> tuple[bool, ndarray | None]:
        for cache in self._cache.values():
            if frame_id in cache:
                return True, cache[frame_id]
        return False, None

    def put(self, reader: BaseVideoReader, frame_id: int, frame: ndarray) -> None:
        cache = self._cache[reader]
        cache[frame_id] = frame
        if self.maxsize > 0 and len(cache) > self.maxsize:
            cache.popitem(last=False)

    def clear(self) -> None:
        for reader, cache in self._cache.items():
            cache.clear()
            reader.clear()

    def close(self) -> None:
        for reader, cache in self._cache.items():
            cache.clear()
            reader.close()
        self._cache.clear()
