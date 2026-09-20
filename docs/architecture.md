# Arquitetura Modular (`aniseek`)

O `aniseek` é estruturado em **três camadas modulares independentes**, garantindo separação clara de responsabilidades, alta testabilidade e desacoplamento de dependências de apresentação gráfica e decodificação.

```text
               ┌───────────────────────────────┐
               │         aniseek.view          │  (GUI OpenCV, Comandos, VideoCon)
               └───────────────┬───────────────┘
                               │ depende de
                               ▼
               ┌───────────────────────────────┐
               │        aniseek.editing        │  (Seções, Mementos, Trash, VideoManager)
               └───────────────┬───────────────┘
                               │ depende de
                               ▼
               ┌───────────────────────────────┐
               │         aniseek.core          │  (Buffers Concorrentes, FrameMapper,
               └───────────────────────────────┘   IFrameSource, VideoReader)
```

---

## 1. Camada `core` — Motor de Leitura e Bufferização

O módulo `aniseek.core` é o coração do pacote. É completamente desacoplado de interfaces gráficas e do backend de decodificação.

### Componentes Principais:

1. **`IFrameSource` (`aniseek.core.interfaces.source`):**
   - Interface abstrata (`abc.ABC`) que padroniza o acesso a frames:
     - `frame_count -> int`
     - `fps -> float`
     - `seek(frame_id: int) -> None`
     - `read() -> tuple[bool, ndarray | None]`
     - `grab() -> bool`
     - `is_opened() -> bool`
     - `release() -> None`

2. **`OpenCVVideoSource` (`aniseek.core.sources.opencv`):**
   - Implementação de `IFrameSource` baseada em `cv2.VideoCapture`.
   - Encapsula o ciclo de vida do decodificador nativo OpenCV.

3. **Buffers Concorrentes (`VideoBufferRight` e `VideoBufferLeft`):**
   - Operam em threads paralelas utilizando `reader_task`.
   - `VideoBufferRight`: Pré-carrega frames em ordem crescente (`+1`).
   - `VideoBufferLeft`: Calcula blocos anteriores e pré-carrega em ordem decrescente (`-1`).
   - Comunicação via canais protegidos por locks (`_Channel`, `Channel1`).

4. **`FrameMapper` (`aniseek.core.frame_mapper`):**
   - Mantém uma lista ordenada em C (`array('l')`) de IDs de frames válidos.
   - Permite buscas binárias instantâneas via `bisect`.
   - Decide entre leitura completa (`read()`) e avanço rápido de cabeçalho (`grab()`).

5. **Leitores de Vídeo (`aniseek.core.video_reader`):**
   - `ForwardReader`: Leitura sequencial para frente com buffer único.
   - `ReverseReader`: Leitura sequencial reversa com buffer único.
   - `VideoReader`: Leitor bidirecional com duplo buffer cooperativo (`servant` / `master`) e inversão de ponteiros com latência zero.

---

## 2. Camada `editing` — Edição, Seções e Histórico

O módulo `aniseek.editing` gerencia o ciclo de vida de edição de vídeos, fatiamento, cortes, histórico de desfazer/refazer e controle de reprodução.

### Componentes Principais:

1. **Gestão de Seções (`VideoSection`, `SectionManager`, `SectionWrapper`):**
   - Modela trechos contínuos de vídeo, frames removidos e listas negras de exclusão.
   - Permite união, divisão e remoção de seções.

2. **Lixeira de Frames (`Trash`):**
   - Buffer dedicado que retém frames descartados para permitir operações de restauração (`undo`).

3. **Padrão Memento (`Caretaker`, `SectionOriginator`, `TrashOriginator`):**
   - Captura e restaura o estado de seções e da lixeira sem violar o encapsulamento.

4. **Controle de Reprodução (`PlayerControl`):**
   - Coordena direção (`proceed` / `rewind`), pausas e controle de atraso temporal (`delay`).

5. **Gerenciador Central (`VideoManager`):**
   - Orquestra os componentes de `core` (buffers, sources, mapping) com os componentes de `editing` (seções, trash, player).

6. **Lista de Reprodução (`Playlist`):**
   - Gerencia filas de vídeos a serem processados sequencialmente.

---

## 3. Camada `view` — Interface e Comandos

O módulo `aniseek.view` contém o acoplamento com a interface gráfica do OpenCV e mapeamento de comandos de usuário.

### Componentes Principais:

1. **`VideoCon` (`aniseek.view.video`):**
   - Fachada de alto nível para exibição em janela nativa OpenCV (`namedWindow`, `imshow`).
   - Gerencia atalhos de teclado e loop de exibição.

2. **`VideoController` (`aniseek.view.video_controller`):**
   - Conecta as ações da interface (`view`) ao `VideoManager` e à `Playlist`.

3. **Padrão Command (`aniseek.view.video_command`):**
   - `Invoker` e comandos concretos (`ProceedCommand`, `RewindCommand`, `PauseCommand`, `RemoveFrameCommand`, `UndoFrameCommand`, `SplitSectionCommand`, etc.).
   - Permite disparar ações desacopladas a partir de eventos de teclado ou scripts.

---

## 4. Utilitários e Exceções Compartilhadas

- **`aniseek.time_utils`:** Funções puras de conversão bidirecional entre timestamps (`str`), segundos (`float`) e índices de frames (`int`).
- **`aniseek.custom_exceptions`:** Hierarquia de exceções especializadas do projeto (`VideoBufferError`, `InvalidFrameIdError`, `SectionManagerError`, `PlaylistError`, etc.).
- **`aniseek.__init__`:** Ponto de entrada que reexporta os leitores principais (`VideoReader`, `ForwardReader`, `ReverseReader`, `BaseVideoReader`, `Direction`) e utilitários temporais para consumo conveniente da biblioteca.
