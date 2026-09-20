from __future__ import annotations

from aniseek.view.input_handler import CV2KeyReader, HybridKeyReader, PynputKeyReader
from aniseek.view.interfaces.input import InputHandler

IP = InputHandler

CV2_SHORTCUTS: dict[int, str] = {
    ord('b'): 'PauseCommand',
    ord('q'): 'QuitCommand',
    ord('a'): 'RewindCommand',
    ord('d'): 'ProceesCommand',
    ord(']'): 'IncreaseSpeedCommand',
    ord('['): 'DecreaseSpeedCommand',
    ord(' '): 'PauseDelayCommand',
    ord('='): 'RestoreDelayCommand',
    ord('x'): 'RemoveFrameCommand',
    ord('u'): 'UndoFrameCommand',
    ord('n'): 'NextVideoCommand',
    ord('p'): 'PrevVideoCommand',
    ord('k'): 'NextSectionCommand',
    ord('j'): 'PrevSectionCommand',
    IP.SHIFT_BIT | ord('d'): 'NextSectionCommand',
    IP.SHIFT_BIT | ord('a'): 'PrevSectionCommand',
    ord('s'): 'SplitSectionCommand',
    ord('y'): 'UndoSectionCommand',
    IP.SHIFT_BIT | ord('u'): 'UndoSectionCommand',
    ord('c'): 'JoinSectionCommand',
    ord('r'): 'RemoveSectionCommand',
    IP.SHIFT_BIT | ord('x'): 'RemoveSectionCommand',
}

PYNPUT_SHORTCUTS: dict[int, str] = {
    ord('b'): 'PauseCommand',
    ord('q'): 'QuitCommand',
    ord('a'): 'RewindCommand',
    ord('d'): 'ProceesCommand',
    ord(']'): 'IncreaseSpeedCommand',
    ord('['): 'DecreaseSpeedCommand',
    ord(' '): 'PauseDelayCommand',
    ord('='): 'RestoreDelayCommand',
    ord('x'): 'RemoveFrameCommand',
    ord('u'): 'UndoFrameCommand',
    ord('n'): 'NextVideoCommand',
    ord('p'): 'PrevVideoCommand',
    IP.CTRL_BIT | ord('d'): 'NextSectionCommand',
    IP.CTRL_BIT | ord('a'): 'PrevSectionCommand',
    ord('s'): 'SplitSectionCommand',
    IP.CTRL_BIT | ord('u'): 'UndoSectionCommand',
    ord('c'): 'JoinSectionCommand',
    IP.CTRL_BIT | ord('x'): 'RemoveSectionCommand',
}

HYBRID_SHORTCUTS = PYNPUT_SHORTCUTS

SHORTCUTS: dict[type[InputHandler], dict[int, str]] = {
    CV2KeyReader: CV2_SHORTCUTS,
    PynputKeyReader: PYNPUT_SHORTCUTS,
    HybridKeyReader: HYBRID_SHORTCUTS,
}
