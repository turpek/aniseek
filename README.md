# aniseek

**aniseek** é um motor inteligente para busca, navegação e leitura precisa frame a frame de vídeos e sequências de imagens, desenvolvido em Python 3.12+. Focado na manipulação, fatiamento e extração temporal de frames, o aniseek oferece avanço e retrocesso instantâneos via buffers concorrentes em memória e um visualizador/editor desacoplado.

Sua arquitetura é baseada em um sistema de duplo buffer concorrente (`VideoBufferLeft` e `VideoBufferRight`), que permite alternância de marcha temporal com latência zero e consumo cooperativo entre `proceed` (+1) e `rewind` (-1).

---

## ✨ Funcionalidades Principais

- **Leitura Bidirecional Cooperativa (`VideoReader`):** Alternância instantânea de direção (`proceed` / `rewind`) com cache em memória entre buffers paralelos, eliminando redecodificação pesada.
- **Leitores Unidirecionais Otimizados (`ForwardReader` e `ReverseReader`):** Leitura direta ou reversa com buffer único concorrente e baixo consumo de memória.
- **Desacoplamento Total de Backend (`IFrameSource`):**
  - [`OpenCVVideoSource`](docs/sources.md): Decodificação de arquivos de vídeo via OpenCV.
  - [`ImageSource`](docs/sources.md): Leitura sequencial de diretórios de imagens (`.png`, `.jpg`, `.webp`, `.bmp`).
  - [`SourceRegistry`](docs/sources.md): Singleton com context manager (`use()`) e construtor inteligente (`from_default`) para resolução automática de formato.
- **Visualizador e Editor Interativo (`FrameViewer`):**
  - Interface visual limpa via OpenCV GUI com suporte a atalhos de teclado de alto nível via `pynput`.
  - Loop canônico não-bloqueante orientado a eventos (`while not viewer.quit():`).
- **Gerenciamento de Seções e Edição Não-Destrutiva:**
  - Divida (`Split`), junte (`Join`) e remova seções em tempo real.
  - Lixeira (`Trash`) com histórico Memento para desfazer (`undo`) remoção de frames ou seções.
  - Modo Preview (*Rough Cut*) para visualização contínua das seções ativas.
- **Persistência Explícita:**
  - Fim do salvamento forçado. Salve explicitamente via método `.save()` ou atalho de teclado (`Ctrl + w` / `Shift + w`).
  - Suporte a injeção de seções em múltiplos formatos: `dict`, arquivo `.json` ou instância de `SectionManager`.
- **Extensibilidade com Padrão Command:**
  - Vincule comandos personalizados com tipagem estrita via `viewer.bind(key, command)`.
  - Agrupe e execute múltiplos comandos em sequência com `MacroCommand`.

---

## 🛠️ Tecnologias Utilizadas

- [Python 3.12+](https://www.python.org/)
- [OpenCV (`opencv-python`)](https://pypi.org/project/opencv-python/): Decodificação e exibição nativa de frames.
- [pynput](https://pypi.org/project/pynput/): Captura precisa de modificadores de teclado (`Ctrl`, `Shift`, `Alt`) em nível de sistema operacional.
- [NumPy](https://numpy.org/): Manipulação eficiente de arrays de frames.
- [Loguru](https://github.com/Delgan/loguru): Logging estruturado.
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

### 1. Leitura de Vídeo com `VideoReader`

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

### 2. Leitura com Injeção de Backend Explícito

```python
from aniseek import ForwardReader
from aniseek.core.sources import OpenCVVideoSource, ImageSource

# Injeção de backend de vídeo:
source = OpenCVVideoSource("video.mp4")
with ForwardReader(source, start="01:00", end="01:30", step=2) as reader:
    for ret, frame in reader:
        if not ret:
            continue
        # Processar frame

# Injeção de backend de pasta de imagens:
img_source = ImageSource("frames_dir/", fps=24.0)
with ForwardReader(img_source) as reader:
    for ret, frame in reader:
        if not ret:
            continue
        # Processar imagem
```

### 3. Visualizador e Editor (`FrameViewer`)

O loop canônico e idiomático do `FrameViewer` é governado por `while not viewer.quit():`:

```python
from aniseek.view import FrameViewer

with FrameViewer.from_default("video.mp4") as viewer:
    while not viewer.quit():
        ret, frame = viewer.read()
        viewer.show(ret, frame)
```

### 4. Injeção de Seções e Salvamento Explícito

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

### 5. Comandos Personalizados e `MacroCommand`

```python
from aniseek.view import FrameViewer
from aniseek.view.interfaces.command import Command
from aniseek.view.video_command import MacroCommand, PauseCommand, SaveCommand

class NotificarCommand(Command):
    def executor(self) -> None:
        print("Ação personalizada executada!")

with FrameViewer.from_default("video.mp4") as viewer:
    ctrl = viewer._FrameViewer__video_controller

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

---

## ⌨️ Comandos e Atalhos do `FrameViewer`

| Tecla | Modificador | Ação | Descrição |
| :---: | :---: | :--- | :--- |
| **`d`** | — | **Proceed** | Avança frame a frame (+1). |
| **`a`** | — | **Rewind** | Retrocede frame a frame (-1). |
| **`espaço`** | — | **Pause/Play (Delay)** | Pausa ativa para edição (delay=0) ou retoma reprodução. |
| **`b`** | — | **Pause/Play (Toggle)** | Alterna pausa e reprodução contínua. |
| **`x`** | — | **Remover Frame** | Remove o frame atual e envia para a lixeira (`Trash`). |
| **`u`** | — | **Desfazer Frame** | Restaura o último frame da lixeira. |
| **`[`** / **`]`** | — | **Velocidade** | Diminui / Aumenta a velocidade de reprodução. |
| **`=`** | — | **Restaurar Velocidade**| Restaura o delay padrão de reprodução. |
| **`w`** | `Ctrl` / `Shift` | **Salvar** | Persiste o estado das seções explicitamente no arquivo `.json`. |
| **`d`** | `Ctrl` / `Shift` | **Próxima Seção** | Salta para o início da próxima seção. |
| **`a`** | `Ctrl` / `Shift` | **Seção Anterior** | Salta para o fim da seção anterior. |
| **`s`** | `Ctrl` / `Shift` | **Dividir Seção** | Divide a seção atual no frame corrente (**S**plit). |
| **`j`** | `Ctrl` / `Shift` | **Juntar Seção** | Mescla a seção atual com a adjacente (**J**oin). |
| **`x`** | `Ctrl` / `Shift` | **Remover Seção** | Remove a seção inteira atual. |
| **`u`** | `Ctrl` / `Shift` | **Desfazer Seção** | Restaura a última seção removida ou dividida (**U**ndo). |
| **`Home`** / **`End`** | — | **Início / Fim** | Salta para o primeiro ou último frame da seção atual. |
| **`v`** | — | **Toggle Preview** | Alterna entre o modo de edição e o modo preview (*Rough Cut*). |
| **`n`** / **`p`** | — | **Playlist** | Avança para o próximo vídeo ou volta ao anterior. |
| **`q`** | — | **Sair** | Encerra o visualizador de forma limpa. |

---

## 📚 Documentação Completa

Para aprofundar-se na arquitetura e nas APIs detalhadas:

- 🏛️ [**Arquitetura do Sistema (`docs/architecture.md`)**](docs/architecture.md): Visão detalhada das camadas `core`, `editing` e `view`, sistema servant/master e threading.
- 📖 [**Leitores de Vídeo (`docs/readers.md`)**](docs/readers.md): Guia completo de `BaseVideoReader`, `ForwardReader`, `ReverseReader` e `VideoReader`.
- 🖼️ [**Visualizador e Edição (`docs/viewer.md`)**](docs/viewer.md): Guia do `FrameViewer`, customização de atalhos, comandos e `MacroCommand`.
- 🔌 [**Fontes e Backends (`docs/sources.md`)**](docs/sources.md): Detalhes de `IFrameSource`, `OpenCVVideoSource`, `ImageSource` e `SourceRegistry`.
