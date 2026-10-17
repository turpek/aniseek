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
    display: type[IFrameDisplay] | str = CV2Display,
    log: bool = False,
    title_formatter: TitleFormatter | None = None,
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
    display: type[IFrameDisplay] | str = CV2Display,
    backend: type[IFrameSource] | str | None = None,
    log: bool = False,
    title_formatter: TitleFormatter | None = None,
)
```

### C. Assinatura de `from_playlist`:

```python
FrameViewer.from_playlist(
    playlist: Playlist,
    *,
    sections: SectionManager | dict | Path | str | None = None,
    shortcuts: dict[int, str] | None = None,
    buffersize: int = 60,
    key_reader: type[InputHandler] = PynputKeyReader,
    display: type[IFrameDisplay] | str = CV2Display,
    log: bool = False,
    title_formatter: TitleFormatter | None = None,
)
```

### Tabela de Parâmetros:

| Parâmetro | Tipo | Padrão | Descrição |
| :--- | :--- | :--- | :--- |
| `source` | `IFrameSource` | *Obrigatório (`__init__`)* | Instância de backend de extração de frames. |
| `path` | `str \| Path` | *Obrigatório (`from_default`)* | Caminho para arquivo de vídeo ou diretório de imagens. |
| `playlist` | `Playlist` | *Obrigatório (`from_playlist`)* | Instância de playlist contendo múltiplos caminhos de mídia. |
| `sections` | `SectionManager \| dict \| Path \| str \| None` | `None` | Seções injetadas para edição (dicionário serializado, caminho JSON ou instância). |
| `shortcuts` | `dict[int, str] \| None` | `None` | Dicionário de atalhos para estender/sobrescrever o mapeamento padrão da instância. |
| `buffersize` | `int` | `60` | Capacidade dos buffers concorrentes em memória. |
| `key_reader` | `type[InputHandler]` | `PynputKeyReader` | Classe responsável pela captura de eventos de teclado (`PynputKeyReader` ou `CV2KeyReader`). |
| `display` | `type[IFrameDisplay] \| str` | `CV2Display` | Renderizador de exibição (`"opencv"`, `"cv2"`, `"null"`, `"headless"` ou subclasse de `IFrameDisplay`). |
| `backend` | `type[IFrameSource] \| str \| None` | `None` | Backend de decodificação de vídeo (`"opencv"`, `"pyav"` ou subclasse de `IFrameSource`). |
| `log` | `bool` | `False` | Habilita logs detalhados dos buffers concorrentes. |
| `title_formatter`| `TitleFormatter \| None` | `None` | Função customizada para formatação da barra de título da janela. |

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
    ctrl = viewer.controller  # Acesso direto e limpo ao VideoController

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

## 7. Renderização e Display Desacoplado (`IFrameDisplay`)

O `FrameViewer` isola a camada gráfica através do contrato **`IFrameDisplay`** (`aniseek.view.interfaces.display`), permitindo alternar facilmente entre janelas nativas, execução *headless* ou engines gráficos externos.

### A. Contrato da Interface (`IFrameDisplay`):

```python
from abc import ABC, abstractmethod
from numpy import ndarray

class IFrameDisplay(ABC):
    @abstractmethod
    def create_window(self, name: str = "aniseek", width: int = 720, height: int = 420) -> None:
        """Cria e dimensiona a janela de exibição."""
        ...

    @abstractmethod
    def show_frame(self, frame: ndarray) -> None:
        """Renderiza um único frame na tela."""
        ...

    @abstractmethod
    def set_title(self, title: str) -> None:
        """Atualiza a barra de título da janela com metadados."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Fecha a janela e libera recursos gráficos subjacentes."""
        ...
```

### B. Implementações Nativas:

1. **`CV2Display` (`aniseek.view.display`):**
   - Implementação padrão via OpenCV HighGUI (`cv2.namedWindow`, `cv2.imshow`, `cv2.setWindowTitle`, `cv2.destroyWindow`).
   - Identificador de janela limpo padronizado em `"aniseek"`.
2. **`NullDisplay` (`aniseek.view.display`):**
   - Implementação *headless* (no-op) em memória. Não requisita servidor X11/Wayland nem inicializa recursos gráficos.
   - Armazena `last_frame` e `last_title` para inspeção direta.
   - Ideal para testes unitários, automação em lote, pipelines de CI/CD e servidores sem interface gráfica.

### C. Seleção por String ou Tipo:

O parâmetro `display` aceita classes ou os seguintes identificadores textuais:
- `"opencv"` ou `"cv2"`: Instancia `CV2Display` (padrão).
- `"null"` ou `"headless"`: Instancia `NullDisplay`.

```python
from aniseek.view import FrameViewer

# Execução headless completa (sem abrir janelas):
with FrameViewer.from_default("video.mp4", display="null") as viewer:
    while not viewer.quit():
        ret, frame = viewer.read()
        viewer.show(ret, frame)
        # O frame é processado sem overhead gráfico
```

### D. Criando um Display Personalizado (ex: PyQt, Web, Pygame):

```python
from aniseek.view.interfaces.display import IFrameDisplay
import numpy as np

class WebStreamDisplay(IFrameDisplay):
    """Exemplo de display que envia frames para um stream HTTP/WebRTC."""

    def create_window(self, name: str = "aniseek", width: int = 720, height: int = 420) -> None:
        print(f"Iniciando stream '{name}' ({width}x{height})")

    def show_frame(self, frame: np.ndarray) -> None:
        # Codifica e transmite o frame via websocket/HTTP
        pass

    def set_title(self, title: str) -> None:
        # Envia metadados atualizados para o cliente web
        pass

    def close(self) -> None:
        print("Finalizando stream")

# Uso:
viewer = FrameViewer.from_default("video.mp4", display=WebStreamDisplay)
```

---

## 8. Subsistema de Entrada e Captura de Teclado (`InputHandler`)

A recepção de eventos de teclado é gerenciada pela classe abstrata **`InputHandler`** (`aniseek.view.interfaces.input`), garantindo captura unificada de teclas e modificadores.

### A. Constantes e Estrutura da Interface:

```python
class InputHandler(ABC):
    # Máscaras de bits para identificação de modificadores combinados
    CTRL_BIT = 0x100   # 256
    SHIFT_BIT = 0x200  # 512
    ALT_BIT = 0x400    # 1024

    # Teclas de navegação padronizadas
    KEY_HOME  = 0xFF50
    KEY_LEFT  = 0xFF51
    KEY_UP    = 0xFF52
    KEY_RIGHT = 0xFF53
    KEY_DOWN  = 0xFF54
    KEY_END   = 0xFF57

    @abstractmethod
    def get_code(self, delay: int) -> int:
        """Retorna o código numérico da tecla pressionada ou -1 se nenhuma."""
        ...

    def get_event(self, delay: int) -> tuple[int, ButtonState] | None:
        """Retorna uma tupla (codigo_tecla, ButtonState) ou None."""
        ...

    def join(self) -> None:
        """Encerra threads ou listeners em segundo plano de forma graciosa."""
        ...
```

### B. Implementações Disponíveis:

1. **`PynputKeyReader` (`aniseek.view.input_handler`) — Padrão:**
   - Utiliza `pynput.keyboard.Listener` em uma thread *daemon* dedicada.
   - Captura com precisão modificadores no nível do sistema operacional (`Ctrl`, `Shift`, `Alt`), mesmo durante cliques rápidos.
   - Suporte inteligente a caracteres de controle ASCII (`Ctrl+a` até `Ctrl+z`), teclas especiais e teclado numérico (*Numpad*).
   - Emite eventos estruturados com `ButtonState` (`PRESS`, `HOLD`, `RELEASE`).
   - O método `join()` assegura liberação imediata da thread listener, prevenindo travamentos no encerramento da aplicação.

2. **`CV2KeyReader` (`aniseek.view.input_handler`):**
   - Fallback simples baseado exclusivamente em `cv2.waitKeyEx(delay)`.
   - Útil em ambientes restritos (como contêineres Docker sem permissões de input do sistema) onde o `pynput` não possa registrar hooks.

### C. Implementando um `InputHandler` Personalizado (ex: Gamepad, Rede ou Mock):

```python
from aniseek.view.interfaces.input import InputHandler
from aniseek.view.interfaces.command import ButtonState

class JoystickInputHandler(InputHandler):
    """Handler customizado para mapear controles de gamepad/joystick."""

    def __init__(self) -> None:
        super().__init__()
        # Inicializa driver de joystick (ex: pygame.joystick)

    def get_code(self, delay: int) -> int:
        # Retorna código simulado para o método tradicional
        return -1

    def get_event(self, delay: int) -> tuple[int, ButtonState] | None:
        # Lê eventos do joystick e mapeia para códigos do aniseek:
        # Exemplo: Botão 'D-Pad Right' -> (ord('d'), ButtonState.PRESS)
        return None

    def join(self) -> None:
        # Libera recursos do driver
        pass

# Injetando no FrameViewer:
viewer = FrameViewer.from_default("video.mp4", key_reader=JoystickInputHandler)
```

---

## 9. Arquitetura de Comandos (`Command` & `Invoker`)

O `aniseek` implementa o padrão **Command** desacoplado, onde cada ação do visualizador é um objeto independente que implementa a interface abstrata **`Command`** (`aniseek.view.interfaces.command`).

### A. Contrato da Interface `Command`:

```python
from abc import ABC, abstractmethod

class Command(ABC):
    @abstractmethod
    def executor(self) -> None:
        """Executa a ação principal do comando."""
        ...

    def execute(self) -> None:
        """Alias idiomático para executor()."""
        self.executor()

    def undo(self) -> None:
        """Reverte a ação realizada, se suportado."""
        ...

    def on_press(self) -> None:
        """Disparado imediatamente quando a tecla é pressionada (ButtonState.PRESS)."""
        self.executor()

    def on_hold(self) -> None:
        """Disparado repetidamente enquanto a tecla permanece pressionada (ButtonState.HOLD)."""
        self.executor()

    def on_release(self) -> None:
        """Disparado quando a tecla é liberada (ButtonState.RELEASE)."""
        ...
```

### B. O Despachante `Invoker`:

O `Invoker` (`viewer.command`) mantém o registro de comandos por nome e código de tecla:
- `set_command(name_or_key, command)`: Registra um comando.
- `executor_command(key, state: ButtonState)`: Despacha o comando chamando `on_press()`, `on_hold()` ou `on_release()` conforme o ciclo de vida da tecla.

### C. Catálogo de Comandos Nativos (`aniseek.view.video_command`):

| Categoria | Classe do Comando | Responsabilidade |
| :--- | :--- | :--- |
| **Reprodução & Navegação** | `ProceedCommand` | Avança 1 frame com `HoldTimer` para aceleração contínua suave. |
| | `RewindCommand` | Retrocede 1 frame com `HoldTimer` para aceleração contínua suave. |
| | `DynamicProceedCommand` | Alterna sentido para forward sem alterar pausa. |
| | `DynamicRewindCommand` | Alterna sentido para rewind sem alterar pausa. |
| | `PauseCommand` | Pausa total da reprodução. |
| | `PauseDelayCommand` | Alterna pausa de delay ou retoma velocidade. |
| | `IncreaseSpeedCommand` | Aumenta velocidade de reprodução (reduz delay entre frames). |
| | `DecreaseSpeedCommand` | Reduz velocidade de reprodução (aumenta delay entre frames). |
| | `RestoreDelayCommand` | Restaura a velocidade nominal padrão do vídeo. |
| | `QuitCommand` | Sinaliza encerramento do visualizador (`quit() -> True`). |
| **Edição & Seções** | `RemoveFrameCommand` | Envia o frame atual para a lixeira (`Trash`). |
| | `UndoFrameCommand` | Restaura o último frame descartado da lixeira. |
| | `NextSectionCommand` | Salta para o primeiro frame da próxima seção. |
| | `PrevSectionCommand` | Salta para o último frame da seção anterior. |
| | `SplitSectionCommand` | Divide a seção ativa na posição do frame atual. |
| | `JoinSectionCommand` | Mescla a seção ativa com a seção adjacente. |
| | `RemoveSectionCommand` | Descarta a seção ativa por inteiro. |
| | `UndoSectionCommand` | Desfaz a última operação de edição via Memento (`Caretaker`). |
| | `JumpSectionStartCommand`| Posiciona o cursor no início da seção atual. |
| | `JumpSectionEndCommand` | Posiciona o cursor no fim da seção atual. |
| | `TogglePreviewCommand` | Alterna entre modo de corte interativo e *Rough Cut Preview*. |
| | `SaveCommand` | Persiste explicitamente as seções em arquivo JSON sidecar. |
| **Playlist & Prefill** | `NextVideoCommand` | Avança para o início do próximo vídeo da playlist. |
| | `PrevVideoCommand` | Retorna para o início do vídeo anterior da playlist. |
| | `NextVideoEndCommand` | Salta para o final do próximo vídeo com pré-aquecimento de buffer. |
| | `PrevVideoEndCommand` | Salta para o final do vídeo anterior com pré-aquecimento de buffer. |
| **Composição** | `MacroCommand` | Executa múltiplos comandos sequencialmente em lote. |

## 10. Ciclo de Vida de Eventos e Repetição (`HoldTimer`)

Os comandos do `FrameViewer` suportam o ciclo de vida completo do botão via enumeração `ButtonState` (`PRESS`, `HOLD` e `RELEASE`). Para eliminar saltos acidentais de múltiplos frames no clique rápido e permitir aceleração contínua suave ao segurar uma tecla, os comandos contínuos utilizam internamente um **`HoldTimer`**:

```python
class HoldTimer:
    def __init__(self, delay: float = 0.15, interval: float = 1.0 / 30) -> None:
        ...
```

### Como Funciona:
1. **No clique rápido (`ButtonState.PRESS`):** O comando executa exatamente uma vez (`on_press`) e ativa o timer com a tolerância de atraso (`delay`). Se a tecla for solta em menos de 150ms (`ButtonState.RELEASE`), o timer é cancelado e **nenhum frame adicional é lido**.
2. **Ao manter pressionado (`ButtonState.HOLD`):** Enquanto a tecla permanecer pressionada, após o `delay` inicial expirar, o timer dispara a execução repetida a cada `interval` (padrão: 30 FPS).
3. **Na liberação (`ButtonState.RELEASE`):** O comando finaliza o ciclo e desliga o timer com segurança.

### Customização Global dos Tempos:
Os parâmetros temporais são configurados centralmente no singleton `config`:

```python
from aniseek import config

# Aumentar a tolerância do clique para 200ms e a taxa de repetição para 60 FPS:
config.hold_delay = 0.20
config.hold_interval = 1.0 / 60
```

---

## 11. Navegação em Playlist e Saltos Reversos com Pré-Aquecimento (Prefill)

O `FrameViewer` suporta navegação direta e reversa entre arquivos de mídia da `Playlist`:

- **Navegação Convencional (`NextVideoCommand` / `PrevVideoCommand`):**
  - Atalhos: **`n`** (próximo vídeo) e **`p`** (vídeo anterior).
  - Posiciona a reprodução no primeiro frame válido (`mapping[0]`) e garante o sentido de avanço direto (`proceed`).

- **Saltos Reversos Instantâneos (`NextVideoEndCommand` / `PrevVideoEndCommand`):**
  - Atalhos:
    - **`pynput`:** **`Ctrl + n`** (próximo ao fim) e **`Ctrl + p`** (anterior ao fim).
    - **OpenCV:** **`Shift + n`** / **`N`** (próximo ao fim) e **`Shift + p`** / **`P`** (anterior ao fim).
  - **Mecanismo de Pré-Aquecimento:** Decodificar diretamente no sentido reverso a partir do último frame de um vídeo pode gerar latência se o buffer reverso estiver vazio. Os comandos `NextVideoEndCommand` e `PrevVideoEndCommand` posicionam o cursor em `max(0, target_frame - prefill_frames)`, decodificam rapidamente para frente preenchendo a janela de RAM do buffer e invertem o leitor para `rewind`. O usuário imediatamente visualiza o último frame e pode retroceder a 50+ FPS com latência zero.

---

## 12. Tabela Completa de Atalhos Padrão

| Tecla | Modificador | Comando | Descrição |
| :---: | :---: | :--- | :--- |
| **`d`** ou **`→`** | — | `ProceedCommand` | Avança frame a frame (+1) com repetição contínua ao segurar. |
| **`a`** ou **`←`** | — | `RewindCommand` | Retrocede frame a frame (-1) com repetição contínua ao segurar. |
| **`espaço`** | — | `PauseDelayCommand` | Alterna pausa de delay para edição ou retoma velocidade. |
| **`b`** | — | `PauseCommand` | Pausa total da reprodução. |
| **`x`** | — | `RemoveFrameCommand` | Remove frame atual e envia para a lixeira (`Trash`). |
| **`u`** | — | `UndoFrameCommand` | Restaura o último frame da lixeira. |
| **`[`** / **`]`** | — | `DecreaseSpeed` / `IncreaseSpeed` | Ajusta delay de exibição entre frames. |
| **`=`** | — | `RestoreDelayCommand` | Restaura a velocidade padrão de reprodução. |
| **`w`** | `Ctrl` / `Shift` / `W` | `SaveCommand` | Salva o estado das seções explicitamente em disco. |
| **`d`** ou **`↑`** | `Ctrl` / `Shift` | `NextSectionCommand` | Salta para o início da próxima seção. |
| **`a`** ou **`↓`** | `Ctrl` / `Shift` | `PrevSectionCommand` | Salta para o fim da seção anterior. |
| **`s`** | `Ctrl` / `Shift` | `SplitSectionCommand` | Divide a seção no frame atual (**S**plit). |
| **`j`** | `Ctrl` / `Shift` | `JoinSectionCommand` | Une a seção atual com a adjacente (**J**oin). |
| **`x`** | `Ctrl` / `Shift` | `RemoveSectionCommand`| Remove a seção atual inteira. |
| **`u`** | `Ctrl` / `Shift` | `UndoSectionCommand` | Desfaz a última alteração de seção (**U**ndo). |
| **`Home`** / **`End`** | — | `JumpSectionStart` / `JumpSectionEnd` | Salta para o primeiro ou último frame da seção. |
| **`v`** | — | `TogglePreviewCommand` | Alterna entre modo de edição e preview contínuo (*Rough Cut*). |
| **`n`** | — | `NextVideoCommand` | Avança para o próximo vídeo da `Playlist` (início, reproduz em forward). |
| **`n`** / **`N`** | `Ctrl` (pynput) / `Shift` ou `N` (OpenCV) | `NextVideoEndCommand` | Salta para o final do próximo vídeo com pré-aquecimento de buffer e inicia em rewind. |
| **`p`** | — | `PrevVideoCommand` | Retorna para o vídeo anterior da `Playlist` (início, reproduz em forward). |
| **`p`** / **`P`** | `Ctrl` (pynput) / `Shift` ou `P` (OpenCV) | `PrevVideoEndCommand` | Salta para o final do vídeo anterior com pré-aquecimento de buffer e inicia em rewind. |
| **`q`** | — | `QuitCommand` | Encerra a reprodução e fecha a janela. |

---

## 13. Propriedades Públicas e Customização da Barra de Título

O `FrameViewer` expõe propriedades protegidas e públicas para facilitar integração programática e introspecção de estado:

### A. Acesso a Subcomponentes:
- **`viewer.controller`** (ou **`viewer.video_controller`**): Instância de `VideoController` que orquestra playlist, reprodução e seções.
- **`viewer.video_manager`**: Instância de `VideoManager` gerenciando buffers concorrentes e decodificação em baixo nível.
- **`viewer.display`**: Instância ativa de `IFrameDisplay` (`CV2Display`, `NullDisplay` ou customizada).
- **`viewer.frame_id`**: Identificador numérico absoluto (0-based) do quadro renderizado no momento.

### B. Customização da Barra de Título (`ViewerTitleContext`):

Você pode injetar um formatador de título personalizado através do parâmetro `title_formatter` no construtor ou a qualquer momento com `viewer.set_title_formatter(formatter)`:

```python
from aniseek.view import FrameViewer, ViewerTitleContext

def meu_formatador(ctx: ViewerTitleContext) -> str:
    status = "PAUSA" if ctx.is_paused else ("<<" if ctx.is_rewind else ">>")
    return f"Meu Player | Frame {ctx.frame_id} | Seção {ctx.section_index}/{ctx.total_sections} [{status}]"

with FrameViewer.from_default("video.mp4", title_formatter=meu_formatador) as viewer:
    while not viewer.quit():
        ret, frame = viewer.read()
        viewer.show(ret, frame)
```

O dataclass `ViewerTitleContext` disponibiliza os seguintes campos:
- `frame_id: int | None` — ID absoluto do frame.
- `relative_frame: int` — Posição relativa do frame dentro da seção ativa.
- `section_frames: int` — Total de frames da seção ativa.
- `section_index: int` — Índice da seção atual (1-based).
- `total_sections: int` — Quantidade total de seções ativas.
- `is_preview: bool` — Indica se o modo de visualização rápida (*Preview*) está ativo.
- `is_rewind: bool` — `True` se a direção de reprodução for reversa.
- `is_paused: bool` — `True` se o player estiver pausado.
- `playlist_index: int | None` — Índice do vídeo ativo na playlist.
- `playlist_total: int | None` — Total de vídeos na playlist.
- `label: str | None` — Nome ou identificador do vídeo ativo na playlist.
