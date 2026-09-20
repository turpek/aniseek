# Visualizador e Editor Interativo (`FrameViewer`)

O módulo `aniseek.view` disponibiliza o **`FrameViewer`**, uma fachada visual de alto nível construída sobre o OpenCV GUI e o subsistema de entrada por teclado (`pynput` / `OpenCV`). O `FrameViewer` permite inspecionar, navegar, fatiar e editar vídeos e sequências de imagens de forma interativa e não-destrutiva.

---

## 1. Construtores e Inicialização

O `FrameViewer` segue a regra de tipagem estrita da biblioteca:
- **Construtor Primário (`__init__`):** Exige estritamente uma instância de [`IFrameSource`](sources.md).
- **Construtor Alternativo Inteligente (`from_default`):** Exige um caminho (`str` ou `Path`) e resolve automaticamente o backend adequado via `SourceRegistry`.

### A. Assinatura do Construtor Primário:

```python
FrameViewer(
    source: IFrameSource,
    *,
    sections: SectionManager | dict | Path | str | None = None,
    shortcuts: dict[int, str] | None = None,
    buffersize: int = 60,
    key_reader: type[InputHandler] = PynputKeyReader,
    log: bool = False,
)
```

### B. Assinatura de `from_default`:

```python
FrameViewer.from_default(
    path: str | Path,
    *,
    sections: SectionManager | dict | Path | str | None = None,
    shortcuts: dict[int, str] | None = None,
    buffersize: int = 60,
    key_reader: type[InputHandler] = PynputKeyReader,
    log: bool = False,
)
```

### Tabela de Parâmetros:

| Parâmetro | Tipo | Padrão | Descrição |
| :--- | :--- | :--- | :--- |
| `source` | `IFrameSource` | *Obrigatório (`__init__`)* | Instância de backend de extração de frames. |
| `path` | `str \| Path` | *Obrigatório (`from_default`)* | Caminho para arquivo de vídeo ou diretório de imagens. |
| `sections` | `SectionManager \| dict \| Path \| str \| None` | `None` | Seções injetadas para edição (dicionário serializado, caminho JSON ou instância). |
| `shortcuts` | `dict[int, str] \| None` | `None` | Dicionário de atalhos para estender/sobrescrever o mapeamento padrão da instância. |
| `buffersize` | `int` | `60` | Capacidade dos buffers concorrentes em memória. |
| `key_reader` | `type[InputHandler]` | `PynputKeyReader` | Classe responsável pela captura de eventos de teclado. |
| `log` | `bool` | `False` | Habilita logs detalhados dos buffers concorrentes. |

---

## 2. Ciclo de Vida e o Loop Canônico

O loop idiomático do `FrameViewer` é governado pelo método **`.quit()`**:

```python
from aniseek.view import FrameViewer

with FrameViewer.from_default("video.mp4") as viewer:
    while not viewer.quit():
        ret, frame = viewer.read()
        viewer.show(ret, frame)
```

### Por que usar `while not viewer.quit():`?
- **Desacoplamento do término:** O método `viewer.quit()` retorna `False` durante a reprodução normal e muda para `True` quando o usuário pressiona a tecla de saída (`q` via `QuitCommand`) ou quando a playlist/vídeo se esgota.
- **Despacho automático no `show()`:** O método `viewer.show(ret, frame)` exibe o frame na janela OpenCV, atualiza a barra de título com metadados (seção ativa, frame atual, delay, direção) e processa os comandos de teclado no delay configurado.

---

## 3. Injeção Flexível de Seções

O `FrameViewer` aceita cortes e seções pré-existentes em múltiplos formatos, sem criar arquivos no disco sem autorização:

```python
from aniseek.view import FrameViewer
from aniseek.editing.section import SectionManager, VideoSection

# Forma 1: Dicionário em memória
data = {
    "SECTIONS": [
        {"RANGE_FRAME_ID": (0, 100), "REMOVED_FRAMES": [], "BLACK_LIST": []},
        {"RANGE_FRAME_ID": (200, 500), "REMOVED_FRAMES": [], "BLACK_LIST": []},
    ],
    "REMOVED": [],
}
viewer = FrameViewer.from_default("video.mp4", sections=data)

# Forma 2: Arquivo JSON existente
viewer = FrameViewer.from_default("video.mp4", sections="meu_corte.json")

# Forma 3: Instância de SectionManager
secman = SectionManager([VideoSection(0, 150), VideoSection(300, 600)])
viewer = FrameViewer.from_default("video.mp4", sections=secman)

# Forma 4: None (Padrão)
# Cria uma seção única cobrindo 100% dos frames em memória. Nenhum arquivo .json é gerado.
viewer = FrameViewer.from_default("video.mp4")
```

---

## 4. Persistência Explícita (`.save()`)

O salvamento **não ocorre automaticamente** ao sair ou alternar de vídeo. O controle é explícito:

### Via Código:
```python
# Salva no arquivo sidecar padrão (<video>.json)
viewer.save()

# Ou salva em um caminho específico:
viewer.save("caminho/personalizado/secoes.json")
```

### Via Interface (Atalho):
- Pressione **`Ctrl + w`** (ou **`Shift + w`** / **`W`**) para disparar o `SaveCommand` e persistir as seções imediatamente.

---

## 5. Customização de Atalhos e Comandos

### A. Sobrescrita de Atalhos via Construtor (`shortcuts={...}`)

Você pode passar um dicionário mapeando o código da tecla para o nome do comando:

```python
from aniseek.view import FrameViewer

meus_atalhos = {
    ord("k"): "PauseCommand",         # Tecla 'k' para pausar/despausar
    ord("s"): "SaveCommand",          # Tecla 's' para salvar
}

with FrameViewer.from_default("video.mp4", shortcuts=meus_atalhos) as viewer:
    while not viewer.quit():
        ret, frame = viewer.read()
        viewer.show(ret, frame)
```

### B. Vinculação Estrita de Comandos Personalizados (`.bind()`)

O método `.bind(key, command)` aceita **estritamente instâncias de [`Command`](file:///home/gui/python/aniseek/src/aniseek/view/interfaces/command.py#L4-L10)**:

```python
from aniseek.view import FrameViewer
from aniseek.view.interfaces.command import Command

class LogFrameCommand(Command):
    def __init__(self, viewer):
        self.viewer = viewer

    def executor(self) -> None:
        print(f"[LOG] Frame ID atual: {self.viewer.frame_id}")

with FrameViewer.from_default("video.mp4") as viewer:
    # Vincula a tecla 'm' ao comando personalizado
    viewer.bind(ord("m"), LogFrameCommand(viewer))

    while not viewer.quit():
        ret, frame = viewer.read()
        viewer.show(ret, frame)
```

Qualquer tentativa de passar callables ou objetos que não herdem de `Command` levanta `TypeError`:
```python
viewer.bind(ord("m"), lambda: print("invalido"))  # TypeError: Expected command to be an instance of Command
```

---

## 6. Agrupando Comandos com `MacroCommand`

O `MacroCommand` implementa o padrão Composite para executar uma sequência ordenada de múltiplos comandos com um único atalho:

```python
from aniseek.view import FrameViewer
from aniseek.view.video_command import MacroCommand, PauseCommand, SaveCommand
from aniseek.view.interfaces.command import Command

class NotificarCommand(Command):
    def executor(self) -> None:
        print("Vídeo pausado e seções salvas!")

with FrameViewer.from_default("video.mp4") as viewer:
    ctrl = viewer._FrameViewer__video_controller

    # Composição: Pausar -> Salvar -> Notificar
    macro = MacroCommand([
        PauseCommand(ctrl),
        SaveCommand(ctrl),
        NotificarCommand(),
    ])

    # É possível adicionar mais comandos dinamicamente:
    # macro.add(OutroCommand())

    # Vincular à tecla 'z'
    viewer.bind(ord("z"), macro)

    while not viewer.quit():
        ret, frame = viewer.read()
        viewer.show(ret, frame)
```

---

## 7. Tabela Completa de Atalhos Padrão

| Tecla | Modificador | Comando | Descrição |
| :---: | :---: | :--- | :--- |
| **`d`** | — | `ProceesCommand` | Avança frame a frame (+1). |
| **`a`** | — | `RewindCommand` | Retrocede frame a frame (-1). |
| **`espaço`** | — | `PauseDelayCommand` | Alterna pausa de delay para edição ou retoma velocidade. |
| **`b`** | — | `PauseCommand` | Pausa total da reprodução. |
| **`x`** | — | `RemoveFrameCommand` | Remove frame atual e envia para a lixeira (`Trash`). |
| **`u`** | — | `UndoFrameCommand` | Restaura o último frame da lixeira. |
| **`[`** / **`]`** | — | `DecreaseSpeed` / `IncreaseSpeed` | Ajusta delay de exibição entre frames. |
| **`=`** | — | `RestoreDelayCommand` | Restaura a velocidade padrão de reprodução. |
| **`w`** | `Ctrl` / `Shift` / `W` | `SaveCommand` | Salva o estado das seções explicitamente em disco. |
| **`d`** | `Ctrl` / `Shift` | `NextSectionCommand` | Salta para o início da próxima seção. |
| **`a`** | `Ctrl` / `Shift` | `PrevSectionCommand` | Salta para o fim da seção anterior. |
| **`s`** | `Ctrl` / `Shift` | `SplitSectionCommand` | Divide a seção no frame atual (**S**plit). |
| **`j`** | `Ctrl` / `Shift` | `JoinSectionCommand` | Une a seção atual com a adjacente (**J**oin). |
| **`x`** | `Ctrl` / `Shift` | `RemoveSectionCommand`| Remove a seção atual inteira. |
| **`u`** | `Ctrl` / `Shift` | `UndoSectionCommand` | Desfaz a última alteração de seção (**U**ndo). |
| **`Home`** / **`End`** | — | `JumpSectionStart` / `JumpSectionEnd` | Salta para o primeiro ou último frame da seção. |
| **`v`** | — | `TogglePreviewCommand` | Alterna entre modo de edição e preview contínuo (*Rough Cut*). |
| **`n`** / **`p`** | — | `NextVideo` / `PrevVideo` | Avança ou retorna entre itens da `Playlist`. |
| **`q`** | — | `QuitCommand` | Encerra a reprodução e fecha a janela. |
