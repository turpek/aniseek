from __future__ import annotations

import sys
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from loguru import logger

DEFAULT_BUFFERSIZE: int = 30
DEFAULT_IMAGE_FPS: float = 24.0
DEFAULT_VIDEO_EXTENSIONS: tuple[str, ...] = (
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".webm",
    ".flv",
    ".wmv",
    ".m4v",
    ".ts",
)
DEFAULT_HOLD_DELAY: float = 0.15
DEFAULT_HOLD_INTERVAL: float = 1.0 / 30
DEFAULT_IMAGE_EXTENSIONS: tuple[str, ...] = (
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
)
DEFAULT_LOG_LEVEL: str = "INFO"
VALID_LOG_LEVELS: tuple[str, ...] = (
    "TRACE",
    "DEBUG",
    "INFO",
    "SUCCESS",
    "WARNING",
    "ERROR",
    "CRITICAL",
)


class Config:
    """Configuração global centralizada do aniseek."""

    _handler_id: int | None = None

    def __init__(self, apply_logging: bool = False) -> None:
        self._buffersize: int = DEFAULT_BUFFERSIZE
        self._image_fps: float = DEFAULT_IMAGE_FPS
        self._video_extensions: tuple[str, ...] = DEFAULT_VIDEO_EXTENSIONS
        self._image_extensions: tuple[str, ...] = DEFAULT_IMAGE_EXTENSIONS
        self._hold_delay: float = DEFAULT_HOLD_DELAY
        self._hold_interval: float = DEFAULT_HOLD_INTERVAL
        self._log_level: str = DEFAULT_LOG_LEVEL
        if apply_logging:
            self._apply_log_level()

    def _apply_log_level(self) -> None:
        """Aplica o nível de log no handler do Loguru gerenciado pelo aniseek."""
        if Config._handler_id is not None:
            try:
                logger.remove(Config._handler_id)
            except ValueError:
                pass
        else:
            try:
                logger.remove(0)
            except ValueError:
                pass
        Config._handler_id = logger.add(sys.stderr, level=self._log_level)

    @property
    def buffersize(self) -> int:
        """Tamanho padrão da janela deslizante do buffer de vídeo."""
        return self._buffersize

    @buffersize.setter
    def buffersize(self, value: int) -> None:
        if not isinstance(value, int) or value <= 0:
            raise ValueError(f"buffersize deve ser um inteiro positivo, recebeu: {value}")
        self._buffersize = value

    @property
    def image_fps(self) -> float:
        """FPS padrão para sequências de imagem quando não fornecido pelo usuário."""
        return self._image_fps

    @image_fps.setter
    def image_fps(self, value: float) -> None:
        if value <= 0:
            raise ValueError(f"image_fps deve ser positivo, recebeu: {value}")
        self._image_fps = float(value)

    @property
    def video_extensions(self) -> tuple[str, ...]:
        """Extensões de arquivo reconhecidas como vídeo."""
        return self._video_extensions

    @video_extensions.setter
    def video_extensions(self, value: tuple[str, ...]) -> None:
        self._video_extensions = tuple(ext.lower() for ext in value)

    @property
    def image_extensions(self) -> tuple[str, ...]:
        """Extensões de arquivo reconhecidas como imagem."""
        return self._image_extensions

    @image_extensions.setter
    def image_extensions(self, value: tuple[str, ...]) -> None:
        self._image_extensions = tuple(ext.lower() for ext in value)

    @property
    def hold_delay(self) -> float:
        """Tempo de tolerância inicial antes de repetir tecla segurada (em segundos)."""
        return self._hold_delay

    @hold_delay.setter
    def hold_delay(self, value: float) -> None:
        if value < 0:
            raise ValueError(f"hold_delay deve ser não-negativo, recebeu: {value}")
        self._hold_delay = float(value)

    @property
    def hold_interval(self) -> float:
        """Intervalo entre repetições contínuas quando a tecla é mantida pressionada (em segundos)."""
        return self._hold_interval

    @hold_interval.setter
    def hold_interval(self, value: float) -> None:
        if value <= 0:
            raise ValueError(f"hold_interval deve ser positivo, recebeu: {value}")
        self._hold_interval = float(value)

    @property
    def log_level(self) -> str:
        """Nível mínimo de log do sistema ('TRACE', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')."""
        return self._log_level

    @log_level.setter
    def log_level(self, value: str) -> None:
        if not isinstance(value, str) or value.upper() not in VALID_LOG_LEVELS:
            raise ValueError(
                f"log_level deve ser um de {VALID_LOG_LEVELS}, recebeu: {value}"
            )
        self._log_level = value.upper()
        self._apply_log_level()

    def reset(self) -> None:
        """Restaura todas as configurações para seus valores padrão de fábrica."""
        self._buffersize = DEFAULT_BUFFERSIZE
        self._image_fps = DEFAULT_IMAGE_FPS
        self._video_extensions = DEFAULT_VIDEO_EXTENSIONS
        self._image_extensions = DEFAULT_IMAGE_EXTENSIONS
        self._hold_delay = DEFAULT_HOLD_DELAY
        self._hold_interval = DEFAULT_HOLD_INTERVAL
        self.log_level = DEFAULT_LOG_LEVEL

    @contextmanager
    def __call__(self, **kwargs: Any) -> Generator[Config, None, None]:
        """Aplica configurações temporárias dentro de um bloco 'with'."""
        old_state: dict[str, Any] = {}
        for key in kwargs:
            if not hasattr(self, key) or key.startswith("_"):
                raise AttributeError(f"Opção de configuração inválida: '{key}'")
            old_state[key] = getattr(self, key)

        try:
            for key, value in kwargs.items():
                setattr(self, key, value)
            yield self
        finally:
            for key, old_value in old_state.items():
                setattr(self, key, old_value)


config = Config(apply_logging=True)
