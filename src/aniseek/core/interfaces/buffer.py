from abc import ABC, abstractmethod


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
