from __future__ import annotations

import time

from aniseek.view.interfaces.command import ButtonState, Command
from aniseek.view.video_controller import VideoController


class HoldTimer:
    def __init__(self, delay: float = 0.15, interval: float = 1.0 / 30):
        self.delay = delay
        self.interval = interval
        self._target: float | None = None

    def activate(self) -> None:
        self._target = time.perf_counter() + self.delay

    def collapsed(self) -> bool:
        if self._target is None:
            return False
        return time.perf_counter() >= self._target

    def reactivate(self) -> None:
        self._target = time.perf_counter() + self.interval

    def stop(self) -> None:
        self._target = None


class PauseCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def on_press(self) -> None:
        self.receiver.set_pause()


class RewindCommand(Command):
    def __init__(self, receiver: VideoController, delay: float = 0.15, interval: float = 1.0 / 30):
        self.receiver = receiver
        self.timer = HoldTimer(delay, interval)

    def on_press(self) -> None:
        self.receiver.rewind()
        self.timer.activate()

    def on_hold(self) -> None:
        if self.timer.collapsed():
            self.receiver.rewind()
            self.timer.reactivate()

    def on_release(self) -> None:
        self.timer.stop()


class ProceesCommand(Command):
    def __init__(self, receiver: VideoController, delay: float = 0.15, interval: float = 1.0 / 30):
        self.receiver = receiver
        self.timer = HoldTimer(delay, interval)

    def on_press(self) -> None:
        self.receiver.proceed()
        self.timer.activate()

    def on_hold(self) -> None:
        if self.timer.collapsed():
            self.receiver.proceed()
            self.timer.reactivate()

    def on_release(self) -> None:
        self.timer.stop()


class QuitCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def on_press(self) -> None:
        self.receiver.set_quit()


class IncreaseSpeedCommand(Command):
    def __init__(self, receiver: VideoController, delay: float = 0.15, interval: float = 1.0 / 30):
        self.receiver = receiver
        self.timer = HoldTimer(delay, interval)

    def on_press(self) -> None:
        self.receiver.increase_speed()
        self.timer.activate()

    def on_hold(self) -> None:
        if self.timer.collapsed():
            self.receiver.increase_speed()
            self.timer.reactivate()

    def on_release(self) -> None:
        self.timer.stop()


class DecreaseSpeedCommand(Command):
    def __init__(self, receiver: VideoController, delay: float = 0.15, interval: float = 1.0 / 30):
        self.receiver = receiver
        self.timer = HoldTimer(delay, interval)

    def on_press(self) -> None:
        self.receiver.decrease_speed()
        self.timer.activate()

    def on_hold(self) -> None:
        if self.timer.collapsed():
            self.receiver.decrease_speed()
            self.timer.reactivate()

    def on_release(self) -> None:
        self.timer.stop()


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
    def __init__(self, receiver: VideoController, delay: float = 0.15, interval: float = 1.0 / 30):
        self.receiver = receiver
        self.timer = HoldTimer(delay, interval)

    def on_press(self) -> None:
        self.receiver.remove_frame()
        self.timer.activate()

    def on_hold(self) -> None:
        if self.timer.collapsed():
            self.receiver.remove_frame()
            self.timer.reactivate()

    def on_release(self) -> None:
        self.timer.stop()


class UndoFrameCommand(Command):
    def __init__(self, receiver: VideoController, delay: float = 0.15, interval: float = 1.0 / 30):
        self.receiver = receiver
        self.timer = HoldTimer(delay, interval)

    def on_press(self) -> None:
        self.receiver.undo()
        self.timer.activate()

    def on_hold(self) -> None:
        if self.timer.collapsed():
            self.receiver.undo()
            self.timer.reactivate()

    def on_release(self) -> None:
        self.timer.stop()


class NextVideoCommand(Command):
    def __init__(self, receiver: VideoController, delay: float = 0.15, interval: float = 1.0 / 30):
        self.receiver = receiver
        self.timer = HoldTimer(delay, interval)

    def on_press(self) -> None:
        self.receiver.next_video()
        self.timer.activate()

    def on_hold(self) -> None:
        if self.timer.collapsed():
            self.receiver.next_video()
            self.timer.reactivate()

    def on_release(self) -> None:
        self.timer.stop()


class PrevVideoCommand(Command):
    def __init__(self, receiver: VideoController, delay: float = 0.15, interval: float = 1.0 / 30):
        self.receiver = receiver
        self.timer = HoldTimer(delay, interval)

    def on_press(self) -> None:
        self.receiver.prev_video()
        self.timer.activate()

    def on_hold(self) -> None:
        if self.timer.collapsed():
            self.receiver.prev_video()
            self.timer.reactivate()

    def on_release(self) -> None:
        self.timer.stop()


class NextSectionCommand(Command):
    def __init__(self, receiver: VideoController, delay: float = 0.15, interval: float = 1.0 / 30):
        self.receiver = receiver
        self.timer = HoldTimer(delay, interval)

    def on_press(self) -> None:
        self.receiver.next_section()
        self.timer.activate()

    def on_hold(self) -> None:
        if self.timer.collapsed():
            self.receiver.next_section()
            self.timer.reactivate()

    def on_release(self) -> None:
        self.timer.stop()


class PrevSectionCommand(Command):
    def __init__(self, receiver: VideoController, delay: float = 0.15, interval: float = 1.0 / 30):
        self.receiver = receiver
        self.timer = HoldTimer(delay, interval)

    def on_press(self) -> None:
        self.receiver.prev_section()
        self.timer.activate()

    def on_hold(self) -> None:
        if self.timer.collapsed():
            self.receiver.prev_section()
            self.timer.reactivate()

    def on_release(self) -> None:
        self.timer.stop()


class RemoveSectionCommand(Command):
    def __init__(self, receiver: VideoController, delay: float = 0.15, interval: float = 1.0 / 30):
        self.receiver = receiver
        self.timer = HoldTimer(delay, interval)

    def on_press(self) -> None:
        self.receiver.remove_section()
        self.timer.activate()

    def on_hold(self) -> None:
        if self.timer.collapsed():
            self.receiver.remove_section()
            self.timer.reactivate()

    def on_release(self) -> None:
        self.timer.stop()


class SplitSectionCommand(Command):
    def __init__(self, receiver: VideoController, delay: float = 0.15, interval: float = 1.0 / 30):
        self.receiver = receiver
        self.timer = HoldTimer(delay, interval)

    def on_press(self) -> None:
        self.receiver.split_section()
        self.timer.activate()

    def on_hold(self) -> None:
        if self.timer.collapsed():
            self.receiver.split_section()
            self.timer.reactivate()

    def on_release(self) -> None:
        self.timer.stop()


class UndoSectionCommand(Command):
    def __init__(self, receiver: VideoController, delay: float = 0.15, interval: float = 1.0 / 30):
        self.receiver = receiver
        self.timer = HoldTimer(delay, interval)

    def on_press(self) -> None:
        self.receiver.undo_section()
        self.timer.activate()

    def on_hold(self) -> None:
        if self.timer.collapsed():
            self.receiver.undo_section()
            self.timer.reactivate()

    def on_release(self) -> None:
        self.timer.stop()


class JoinSectionCommand(Command):
    def __init__(self, receiver: VideoController, delay: float = 0.15, interval: float = 1.0 / 30):
        self.receiver = receiver
        self.timer = HoldTimer(delay, interval)

    def on_press(self) -> None:
        self.receiver.join_section()
        self.timer.activate()

    def on_hold(self) -> None:
        if self.timer.collapsed():
            self.receiver.join_section()
            self.timer.reactivate()

    def on_release(self) -> None:
        self.timer.stop()


class JumpSectionStartCommand(Command):
    def __init__(self, receiver: VideoController, delay: float = 0.15, interval: float = 1.0 / 30):
        self.receiver = receiver
        self.timer = HoldTimer(delay, interval)

    def on_press(self) -> None:
        self.receiver.jump_section_start()
        self.timer.activate()

    def on_hold(self) -> None:
        if self.timer.collapsed():
            self.receiver.jump_section_start()
            self.timer.reactivate()

    def on_release(self) -> None:
        self.timer.stop()


class JumpSectionEndCommand(Command):
    def __init__(self, receiver: VideoController, delay: float = 0.15, interval: float = 1.0 / 30):
        self.receiver = receiver
        self.timer = HoldTimer(delay, interval)

    def on_press(self) -> None:
        self.receiver.jump_section_end()
        self.timer.activate()

    def on_hold(self) -> None:
        if self.timer.collapsed():
            self.receiver.jump_section_end()
            self.timer.reactivate()

    def on_release(self) -> None:
        self.timer.stop()


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
