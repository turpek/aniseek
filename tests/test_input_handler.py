from __future__ import annotations

from unittest.mock import patch

import pytest
from pynput import keyboard

from aniseek.view.input_handler import (
    CV2KeyReader,
    HybridKeyReader,
    KeyModifierState,
    PynputKeyReader,
)
from aniseek.view.interfaces.command import ButtonState
from aniseek.view.interfaces.input import InputHandler
from aniseek.view.shortcuts import (
    CV2_SHORTCUTS,
    HYBRID_SHORTCUTS,
    PYNPUT_SHORTCUTS,
    SHORTCUTS,
)


def test_key_modifier_state_ctrl_lifecycle():
    """Verifica ativação e desativação de Ctrl no KeyModifierState."""
    state = KeyModifierState()

    state.on_press(keyboard.Key.ctrl)
    assert state.ctrl is True
    assert state.just_pressed() is True

    ctrl, shift, alt = state.snapshot()
    assert ctrl is True
    assert shift is False
    assert alt is False
    assert state.just_pressed() is False

    state.on_release(keyboard.Key.ctrl)
    assert state.ctrl is False


def test_key_modifier_state_shift_lifecycle():
    """Verifica ativação e desativação de Shift no KeyModifierState."""
    state = KeyModifierState()

    state.on_press(keyboard.Key.shift)
    assert state.shift is True
    assert state.just_pressed() is True

    ctrl, shift, alt = state.snapshot()
    assert ctrl is False
    assert shift is True
    assert alt is False
    assert state.just_pressed() is False

    state.on_release(keyboard.Key.shift)
    assert state.shift is False


def test_key_modifier_state_alt_lifecycle():
    """Verifica ativação e desativação de Alt no KeyModifierState."""
    state = KeyModifierState()

    state.on_press(keyboard.Key.alt)
    assert state.alt is True
    assert state.just_pressed() is True

    ctrl, shift, alt = state.snapshot()
    assert ctrl is False
    assert shift is False
    assert alt is True
    assert state.just_pressed() is False

    state.on_release(keyboard.Key.alt)
    assert state.alt is False


def test_cv2_key_reader():
    """Verifica se CV2KeyReader delega para cv2.waitKeyEx."""
    reader = CV2KeyReader()
    with patch("aniseek.view.input_handler.cv2.waitKeyEx", return_value=ord("a")) as mock_wait:
        code = reader.get_code(30)
        assert code == ord("a")
        mock_wait.assert_called_once_with(30)


def test_pynput_key_reader_no_key_pressed():
    """Verifica retorno de -1 quando nenhuma tecla foi enfileirada."""
    with patch("aniseek.view.input_handler.keyboard.Listener"):
        reader = PynputKeyReader()
        with patch("aniseek.view.input_handler.cv2.waitKey", return_value=-1):
            assert reader.get_code(30) == -1
        reader.join()


def test_pynput_key_reader_with_ctrl():
    """Verifica aplicação do CTRL_BIT quando Ctrl e uma tecla são pressionados."""
    with patch("aniseek.view.input_handler.keyboard.Listener"):
        reader = PynputKeyReader()
        reader._on_press(keyboard.Key.ctrl)
        reader._on_press(keyboard.KeyCode.from_char("d"))
        reader._on_release(keyboard.KeyCode.from_char("d"))
        reader._on_release(keyboard.Key.ctrl)

        with patch("aniseek.view.input_handler.cv2.waitKey", return_value=-1):
            code = reader.get_code(30)
            assert code == (InputHandler.CTRL_BIT | ord("d"))
        reader.join()


def test_pynput_key_reader_with_shift():
    """Verifica aplicação do SHIFT_BIT quando Shift e uma tecla são pressionados."""
    with patch("aniseek.view.input_handler.keyboard.Listener"):
        reader = PynputKeyReader()
        reader._on_press(keyboard.Key.shift)
        reader._on_press(keyboard.KeyCode.from_char("d"))
        reader._on_release(keyboard.KeyCode.from_char("d"))
        reader._on_release(keyboard.Key.shift)

        with patch("aniseek.view.input_handler.cv2.waitKey", return_value=-1):
            code = reader.get_code(30)
            assert code == (InputHandler.SHIFT_BIT | ord("d"))
        reader.join()


def test_pynput_key_reader_with_alt():
    """Verifica aplicação do ALT_BIT quando Alt e uma tecla são pressionados."""
    with patch("aniseek.view.input_handler.keyboard.Listener"):
        reader = PynputKeyReader()
        reader._on_press(keyboard.Key.alt)
        reader._on_press(keyboard.KeyCode.from_char("d"))
        reader._on_release(keyboard.KeyCode.from_char("d"))
        reader._on_release(keyboard.Key.alt)

        with patch("aniseek.view.input_handler.cv2.waitKey", return_value=-1):
            code = reader.get_code(30)
            assert code == (InputHandler.ALT_BIT | ord("d"))
        reader.join()


@pytest.mark.parametrize(
    ("key", "expected_code"),
    [
        (keyboard.Key.space, ord(" ")),
        (keyboard.Key.esc, 27),
        (keyboard.Key.enter, 13),
        (keyboard.Key.tab, 9),
        (keyboard.Key.backspace, 8),
        (keyboard.Key.delete, 127),
    ],
    ids=["space", "esc", "enter", "tab", "backspace", "delete"],
)
def test_pynput_key_reader_special_keys(key, expected_code):
    """Verifica decodificação de teclas especiais mapeadas pelo pynput."""
    with patch("aniseek.view.input_handler.keyboard.Listener"):
        reader = PynputKeyReader()
        reader._on_press(key)
        reader._on_release(key)

        with patch("aniseek.view.input_handler.cv2.waitKey", return_value=-1):
            code = reader.get_code(30)
            assert code == expected_code
        reader.join()


def test_pynput_key_reader_ctrl_ascii_control_char():
    """Verifica conversão de caractere de controle ASCII gerado com Ctrl."""
    with patch("aniseek.view.input_handler.keyboard.Listener"):
        reader = PynputKeyReader()
        reader._on_press(keyboard.Key.ctrl)
        # ASCII 4 is EOF (Ctrl+D)
        reader._on_press(keyboard.KeyCode.from_char("\x04"))
        reader._on_release(keyboard.KeyCode.from_char("\x04"))
        reader._on_release(keyboard.Key.ctrl)

        with patch("aniseek.view.input_handler.cv2.waitKey", return_value=-1):
            code = reader.get_code(30)
            assert code == (InputHandler.CTRL_BIT | ord("d"))
        reader.join()


def test_shortcuts_mapping():
    """Verifica consistência das tabelas de atalhos."""
    assert SHORTCUTS[CV2KeyReader] is CV2_SHORTCUTS
    assert SHORTCUTS[PynputKeyReader] is PYNPUT_SHORTCUTS
    assert SHORTCUTS[HybridKeyReader] is HYBRID_SHORTCUTS
    assert CV2_SHORTCUTS[ord("d")] == "ProceesCommand"
    assert PYNPUT_SHORTCUTS[InputHandler.CTRL_BIT | ord("d")] == "NextSectionCommand"
    assert PYNPUT_SHORTCUTS[InputHandler.CTRL_BIT | ord("s")] == "SplitSectionCommand"
    assert PYNPUT_SHORTCUTS[InputHandler.CTRL_BIT | ord("j")] == "JoinSectionCommand"
    assert CV2_SHORTCUTS[InputHandler.SHIFT_BIT | ord("d")] == "NextSectionCommand"
    assert CV2_SHORTCUTS[InputHandler.SHIFT_BIT | ord("s")] == "SplitSectionCommand"
    assert CV2_SHORTCUTS[ord("S")] == "SplitSectionCommand"
    assert CV2_SHORTCUTS[ord("J")] == "JoinSectionCommand"
    assert CV2_SHORTCUTS[InputHandler.SHIFT_BIT | ord("w")] == "SaveCommand"
    assert CV2_SHORTCUTS[ord("W")] == "SaveCommand"
    assert CV2_SHORTCUTS[InputHandler.CTRL_BIT | ord("w")] == "SaveCommand"
    assert PYNPUT_SHORTCUTS[InputHandler.CTRL_BIT | ord("w")] == "SaveCommand"
    assert PYNPUT_SHORTCUTS[InputHandler.SHIFT_BIT | ord("w")] == "SaveCommand"
    assert PYNPUT_SHORTCUTS[ord("W")] == "SaveCommand"
    assert CV2_SHORTCUTS[InputHandler.KEY_RIGHT] == "DynamicProceedCommand"
    assert CV2_SHORTCUTS[InputHandler.KEY_LEFT] == "DynamicRewindCommand"
    assert PYNPUT_SHORTCUTS[InputHandler.KEY_RIGHT] == "DynamicProceedCommand"
    assert PYNPUT_SHORTCUTS[InputHandler.KEY_LEFT] == "DynamicRewindCommand"


@pytest.mark.parametrize(
    ("vk", "expected_code"),
    [
        (0xFF9D, ord("5")),  # XK_KP_Begin (Numpad 5)
        (0xFFB5, ord("5")),  # XK_KP_5
        (0xFFB1, ord("1")),  # XK_KP_1
        (0x65, ord("5")),    # VK_NUMPAD5 (Windows)
        (0xFF8D, 13),        # XK_KP_Enter
        (0xFFAB, ord("+")),  # XK_KP_Add
    ],
    ids=["numpad_5_begin", "numpad_5_x11", "numpad_1_x11", "numpad_5_win", "numpad_enter", "numpad_add"],
)
def test_pynput_key_reader_numpad_keys(vk, expected_code):
    """Verifica decodificação de teclas numéricas do Numpad com char=None."""
    with patch("aniseek.view.input_handler.keyboard.Listener"):
        reader = PynputKeyReader()
        key = keyboard.KeyCode.from_vk(vk)
        reader._on_press(key)
        reader._on_release(key)

        with patch("aniseek.view.input_handler.cv2.waitKey", return_value=-1):
            code = reader.get_code(30)
            assert code == expected_code
        reader.join()


@pytest.mark.parametrize(
    ("key", "expected_code"),
    [
        (keyboard.Key.left, InputHandler.KEY_LEFT),
        (keyboard.Key.right, InputHandler.KEY_RIGHT),
        (keyboard.Key.up, InputHandler.KEY_UP),
        (keyboard.Key.down, InputHandler.KEY_DOWN),
    ],
    ids=["arrow_left", "arrow_right", "arrow_up", "arrow_down"],
)
def test_pynput_key_reader_arrow_keys(key, expected_code):
    """Verifica decodificação de teclas direcionais mapeadas pelo pynput."""
    with patch("aniseek.view.input_handler.keyboard.Listener"):
        reader = PynputKeyReader()
        reader._on_press(key)
        reader._on_release(key)

        with patch("aniseek.view.input_handler.cv2.waitKey", return_value=-1):
            code = reader.get_code(30)
            assert code == expected_code
        reader.join()


def test_pynput_key_reader_get_event_lifecycle():
    """Verifica o ciclo completo de eventos PRESS, HOLD e RELEASE no get_event."""
    with patch("aniseek.view.input_handler.keyboard.Listener"):
        reader = PynputKeyReader()
        reader._on_press(keyboard.Key.right)

        with patch("aniseek.view.input_handler.cv2.waitKey", return_value=-1):
            event_press = reader.get_event(30)
            assert event_press == (InputHandler.KEY_RIGHT, ButtonState.PRESS)

            event_hold = reader.get_event(30)
            assert event_hold == (InputHandler.KEY_RIGHT, ButtonState.HOLD)

            reader._on_release(keyboard.Key.right)

            event_release = reader.get_event(30)
            assert event_release == (InputHandler.KEY_RIGHT, ButtonState.RELEASE)

            event_none = reader.get_event(30)
            assert event_none is None
        reader.join()
