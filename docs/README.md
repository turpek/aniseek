# aniseek

**aniseek** é um motor inteligente para busca, navegação e leitura precisa frame a frame de vídeos e sequências de imagens, desenvolvido em Python 3.12+. Focado na manipulação, fatiamento e extração temporal de frames, o aniseek oferece avanço e retrocesso instantâneos via buffers concorrentes em memória e um visualizador/editor totalmente desacoplado.

Sua arquitetura é baseada em um sistema de duplo buffer concorrente (`VideoBufferLeft` e `VideoBufferRight`), que permite alternância de marcha temporal com latência zero e consumo cooperativo entre `proceed` (+1) e `rewind` (-1).

---

## ✨ Funcionalidades Principais

- **Leitura Bidirecional Cooperativa (`VideoReader`):** Alternância instantânea de direção (`proceed` / `rewind`) com cache em memória entre buffers paralelos, eliminando redecodificação pesada. Atravessa mais de **500+ FPS** em leitura reversa com dimensionamento adaptativo de buffer proporcional ao FPS do vídeo.
- **Abertura Instantânea (TTFF) e Detecção Resiliente de EOF:** Resolução *lazy* de propriedades na abertura de arquivos, combinada com *reverse tail probe* e busca galopante $O(\log N)$ para contagem exata e determinística do último frame físico decodificável, prevenindo leituras inválidas e deadlocks.
- **Indexação Binária de Keyframes (Matroska / EBML Cues):** Parser binário puro e de alta velocidade para containers Matroska (`.mkv`), extraindo pontos de quadros-chave diretamente em milissegundos sem invocar ferramentas externas.
- **Navegação de Playlist com Carregamento Sob Demanda (*Lazy Open*) e Prefill:** Alternância instantânea entre vídeos de uma lista de reprodução, com comandos dedicados de avanço e retrocesso com pré-aquecimento de buffer em RAM (`NextVideoEndCommand` / `PrevVideoEndCommand`) para reprodução reversa imediata a 50+ FPS.
- **Leitores Unidirecionais Otimizados (`ForwardReader` e `ReverseReader`):** Leitura direta ou reversa com buffer único concorrente e baixo consumo de memória.
- **Desacoplamento Total de Backend de Decodificação (`IFrameSource`):**
  - [`OpenCVVideoSource`](sources.md): Decodificação de arquivos de vídeo via OpenCV (`cv2.VideoCapture`).
  - [`PyAVVideoSource`](sources.md): Decodificação de alta performance via PyAV / FFmpeg, com suporte nativo a **AV1 10-bit (`libdav1d`)**, HEVC e H.264, cache FIFO de frames intermediários e pegada de memória desprezível.
  - [`ImageSource`](sources.md): Leitura sequencial de diretórios de imagens (`.png`, `.jpg`, `.webp`, `.bmp`).
  - [`SourceRegistry`](sources.md): Factory inteligente com seleção por string (`backend="pyav"` ou `backend="opencv"`), context manager (`use()`) e construtor automático (`from_default`).
- **Visualizador e Editor Desacoplado (`FrameViewer`):**
  - **Exibição Desacoplada (`IFrameDisplay`):** Renderizador padrão OpenCV ([`CV2Display`](viewer.md)) e suporte nativo a modo headless ([`NullDisplay`](viewer.md)) para testes e pipelines de CI/CD sem dependência de X11/Wayland.
  - **Entrada Desacoplada (`InputHandler`):** Captura de teclas flexível via [`PynputKeyReader`](viewer.md) (com suporte nativo a modificadores no SO) e [`CV2KeyReader`](viewer.md), ou classes personalizadas.
  - **Repetição Suave (`HoldTimer`):** Diferenciação de clique rápido (exatamente 1 frame) de tecla pressionada contínua com repetição suave e configurável.
  - **Título Dinâmico e Limpo:** Sem prefixos legados, exibindo seções ativas, frames relativos e globais, direção e playlist via [`TitleFormatter`](viewer.md).
- **Gerenciamento de Seções e Edição Não-Destrutiva:**
  - Divida (`Split`), junte (`Join`) e remova seções em tempo real.
  - Lixeira (`Trash`) com histórico Memento para desfazer (`undo`) remoção de frames ou seções.
  - Modo Preview (*Rough Cut*) para visualização contínua das seções ativas.
- **Persistência Explícita:**
  - Salve explicitamente via método `.save()` ou atalho de teclado (`Ctrl + w` / `Shift + w`).
  - Suporte a injeção de seções em múltiplos formatos: `dict`, arquivo `.json` ou instância de `SectionManager`.
- **Extensibilidade com Padrão Command:**
  - Vincule comandos personalizados com tipagem estrita via `viewer.bind(key, command)`.
  - Agrupe e execute múltiplos comandos em sequência com `MacroCommand`.

---

## 🛠️ Tecnologias Utilizadas

- [Python 3.12+](https://www.python.org/)
- [PyAV (`av`)](https://pyav.org/): Decodificação avançada via FFmpeg com suporte nativo a AV1 10-bit e HEVC.
- [OpenCV (`opencv-python`)](https://pypi.org/project/opencv-python/): Decodificação e exibição gráfica de frames.
- [pynput](https://pypi.org/project/pynput/): Captura precisa de modificadores de teclado (`Ctrl`, `Shift`, `Alt`) em nível de sistema operacional.
- [NumPy](https://numpy.org/): Manipulação eficiente de arrays de frames.
- [Loguru](https://github.com/Delgan/loguru): Logging estruturado de alto desempenho com proteção de hot-path.
- [uv](https://github.com/astral-sh/uv): Gerenciamento moderno de pacotes e ambientes virtuais.

---

## 🚀 Instalação

```bash
# Clone o repositório:
git clone https://github.com/turpek/aniseek.git
cd aniseek

# Instale as dependências via uv (recomendado):
uv sync
```

*Ou via pip convencional:*
```bash
python -m venv .venv
source .venv/bin/activate  # No Windows: .venv\Scripts\activate
pip install -e .
```

---

## 📖 Exemplos de Uso

### 1. Leitura de Vídeo Bidirecional (`VideoReader`)

```python
from aniseek import VideoReader

# Construtor inteligente: detecta vídeo ou diretório de imagens automaticamente
with VideoReader.from_default("video.mp4") as reader:
    # Avanço normal (+1)
    frame_id, frame = reader.proceed()
    print(f"Frame lido: {frame_id}")

    # Retrocesso instantâneo (-1) com cache em memória
    frame_id, frame = reader.rewind()
    print(f"Frame lido: {frame_id}")
```

### 2. Leitura com Seleção de Backend (`PyAV` ou `OpenCV`)

```python
from aniseek import VideoReader

# Leitura com backend PyAV (ideal para AV1 10-bit ou HEVC):
with VideoReader.from_default("anime.mkv", backend="pyav") as reader:
    for ret, frame in reader:
        if not ret:
            continue
        # Processar frame

# Leitura com backend OpenCV padrão:
with VideoReader.from_default("video.mp4", backend="opencv") as reader:
    for ret, frame in reader:
        if not ret:
            continue
        # Processar frame
```

### 3. Leitores Unidirecionais Especializados

```python
from aniseek import ForwardReader, ReverseReader
from aniseek.core.sources import ImageSource, PyAVVideoSource

# Avanço direto fatiado por tempo:
source = PyAVVideoSource("video.mkv")
with ForwardReader(source, start="01:00", end="01:30", step=2) as reader:
    for ret, frame in reader:
        if ret:
            # Frame lido
            pass

# Retrocesso direto a partir de diretório de imagens:
img_source = ImageSource("frames_dir/", fps=24.0)
with ReverseReader(img_source) as reader:
    for ret, frame in reader:
        if ret:
            # Frame lido de trás para frente
            pass
```

### 4. Visualizador e Editor (`FrameViewer`)

O loop canônico e idiomático do `FrameViewer` é governado por `while not viewer.quit():`:

```python
from aniseek.view import FrameViewer

with FrameViewer.from_default("video.mp4") as viewer:
    while not viewer.quit():
        ret, frame = viewer.read()
        viewer.show(ret, frame)
```

### 5. Visualizador em Modo Headless (Sem Janela / CI / Testes)

```python
from aniseek.view import FrameViewer, NullDisplay

# display="null" executa sem abrir nenhuma janela na tela
with FrameViewer.from_default("video.mp4", display="null") as viewer:
    for _ in range(30):
        ret, frame = viewer.read()
        viewer.show(ret, frame)
```

### 6. Injeção de Seções e Salvamento Explícito

```python
from aniseek.view import FrameViewer

# Injeção via dicionário em memória:
sections_data = {
    "SECTIONS": [
        {"RANGE_FRAME_ID": (0, 100), "REMOVED_FRAMES": [], "BLACK_LIST": []},
        {"RANGE_FRAME_ID": (200, 300), "REMOVED_FRAMES": [], "BLACK_LIST": []},
    ],
    "REMOVED": [],
}

with FrameViewer.from_default("video.mp4", sections=sections_data) as viewer:
    # Salvar manualmente a qualquer momento:
    viewer.save("meu_corte.json")

    while not viewer.quit():
        ret, frame = viewer.read()
        viewer.show(ret, frame)
```

### 7. Comandos Personalizados e `MacroCommand`

```python
from aniseek.view import FrameViewer
from aniseek.view.interfaces.command import Command
from aniseek.view.video_command import MacroCommand, PauseCommand, SaveCommand

class NotificarCommand(Command):
    def on_press(self) -> None:
        print("Ação personalizada executada!")

with FrameViewer.from_default("video.mp4") as viewer:
    ctrl = viewer.controller

    # Agrupar múltiplos comandos em uma macro ordenada:
    macro = MacroCommand([
        PauseCommand(ctrl),
        SaveCommand(ctrl),
        NotificarCommand(),
    ])

    # Vincular à tecla 'z' (estritamente instâncias de Command):
    viewer.bind(ord("z"), macro)

    while not viewer.quit():
        ret, frame = viewer.read()
        viewer.show(ret, frame)
```

### 8. Gerenciador de Teclado Personalizado (`InputHandler`)

```python
from aniseek.view import FrameViewer
from aniseek.view.interfaces.input import InputHandler

class MyCustomKeyReader(InputHandler):
    def get_code(self, delay: int) -> int:
        # Lê a tecla da sua própria biblioteca ou hardware:
        # Retorna o código numérico da tecla ou -1 se timeout.
        return -1

with FrameViewer.from_default("video.mp4", key_reader=MyCustomKeyReader) as viewer:
    while not viewer.quit():
        ret, frame = viewer.read()
        viewer.show(ret, frame)
```

### 9. Configuração Global Centralizada (`config`)

O `aniseek` expõe um singleton global `config` para ajustar buffers, tempos de repetição de teclas e níveis de log:

```python
from aniseek import config

# Ajustar parâmetros globais:
config.buffersize = 45           # Capacidade do buffer de vídeo
config.hold_delay = 0.20         # Tolerância inicial de clique antes de repetir (em segundos)
config.hold_interval = 1.0 / 60  # Taxa de repetição ao manter pressionado (60 FPS)
config.log_level = "DEBUG"       # 'TRACE', 'DEBUG', 'INFO', 'WARNING', 'ERROR'

# Ou usar gerenciador de contexto temporário:
with config(hold_delay=0.10, log_level="TRACE"):
    # Executar testes ou depurações específicas
    ...

# Restaurar valores de fábrica:
config.reset()
```

---

## ⌨️ Comandos e Atalhos do `FrameViewer`

Todos os comandos de navegação possuem suporte nativo ao **`HoldTimer`**:
- **Clique rápido:** Avança ou retrocede com precisão cirúrgica de exatamente **1 único frame**.
- **Segurar tecla:** Inicia a repetição contínua e suave após `config.hold_delay` (padrão: 150ms) a `config.hold_interval` (padrão: 30 FPS).

| Tecla | Modificador | Ação | Descrição |
| :---: | :---: | :--- | :--- |
| **`d`** ou **`→`** | — | **Proceed** | Avança frame a frame (+1) com repetição contínua ao segurar. |
| **`a`** ou **`←`** | — | **Rewind** | Retrocede frame a frame (-1) com repetição contínua ao segurar. |
| **`espaço`** | — | **Pause/Play (Delay)** | Pausa ativa para edição (delay=0) ou retoma reprodução. |
| **`b`** | — | **Pause/Play (Toggle)** | Alterna pausa e reprodução contínua. |
| **`x`** | — | **Remover Frame** | Remove o frame atual e envia para a lixeira (`Trash`). |
| **`u`** | — | **Desfazer Frame** | Restaura o último frame da lixeira. |
| **`[`** / **`]`** | — | **Velocidade** | Diminui / Aumenta a velocidade de reprodução. |
| **`=`** | — | **Restaurar Velocidade**| Restaura o delay padrão de reprodução. |
| **`w`** | `Ctrl` / `Shift` | **Salvar** | Persiste o estado das seções explicitamente no arquivo `.json`. |
| **`d`** ou **`↑`** | `Ctrl` / `Shift` | **Próxima Seção** | Salta para o início da próxima seção. |
| **`a`** ou **`↓`** | `Ctrl` / `Shift` | **Seção Anterior** | Salta para o fim da seção anterior. |
| **`s`** | `Ctrl` / `Shift` | **Dividir Seção** | Divide a seção atual no frame corrente (**S**plit). |
| **`j`** | `Ctrl` / `Shift` | **Juntar Seção** | Mescla a seção atual com a adjacente (**J**oin). |
| **`x`** | `Ctrl` / `Shift` | **Remover Seção** | Remove a seção inteira atual. |
| **`u`** | `Ctrl` / `Shift` | **Desfazer Seção** | Restaura a última seção removida ou dividida (**U**ndo). |
| **`Home`** / **`End`** | — | **Início / Fim** | Salta para o primeiro ou último frame da seção atual. |
| **`v`** | — | **Toggle Preview** | Alterna entre o modo de edição e o modo preview (*Rough Cut*). |
| **`n`** | — | **Próximo Vídeo** | Avança para o início do próximo vídeo da `Playlist` (sentido forward). |
| **`n`** / **`N`** | `Ctrl` (pynput) / `Shift` ou `N` (OpenCV) | **Próximo Vídeo (Fim)** | Salta para o final do próximo vídeo com pré-aquecimento de buffer e inicia em rewind. |
| **`p`** | — | **Vídeo Anterior** | Retorna para o início do vídeo anterior da `Playlist` (sentido forward). |
| **`p`** / **`P`** | `Ctrl` (pynput) / `Shift` ou `P` (OpenCV) | **Vídeo Anterior (Fim)** | Salta para o final do vídeo anterior com pré-aquecimento de buffer e inicia em rewind. |
| **`q`** | — | **Sair** | Encerra o visualizador de forma limpa. |

---

## 🏛️ Interfaces Principais

O `aniseek` segue o princípio de segregação de interfaces e inversão de dependência:

| Interface | Módulo | Papel | Implementações Nativas |
| :--- | :--- | :--- | :--- |
| **`IFrameSource`** | `aniseek.core.interfaces.source` | Contrato de decodificação e fatiamento temporal de frames. | `OpenCVVideoSource`, `PyAVVideoSource`, `ImageSource` |
| **`IFrameDisplay`** | `aniseek.view.interfaces.display` | Contrato de renderização e ciclo de vida de janelas. | `CV2Display`, `NullDisplay` |
| **`InputHandler`** | `aniseek.view.interfaces.input` | Contrato para leitura e captura de eventos de teclado. | `PynputKeyReader`, `CV2KeyReader` |
| **`Command`** | `aniseek.view.interfaces.command` | Contrato para ações disparadas por atalhos e estados de botão (`PRESS`, `HOLD`, `RELEASE`). | `ProceedCommand`, `RewindCommand`, `SaveCommand`, etc. |
| **`IMemento`** | `aniseek.editing.interfaces.memento` | Contrato para captura e restauração de estados de edição (Undo). | `TrashMemento`, `SectionMemento` |

---

## 📚 Documentação Completa

Para aprofundar-se na arquitetura e nas APIs detalhadas:

- 🏛️ [**Arquitetura do Sistema (`architecture.md`)**](architecture.md): Visão detalhada das camadas `core`, `editing` e `view`, sistema servant/master, singleton `config` e política de logs.
- 📖 [**Leitores de Vídeo (`readers.md`)**](readers.md): Guia completo de `BaseVideoReader`, `ForwardReader`, `ReverseReader` e `VideoReader`.
- 🖼️ [**Visualizador e Edição (`viewer.md`)**](viewer.md): Guia do `FrameViewer`, `IFrameDisplay`, `InputHandler`, `HoldTimer`, comandos e `MacroCommand`.
- 🔌 [**Fontes e Backends (`sources.md`)**](sources.md): Detalhes de `IFrameSource`, `OpenCVVideoSource`, `PyAVVideoSource`, `ImageSource` e `SourceRegistry`.
