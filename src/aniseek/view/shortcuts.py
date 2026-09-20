from __future__ import annotations

from aniseek.view.input_handler import CV2KeyReader, HybridKeyReader, PynputKeyReader
from aniseek.view.interfaces.input import InputHandler

IP = InputHandler

CV2_SHORTCUTS: dict[int, str] = {
    # Playback & speed control
    ord('b'): 'PauseCommand',
    ord('q'): 'QuitCommand',
    ord(' '): 'PauseDelayCommand',
    ord('='): 'RestoreDelayCommand',
    ord(']'): 'IncreaseSpeedCommand',
    ord('['): 'DecreaseSpeedCommand',
    ord('n'): 'NextVideoCommand',
    ord('p'): 'PrevVideoCommand',
    # Frame operations (no modifier)
    ord('d'): 'ProceesCommand',
    ord('a'): 'RewindCommand',
    ord('x'): 'RemoveFrameCommand',
    ord('u'): 'UndoFrameCommand',
    # Section operations (with Shift or Uppercase)
    IP.SHIFT_BIT | ord('d'): 'NextSectionCommand',
    ord('D'): 'NextSectionCommand',
    IP.SHIFT_BIT | ord('a'): 'PrevSectionCommand',
    ord('A'): 'PrevSectionCommand',
    IP.SHIFT_BIT | ord('s'): 'SplitSectionCommand',
    ord('S'): 'SplitSectionCommand',
    IP.SHIFT_BIT | ord('j'): 'JoinSectionCommand',
    ord('J'): 'JoinSectionCommand',
    IP.SHIFT_BIT | ord('x'): 'RemoveSectionCommand',
    ord('X'): 'RemoveSectionCommand',
    IP.SHIFT_BIT | ord('u'): 'UndoSectionCommand',
    ord('U'): 'UndoSectionCommand',
    IP.KEY_HOME: 'JumpSectionStartCommand',
    IP.KEY_END: 'JumpSectionEndCommand',
    ord('v'): 'TogglePreviewCommand',
    ord('V'): 'TogglePreviewCommand',
    # Save operation
    IP.SHIFT_BIT | ord('w'): 'SaveCommand',
    ord('W'): 'SaveCommand',
    IP.CTRL_BIT | ord('w'): 'SaveCommand',
    IP.CTRL_BIT | ord('W'): 'SaveCommand',
}

PYNPUT_SHORTCUTS: dict[int, str] = {
    # Playback & speed control
    ord('b'): 'PauseCommand',
    ord('q'): 'QuitCommand',
    ord(' '): 'PauseDelayCommand',
    ord('='): 'RestoreDelayCommand',
    ord(']'): 'IncreaseSpeedCommand',
    ord('['): 'DecreaseSpeedCommand',
    ord('n'): 'NextVideoCommand',
    ord('p'): 'PrevVideoCommand',
    # Frame operations (no modifier)
    ord('d'): 'ProceesCommand',
    ord('a'): 'RewindCommand',
    ord('x'): 'RemoveFrameCommand',
    ord('u'): 'UndoFrameCommand',
    # Section operations (with Ctrl)
    IP.CTRL_BIT | ord('d'): 'NextSectionCommand',
    IP.CTRL_BIT | ord('a'): 'PrevSectionCommand',
    IP.CTRL_BIT | ord('s'): 'SplitSectionCommand',
    IP.CTRL_BIT | ord('j'): 'JoinSectionCommand',
    IP.CTRL_BIT | ord('x'): 'RemoveSectionCommand',
    IP.CTRL_BIT | ord('u'): 'UndoSectionCommand',
    # Save operation
    IP.CTRL_BIT | ord('w'): 'SaveCommand',
    IP.SHIFT_BIT | ord('w'): 'SaveCommand',
    ord('W'): 'SaveCommand',
    IP.KEY_HOME: 'JumpSectionStartCommand',
    IP.KEY_END: 'JumpSectionEndCommand',
    ord('v'): 'TogglePreviewCommand',
    ord('V'): 'TogglePreviewCommand',
}

HYBRID_SHORTCUTS = PYNPUT_SHORTCUTS

SHORTCUTS: dict[type[InputHandler], dict[int, str]] = {
    CV2KeyReader: CV2_SHORTCUTS,
    PynputKeyReader: PYNPUT_SHORTCUTS,
    HybridKeyReader: HYBRID_SHORTCUTS,
}
