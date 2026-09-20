from __future__ import annotations

from collections import deque

from loguru import logger

from aniseek.core.frame_mapper import FrameMapper
from aniseek.custom_exceptions import SectionManagerError, SectionSplitProcessError
from aniseek.editing.trash import Trash
from aniseek.editing.utils import FrameMementoHandler, partition_by_value


class VideoSection:
    def __init__(
        self,
        start: int,
        end: int,
        removed_frames: deque[int] | list[int] | None = None,
        black_list_frames: list[int] | None = None,
        id: int | None = None,
    ) -> None:
        self._start = start
        self._end = end
        self._removed_frames = deque(removed_frames) if removed_frames is not None else deque()
        self._black_list_frames = list(black_list_frames) if black_list_frames is not None else []
        self._id = id if id is not None else self._calculate_id()
        self._mapping = self._calculate_mapping()

    @property
    def start(self) -> int:
        return self._start

    @property
    def end(self) -> int:
        return self._end

    @property
    def removed_frames(self) -> deque[int]:
        return self._removed_frames

    @property
    def black_list_frames(self) -> list[int]:
        return self._black_list_frames

    @property
    def id(self) -> int:
        return self._id

    @property
    def mapping(self) -> list[int]:
        return self._mapping

    @classmethod
    def from_dict(cls, data: dict) -> VideoSection:
        """Cria a seção diretamente do dicionário serializado."""
        start, end = data['RANGE_FRAME_ID']
        return cls(
            start=start,
            end=end,
            removed_frames=data.get('REMOVED_FRAMES'),
            black_list_frames=data.get('BLACK_LIST'),
        )

    def to_dict(self) -> dict:
        """Serializa a seção para persistência JSON."""
        return {
            'RANGE_FRAME_ID': (self._start, self._end),
            'REMOVED_FRAMES': list(self._removed_frames),
            'BLACK_LIST': self._black_list_frames,
        }

    def split(self, frame_id: int) -> tuple[VideoSection, VideoSection]:
        """Fatia a seção em duas diretamente em memória."""
        if len(self._mapping) < 2:
            raise SectionSplitProcessError(
                f'Cannot split section with fewer than 2 frames (has {len(self._mapping)}).'
            )
        if frame_id <= self._start or frame_id >= self._end:
            raise SectionSplitProcessError(
                f'Cannot split at position "{frame_id}": outside section bounds ({self._start}..{self._end}).'
            )
        if frame_id <= self._mapping[0] or frame_id > self._mapping[-1]:
            raise SectionSplitProcessError(
                f'Cannot split at position "{frame_id}": would create an empty section.'
            )
        if frame_id not in self._mapping:
            raise SectionSplitProcessError(
                f'Cannot split at position "{frame_id}": frame is deleted or blacklisted.'
            )

        removed_1, removed_2 = partition_by_value(self._removed_frames, frame_id)
        black_1, black_2 = partition_by_value(self._black_list_frames, frame_id)

        section_1 = VideoSection(self._start, frame_id, removed_1, black_1)
        section_2 = VideoSection(frame_id, self._end, removed_2, black_2)
        return section_1, section_2

    def split_section(self, frame_id: int) -> tuple[VideoSection, VideoSection]:
        return self.split(frame_id)

    def join(self, other: VideoSection) -> VideoSection:
        """Funde a seção atual com outra adjacente diretamente em memória."""
        lower, upper = (self, other) if self.id <= other.id else (other, self)

        new_start = lower.start
        new_end = upper.end
        new_removed = deque(list(lower.removed_frames) + list(upper.removed_frames))

        true_end_lower = max(lower.removed_frames) if len(lower.removed_frames) > 0 else lower.end
        true_end_lower = max(lower.end, true_end_lower)
        neighbor_start = true_end_lower + 1
        neighbor_end = upper.id
        neighborhood = list(range(neighbor_start, neighbor_end)) if neighbor_start < neighbor_end else []
        new_black_list = lower.black_list_frames + neighborhood + upper.black_list_frames

        return VideoSection(new_start, new_end, new_removed, new_black_list)

    def _calculate_id(self) -> int:
        if len(self._removed_frames) > 0:
            return min(self._start, min(self._removed_frames))
        return self._start

    def _calculate_mapping(self) -> list[int]:
        if self._start is None:
            return []
        frames_id = set(range(self._start, self._end))
        removeds = set(list(self._removed_frames) + self._black_list_frames)
        return sorted(frames_id - removeds)

    def update_range(self, frame_map: FrameMapper | list[int]) -> None:
        """Atualiza o range da seção, ou seja, o start e end dos frames."""
        self._start = frame_map[0]
        self._end = frame_map[-1]

    def get_trash(self) -> deque[int]:
        return self._removed_frames

    def get_mapping(self) -> list[int]:
        return self._mapping

    def __repr__(self) -> str:
        return f"VideoSection(id={self.id}, range=({self._start}, {self._end}))"

    def __add__(self, obj: VideoSection) -> VideoSection:
        return self.join(obj)

    def __truediv__(self, frame_id: int) -> tuple[VideoSection, VideoSection]:
        return self.split(frame_id)

    def __eq__(self, other: VideoSection) -> bool:
        return self.id == other.id

    def __lt__(self, other: VideoSection) -> bool:
        return self.id < other.id

    def __le__(self, other: VideoSection) -> bool:
        return self.id <= other.id


class SectionManager:
    def __init__(
        self,
        sections: list[VideoSection],
        removed_sections: list[list[VideoSection | None]] | None = None,
    ) -> None:
        if not sections and not removed_sections:
            raise SectionManagerError('there are no sections id to work with')
        self._sections: list[VideoSection] = list(sections)
        self._current_index: int = 0
        self._removed_history: list[list[VideoSection | None]] = (
            list(removed_sections) if removed_sections is not None else []
        )
        self._removed_sections: list[list[VideoSection | None]] = []
        self._undo_stack: deque[dict] = deque()
        self._undo_frame: int | None = None

    @property
    def undo_frame(self) -> int | None:
        return self._undo_frame

    @property
    def sections(self) -> list[VideoSection]:
        return self._sections

    @property
    def current_index(self) -> int:
        return self._current_index

    @property
    def removed_sections(self) -> list[list[VideoSection | None]]:
        return self._removed_sections

    @property
    def current_section(self) -> VideoSection:
        if 0 <= self._current_index < len(self._sections):
            return self._sections[self._current_index]
        raise SectionManagerError('No active section available')

    @property
    def section_id(self) -> int | None:
        if self._sections and 0 <= self._current_index < len(self._sections):
            return self.current_section.id
        return None

    @classmethod
    def from_dict(cls, data: dict) -> SectionManager:
        raw_sections = data.get('SECTIONS', [])
        sections = [VideoSection.from_dict(s) for s in raw_sections]
        raw_removed = data.get('REMOVED', [])
        removed_sections = []
        for pair in raw_removed:
            if pair is None:
                continue
            sec1 = VideoSection.from_dict(pair[0]) if pair[0] is not None else None
            sec2 = VideoSection.from_dict(pair[1]) if len(pair) > 1 and pair[1] is not None else None
            removed_sections.append([sec1, sec2])
        return cls(sections=sections, removed_sections=removed_sections)

    def to_dict(self, trash: Trash | None = None) -> dict:
        if trash is not None:
            self.store_mementos_frames(trash)
        return {
            'SECTIONS': [s.to_dict() for s in self._sections],
            'REMOVED': [
                [s.to_dict() if s is not None else None for s in pair]
                for pair in self._removed_history
            ],
        }

    def __len__(self) -> int:
        return len(self._sections)

    def get_section(self) -> VideoSection:
        return self.current_section

    def get_mapping(self) -> list[int]:
        if not self._sections:
            return []
        return self.current_section.get_mapping()

    def get_preview_mapping(self) -> list[int]:
        """Retorna o mapping contínuo unindo todas as seções ativas (Rough Cut Preview)."""
        preview = []
        for sec in self._sections:
            preview.extend(sec.get_mapping())
        return preview

    def index_of(self, frame_id: int) -> int | None:
        """Retorna o índice da seção que contém o frame_id."""
        for idx, sec in enumerate(self._sections):
            if frame_id in sec.mapping:
                return idx
        return None

    def goto_frame(self, frame_id: int, trash: Trash | None = None) -> bool:
        """Posiciona o índice ativo na seção que contém o frame_id."""
        idx = self.index_of(frame_id)
        if idx is not None and idx != self._current_index:
            if trash is not None:
                self.store_mementos_frames(trash)
            self._current_index = idx
            if trash is not None:
                trash.reset(None)
                self.load_mementos_frames(trash)
            return True
        return False

    def update_mapping(self) -> None:
        if self._sections and 0 <= self._current_index < len(self._sections):
            self.current_section.mapping = self.current_section._calculate_mapping()

    def can_next(self) -> bool:
        return self._current_index < len(self._sections) - 1

    def can_prev(self) -> bool:
        return self._current_index > 0

    def _next_section(self) -> bool:
        if self.can_next():
            self._current_index += 1
            return True
        return False

    def _prev_section(self) -> bool:
        if self.can_prev():
            self._current_index -= 1
            return True
        return False

    def next_section(self, trash: Trash) -> bool:
        if not self.can_next():
            return False
        self.store_mementos_frames(trash)
        self._next_section()
        trash.reset(None)
        self.load_mementos_frames(trash)
        return True

    def prev_section(self, trash: Trash) -> bool:
        if not self.can_prev():
            return False
        self.store_mementos_frames(trash)
        self._prev_section()
        trash.reset(None)
        self.load_mementos_frames(trash)
        return True

    def load_mementos_frames(self, trash: Trash) -> None:
        if not self._sections or self._current_index >= len(self._sections):
            return
        curr = self.current_section
        trash_originator = trash.get_originator()
        trash_caretaker = trash.get_caretaker()
        frame_handler = FrameMementoHandler(trash_originator, trash_caretaker)
        frame_handler.load_mementos(curr)

    def store_mementos_frames(self, trash: Trash) -> None:
        if not self._sections or self._current_index >= len(self._sections):
            return
        curr = self.current_section
        trash_originator = trash.get_originator()
        trash_caretaker = trash.get_caretaker()
        frame_handler = FrameMementoHandler(trash_originator, trash_caretaker, trash)
        frame_handler.store_mementos(curr)

    def split_section(self, frame_id: int, trash: Trash, direction: int = 1) -> bool:
        if not self._sections:
            return False
        try:
            self.store_mementos_frames(trash)
            curr = self.current_section
            sec1, sec2 = curr.split(frame_id)
        except Exception as e:
            logger.warning(f"Could not split section at frame {frame_id}: {e}")
            self.load_mementos_frames(trash)
            return False

        self._save_undo_state(frame_id=frame_id)
        self._removed_history.append([curr, None])
        self._sections[self._current_index] = sec1
        self._sections.insert(self._current_index + 1, sec2)
        if direction == 1:
            self._current_index += 1
        return True

    def can_join_prev(self) -> bool:
        return self._current_index > 0

    def can_join_next(self) -> bool:
        return self._current_index < len(self._sections) - 1

    def join_section(self, trash: Trash, direction: int = -1, frame_id: int | None = None) -> bool:
        """Funde a seção atual com a vizinha (anterior se direction == -1, próxima se direction == 1)."""
        if direction == -1:
            if not self.can_join_prev():
                return False
            idx1 = self._current_index - 1
            idx2 = self._current_index
        else:
            if not self.can_join_next():
                return False
            idx1 = self._current_index
            idx2 = self._current_index + 1

        self.store_mementos_frames(trash)
        self._save_undo_state(frame_id=frame_id)

        sec1 = self._sections[idx1]
        sec2 = self._sections[idx2]
        self._removed_history.append([sec1, sec2])
        joined = sec1.join(sec2)

        self._sections[idx1] = joined
        del self._sections[idx2]
        self._current_index = idx1
        return True

    def remove_section(self, trash: Trash, frame_id: int | None = None) -> bool:
        if not self._sections:
            logger.debug('there are no more sections to remove')
            return False

        self.store_mementos_frames(trash)
        self._save_undo_state(frame_id=frame_id)

        removed = self._sections.pop(self._current_index)
        self._removed_history.append([removed, None])

        if self._current_index >= len(self._sections) and len(self._sections) > 0:
            self._current_index = len(self._sections) - 1
        elif len(self._sections) == 0:
            self._current_index = 0

        trash.reset(None)
        self.load_mementos_frames(trash)
        return True

    def restore_section(self, trash: Trash | None = None) -> bool:
        if self._undo_stack:
            state = self._undo_stack.pop()
            self._sections = [
                VideoSection(
                    start=s.start,
                    end=s.end,
                    removed_frames=deque(s.removed_frames),
                    black_list_frames=list(s.black_list_frames),
                    id=s.id,
                )
                for s in state['sections']
            ]
            self._current_index = state['current_index']
            self._undo_frame = state.get('frame_id')
            self._removed_history = [
                [
                    VideoSection(
                        start=s.start,
                        end=s.end,
                        removed_frames=deque(s.removed_frames),
                        black_list_frames=list(s.black_list_frames),
                        id=s.id,
                    )
                    if s is not None else None
                    for s in pair
                ]
                for pair in state['removed_history']
            ]
            if trash is not None:
                trash.reset(None)
                self.load_mementos_frames(trash)
            return True

        if self._removed_history:
            pair = self._removed_history.pop()
            sec1, sec2 = pair[0], pair[1] if len(pair) > 1 else None
            if sec2 is None and sec1 is not None:
                parent = sec1
                contained = [
                    (i, s) for i, s in enumerate(self._sections)
                    if s.start >= parent.start and s.end <= parent.end
                ]
                if len(contained) >= 2:
                    first_idx = contained[0][0]
                    last_idx = contained[-1][0]
                    self._sections = (
                        self._sections[:first_idx]
                        + [parent]
                        + self._sections[last_idx + 1:]
                    )
                    self._current_index = min(first_idx, len(self._sections) - 1)
                else:
                    idx = 0
                    while idx < len(self._sections) and self._sections[idx].id < parent.id:
                        idx += 1
                    self._sections.insert(idx, parent)
                    self._current_index = idx
            elif sec1 is not None and sec2 is not None:
                joined_idx = None
                for i, s in enumerate(self._sections):
                    if s.start == sec1.start and s.end == sec2.end:
                        joined_idx = i
                        break
                if joined_idx is not None:
                    self._sections[joined_idx] = sec1
                    self._sections.insert(joined_idx + 1, sec2)
                    self._current_index = joined_idx
                else:
                    idx = 0
                    while idx < len(self._sections) and self._sections[idx].id < sec1.id:
                        idx += 1
                    self._sections.insert(idx, sec1)
                    idx2 = idx + 1
                    while idx2 < len(self._sections) and self._sections[idx2].id < sec2.id:
                        idx2 += 1
                    self._sections.insert(idx2, sec2)
                    self._current_index = idx

            if trash is not None:
                trash.reset(None)
                self.load_mementos_frames(trash)
            return True

        return False

    def _save_undo_state(self, frame_id: int | None = None) -> None:
        sections_copy = [
            VideoSection(
                start=s.start,
                end=s.end,
                removed_frames=deque(s.removed_frames),
                black_list_frames=list(s.black_list_frames),
                id=s.id,
            )
            for s in self._sections
        ]
        removed_copy = [
            [
                VideoSection(
                    start=s.start,
                    end=s.end,
                    removed_frames=deque(s.removed_frames),
                    black_list_frames=list(s.black_list_frames),
                    id=s.id,
                )
                if s is not None else None
                for s in pair
            ]
            for pair in self._removed_history
        ]
        self._undo_stack.append({
            'sections': sections_copy,
            'current_index': self._current_index,
            'removed_history': removed_copy,
            'frame_id': frame_id,
        })
