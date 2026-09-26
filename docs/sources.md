# Fontes de Frames e Backends (`aniseek.core.sources`)

O `aniseek` adota uma arquitetura de decodificação totalmente desacoplada. O motor de leitura (`reader_task`, buffers concorrentes, `VideoReader`) consome estritamente o contrato da interface abstrata **`IFrameSource`**, sem depender diretamente de `cv2.VideoCapture` ou de qualquer biblioteca específica.

---

## 1. Contrato da Interface (`IFrameSource`)

Definido em `aniseek.core.interfaces.source`, todo backend deve implementar os seguintes métodos e propriedades:

```python
from abc import ABC, abstractmethod
from numpy import ndarray

class IFrameSource(ABC):
    """Generic interface for frame extraction sources."""

    @property
    @abstractmethod
    def frame_count(self) -> int:
        """Total de quadros disponíveis na fonte."""
        ...

    @property
    @abstractmethod
    def fps(self) -> float:
        """Taxa de quadros por segundo da fonte."""
        ...

    @abstractmethod
    def seek(self, frame_id: int) -> None:
        """Posiciona o cursor de leitura no frame especificado (0-based)."""
        ...

    @abstractmethod
    def read(self) -> tuple[bool, ndarray | None]:
        """Decodifica e retorna o próximo frame. Retorna (success, frame)."""
        ...

    @abstractmethod
    def grab(self) -> bool:
        """Avança o cursor sem decodificar o frame (pulo leve de cabeçalho)."""
        ...

    @abstractmethod
    def is_opened(self) -> bool:
        """Verifica se a fonte está aberta e pronta para leitura."""
        ...

    @abstractmethod
    def release(self) -> None:
        """Libera todos os descritores e recursos mantidos pela fonte."""
        ...
```

---

## 2. Backends Nativos

### A. `OpenCVVideoSource` (`aniseek.core.sources.opencv`)

Backend padrão para arquivos de vídeo individuais (`.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`, etc.).

```python
from aniseek.core.sources import OpenCVVideoSource

source = OpenCVVideoSource("meu_video.mp4")
print(f"Total de frames: {source.frame_count}")
print(f"FPS: {source.fps}")

# Suporte nativo a context manager:
with OpenCVVideoSource("meu_video.mp4") as src:
    success, frame = src.read()
```

#### Características e Otimizações de Performance:
- **TTFF Instantâneo (Resolução *Lazy*):** Elimina validações síncronas pesadas durante a inicialização (`__init__`), permitindo abertura de vídeos grandes em milissegundos.
- **Detecção Confinada via Busca Binária $O(\log N)$:** Em caso de metadados imprecisos ou vídeos corrompidos, utiliza busca binária com janela de tolerância para frames defeituosos pontuais, encontrando o limite real exato do arquivo sem penalizar o início da leitura.
- **`seek` Otimizado:** Só emite instrução de posicionamento para o container nativo caso o frame desejado seja diferente da posição atual do cursor.
- **Suporte a `grab`:** Utiliza `cap.grab()` para avanços rápidos sem carga pesada de decodificação de pixels na CPU/GPU.

---

### B. `ImageSource` (`aniseek.core.sources.image`)

Backend nativo para leitura sequencial de diretórios contendo imagens numeradas ou nomeadas.

```python
from aniseek.core.sources import ImageSource

# Lê todas as imagens compatíveis no diretório em ordem alfabética natural
source = ImageSource("caminho/para/pasta_frames/", fps=30.0)

print(f"Total de imagens encontradas: {source.frame_count}")
print(f"FPS configurado: {source.fps}")
```

#### Características:
- **Extensões Suportadas:** `.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`.
- **`seek` Instantâneo:** O reposicionamento do cursor é imediato (ajuste de índice em lista de caminhos em memória).
- **`grab` com Custo Zero:** O `grab()` apenas incrementa o cursor numérico, sem ler o arquivo do disco.

---

## 3. Gerenciamento Global e Alternância (`SourceRegistry`)

O **`SourceRegistry`** (`aniseek.core.sources.registry`) é o singleton responsável por registrar as classes padrão de vídeo e imagem e resolver caminhos automaticamente.

### A. Resolução Inteligente (`create_source`)

O método `source_registry.create_source(path)` inspeciona o caminho fornecido:
- Se for **diretório** (`p.is_dir()`): instancia `ImageSource`.
- Se tiver **extensão de vídeo** (`.mp4`, `.mkv`, `.avi`, etc.): instancia `OpenCVVideoSource`.
- Se tiver extensão não suportada (ex: `.pdf`, `.txt`): levanta `ValueError`.

```python
from aniseek.core.sources import source_registry

# Retorna uma instância de OpenCVVideoSource:
video_src = source_registry.create_source("video.mp4")

# Retorna uma instância de ImageSource:
img_src = source_registry.create_source("pasta_frames/")
```

---

### B. Alternância Temporária via Context Manager (`use()`)

Para alternar backends temporariamente sem afetar o restante da aplicação:

```python
from aniseek.core.sources import source_registry
from minha_lib import PyAVVideoSource  # Classe customizada que herda de IFrameSource

with source_registry.use(video=PyAVVideoSource):
    # Dentro deste bloco, qualquer chamada from_default() usará PyAVVideoSource
    reader = VideoReader.from_default("video.mp4")

# Fora do bloco, o registry volta automaticamente para OpenCVVideoSource
```

---

### C. Registro Permanente de Novo Backend

Para substituir o backend padrão globalmente:

```python
from aniseek.core.sources import source_registry
from minha_lib import PyAVVideoSource

# Define PyAVVideoSource como o novo backend padrão de vídeo:
source_registry.video_source = PyAVVideoSource

# Redefinir para os padrões de fábrica:
source_registry.reset()
```

---

## 4. Criando um Backend Personalizado

Para criar seu próprio backend (ex: decodificador baseado em PyAV, Decord, GPU/NVDEC ou gerador sintético em memória), basta herdar de `IFrameSource`:

```python
import numpy as np
from aniseek.core.interfaces.source import IFrameSource

class SyntheticSource(IFrameSource):
    """Fonte sintética que gera frames geométricos em memória sem arquivos."""

    def __init__(self, count: int = 500, fps: float = 30.0):
        self._frame_count = count
        self._fps = fps
        self._cursor = 0
        self._opened = True

    @property
    def frame_count(self) -> int:
        return self._frame_count

    @property
    def fps(self) -> float:
        return self._fps

    def seek(self, frame_id: int) -> None:
        self._cursor = max(0, min(frame_id, self._frame_count))

    def read(self) -> tuple[bool, np.ndarray | None]:
        if not self._opened or self._cursor >= self._frame_count:
            return False, None
        # Gera uma imagem sintética
        frame = np.full((480, 640, 3), (self._cursor % 256), dtype=np.uint8)
        self._cursor += 1
        return True, frame

    def grab(self) -> bool:
        if not self._opened or self._cursor >= self._frame_count:
            return False
        self._cursor += 1
        return True

    def is_opened(self) -> bool:
        return self._opened

    def release(self) -> None:
        self._opened = False
```

### Integrando ao `VideoReader` ou `FrameViewer`:

Basta passar a instância diretamente ao construtor primário:

```python
from aniseek import VideoReader
from aniseek.view import FrameViewer

synthetic = SyntheticSource(count=1000)

# 1. Usar com o VideoReader bidirecional:
with VideoReader(synthetic) as reader:
    frame_id, frame = reader.proceed()

# 2. Usar com o FrameViewer interativo:
with FrameViewer(synthetic) as viewer:
    while not viewer.quit():
        ret, frame = viewer.read()
        viewer.show(ret, frame)
```
