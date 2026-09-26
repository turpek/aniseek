from __future__ import annotations

import time

from aniseek.view.interfaces.command import ButtonState, Command
from aniseek.view.video_controller import VideoController


class PauseCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def on_press(self) -> None:
        self.receiver.set_pause()


class RewindCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def on_press(self) -> None:
        self.receiver.rewind()


class ProceesCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def on_press(self) -> None:
        self.receiver.proceed()


class QuitCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def on_press(self) -> None:
        self.receiver.set_quit()


class IncreaseSpeedCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def on_press(self) -> None:
        self.receiver.increase_speed()


class DecreaseSpeedCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def on_press(self) -> None:
        self.receiver.decrease_speed()


class PauseDelayCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def on_press(self) -> None:
        self.receiver.pause_delay()


class RestoreDelayCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def on_press(self) -> None:
        self.receiver.restore_delay()


class RemoveFrameCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def on_press(self) -> None:
        self.receiver.remove_frame()


class UndoFrameCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def on_press(self) -> None:
        self.receiver.undo()


class NextVideoCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def on_press(self) -> None:
        self.receiver.next_video()


class PrevVideoCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def on_press(self) -> None:
        self.receiver.prev_video()


class NextSectionCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def on_press(self) -> None:
        self.receiver.next_section()


class PrevSectionCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def on_press(self) -> None:
        self.receiver.prev_section()


class RemoveSectionCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def on_press(self) -> None:
        self.receiver.remove_section()


class SplitSectionCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def on_press(self) -> None:
        self.receiver.split_section()


class UndoSectionCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def on_press(self) -> None:
        self.receiver.undo_section()


class JoinSectionCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def on_press(self) -> None:
        self.receiver.join_section()


class JumpSectionStartCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def on_press(self) -> None:
        self.receiver.jump_section_start()


class JumpSectionEndCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def on_press(self) -> None:
        self.receiver.jump_section_end()


class TogglePreviewCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def on_press(self) -> None:
        self.receiver.toggle_preview()


class SaveCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def on_press(self) -> None:
        self.receiver.save()


class DynamicProceedCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver
        self._saved_delay: int | None = None
        self._start_time: float | None = None

    def on_press(self) -> None:
        self._start_time = time.perf_counter()
        self._saved_delay = self.receiver.delay
        self.receiver.proceed()

    def on_hold(self) -> None:
        if self._start_time is None:
            self._start_time = time.perf_counter()
        if self._saved_delay is None:
            self._saved_delay = self.receiver.delay

        elapsed = time.perf_counter() - self._start_time
        if elapsed < 0.15:
            return
        elif elapsed < 0.40:
            self.receiver.set_delay(40)
        elif elapsed < 0.80:
            self.receiver.set_delay(16)
        else:
            self.receiver.set_delay(1)

    def on_release(self) -> None:
        self._start_time = None
        if self._saved_delay is not None:
            self.receiver.set_delay(self._saved_delay)
            self._saved_delay = None


class DynamicRewindCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver
        self._saved_delay: int | None = None
        self._start_time: float | None = None

    def on_press(self) -> None:
        self._start_time = time.perf_counter()
        self._saved_delay = self.receiver.delay
        self.receiver.rewind()

    def on_hold(self) -> None:
        if self._start_time is None:
            self._start_time = time.perf_counter()
        if self._saved_delay is None:
            self._saved_delay = self.receiver.delay

        elapsed = time.perf_counter() - self._start_time
        if elapsed < 0.15:
            return
        elif elapsed < 0.40:
            self.receiver.set_delay(40)
        elif elapsed < 0.80:
            self.receiver.set_delay(16)
        else:
            self.receiver.set_delay(1)

    def on_release(self) -> None:
        self._start_time = None
        if self._saved_delay is not None:
            self.receiver.set_delay(self._saved_delay)
            self._saved_delay = None


class MacroCommand(Command):
    def __init__(self, commands: list[Command] | tuple[Command, ...] | None = None):
        self._commands: list[Command] = []
        if commands is not None:
            for cmd in commands:
                self.add(cmd)

    def add(self, command: Command) -> None:
        if not isinstance(command, Command):
            raise TypeError(
                f"Expected command to be an instance of Command, got {type(command).__name__}"
            )
        self._commands.append(command)

    def executor(self, state: ButtonState) -> None:
        for command in self._commands:
            command.executor(state)


class Invoker:
    def __init__(self):
        self.commands: dict[int | str, Command] = {}

    def set_command(self, key: int | str, command: Command) -> None:
        self.commands[key] = command

    def executor_command(self, key: int | str, state: ButtonState) -> None:
        if key in self.commands:
            self.commands[key].executor(state)
