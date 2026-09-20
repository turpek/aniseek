from abc import ABC, abstractmethod
from collections import deque


class IVideoBuffer(ABC):

    def __init__(self):
        ...

    @abstractmethod
    def set_frame_id(self) -> None:
        ...


class IFakeVideoBuffer(IVideoBuffer):

    def __init__(self):
        ...

    def set_frame_id(self) -> None:
        ...


class IMemento(ABC):
    @abstractmethod
    def get_state(self) -> int:
        ...


class IOriginator(ABC):
    @abstractmethod
    def save(self) -> IMemento:
        ...

    @abstractmethod
    def undo(self, memento: IMemento):
        ...


class Command(ABC):
    @abstractmethod
    def executor(self):
        ...


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


class IMementoHandler(ABC):

    @abstractmethod
    def store_mementos(self, section):
        ...

    @abstractmethod
    def load_mementos(self, section):
        ...


class IDataReader(ABC):

    @abstractmethod
    def read(self, filename: str):
        ...


class IDataWriter(ABC):

    @abstractmethod
    def write(self, file_path: str, data):
        ...
