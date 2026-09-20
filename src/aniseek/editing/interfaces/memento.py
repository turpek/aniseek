from abc import ABC, abstractmethod


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


class IMementoHandler(ABC):

    @abstractmethod
    def store_mementos(self, section):
        ...

    @abstractmethod
    def load_mementos(self, section):
        ...
