from __future__ import annotations

import bisect
from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from aniseek.custom_exceptions import SectionSplitProcessError
from aniseek.interfaces import ISectionAdapter, ISectionManagerAdapter
from aniseek.readers import JSONReader, JSONWriter
from aniseek.utils import partition_by_value

if TYPE_CHECKING:
    from aniseek.section import VideoSection


class SectionUnionAdapter(ISectionAdapter):
    def __init__(self, section_1: VideoSection | None, section_2: VideoSection):

        lower, upper = self.__get_sections(section_1, section_2)

        self.__start = lower.start
        self.__end = upper.end
        self.__removed_frames = lower.get_trash() + upper.get_trash()
        self.__black_list = self.__get_black_list(lower, upper)

    def __get_sections(self, section_1, section_2):
        if section_2.id_ > section_1.id_:
            return section_1, section_2
        return section_2, section_1

    def __get_true_end(self, section):
        if len(section.get_trash()) > 0:
            end = max(section.get_trash())
            return max(section.end, end)
        return section.end

    def __get_black_list(self, lower, upper):
        neighbor_start = self.__get_true_end(lower) + 1
        neighbor_end = upper.id_
        neighborhood = list(range(neighbor_start, neighbor_end))
        return lower.black_list_frames + neighborhood + upper.black_list_frames

    def start(self) -> int:
        return self.__start

    def end(self) -> int:
        return self.__end

    def removed_frames(self) -> deque:
        return self.__removed_frames

    def black_list_frames(self) -> list:
        return self.__black_list


class SectionSplitProcess():
    def __init__(self, section: VideoSection, frame_id: int):

        mapping = section.get_mapping()
        if frame_id == section.start:
            raise SectionSplitProcessError('cannot split section from start frame')
        elif frame_id > section.end or frame_id < section.start or frame_id not in mapping:
            raise SectionSplitProcessError(
                f'Cannot split at position "{frame_id}": ' +
                'frame is either deleted or not in the current section.'
            )

        data_1 = dict()
        data_2 = dict()

        removed_1, removed_2 = partition_by_value(section.get_trash(), frame_id)
        black_1, black_2 = partition_by_value(section.black_list_frames, frame_id)

        start_1 = section.start
        idx_end = bisect.bisect_left(mapping, frame_id) - 1
        end_1 = mapping[idx_end]
        data_1['RANGE_FRAME_ID'] = (start_1, end_1)
        data_1['REMOVED_FRAMES'] = removed_1
        data_1['BLACK_LIST'] = black_1

        start_2 = frame_id
        end_2 = section.end
        data_2['RANGE_FRAME_ID'] = (start_2, end_2)
        data_2['REMOVED_FRAMES'] = removed_2
        data_2['BLACK_LIST'] = black_2

        self.__data_1 = data_1
        self.__data_2 = data_2

    def split(self) -> tuple[JSONSectionAdapter, JSONSectionAdapter]:
        return (
            JSONSectionAdapter(self.__data_1),
            JSONSectionAdapter(self.__data_2)
        )


class JSONSectionAdapter(ISectionAdapter):
    def __init__(self, data):
        start, end = data['RANGE_FRAME_ID']
        self.__start = start
        self.__end = end
        self.__removed_frames = deque(data['REMOVED_FRAMES'])
        self.__black_list = data['BLACK_LIST']

    def start(self) -> int:
        return self.__start

    def end(self) -> int:
        return self.__end

    def removed_frames(self) -> deque:
        return self.__removed_frames

    def black_list_frames(self) -> list:
        return self.__black_list


class JSONSectionManagerAdapter(ISectionManagerAdapter):
    def __init__(self, data):
        self._sections = [s for s in data['SECTIONS']]
        self._removed_sections = [r for r in data['REMOVED']]

    def get_sections(self) -> list[dict]:
        return self._sections

    def removed_sections(self) -> list[dict]:
        return self._removed_sections

    @property
    def section_adapter(self) -> JSONSectionAdapter:
        return JSONSectionAdapter


class JSONSectionSave:

    @staticmethod
    def save(file_path: Path, label: str, data: dict):
        logger.info(f'saving section data to "{file_path}" with label "{label}".')
        data_file = JSONReader.read(str(file_path))
        data_file[label] = data
        JSONWriter.write(str(file_path), data_file)


class FakeSectionAdapter(ISectionAdapter):
    def __init__(self, data):
        start, end = data['RANGE_FRAME_ID']
        self.__start = start
        self.__end = end
        self.__removed_frames = deque(data['REMOVED_FRAMES'])
        self.__black_list = data['BLACK_LIST']

    def start(self) -> int:
        return self.__start

    def end(self) -> int:
        return self.__end

    def removed_frames(self) -> deque:
        return self.__removed_frames

    def black_list_frames(self) -> list:
        return self.__black_list


class FakeSectionManagerAdapter(ISectionManagerAdapter):
    def __init__(self, data):
        self._sections = [s for s in data['SECTIONS']]
        self._removed_sections = [r for r in data['REMOVED']]

    def get_sections(self) -> list[dict]:
        return self._sections

    def removed_sections(self) -> list[tuple[dict, dict | None]]:
        return self._removed_sections

    @property
    def section_adapter(self) -> FakeSectionAdapter:
        return FakeSectionAdapter
