from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from aniseek.view.interfaces.command import ButtonState, Command
from aniseek.view.video_command import (
    DecreaseSpeedCommand,
    DynamicProceedCommand,
    DynamicRewindCommand,
    HoldTimer,
    IncreaseSpeedCommand,
    Invoker,
    JoinSectionCommand,
    JumpSectionEndCommand,
    JumpSectionStartCommand,
    MacroCommand,
    NextSectionCommand,
    NextVideoCommand,
    PrevSectionCommand,
    PrevVideoCommand,
    ProceesCommand,
    RemoveFrameCommand,
    RemoveSectionCommand,
    RewindCommand,
    SplitSectionCommand,
    UndoFrameCommand,
    UndoSectionCommand,
)


def test_button_state_enum_values():
    """Verifica correspondência exata dos valores do enum ButtonState aos nomes dos métodos."""
    assert ButtonState.PRESS.value == "on_press"
    assert ButtonState.HOLD.value == "on_hold"
    assert ButtonState.RELEASE.value == "on_release"


def test_command_executor_dispatches_to_on_press():
    """Verifica que executor com ButtonState.PRESS chama on_press."""
    calls = []

    class DummyCommand(Command):
        def on_press(self) -> None:
            calls.append("press")

    cmd = DummyCommand()
    cmd.executor(ButtonState.PRESS)
    assert calls == ["press"]


def test_command_executor_dispatches_to_on_hold():
    """Verifica que executor com ButtonState.HOLD chama on_hold."""
    calls = []

    class DummyCommand(Command):
        def on_hold(self) -> None:
            calls.append("hold")

    cmd = DummyCommand()
    cmd.executor(ButtonState.HOLD)
    assert calls == ["hold"]


def test_command_executor_dispatches_to_on_release():
    """Verifica que executor com ButtonState.RELEASE chama on_release."""
    calls = []

    class DummyCommand(Command):
        def on_release(self) -> None:
            calls.append("release")

    cmd = DummyCommand()
    cmd.executor(ButtonState.RELEASE)
    assert calls == ["release"]


def test_command_default_hooks_are_no_op():
    """Verifica que os métodos padrão on_press, on_hold e on_release não realizam operações."""
    cmd = Command()
    cmd.executor(ButtonState.PRESS)
    cmd.executor(ButtonState.HOLD)
    cmd.executor(ButtonState.RELEASE)


def test_invoker_dispatches_state_to_registered_command():
    """Verifica que o Invoker delega o comando e o estado correspondente."""
    invoker = Invoker()
    mock_cmd = MagicMock(spec=Command)
    invoker.set_command("test", mock_cmd)

    invoker.executor_command("test", ButtonState.HOLD)
    mock_cmd.executor.assert_called_once_with(ButtonState.HOLD)


def test_invoker_ignores_unregistered_key():
    """Verifica que chaves não registradas no Invoker não disparam comandos nem erros."""
    invoker = Invoker()
    invoker.executor_command("non_existent", ButtonState.PRESS)


def test_macro_command_propagates_state_to_children():
    """Verifica que MacroCommand propaga o estado recebido para todos os subcomandos."""
    cmd1 = MagicMock(spec=Command)
    cmd2 = MagicMock(spec=Command)
    macro = MacroCommand([cmd1, cmd2])

    macro.executor(ButtonState.RELEASE)
    cmd1.executor.assert_called_once_with(ButtonState.RELEASE)
    cmd2.executor.assert_called_once_with(ButtonState.RELEASE)


def test_dynamic_proceed_command_on_press_advances_and_saves_delay():
    """Verifica que DynamicProceedCommand executa proceed e memoriza o delay atual."""
    mock_receiver = MagicMock()
    mock_receiver.delay = 35
    cmd = DynamicProceedCommand(mock_receiver)

    cmd.executor(ButtonState.PRESS)
    mock_receiver.proceed.assert_called_once()
    assert cmd._saved_delay == 35


def test_dynamic_proceed_command_on_hold_short_tap_maintains_step():
    """Verifica que toque curto no on_hold não altera o delay do player."""
    mock_receiver = MagicMock()
    mock_receiver.delay = 0
    cmd = DynamicProceedCommand(mock_receiver)
    cmd.executor(ButtonState.PRESS)

    with patch("time.perf_counter", return_value=cmd._start_time + 0.10):
        cmd.executor(ButtonState.HOLD)

    mock_receiver.set_delay.assert_not_called()


@pytest.mark.parametrize(
    ("elapsed_time", "expected_delay"),
    [
        (0.30, 40),  # rampa estágio 1 (~25 fps)
        (0.60, 16),  # rampa estágio 2 (~60 fps)
        (1.20, 1),   # rampa estágio 3 (máximo)
    ],
    ids=["ramp_stage_1", "ramp_stage_2", "ramp_max"],
)
def test_dynamic_proceed_command_on_hold_ramp(elapsed_time, expected_delay):
    """Verifica estágios da rampa de aceleração do DynamicProceedCommand com base no tempo."""
    mock_receiver = MagicMock()
    mock_receiver.delay = 0
    cmd = DynamicProceedCommand(mock_receiver)
    cmd.executor(ButtonState.PRESS)

    with patch("time.perf_counter", return_value=cmd._start_time + elapsed_time):
        cmd.executor(ButtonState.HOLD)

    mock_receiver.set_delay.assert_called_with(expected_delay)


def test_dynamic_proceed_command_on_release_restores_delay():
    """Verifica que DynamicProceedCommand restaura o delay original no evento de release."""
    mock_receiver = MagicMock()
    mock_receiver.delay = 0
    cmd = DynamicProceedCommand(mock_receiver)
    cmd.executor(ButtonState.PRESS)

    with patch("time.perf_counter", return_value=cmd._start_time + 1.0):
        cmd.executor(ButtonState.HOLD)

    cmd.executor(ButtonState.RELEASE)
    mock_receiver.set_delay.assert_called_with(0)
    assert cmd._saved_delay is None


def test_dynamic_rewind_command_on_press_rewinds_and_saves_delay():
    """Verifica que DynamicRewindCommand executa rewind e memoriza o delay atual."""
    mock_receiver = MagicMock()
    mock_receiver.delay = 35
    cmd = DynamicRewindCommand(mock_receiver)

    cmd.executor(ButtonState.PRESS)
    mock_receiver.rewind.assert_called_once()
    assert cmd._saved_delay == 35


def test_dynamic_rewind_command_on_release_restores_delay():
    """Verifica que DynamicRewindCommand restaura o delay original no evento de release."""
    mock_receiver = MagicMock()
    mock_receiver.delay = 0
    cmd = DynamicRewindCommand(mock_receiver)
    cmd.executor(ButtonState.PRESS)

    with patch("time.perf_counter", return_value=cmd._start_time + 1.0):
        cmd.executor(ButtonState.HOLD)

    cmd.executor(ButtonState.RELEASE)
    mock_receiver.set_delay.assert_called_with(0)
    assert cmd._saved_delay is None


def test_hold_timer_inactive_by_default():
    """Verifica que o HoldTimer inicia inativo e não colapsado."""
    timer = HoldTimer(delay=0.15, interval=1.0 / 30)
    assert not timer.collapsed()


def test_hold_timer_activation_and_collapse():
    """Verifica que HoldTimer só colapsa após decorrido o delay configurado."""
    timer = HoldTimer(delay=0.15, interval=1.0 / 30)
    with patch("time.perf_counter", return_value=100.0):
        timer.activate()

    with patch("time.perf_counter", return_value=100.10):
        assert not timer.collapsed()

    with patch("time.perf_counter", return_value=100.15):
        assert timer.collapsed()


def test_hold_timer_reactivation_and_interval():
    """Verifica que reactivate respeita o intervalo configurado para repetição."""
    timer = HoldTimer(delay=0.15, interval=1.0 / 30)
    with patch("time.perf_counter", return_value=100.0):
        timer.reactivate()

    with patch("time.perf_counter", return_value=100.020):
        assert not timer.collapsed()

    with patch("time.perf_counter", return_value=100.034):
        assert timer.collapsed()


def test_hold_timer_stop_deactivates():
    """Verifica que o método stop desativa o HoldTimer."""
    timer = HoldTimer(delay=0.15, interval=1.0 / 30)
    with patch("time.perf_counter", return_value=100.0):
        timer.activate()
    timer.stop()
    assert not timer.collapsed()


@pytest.mark.parametrize(
    ("cmd_cls", "method_name"),
    [
        (ProceesCommand, "proceed"),
        (RewindCommand, "rewind"),
        (RemoveFrameCommand, "remove_frame"),
        (UndoFrameCommand, "undo"),
        (IncreaseSpeedCommand, "increase_speed"),
        (DecreaseSpeedCommand, "decrease_speed"),
        (NextVideoCommand, "next_video"),
        (PrevVideoCommand, "prev_video"),
        (NextSectionCommand, "next_section"),
        (PrevSectionCommand, "prev_section"),
        (RemoveSectionCommand, "remove_section"),
        (SplitSectionCommand, "split_section"),
        (UndoSectionCommand, "undo_section"),
        (JoinSectionCommand, "join_section"),
        (JumpSectionStartCommand, "jump_section_start"),
        (JumpSectionEndCommand, "jump_section_end"),
    ],
    ids=[
        "proceed",
        "rewind",
        "remove_frame",
        "undo_frame",
        "increase_speed",
        "decrease_speed",
        "next_video",
        "prev_video",
        "next_section",
        "prev_section",
        "remove_section",
        "split_section",
        "undo_section",
        "join_section",
        "jump_section_start",
        "jump_section_end",
    ],
)
def test_continuous_command_lifecycle_with_hold_timer(cmd_cls, method_name):
    """Verifica ciclo do comando com HoldTimer em PRESS, HOLD antes e após colapso e RELEASE."""
    mock_receiver = MagicMock()
    cmd = cmd_cls(mock_receiver)

    with patch("time.perf_counter", return_value=100.0):
        cmd.executor(ButtonState.PRESS)
    getattr(mock_receiver, method_name).assert_called_once()

    # HOLD antes de colapsar o delay inicial: toque rápido não deve executar novamente
    with patch("time.perf_counter", return_value=100.08):
        cmd.executor(ButtonState.HOLD)
    assert getattr(mock_receiver, method_name).call_count == 1

    # HOLD após colapsar o delay inicial: deve executar novamente e reativar o timer com o interval
    with patch("time.perf_counter", return_value=100.0 + cmd.timer.delay + 0.01):
        cmd.executor(ButtonState.HOLD)
    assert getattr(mock_receiver, method_name).call_count == 2

    # RELEASE: desativa o timer
    cmd.executor(ButtonState.RELEASE)
    assert not cmd.timer.collapsed()
