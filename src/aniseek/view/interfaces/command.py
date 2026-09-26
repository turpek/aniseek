from abc import ABC
from enum import Enum


class ButtonState(Enum):
    PRESS = "on_press"
    HOLD = "on_hold"
    RELEASE = "on_release"


class Command(ABC):
    def executor(self, state: ButtonState) -> None:
        getattr(self, state.value)()

    def on_press(self) -> None:
        pass

    def on_hold(self) -> None:
        pass

    def on_release(self) -> None:
        pass
