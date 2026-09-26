from __future__ import annotations

import pytest

from aniseek.config import Config


def test_config_default_values():
    """Valida valores padrão da configuração do sistema."""
    cfg = Config()
    assert cfg.buffersize == 30
    assert cfg.image_fps == 24.0
    assert ".mp4" in cfg.video_extensions
    assert ".png" in cfg.image_extensions
    assert cfg.hold_delay == 0.15
    assert cfg.hold_interval == pytest.approx(1.0 / 30)
    assert cfg.log_level == "INFO"


def test_config_buffersize_setter():
    """Atualiza buffersize com valor válido."""
    cfg = Config()
    cfg.buffersize = 50
    assert cfg.buffersize == 50


@pytest.mark.parametrize("invalid_val", [0, -5, "30", None], ids=["zero", "negative", "string", "none"])
def test_config_buffersize_invalid(invalid_val):
    """Rejeita valores inválidos para buffersize."""
    cfg = Config()
    with pytest.raises(ValueError):
        cfg.buffersize = invalid_val


def test_config_image_fps_setter():
    """Atualiza image_fps com valor válido."""
    cfg = Config()
    cfg.image_fps = 30.0
    assert cfg.image_fps == 30.0


@pytest.mark.parametrize("invalid_val", [0, -10.0], ids=["zero", "negative"])
def test_config_image_fps_invalid(invalid_val):
    """Rejeita valores inválidos para image_fps."""
    cfg = Config()
    with pytest.raises(ValueError):
        cfg.image_fps = invalid_val


def test_config_video_extensions_setter():
    """Atualiza video_extensions e normaliza para minúsculas."""
    cfg = Config()
    cfg.video_extensions = (".MP4", ".MKV")
    assert cfg.video_extensions == (".mp4", ".mkv")


def test_config_image_extensions_setter():
    """Atualiza image_extensions e normaliza para minúsculas."""
    cfg = Config()
    cfg.image_extensions = (".PNG", ".JPG")
    assert cfg.image_extensions == (".png", ".jpg")


def test_config_hold_delay_setter():
    """Atualiza hold_delay com valor válido."""
    cfg = Config()
    cfg.hold_delay = 0.25
    assert cfg.hold_delay == 0.25


@pytest.mark.parametrize("invalid_val", [-0.01, -1.0], ids=["negative_small", "negative_large"])
def test_config_hold_delay_invalid(invalid_val):
    """Rejeita valores negativos para hold_delay."""
    cfg = Config()
    with pytest.raises(ValueError):
        cfg.hold_delay = invalid_val


def test_config_hold_interval_setter():
    """Atualiza hold_interval com valor válido."""
    cfg = Config()
    cfg.hold_interval = 0.05
    assert cfg.hold_interval == 0.05


@pytest.mark.parametrize("invalid_val", [0, -0.01], ids=["zero", "negative"])
def test_config_hold_interval_invalid(invalid_val):
    """Rejeita zero ou valores negativos para hold_interval."""
    cfg = Config()
    with pytest.raises(ValueError):
        cfg.hold_interval = invalid_val


def test_config_log_level_setter():
    """Atualiza log_level com valor válido e normaliza para maiúsculas."""
    cfg = Config()
    cfg.log_level = "debug"
    assert cfg.log_level == "DEBUG"


@pytest.mark.parametrize("invalid_val", ["INVALID", 123, None], ids=["unknown_string", "integer", "none"])
def test_config_log_level_invalid(invalid_val):
    """Rejeita valores inválidos para log_level."""
    cfg = Config()
    with pytest.raises(ValueError):
        cfg.log_level = invalid_val


def test_config_reset():
    """Restaura todas as configurações para os valores de fábrica."""
    cfg = Config()
    cfg.buffersize = 99
    cfg.image_fps = 60.0
    cfg.video_extensions = (".custom",)
    cfg.image_extensions = (".myimg",)
    cfg.hold_delay = 0.5
    cfg.hold_interval = 0.1
    cfg.log_level = "TRACE"

    cfg.reset()

    assert cfg.buffersize == 30
    assert cfg.image_fps == 24.0
    assert ".mp4" in cfg.video_extensions
    assert ".png" in cfg.image_extensions
    assert cfg.hold_delay == 0.15
    assert cfg.hold_interval == pytest.approx(1.0 / 30)
    assert cfg.log_level == "INFO"


def test_config_context_manager():
    """Aplica configurações temporárias dentro de bloco with e restaura ao sair."""
    cfg = Config()
    with cfg(buffersize=15, image_fps=12.0, hold_delay=0.3, hold_interval=0.05, log_level="DEBUG"):
        assert cfg.buffersize == 15
        assert cfg.image_fps == 12.0
        assert cfg.hold_delay == 0.3
        assert cfg.hold_interval == 0.05
        assert cfg.log_level == "DEBUG"

    assert cfg.buffersize == 30
    assert cfg.image_fps == 24.0
    assert cfg.hold_delay == 0.15
    assert cfg.hold_interval == pytest.approx(1.0 / 30)
    assert cfg.log_level == "INFO"


def test_config_context_manager_restores_on_exception():
    """Restaura configuração original mesmo quando ocorre exceção no bloco with."""
    cfg = Config()
    with pytest.raises(RuntimeError):
        with cfg(buffersize=10):
            assert cfg.buffersize == 10
            raise RuntimeError("Erro forçado")

    assert cfg.buffersize == 30


def test_config_context_manager_rejects_unknown_attribute():
    """Levanta AttributeError ao tentar sobrescrever chave de configuração inexistente."""
    cfg = Config()
    with pytest.raises(AttributeError):
        with cfg(inexistent_option=123):
            pass
