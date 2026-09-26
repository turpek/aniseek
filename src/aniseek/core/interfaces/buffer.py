from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from numpy import ndarray

from aniseek.core.interfaces.source import IFrameSource

if TYPE_CHECKING:
    from aniseek.core.buffer import Buffer


class IVideoBuffer(ABC):
    """Interface abstrata para buffers concorrentes de vídeo."""

    buffersize: int
    source: IFrameSource
    _buffer: Buffer

    @abstractmethod
    def is_task_complete(self) -> bool:
        """Indica se todos os frames mapeados foram consumidos pelo buffer."""
        ...

    @abstractmethod
    def is_done(self) -> bool:
        """Indica se todos os frames foram lidos e enfileirados pela thread."""
        ...

    @abstractmethod
    def do_task(self) -> bool:
        """Indica se uma nova tarefa de leitura pode ser iniciada."""
        ...

    @abstractmethod
    def set(self, frame_id: int) -> None:
        """Define o cursor alvo para o próximo ciclo de leitura."""
        ...

    @abstractmethod
    def set_frame_id(self) -> None:
        """Define o frame_id no buffer (legado/compatibilidade)."""
        ...

    @abstractmethod
    def run(self) -> None:
        """Inicia uma tarefa de decodificação se elegível."""
        ...

    @abstractmethod
    def join(self) -> None:
        """Aguarda a finalização da thread e libera a fonte de captura."""
        ...

    @abstractmethod
    def join_like(self) -> None:
        """Aguarda a finalização da thread sem fechar a fonte de captura."""
        ...

    @abstractmethod
    def put(self, frame_id: int, frame: ndarray) -> None:
        """Enfileira manualmente um frame no buffer."""
        ...

    @abstractmethod
    def get(self) -> tuple[int | None, ndarray | None]:
        """Recupera o próximo frame disponível no buffer."""
        ...

    @property
    @abstractmethod
    def frame_id(self) -> int | None:
        """Identificador do frame atualmente retornado pelo buffer."""
        ...

    @abstractmethod
    def __getitem__(self, index: int) -> int | None:
        """Retorna o frame_id correspondente ao índice no buffer."""
        ...

    @abstractmethod
    def mapper_id(self, index: int) -> int:
        """Retorna o frame_id correspondente ao índice no mapeamento."""
        ...

    @abstractmethod
    def start_frame(self) -> int | None:
        """Calcula o início da janela de leitura."""
        ...

    @abstractmethod
    def end_frame(self) -> int | None:
        """Calcula o término da janela de leitura."""
        ...


class IFakeVideoBuffer(IVideoBuffer):
    """Implementação stub de IVideoBuffer para testes unitários."""

    def __init__(self) -> None:
        self.buffersize = 0
        self._frame_id = 0

    def is_task_complete(self) -> bool:
        return True

    def is_done(self) -> bool:
        return True

    def do_task(self) -> bool:
        return False

    def set(self, frame_id: int) -> None:
        pass

    def set_frame_id(self) -> None:
        pass

    def run(self) -> None:
        pass

    def join(self) -> None:
        pass

    def join_like(self) -> None:
        pass

    def put(self, frame_id: int, frame: ndarray) -> None:
        pass

    def get(self) -> tuple[int | None, ndarray | None]:
        return None, None

    @property
    def frame_id(self) -> int | None:
        return self._frame_id

    def __getitem__(self, index: int) -> int | None:
        return None

    def mapper_id(self, index: int) -> int:
        return index

    def start_frame(self) -> int | None:
        return None

    def end_frame(self) -> int | None:
        return None
