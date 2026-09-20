from abc import ABC, abstractmethod
from collections import deque


class ISectionAdapter(ABC):
    @abstractmethod
    def start(self) -> int:
        ...

    @abstractmethod
    def end(self) -> int:
        ...

    @abstractmethod
    def removed_frames(self) -> deque:
        ...

    @abstractmethod
    def black_list_frames(self) -> list:
        ...


class ISectionManagerAdapter(ABC):

    @abstractmethod
    def get_sections(self):
        ...

    @abstractmethod
    def removed_sections(self):
        ...

    @abstractmethod
    def section_adapter(self):
        ...


class IDataReader(ABC):

    @abstractmethod
    def read(self, filename: str):
        ...


class IDataWriter(ABC):

    @abstractmethod
    def write(self, file_path: str, data):
        ...
