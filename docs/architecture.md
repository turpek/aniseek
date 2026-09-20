# Arquitetura Modular (`aniseek`)

O `aniseek` é estruturado em **três camadas modulares independentes**, garantindo separação clara de responsabilidades, alta testabilidade e total desacoplamento de dependências de apresentação gráfica e decodificação.

```text
               ┌───────────────────────────────┐
               │         aniseek.view          │  (GUI OpenCV, FrameViewer, Comandos, Atalhos)
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
               └───────────────────────────────┘   IFrameSource, SourceRegistry, VideoReader)
```

---

## 1. Camada `core` — Motor de Leitura e Bufferização

O módulo `aniseek.core` é o coração do pacote. É completamente desacoplado de interfaces gráficas e de backends específicos de decodificação.

### Componentes Principais:

1. **Interface de Fontes (`IFrameSource` em `aniseek.core.interfaces.source`):**
   - Contrato abstrato (`abc.ABC`) que padroniza o acesso a frames:
     - `frame_count -> int`: Total de quadros disponíveis.
     - `fps -> float`: Taxa de quadros por segundo.
     - `seek(frame_id: int) -> None`: Posicionamento arbitrário do cursor.
     - `read() -> tuple[bool, ndarray | None]`: Decodifica e retorna o próximo quadro.
     - `grab() -> bool`: Avanço rápido de cabeçalho sem carga pesada de decodificação.
     - `is_opened() -> bool`: Estado de prontidão da fonte.
     - `release() -> None`: Liberação de descritores e recursos.

2. **Implementações Nativas de Fonte (`aniseek.core.sources`):**
   - **`OpenCVVideoSource`:** Decodificador de arquivos de vídeo baseado em `cv2.VideoCapture`.
   - **`ImageSource`:** Decodificador de sequências de imagens em diretório (`.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`).

3. **Gerenciador de Fontes (`SourceRegistry` em `aniseek.core.sources.registry`):**
   - Singleton global (`source_registry`) que define as classes padrão para vídeo e imagens.
   - Fornece o context manager `source_registry.use(video=..., image=...)` para alternância temporária de backends.
   - Fornece `create_source(path)` para despacho inteligente baseado em diretório ou extensão de arquivo.

4. **Buffers Concorrentes (`VideoBufferRight` e `VideoBufferLeft`):**
   - Operam em threads paralelas em segundo plano utilizando `reader_task`.
   - `VideoBufferRight`: Pré-carrega frames em ordem crescente (`+1`).
   - `VideoBufferLeft`: Calcula blocos anteriores e pré-carrega em ordem decrescente (`-1`).
   - Comunicação via canais thread-safe protegidos por travas (`_Channel`, `Channel1`).

5. **Otimizador `FrameMapper` (`aniseek.core.frame_mapper`):**
   - Mantém uma lista ordenada em C (`array('l')`) de IDs de frames válidos.
   - Permite buscas binárias instantâneas via `bisect`.
   - Decide dinamicamente entre leitura completa (`read()`) e avanço rápido de cabeçalho (`grab()`).

6. **Leitores de Vídeo (`aniseek.core.video_reader`):**
   - `ForwardReader`: Leitura sequencial direta com buffer único.
   - `ReverseReader`: Leitura sequencial reversa com buffer único.
   - `VideoReader`: Leitor bidirecional com duplo buffer cooperativo (`servant` / `master`) e inversão de ponteiros com latência zero.
   - Todos os construtores aceitam estritamente instâncias de `IFrameSource` ou utilizam o construtor inteligente `@classmethod from_default(path)`.

---

## 2. Camada `editing` — Edição, Seções e Histórico

O módulo `aniseek.editing` gerencia o ciclo de vida de cortes, histórico de desfazer/refazer e controle de reprodução.

### Componentes Principais:

1. **Gestão de Seções (`VideoSection`, `SectionManager`):**
   - Modela trechos contínuos de vídeo, frames removidos e listas negras de exclusão.
   - Suporta divisão (`split`), junção (`join`) e remoção de seções.
   - Suporta importação e exportação de e para dicionários serializados (`to_dict` / `from_dict`).

2. **Lixeira de Frames (`Trash`):**
   - Buffer dedicado que retém frames descartados para permitir restauração (`undo`).

3. **Padrão Memento (`Caretaker`, `SectionOriginator`, `TrashOriginator`):**
   - Captura e restaura o estado de seções e da lixeira sem violar o encapsulamento.

4. **Controle de Reprodução (`PlayerControl`):**
   - Coordena direção (`proceed` / `rewind`), pausas e controle de atraso temporal (`delay`).

5. **Gerenciador Central (`VideoManager`):**
   - Orquestra os componentes do `core` (buffers, sources, mapping) com os componentes de `editing` (seções, trash, player).
   - Suporta injeção de fontes (`load_source`, `open_source`) e resolução flexível de seções (`resolve_section_manager`).

6. **Persistência Explícita (`SectionService`):**
   - O salvamento é estritamente explícito via `.save_section_manager()`. Não há gravação automática em disco na abertura ou ao fechar.

---

## 3. Camada `view` — Interface, Comandos e Visualização

O módulo `aniseek.view` contém o visualizador interativo em OpenCV, a captura de teclado e a arquitetura de comandos desacoplados.

### Componentes Principais:

1. **`FrameViewer` (`aniseek.view.video`):**
   - Visualizador de alto nível em janela nativa OpenCV (`namedWindow`, `imshow`).
   - Loop governado pelo método não-bloqueante `while not viewer.quit():`.
   - Permite injeção de seções (`dict`, `.json`, `SectionManager`), atalhos personalizados (`shortcuts={...}`) e vinculação estrita de comandos (`viewer.bind(key, command)`).

2. **Subsistema de Entrada (`aniseek.view.input_handler`):**
   - **`InputHandler`:** Interface base com máscaras de modificadores (`CTRL_BIT = 0x100`, `SHIFT_BIT = 0x200`, `ALT_BIT = 0x400`).
   - **`PynputKeyReader` (Padrão):** Captura eventos via hooks do sistema operacional (`pynput.keyboard.Listener`), interceptando confiavelmente `Ctrl`, `Shift` e `Alt`.
   - **`CV2KeyReader` (Fallback):** Captura eventos via `cv2.waitKeyEx()`.

3. **Mapeamento de Atalhos (`aniseek.view.shortcuts`):**
   - `PYNPUT_SHORTCUTS`: Mapeamento otimizado para teclado de sistema com modificadores `Ctrl` e `Shift`.
   - `CV2_SHORTCUTS`: Mapeamento adaptado para o backend OpenCV com suporte a `Shift` e maiúsculas.

4. **Padrão Command (`aniseek.view.video_command`):**
   - `Invoker`: Despacha comandos associados a teclas ou identificadores.
   - Comandos Concretos: `ProceedCommand`, `RewindCommand`, `PauseCommand`, `RemoveFrameCommand`, `UndoFrameCommand`, `SplitSectionCommand`, `JoinSectionCommand`, `SaveCommand`, etc.
   - **`MacroCommand`:** Implementa o padrão Composite para agrupar e executar sequências ordenadas de múltiplos comandos.
