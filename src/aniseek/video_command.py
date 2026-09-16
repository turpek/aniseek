from aniseek.interfaces import Command
from aniseek.video_controller import VideoController


class PauseCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def executor(self) -> None:
        self.receiver.set_pause()


class RewindCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def executor(self) -> None:
        self.receiver.rewind()


class ProceesCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def executor(self) -> None:
        self.receiver.proceed()


class QuitCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def executor(self) -> None:
        self.receiver.set_quit()


class IncreaseSpeedCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def executor(self) -> None:
        self.receiver.increase_speed()


class DecreaseSpeedCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def executor(self) -> None:
        self.receiver.decrease_speed()


class PauseDelayCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def executor(self) -> None:
        self.receiver.pause_delay()


class RestoreDelayCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def executor(self) -> None:
        self.receiver.restore_delay()


class RemoveFrameCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def executor(self) -> None:
        self.receiver.remove_frame()


class UndoFrameCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def executor(self) -> None:
        self.receiver.undo()


class NextVideoCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def executor(self) -> None:
        self.receiver.next_video()


class PrevVideoCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def executor(self) -> None:
        self.receiver.prev_video()


class NextSectionCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def executor(self) -> None:
        self.receiver.next_section()


class PrevSectionCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def executor(self) -> None:
        self.receiver.prev_section()


class RemoveSectionCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def executor(self) -> None:
        self.receiver.remove_section()


class SplitSectionCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def executor(self) -> None:
        self.receiver.split_section()


class UndoSectionCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def executor(self) -> None:
        self.receiver.undo_section()


class JoinSectionCommand(Command):
    def __init__(self, receiver: VideoController):
        self.receiver = receiver

    def executor(self) -> None:
        self.receiver.join_section()


class Invoker:
    def __init__(self):
        self.commands = {}

    def set_command(self, key, command: Command) -> None:
        self.commands[key] = command

    def executor_command(self, key) -> None:
        if key in self.commands:
            self.commands[key].executor()
