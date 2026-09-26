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
     - `frame_count -> int`: Total de quadros disponíveis (resolução *lazy* sem overhead no TTFF).
     - `fps -> float`: Taxa de quadros por segundo.
     - `seek(frame_id: int) -> None`: Posicionamento arbitrário do cursor.
     - `read() -> tuple[bool, ndarray | None]`: Decodifica e retorna o próximo quadro.
     - `grab() -> bool`: Avanço rápido de cabeçalho sem carga pesada de decodificação.
     - `is_opened() -> bool`: Estado de prontidão da fonte.
     - `release() -> None`: Liberação de descritores e recursos.

2. **Interface de Buffers (`IVideoBuffer` em `aniseek.core.interfaces.buffer`):**
   - Contrato abstrato (`abc.ABC`) formalizado que rege o ciclo de vida dos buffers concorrentes:
     - `start() -> None`: Inicia a thread de decodificação e bufferização assíncrona.
     - `stop() -> None`: Sinaliza interrupção e encerra a thread limpa e deterministicamente.
     - `clear() -> None`: Esvazia a fila interna de frames.
     - `put(frame_id: int, frame: ndarray | None) -> None`: Alimenta o buffer com frame em memória.
     - `get() -> tuple[int, ndarray | None]`: Consome o próximo frame na direção do buffer.
     - `__getitem__(index: int) -> tuple[int, ndarray | None]`: Acesso posicional determinístico aos frames buffered.
     - `fps -> float`: Taxa temporal de quadros do buffer.
     - Fornece `IFakeVideoBuffer` como classe base de dublê para testes unitários rápidos.

3. **Implementações Nativas de Fonte (`aniseek.core.sources`):**
   - **`OpenCVVideoSource`:** Decodificador de vídeos via OpenCV com TTFF instantâneo (*lazy*) e busca binária $O(\log N)$ tolerante a frames corrompidos.
   - **`ImageSource`:** Decodificador de sequências de imagens em diretório (`.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`).

4. **Gerenciador de Fontes (`SourceRegistry` em `aniseek.core.sources.registry`):**
   - Singleton global (`source_registry`) que define as classes padrão para vídeo e imagens.
   - Fornece o context manager `source_registry.use(video=..., image=...)` para alternância temporária de backends.
   - Fornece `create_source(path)` para despacho inteligente baseado em diretório ou extensão de arquivo.

5. **Buffers Concorrentes (`VideoBufferRight` e `VideoBufferLeft`):**
   - Operam em threads paralelas em segundo plano utilizando `reader_task`.
   - `VideoBufferRight`: Pré-carrega frames em ordem crescente (`+1`).
   - `VideoBufferLeft`: Calcula blocos anteriores e pré-carrega em ordem decrescente (`-1`).
   - Comunicação via canais thread-safe protegidos por travas (`_Channel`, `Channel1`).

6. **Otimizador `FrameMapper` (`aniseek.core.frame_mapper`):**
   - Mantém uma lista ordenada em C (`array('l')`) de IDs de frames válidos.
   - Permite buscas binárias instantâneas via `bisect`.
   - Decide dinamicamente entre leitura completa (`read()`) e avanço rápido de cabeçalho (`grab()`).

7. **Leitores de Vídeo (`aniseek.core.video_reader`):**
   - `ForwardReader`: Leitura sequencial direta com buffer único.
   - `ReverseReader`: Leitura sequencial reversa com buffer único.
   - `VideoReader`: Leitor bidirecional com duplo buffer cooperativo (`servant` / `master`) e inversão de ponteiros com latência zero. Dimensiona os buffers adaptativamente conforme o FPS da fonte, eliminando starvation e atingindo **500+ FPS** em sentido reverso.
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

4. **Padrão Command e Ciclo de Vida (`aniseek.view.video_command`):**
   - Suporte nativo ao ciclo de vida via `ButtonState.PRESS`, `ButtonState.HOLD` e `ButtonState.RELEASE`.
   - Composição de `HoldTimer` para permitir avanço de 1 frame único em clique curto e aceleração contínua sem saltos acidentais ao manter pressionado.
   - `Invoker`: Despacha comandos associados a teclas ou identificadores.
   - Comandos Concretos: `ProceedCommand`, `RewindCommand`, `PauseCommand`, `RemoveFrameCommand`, `UndoFrameCommand`, `SplitSectionCommand`, `JoinSectionCommand`, `SaveCommand`, etc.
   - **`MacroCommand`:** Implementa o padrão Composite para agrupar e executar sequências ordenadas de múltiplos comandos.

---

## 4. Configuração Global Centralizada (`aniseek.config`)

O `aniseek` centraliza parâmetros de ambiente e execução no singleton `config` (`Config`), acessível diretamente no namespace raiz da biblioteca:

```python
from aniseek import config
```

### Propriedades Gerenciadas:
- **`buffersize` (`int`, padrão `30`):** Capacidade da janela deslizante do buffer de vídeo.
- **`image_fps` (`float`, padrão `24.0`):** Taxa de quadros assumida na leitura de sequências de imagens quando não informada.
- **`hold_delay` (`float`, padrão `0.15`):** Tolerância de tempo (em segundos) antes de iniciar repetição de tecla mantida pressionada.
- **`hold_interval` (`float`, padrão `1.0 / 30`):** Intervalo entre disparos repetidos de teclas mantidas pressionadas (taxa de repetição).
- **`log_level` (`str`, padrão `"INFO"`):** Nível de corte do Loguru (`"TRACE"`, `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`, `"CRITICAL"`).
- **`video_extensions` / `image_extensions`:** Tuplas normalizadas de extensões reconhecidas pelo `SourceRegistry`.

### Gerenciamento de Contexto e Reset:
- `config(chave=valor)`: Gerenciador de contexto que aplica parâmetros temporariamente em bloco `with` e restaura o estado anterior ao sair (mesmo em caso de exceção).
- `config.reset()`: Restaura instantaneamente todos os valores para os padrões de fábrica.

---

## 5. Política de Logs e Proteção do Hot-Path

Para garantir reprodução contínua e sem engasgos a **60+ FPS**, o `aniseek` adota uma política rigorosa de isolamento de I/O de console:

### Taxonomia de Níveis:
1. **`TRACE` (Hot-Path):** Operações que ocorrem a cada frame lido, enfileirado ou exibido (`Displaying frame`, `Putting frame into vbuffer`). Avaliado de forma *lazy* via `logger.opt(lazy=True).trace(...)` para **custo zero de CPU** quando desativado.
2. **`DEBUG` (Eventos do Sistema):** Transições de estado esporádicas (mudança de sentido `proceed`/`rewind`, inicialização de threads, cálculo de janelas de buffer).
3. **`INFO` (Marcos do Usuário):** Ações intencionais de alto nível (salvamento de seções, união de seções, alteração de velocidade de reprodução).
4. **`WARNING` (Ações Inválidas Rejeitadas):** Comandos bloqueados por estado inconsistente (tentativa de corte em modo preview, divisão no primeiro/último frame).
5. **`ERROR` / `CRITICAL`:** Falhas de E/S ou quebras irrecuperáveis de sistema.

O controle dinâmico do nível é realizado via `config.log_level = "NIVEL"`, sem necessidade de reiniciar a aplicação ou reconfigurar handlers manualmente.
