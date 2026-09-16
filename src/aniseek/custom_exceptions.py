class InvalidFrameIdError(Exception):
    def __init__(self, message):
        self.message = message


class VideoBufferError(Exception):
    def __init__(self, message):
        self.message = message


class VideoOpenError(Exception):
    def __init__(self, message):
        self.message = message


class SectionError(Exception):
    def __init__(self, message):
        self.message = message


class SectionManagerError(Exception):
    def __init__(self, message):
        self.message = message


class SimpleStackError(Exception):
    def __init__(self, message):
        self.message = message


class FrameWrapperError(Exception):
    def __init__(self, message):
        self.message = message


class FrameStackError(Exception):
    def __init__(self, message):
        self.message = message


class PlaylistError(Exception):
    def __init__(self, message):
        self.message = message


class SectionSplitProcessError(Exception):
    def __init__(self, message):
        self.message = message
