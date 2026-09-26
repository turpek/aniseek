# GEMINI — aniseek

> **Projeto:** `aniseek` — Motor de leitura e manipulação de frames de vídeo com duplo buffer concorrente e navegação bidirecional instantânea.

---

## 1. Visão Geral

- **Descrição curta:** Biblioteca em Python focada na leitura e navegação precisa frame a frame de vídeos. Utiliza uma arquitetura de buffers concorrentes em threads paralelas (`VideoBufferRight` e `VideoBufferLeft`) para possibilitar avanço (`proceed`) e retrocesso (`rewind`) instantâneos com cache cooperativo em memória.
- **Motivação:** Aplicações de visão computacional, ferramentas de rotulagem e projetos de processamento gráfico (como o [`anifuse`](https://github.com/turpek/anifuse)) exigem leitura temporal de frames para frente e para trás, além de fatiamento (`start`, `end`, `step`) e listas arbitrárias de frames sem lentidão de decodificação.
- **Papel na Arquitetura:**
  - **`aniseek.core` (Motor de Leitura):** Fornece os leitores especializados (`ForwardReader`, `ReverseReader`) e o leitor bidirecional (`VideoReader`), estruturas de mapeamento (`FrameMapper`), buffers concorrentes (`VideoBufferRight`, `VideoBufferLeft`) e interface de backend de decodificação (`IFrameSource`, `OpenCVVideoSource`).
  - **`aniseek.editing` (Edição e Gerenciamento):** Gestão de seções (`SectionManager`), histórico (`memento`), lixeira de descarte (`Trash`), controle de playlist (`Playlist`) e reprodutor (`PlayerControl`).
  - **`aniseek.view` (Interface e Comandos):** Apresentação visual e interação via OpenCV GUI (`VideoCon`), mapeamento de comandos (`video_command`) e controle de aplicação (`VideoController`).

---

## 2. Escopo e Recursos Principais

### O que o projeto FAZ (Core Features):
- **Leitura Direta Otimizada (`ForwardReader`):** Leitura frame a frame em ordem crescente com buffer único concorrente.
- **Leitura Reversa Otimizada (`ReverseReader`):** Leitura frame a frame em ordem decrescente com buffer único concorrente.
- **Leitura Bidirecional Cooperativa (`VideoReader`):** Alternância instantânea de sentido (`proceed` / `rewind`) utilizando cache em memória entre buffers.
- **Desacoplamento de Backend (`IFrameSource`):** Interface abstrata para decodificação de frames (com implementação inicial `OpenCVVideoSource`).
- **Fatiamento Flexível (`slice`):** Suporte nativo a `start`, `end` e `step`, pulando frames intermediários via `grab()` sem decodificação pesada.
- **Amostragem Arbitrária (`frames: list[int]`):** Suporte a passar listas explícitas de IDs de frames para o `FrameMapper`.
- **Indicação de Término de Task (`is_task_complete`):** Propriedade conveniente para saber quando a leitura do slice ou lote terminou.

### O que o projeto NÃO faz:
- Não impõe dependência de interface gráfica no Core (desacoplado de janelas ou OpenCV GUI).
- Não grava nem codifica arquivos de vídeo (focado estritamente em leitura e decodificação eficiente).

---

## 3. Stack Tecnológica e Dependências

- **Linguagem:** Python 3.12+ (gerenciado via `uv`).
- **Dependências Principais:**
  - `opencv-python>=4.10.0`
  - `numpy>=2.0.0`
  - `loguru>=0.7.3`
  - `pathlib3x>=2.0.3`
- **Ferramentas de Desenvolvimento e Qualidade:**
  - `autopep8>=2.3.2`, `ruff>=0.9.0`, `mypy>=1.10.0`, `pytest>=9.0.0`, `pytest-cov>=5.0.0`, `ipdb>=0.13.13`.

---

## 4. Estrutura Arquitetural de Pastas

```text
aniseek/
├── src/
│   └── aniseek/
│       ├── core/                      # Motor de leitura e bufferização temporal
│       │   ├── interfaces/            # IFrameSource, IVideoBuffer
│       │   ├── sources/               # OpenCVVideoSource (e futuros backends)
│       │   ├── buffer.py              # Buffer base de fila dupla
│       │   ├── buffer_right.py        # Buffer concorrente para avanço (+1)
│       │   ├── buffer_left.py         # Buffer concorrente para retrocesso (-1)
│       │   ├── channel.py             # Primitiva de sincronização entre threads
│       │   ├── frame_mapper.py        # Mapeamento e indexação de frames com bisect
│       │   ├── reader.py              # Thread de leitura com IFrameSource (read vs grab)
│       │   └── video_reader.py        # BaseVideoReader, ForwardReader, ReverseReader, VideoReader
│       │
│       ├── editing/                   # Lógica de edição, cortes, histórico e gerenciamento
│       │   ├── interfaces/            # IMemento, IOriginator, ISectionAdapter, IDataReader...
│       │   ├── adapter.py             # SectionSplitProcess, FakeSectionAdapter...
│       │   ├── manager.py             # VideoManager (orquestra core + editing)
│       │   ├── memento.py             # Caretaker, SectionOriginator, TrashOriginator
│       │   ├── player_control.py      # PlayerControl (coordena avanço/recuo e delay)
│       │   ├── playlist.py            # Playlist de arquivos de mídia
│       │   ├── readers.py             # JSONReader, JSONWriter
│       │   ├── section.py             # VideoSection, SectionManager, SectionWrapper
│       │   ├── section_service.py     # SectionService para persistência de seções
│       │   ├── template.py            # TemplateFactory
│       │   ├── trash.py               # Lixeira de frames descartados
│       │   └── utils.py               # FrameMementoHandler, FrameStack, VideoInfo...
│       │
│       ├── view/                      # Interface gráfica (OpenCV GUI) e comandos
│       │   ├── interfaces/            # Command
│       │   ├── video.py               # VideoCon (janela OpenCV, imshow, loop)
│       │   ├── video_command.py       # Invoker e comandos de controle
│       │   └── video_controller.py    # VideoController (conecta view ao VideoManager)
│       │
│       ├── custom_exceptions.py       # Exceções compartilhadas do pacote
│       ├── time_utils.py              # Utilitários temporais (timestamp <-> frames)
│       └── __init__.py                # Fachada pública reexportando leitores e utilitários
│
├── tests/                             # Suíte completa de testes unitários e de integração
├── docs/                              # Documentação técnica detalhada
└── scratch/                           # Scripts temporários e diagnósticos
```

---

## 5. Testes, Qualidade e Regras de Interação com a IA (GEMINI)

- **Desenvolvimento Orientado a Testes (TDD):** A suíte de testes (`pytest`) é a fonte de verdade absoluta para validação de buffers e leitores. A IA deve propor e executar cenários de teste antes e durante refatorações.
- **Qualidade e Formatação Automática (ruff check & autopep8):** Sempre que a IA for autorizada a alterar, criar ou refatorar qualquer arquivo Python (`.py`), DEVE obrigatoriamente executar lint com auto-fix e formatação via autopep8 no diretório afetado:
  ```bash
  uv run ruff check <diretório> --fix && uv run autopep8 --in-place --recursive --max-line-length 89 --ignore E501,E402,W503,W504 <diretório>
  ```
- **Arquivos Temporários e Scratch:** Scripts de teste temporários ou de debug DEVEM ser gerados em `scratch/` ou `scripts/`, nunca na raiz do projeto.
- **Imports Estritamente no Top-Level:** Todo e qualquer `import` ou `from ... import ...` DEVE residir obrigatoriamente no topo do arquivo (`top-level`).
  - É **estritamente proibido** colocar declarações de `import` dentro de funções, métodos ou blocos de controle de fluxo (prevenindo violações da regra `PLC0415` do Ruff).
  - Para anotações de tipo que poderiam introduzir dependências circulares em tempo de execução, utilize obrigatoriamente o bloco `if TYPE_CHECKING:` no topo do arquivo acompanhado de `from __future__ import annotations`.

### 5.1. Diretrizes Estritas para Criação de Testes (Pytest):
1. **Docstring Concisa:** Exatamente 1 linha limpa na primeira linha de cada função de teste.
2. **Zero Lógica Condicional (`if/else`):** Proibido `if/else` ou ternários no corpo do teste. O fluxo deve ser estritamente linear: *Arrange -> Act -> Assert*.
3. **Parametrização Declarativa (`@pytest.mark.parametrize`):** Variações de entrada e expectativa devem ser expressas como dados na tabela de parâmetros com IDs descritivos (`id="..."`).
4. **Helpers de Dados Dedicados:** Usar mocks/vídeos sintéticos (`MyVideoCapture`) para garantir determinismo e alta velocidade na suíte.
5. **Asserts Coesos:** Múltiplos asserts são permitidos somente quando pertencerem ao mesmo objeto sob teste e validarem facetas complementares do mesmo resultado.
6. **Casos de Borda Isolados:** Casos específicos (ex: sem frames, 1 frame, buffersize reduzido) devem ser testes dedicados.

### 5.2. Padrão de Commits (Conventional Commits em Português):
- **Estrutura básica:**
  ```text
  tipo: descrição curta no imperativo

  [corpo opcional explicando o porquê]
  ```
- **Tipos mais comuns:**
  - `feat`: nova funcionalidade
  - `fix`: correção de bug
  - `perf`: melhoria de performance
  - `docs`: documentação
  - `style`: formatação (sem mudar comportamento)
  - `refactor`: refatoração sem alterar funcionalidade
  - `test`: testes
  - `chore`: tarefas de manutenção/configuração

### 5.2.1. Separação Estrita de Commits (Produção vs. Dev-Only):
- **Regra Fundamental:** É estritamente proibido misturar arquivos de produção com arquivos exclusivos de desenvolvimento em um mesmo commit.
- **Commits de Produção (Core / Release):**
  - **Arquivos:** `src/`, `tests/`, `README.md`, `pyproject.toml`, `uv.lock`, `Makefile`, `assets/`.
  - **Prefixos:** `feat:`, `fix:`, `refactor:`, `perf:`, `test:`, `style:`.
  - **Objetivo:** Manter a branch `main` e o changelog automático do `make sync-main` limpos e rastreáveis.
- **Commits de Desenvolvimento (Ambiente / Metadados / Benchmarks):**
  - **Arquivos:** `GEMINI.md`, `docs/`, `benchmarks/`, `planos/`, `scratch/`, `scripts/`.
  - **Prefixos:** `docs(dev):`, `bench:`, `chore(dev):`, `docs(plano):`.

---

## 6. Fluxo de Git e Sincronização Multi-PC (`dev` <-> `main`)

- **Branch `dev` (Ambiente de Trabalho Ativo):** Contém todo o repositório rastreado (`GEMINI.md`, `docs/`, planos, código e testes) para sincronização perfeita entre múltiplos computadores.
  - Enviar alterações de dev: `make push-dev` (ou `git push origin dev`).
  - Puxar no outro computador: `make pull-dev` (ou `git pull origin dev`).
- **Branch `main` (Produção e Distribuição Limpa):** Mantém estritamente os arquivos essenciais de código, testes, `README.md` e build, com histórico semântico atômico (cherry-pick de cada commit de produção) gerado automaticamente pelo Makefile.
  - Sincronizar código limpo para a main: `make sync-main`.
  - Publicar a main no GitHub: `make push-main`.

---

## 7. Memória de Arquitetura do Core (Decisões Consolidadas)

### 7.1. Sistema de Duplo Buffer (`VideoBufferRight` & `VideoBufferLeft`)
- Operam em threads independentes consumindo frames via `reader_task`.
- O `VideoBufferRight` enche a fila para frente (`+1`).
- O `VideoBufferLeft` calcula o bloco anterior e enche a fila de modo que o `get()` retorne em ordem decrescente (`-1`).

### 7.2. Cooperação Servant / Master para Troca de Direção
- O buffer ativo (`servant`) entrega os frames ao consumidor.
- A cada frame lido, o buffer passivo (`master`) recebe o frame em memória via `.put(frame_id, frame)`.
- A troca de direção (`proceed` / `rewind`) consiste na inversão de ponteiros (`self.servant, self.master = self.master, self.servant`), garantindo troca de marcha com latência zero e sem redecodificação.

### 7.3. Otimização por `FrameMapper`
- O `FrameMapper` indexa os frames válidos em um array ordenado em C (`array('l')`).
- Na leitura em background: se `frame_id in mapping_frames`, executa `cap.read()`; se não, executa `cap.grab()` (avanço rápido sem carga de CPU).

### 7.4. Desacoplamento de Backend de Decodificação (`IFrameSource`)
- A decodificação e extração de frames é isolada pela interface abstrata `IFrameSource`.
- `OpenCVVideoSource` é a implementação padrão baseada em OpenCV (`cv2.VideoCapture`).
- O core (`reader_task`, buffers, `VideoReader`) consome estritamente o contrato da interface (`frame_count`, `fps`, `seek`, `read`, `grab`, `is_opened`, `release`), eliminando totalmente `hasattr`/`getattr` dinâmicos ou dependência direta de `cv2` no motor de leitura.

### 7.5. Controle de Repetição de Teclas (`HoldTimer`) e Ciclo de Vida (`ButtonState`)
- **Ciclo de Vida:** O subsistema de input emite eventos com `ButtonState` (`PRESS`, `HOLD`, `RELEASE`).
- **Composição de `HoldTimer`:** Os comandos com suporte a repetição contínua compõem internamente uma instância de `HoldTimer(delay, interval)`:
  - `on_press()` executa imediatamente o primeiro frame e arma o timer.
  - Se soltar antes do `hold_delay` (padrão 150ms), o `on_release()` cancela o timer, garantindo **precisão de exatamente 1 frame** por clique.
  - Se mantido pressionado, `on_hold()` dispara repetidamente a cada `hold_interval` (padrão 30 FPS).
- **Assinatura Pura:** `FrameViewer.set_commands` permanece estritamente puro, lendo os parâmetros de temporização diretamente do singleton `config`.

### 7.6. Singleton Centralizado de Configuração (`config`)
- Módulo `aniseek.config` expõe a instância `config` com tipagem estrita e validação para: `buffersize`, `image_fps`, `hold_delay`, `hold_interval`, `log_level`, `video_extensions` e `image_extensions`.
- Suporte nativo a context manager com reversão automática: `with config(hold_delay=0.2, log_level="DEBUG"): ...`.
- Restauração de padrões de fábrica via `config.reset()`.

### 7.7. Arquitetura de Logs e Proteção do Hot-Path
- **Zero I/O no Hot-Path:** Logs a cada frame lido, decodificado ou exibido são estritamente proibidos em modo normal de produção para garantir 60+ FPS sem engasgos de console.
- **Micro-Eventos em `TRACE`:** Detalhes de enfileiramento de frames e inspeção de filas de buffers usam `logger.trace` com formatação *lazy* (`logger.opt(lazy=True).trace(...)`), resultando em **zero alocações de memória e zero custo de CPU** quando o nível `TRACE` está desativado.
- **Padronização em Inglês:** 100% das mensagens de log em todo o pacote utilizam o padrão técnico em inglês (`TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`).
- **Controle Dinâmico:** Nível ativo gerenciado dinamicamente via `config.log_level`.

