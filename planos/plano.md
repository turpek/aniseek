# Master Plan: Aniseek

Este documento centraliza todos os objetivos arquiteturais, otimizações estruturais, correções de bugs e o progresso do desenvolvimento do motor de leitura e manipulação de frames (`aniseek`).

---

## 📋 Lista de Tarefas (Status Atual)

- [x] 1. Desacoplamento do backend de decodificação via interface `IFrameSource` (`OpenCVVideoSource`).
- [x] 2. Otimização de busca binária e pulos leves de cabeçalho (`grab`) com `FrameMapper`.
- [x] 3. Sistema cooperativo de duplo buffer concorrente (`VideoBufferRight` & `VideoBufferLeft`).
- [x] 4. Módulo de input desacoplado com `PynputKeyReader` (suporte a `Ctrl`), `CV2KeyReader` (fallback) e atalhos padronizados.
- [x] 5. **Bugfix no `SectionManager.remove_section` / `VideoManager.create`:** Falha `AttributeError: 'NoneType' object has no attribute '_calculate_mapping'` ao remover seção quando pausado (`Ctrl + x`).
- [x] 6. **Refatoração de Usabilidade das Seções & Modo Preview da Montagem Final (UX / Funcional).**
- [x] 7. **Refatoração Arquitetural e Manutenibilidade do Subsistema de Seções (Clean Code / Arquitetura Interna).**
- [ ] 8. **Otimização de Performance e Taxa de Leitura do Core (TTFF, Leitura Reversa e Benchmark).** [PRIORIDADE IMEDIATA]
- [ ] 9. **Tipagem Estrita e Saneamento do Mypy (`mypy src`).**
- [ ] 10. **Auditoria e Resolução dos 8 Testes Ignorados (`SKIPPED`).**
- [ ] 11. **Limpeza de Código Morto e Estruturas Obsoletas em `editing` (`SimpleStack`).**
- [ ] 12. **Melhorias Funcionais no `FrameViewer` (Navegação Go-To & OSD/HUD).**

---

## 🏗 Detalhamento Arquitetural

---

### Task 5: Bugfix no `SectionManager.remove_section` e `load_mementos_frames` (`AttributeError: 'NoneType'`)

#### 1. Relato do Problema e Reprodução
Ao executar o player interativo no vídeo real, pausar a reprodução utilizando a tecla `espaço` (modo de edição / delay ativo) e pressionar o atalho de remoção de seção (**`Ctrl + x`**), o programa encerra abruptamente com o seguinte traceback:

```text
2026-09-20 03:00:09.468 | INFO     | aniseek.view.video:show:110 - exibindo o frame de id 39
2026-09-20 03:00:12.634 | DEBUG    | aniseek.core.buffer:set:168 - setting synchronization and task control variables with threads
2026-09-20 03:00:12.634 | DEBUG    | aniseek.core.buffer:task_is_done:218 - setting task_is_done to False
2026-09-20 03:00:12.634 | DEBUG    | aniseek.core.buffer:clear:182 - unsetting synchronization and task control variables with threads
2026-09-20 03:00:12.634 | DEBUG    | aniseek.core.buffer:task_is_done:218 - setting task_is_done to True
2026-09-20 03:00:12.639 | DEBUG    | aniseek.core.buffer:set:168 - setting synchronization and task control variables with threads
2026-09-20 03:00:12.639 | DEBUG    | aniseek.core.buffer:task_is_done:218 - setting task_is_done to False
2026-09-20 03:00:12.639 | DEBUG    | aniseek.core.buffer:clear:182 - unsetting synchronization and task control variables with threads
2026-09-20 03:00:12.639 | DEBUG    | aniseek.core.buffer:task_is_done:218 - setting task_is_done to True
2026-09-20 03:00:12.639 | DEBUG    | aniseek.core.buffer:set:168 - setting synchronization and task control variables with threads
2026-09-20 03:00:12.639 | DEBUG    | aniseek.core.buffer:task_is_done:218 - setting task_is_done to False
2026-09-20 03:00:12.639 | DEBUG    | aniseek.core.buffer:clear:182 - unsetting synchronization and task control variables with threads
2026-09-20 03:00:12.639 | DEBUG    | aniseek.core.buffer:task_is_done:218 - setting task_is_done to True
Traceback (most recent call last):
  File "/home/gui/python/aniseek/scratch/test_real_video.py", line 36, in <module>
    video.show(ret, frame)
  File "/home/gui/python/aniseek/src/aniseek/view/video.py", line 113, in show
    return self.control(self.__key_reader.get_code(delay))
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/gui/python/aniseek/src/aniseek/view/video.py", line 139, in control
    self.command.executor_command(shortcut_key)
  File "/home/gui/python/aniseek/src/aniseek/view/video_command.py", line 158, in executor_command
    self.commands[key].executor()
  File "/home/gui/python/aniseek/src/aniseek/view/video_command.py", line 122, in executor
    self.receiver.remove_section()
  File "/home/gui/python/aniseek/src/aniseek/view/video_controller.py", line 150, in remove_section
    self.video_manager.create(self.__section_manager)
  File "/home/gui/python/aniseek/src/aniseek/editing/manager.py", line 79, in create
    section_manager.load_mementos_frames(self.trash)
  File "/home/gui/python/aniseek/src/aniseek/editing/section.py", line 196, in load_mementos_frames
    self._right.top._calculate_mapping(self._right.top.get_trash())
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'NoneType' object has no attribute '_calculate_mapping'
```

---

#### 2. Rastreamento e Causa Raiz

A falha decorre da seguinte sequência de operações:

1. **Disparo do Comando:**
   O atalho `Ctrl + x` executa o `RemoveSectionCommand`, chamando `VideoController.remove_section()`.
2. **Remoção da Seção na Pilha:**
   `VideoController.remove_section()` delega para `self.__section_manager.remove_section(self.video_manager.trash)`.
   * No `SectionManager.remove_section()`:
     ```python
     self.store_mementos_frames(trash)
     self.__remove_section(self._right.pop())
     self.__check_right()
     ```
   * Se o vídeo possuir apenas **uma única seção** (ou se a seção removida for a última restante), `self._right.pop()` esvazia a pilha `self._right`.
   * O método `self.__check_right()` tenta repor uma seção a partir de `self._left`:
     ```python
     if self._right.empty() and not self._left.empty():
         self._prev_section()
     ```
     Como `self._left` também está vazia, a pilha `self._right` permanece vazia (`self._right.empty() == True`).
3. **Recreação do VideoManager:**
   Imediatamente após a remoção, `VideoController.remove_section()` executa:
   ```python
   self.video_manager.create(self.__section_manager)
   ```
   No `VideoManager.create()`:
   ```python
   section_manager.load_mementos_frames(self.trash)
   ```
4. **Desreferenciamento de `None`:**
   Em `SectionManager.load_mementos_frames()`:
   ```python
   self._right.top._calculate_mapping(self._right.top.get_trash())
   ```
   Na implementação de `SimpleStack.top` (`src/aniseek/editing/utils.py`):
   ```python
   @property
   def top(self):
       if not self.empty():
           return self.__stack[-1]
   ```
   Como a pilha está vazia, `self._right.top` avalia para `None`. A chamada `None._calculate_mapping(...)` resulta no `AttributeError`.

---

#### 3. Decisões de Projeto e Regras de Negócio

1. **Permissão de Remoção da Última Seção:**
   * **Abordagem Proibitiva (Recomendada):** Não permitir a remoção da última seção do vídeo (um vídeo deve ter no mínimo uma seção ativa). Caso o usuário tente remover com apenas 1 seção restante, o método retorna `False` e emite um log informativo.
2. **Guard Clauses Defensivas em `SectionManager`:**
   * Métodos como `load_mementos_frames` e `store_mementos_frames` devem checar se `self._right.top is not None` antes de tentar calcular mappings ou carregar mementos de frames.

---

#### 4. Escopo da Investigação e Plano de Ação

- [ ] **Reprodução em Teste Unitário:**
  - Criar teste dedicado em `tests/test_section.py` simulando `remove_section()` com apenas 1 seção na pilha.
- [ ] **Implementação das Guard Clauses:**
  - Adicionar validação em `SectionManager.load_mementos_frames()` e `store_mementos_frames()` para lidar de forma segura com `self._right.empty()`.
- [ ] **Aplicação da Regra de Bloqueio da Última Seção:**
  - Bloquear remoção quando `len == 1` em `SectionManager.remove_section()`.
- [ ] **Validação com o Vídeo Real:**
  - Executar o script `scratch/test_real_video.py`, pausar com a tecla `espaço` e acionar `Ctrl + x`, garantindo encerramento sem crash.

---

### Task 6: Refatoração de Usabilidade das Seções & Modo Preview da Montagem Final (UX / Funcional)

Esta tarefa foca estritamente na experiência do usuário (UX), ergonomia dos atalhos e comportamento previsível do player durante a edição.

#### 📋 Sub-lista de Objetivos da Tarefa 6

- [x] **6.1. Dividir Seção (`Split — Ctrl + s`) Sensível ao Sentido do Buffer:**
  - Aterrissar o cursor no sentido do movimento (`proceed` $\rightarrow$ início da seção da direita; `rewind` $\rightarrow$ fim da seção da esquerda).
  - Bloquear divisão inválida nos limites extremos (`frame_id == start` ou `frame_id == end - 1`) com feedback amigável.
- [x] **6.2. Juntar Seções (`Join — Ctrl + j`) Contextual e Bidirecional:**
  - Regra de ponta automática (primeira junta com próxima; última junta com anterior).
  - Regra de meio automática orientada pelo sentido da reprodução (`proceed` $\rightarrow$ direita; `rewind` $\rightarrow$ esquerda).
  - Operação determinística e sem timers.
- [x] **6.3. Navegação entre Seções (`Next / Prev — Ctrl + d / Ctrl + a`) no Frame Mais Próximo:**
  - `Ctrl + d`: Aterrissa no início da próxima seção (`start`).
  - `Ctrl + a`: Aterrissa no fim da seção anterior (`end - 1`).
  - Atalhos universais `Home` e `End` para saltar para o início e fim da seção atual.
- [x] **6.4. Feedback Visual Imediato e Correção de Congelamento na Pausa com Espaço:**
  - Chamar `set_read()` em todas as operações de seção para destravar o `no_read()`.
  - Alinhamento do sentido de reprodução (`proceed` / `rewind`) e compensação de offset em navegações e extremos.
  - Atualização dinâmica do título da janela OpenCV (`videoseq - [Seção X/Y | Frames A-B | Frame: C] [>>/<<] (PAUSADO)`).
- [x] **6.5. Modo Preview da Montagem Final (`Rough Cut Preview` — Tecla `v`):**
  - Implementar "lente de visualização" da união de todas as seções ativas (`get_preview_mapping()`), ocultando trechos removidos e lixeira.
  - Preservação estrita de estado: `frame_id`, direção, estado de pausa e velocidade permanecem 100% inalterados ao alternar `v`.
  - Sincronização da seção ativa com a seção do frame atual ao desativar o Preview.

---

#### Detalhamento Técnico da Tarefa 6 (UX)

##### 1. Dividir Seção (`Split — Ctrl + s`) Sensível ao Sentido do Buffer
* Se o usuário estava em **`proceed` (+1)**: o cursor aterrissa no **primeiro frame da seção da direita** (`frame_id + 1`), dando continuidade ao fluxo natural de avanço.
* Se o usuário estava em **`rewind` (-1)**: o cursor aterrissa no **último frame da seção da esquerda** (`frame_id`), permitindo continuar inspecionando para trás.
* **Validação de Limites:** Divisões em `frame_id == start` ou `frame_id == end - 1` são rejeitadas com aviso claro, prevenindo seções de tamanho zero.

##### 2. Juntar Seções (`Join — Ctrl + j`) Contextual e Bidirecional (Sem Timer)
* **Ponta Esquerda (Seção 1):** Junta automaticamente com a próxima seção (direita).
* **Ponta Direita (Última Seção):** Junta automaticamente com a seção anterior (esquerda).
* **Seções Intermediárias:** A direção do player dita a união:
  * Se em `proceed` $\rightarrow$ une com a próxima seção (direita).
  * Se em `rewind` $\rightarrow$ une com a seção anterior (esquerda).
* Sem timers ou menus, oferecendo resposta imediata.

##### 3. Navegação entre Seções (`Next / Prev — Ctrl + d / Ctrl + a`) no Frame Mais Próximo
* **`Ctrl + d` (Próxima):** Salta para o **início** da próxima seção (`start`).
* **`Ctrl + a` (Anterior):** Salta para o **fim** da seção anterior (`end - 1`), mantendo o usuário na fronteira imediata do corte.
* Teclas `Home` (início da seção) e `End` (fim da seção) como atalhos diretos de extremos.

##### 4. Feedback Visual Imediato e Correção de Congelamento na Pausa com Espaço
* Todas as operações de seção invocam `self.__player.set_read()` para liberar o frame durante pause ativo (`delay = 0`).
* `VideoManager.create()` dispara `self.servant.run()`, garantindo que os novos buffers estejam ativos.
* Título da janela atualizado dinamicamente via `cv2.setWindowTitle`:
  ```text
  videoseq - [Seção 2/3 | Frames 534-1200 | Frame: 620] (PAUSADO)
  ```

##### 5. Modo Preview da Montagem Final (`Rough Cut Preview` — Tecla `v`)
* Lente de visualização que projeta a linha do tempo contínua de todas as seções ativas (`_left` + `_right`), ocultando seções deletadas e frames no `Trash`.
* Ao alternar `v`, o `frame_id`, direção, estado de pausa e velocidade permanecem 100% inalterados.
* Ao desativar o Preview em um frame pertencente a outra seção, essa seção torna-se ativa automaticamente.

---

### Task 7: Refatoração Arquitetural e Manutenibilidade do Subsistema de Seções (Clean Code / Arquitetura Interna)

Esta tarefa foca na modernização da arquitetura interna, eliminando acoplamentos artificiais (*over-engineering*), pilhas cegas e o excesso de classes desnecessárias.

#### 📋 Sub-lista de Etapas da Tarefa 7

- [x] **7.1. Simplificação da Entidade Base `VideoSection`:**
  - Construtor direto sem dependência obrigatória de adapters (`start`, `end`, `removed_frames`, `black_list_frames`).
  - Métodos `split(frame_id)` e `join(other)` analíticos e diretos em memória.
  - Métodos de serialização `from_dict(data)` e `to_dict()`.
  - Ordenação determinística de `mapping` via `sorted(frames - removed)`.
  - Eliminação de `ISectionAdapter`, `JSONSectionAdapter`, `FakeSectionAdapter`, `SectionUnionAdapter` e `SectionSplitProcess`.
- [x] **7.2. Modernização do `SectionManager` (Lista com Cursor):**
  - Substituição do modelo de 2 pilhas (`SimpleStack(_left)` e `SimpleStack(_right)`) por `_sections: list[VideoSection]` e `_current_index: int`.
  - Acesso direto $O(1)$ à seção ativa (`current_section`), próxima e anterior.
  - Implementação de `can_next()`, `can_prev()`, `can_join_next()`, `can_join_prev()`.
  - Implementação de `get_preview_mapping()` para montagem contínua.
- [x] **7.3. Simplificação do Histórico de Undo / Memento:**
  - Eliminação da classe `SectionWrapper`.
  - Substituição das 9 classes/interfaces de Memento de seções por uma pilha simples de snapshots/ações (`_undo_stack: deque`).
- [x] **7.4. Simplificação da Persistência JSON:**
  - Consolidação das 8 classes de I/O (`SectionService`, `TemplateFactory`, `SectionManagerProcessFactory`, `JSONSectionSave`, `JSONReader`, `JSONWriter`, etc.) em um módulo coeso de armazenamento (`SectionStorage` ou métodos estáticos em `SectionManager`).
- [x] **7.5. Migração e Limpeza dos Testes Unitários:**
  - Adaptação dos testes de `tests/test_section.py` para a nova API limpa e direta, removendo mocks e adapters obsoletos.

---

#### Detalhamento Técnico da Tarefa 7 (Arquitetura)

##### 1. `VideoSection` Autossuficiente
* Elimina a necessidade de 5 classes auxiliares (`ISectionAdapter`, `JSONSectionAdapter`, `FakeSectionAdapter`, `SectionUnionAdapter`, `SectionSplitProcess`).
* `split(frame_id)` divide diretamente as listas e retorna uma tupla `(VideoSection, VideoSection)`.
* `join(other)` valida a adjacência e retorna uma nova `VideoSection` unificada.

##### 2. `SectionManager` com Cursor
* Elimina a fragilidade do modelo Zipper de duas pilhas, onde a próxima seção fica inacessível sob a seção ativa.
* Com `_sections: list[VideoSection]` e `_current_index: int`, operações como inspecionar a próxima seção, saber a quantidade total ou montar o preview tornam-se operações diretas de lista.

##### 3. Histórico de Desfazer Enxuto
* O `undo` de seções armazena diretamente o estado anterior da lista de seções e do cursor, dispensando a hierarquia complexa de `Originator`, `Caretaker` e `Memento` específicos para seções.

##### 4. Persistência Direta
* Leitura de arquivo `.json` com geração automática de template quando não existir e salvamento atômico sem classes intermediárias de processo ou fábrica.

---

### Task 8: Otimização de Performance e Taxa de Leitura do Core (TTFF, Leitura Reversa e Benchmark)

Esta tarefa foca estritamente em maximizar a taxa de leitura (throughput / FPS) e a responsividade temporal do motor de vídeo, eliminando gargalos reais diagnosticados por benchmark em CPU e I/O.

#### 📋 Sub-lista de Objetivos da Tarefa 8

- [x] **8.1. Abertura Instantânea com Validação Lazy e Busca Binária de Fim de Vídeo (Resiliente a Falhas):**
  - Eliminar o seek forçado até o fim do vídeo no construtor `OpenCVVideoSource.__init__`, reduzindo o TTFF de **~1.611 ms para ~60 ms** (ganho de **26x**).
  - Implementar detecção inteligente ao receber `False`/`None` em `source.read()` durante a leitura.
  - Implementar probe de tolerância de $X$ frames com `grab()` para descartar frames corrompidos pontuais (Caso 3) sem truncar o stream.
  - Se o probe falhar (fim prematuro / metadados inflados — Caso 2), acionar busca binária delimitada em $O(\log N)$ seeks no intervalo `[last_valid, frame_count - 1]` para localizar com precisão matemática o verdadeiro frame final decodificável.
  - Sincronização atômica de `_frame_count`, atualização de limites no `FrameMapper` e finalização limpa da task.
- [x] **8.2. Otimização de Throughput na Leitura Reversa (`VideoBufferLeft` e Readers):**
  - Dimensionamento adaptativo do buffer nos leitores (`ForwardReader`, `ReverseReader`, `VideoReader`) com base no FPS da fonte de vídeo e fator multiplicador $3\times$ para o buffer esquerdo (`VideoBufferLeft`), reduzindo a frequência de seeks e decodificações de Keyframes redundantes.
  - Throughput reverso em 720p saltou de **178 FPS para 514+ FPS** (ganho de quase **$3\times$**), sem alterar a independência e agnoscicidade de `VideoBufferLeft` / `VideoBufferRight`.
- [x] **8.3. Correção de Métricas no Script de Benchmark (`benchmarks/bench_core.py`):**
  - Corrigir a função `bench_memory_gc` para utilizar `gc.get_stats()` em vez de `gc.get_count()`, reportando fielmente os ciclos reais de coleta de lixo.
  - Manter suporte a persistência e comparação de resultados via `--save` e `--compare`.

---

#### Detalhamento Técnico da Tarefa 8 (Performance)

##### 1. Validação Lazy e Busca Binária no `OpenCVVideoSource`
* **Diagnóstico da Causa Raiz:** O método `_validate_frame_count()` executado no `__init__` realizava `cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count - 1)`, forçando o FFmpeg a buscar o último Keyframe do arquivo, decodificar dezenas/centenas de frames intermediários até o fim para verificar `grab()`, e depois rebobinar para `POS_FRAMES = 0`. Esse ciclo custava **1,6 segundos inteiros** na abertura de qualquer vídeo.
* **Abertura em Tempo O(1):** No `__init__`, a fonte aceita inicialmente o `frame_count` fornecido pelos metadados do container, abrindo em **~60 ms**.
* **Tratamento de Anomalias de Fim de Arquivo e Corrupção:**
  Ao receber retorno falso ou frame nulo (`ret == False` ou `frame is None`):
  1. Se `frame_id >= source.frame_count`: Fim natural esperado da mídia (Caso 1).
  2. Se `frame_id < source.frame_count`: Dispara o probe leve de tolerância executando até $X$ avanços rápidos via `grab()`:
     - **Recuperação de Corrupção (Caso 3):** Se algum dos próximos $X$ frames for obtido com sucesso via `grab()`, trata-se de frame corrompido isolado; o cursor avança e a reprodução continua sem truncar o restante do vídeo.
     - **Fim Prematuro do Vídeo (Caso 2):** Se todos os $X$ probes falharem, o vídeo encerrou antes da contagem do cabeçalho.
  3. **Busca Binária Confinada:** Dispara busca binária no intervalo `[last_valid_frame, nominal_frame_count - 1]`. Em apenas $\lceil\log_2(\text{intervalo})\rceil$ passos (tipicamente 3 a 5 seeks), localiza o último frame decodificável exato.
  4. **Propagação de Estado:** Atualiza `self._frame_count = true_end`, notifica o `FrameMapper` para ajustar seus índices e encerra o buffer com `end_task.set()`.

##### 2. Aceleração da Leitura Reversa (`VideoBufferLeft`)
* O leitor reverso opera em blocos de trás para frente. Quando cada bloco é requisitado, o `seek` no OpenCV força o decodificador a encontrar o I-frame anterior mais próximo na tabela de GOP.
* Ao dimensionar as fatias de leitura reversa de forma mais ampla e alinhada à retenção de frames já decodificados no canal, diminui-se o número de seeks por segundo, aproximando o throughput reverso do patamar de 500 FPS.

##### 3. Correção de Medição de Memória no Benchmark
* A função `bench_memory_gc` utilizava `gc.get_count()`, que retorna o número de objetos pequenos rastreados na heap do Python, inflando artificialmente para "341 coletas de GC" um cenário onde ocorreram 0 coletas reais (pois arrays do NumPy são liberados instantaneamente via `Py_DECREF` em C).
* A métrica passa a consultar `gc.get_stats()` para reportar com precisão as coletas de lixo das três gerações.

---

### Task 9: Tipagem Estrita e Saneamento do Mypy (`mypy src`)

Esta tarefa visa atingir conformidade estrita de tipos em 100% do código-fonte do motor (`src/aniseek`), eliminando os 161 erros atualmente apontados pelo `mypy src`.

#### 📋 Sub-lista de Objetivos da Tarefa 9

- [x] **9.1. Contrato Formal da Interface `IVideoBuffer` e `IFrameSource`:**
  - Adicionadas formalmente na interface abstrata `IVideoBuffer` (`src/aniseek/core/interfaces/buffer.py`) as assinaturas completas com tipagem estrita de: `get()`, `put()`, `set()`, `set_frame_id()`, `run()`, `join()`, `join_like()`, `is_task_complete()`, `is_done()`, `do_task()`, `mapper_id()`, `start_frame()`, `end_frame()`, `frame_id`, `buffersize`, `source` e `_buffer: Buffer`.
  - Atualizado `IFakeVideoBuffer` fornecendo stubs concretos para testes.
  - Adicionada propriedade abstrata `@property @abstractmethod def fps(self) -> float` em `IFrameSource` e atualizados os mocks de teste correspondentes.
  - Tipagem polimórfica de `servant` e `master` como `IVideoBuffer` em `VideoReader` e anotação `# type: ignore[arg-type]` na chamada de `put()` no `read()`.
- [ ] **9.2. Saneamento de Tipagem em `PlayerControl` e `VideoReader`:**
  - Tipagem correta da alternância servant/master (`VideoBufferRight` $\leftrightarrow$ `VideoBufferLeft`) utilizando a interface base `IVideoBuffer`.
  - Anotação explícita de variáveis de controle (`__current_frame_id`, `__current_frame: ndarray | None`).
- [ ] **9.3. Conformidade PEP 484 em Assinaturas Opcionais:**
  - Corrigir parâmetros com padrão `None` sem `| None` nas anotações (ex: `labels: list[str | None] | None = None` em `playlist.py` e `frame_ids: list[int] | None = None` em `manager.py`).
  - Anotar explicitamente os atributos de coleção `__right_videos: list[VideoInfo]` e `__left_videos: list[VideoInfo]`.
- [ ] **9.4. Saneamento no Módulo `view` (`VideoController` e `VideoCon`):**
  - Tipagem estrita de referências ao `SectionManager` e `VideoManager` em `VideoController`.
  - Resolução de incompatibilidades de tipo no manuseio de delay e frame format em `VideoCon`.
- [ ] **9.5. Verificação Limpa:**
  - Execução de `uv run mypy src` com 0 erros encontrados.

---

### Task 10: Auditoria e Resolução dos 8 Testes Ignorados (`SKIPPED`)

Esta tarefa tem como objetivo auditar individualmente cada um dos 8 testes pulados na suíte do pytest, garantindo que nenhum teste permaneça esquecido ou ignorado sem justificativa técnica permanente.

#### 📋 Sub-lista de Objetivos da Tarefa 10

- [ ] **10.1. `tests/test_player_control.py:179`** (*"Não lembro o porque, desse teste passar"*):
  - Inspecionar a lógica de teste de delay e fluxo do `PlayerControl`, ajustar para a API corrente e reativar.
- [ ] **10.2. `tests/test_video.py:36` e `tests/test_video.py:43`** (*"deprecado"*):
  - Verificar se referenciam interfaces de janela antigas do OpenCV GUI (`VideoCon`). Atualizar para a API corrente ou remover caso o método testado tenha sido formalmente expurgado.
- [ ] **10.3. `tests/test_video.py:100`** (*"Por enquanto o programa está definido para receber None quando chega ao final"*):
  - Validar contra a nova estratégia de término de vídeo da Task 8 e reativar com a asserção esperada.
- [ ] **10.4. `tests/test_video.py:130`** (*"Fica para depois"*):
  - Analisar o cenário pendente no `VideoCon`, implementar a cobertura e remover o `@pytest.mark.skip`.
- [ ] **10.5. `tests/test_video_buffer_left.py:250` e `tests/test_video_buffer_left.py:423`** (*"pq sim"*):
  - Auditar os fluxos de borda do buffer esquerdo, corrigir o teste e reativar.
- [ ] **10.6. `tests/test_video_buffer_left.py:720`** (*"Verificar como a mudança do __frame_id no set influencia em is_task_complete"*):
  - Validar a relação entre o reset de posição e o estado `is_task_complete`, consolidando a asserção determinística.
- [ ] **10.7. Suíte 100% Verde e 0 Skipped:**
  - Garantir que todos os 895 testes da suíte rodem e passem sem nenhum skip.

---

### Task 11: Limpeza de Código Morto e Estruturas Obsoletas em `editing` (`SimpleStack`)

Esta tarefa elimina resquícios de arquitetura legada que se tornaram obsoletos após a conclusão da Task 7 (modernização do `SectionManager` para lista com cursor).

#### 📋 Sub-lista de Objetivos da Tarefa 11

- [ ] **11.1. Remoção da Classe `SimpleStack`:**
  - Remover a implementação de `SimpleStack` de `src/aniseek/editing/utils.py`.
  - Remover a exportação de `SimpleStack` em `src/aniseek/editing/__init__.py`.
- [ ] **11.2. Remoção da Exceção `SimpleStackError`:**
  - Remover a classe `SimpleStackError` de `src/aniseek/custom_exceptions.py`.
- [ ] **11.3. Limpeza dos Testes Unitários de `SimpleStack`:**
  - Remover os 10 testes dedicados em `tests/test_utils.py` que testavam exclusivamente a pilha obsoleta.
- [ ] **11.4. Validação de Regressão:**
  - Confirmar que nenhum outro módulo ou teste do projeto faz uso de `SimpleStack`.

---

### Task 12: Melhorias Funcionais no `FrameViewer` (Navegação Go-To & OSD/HUD)

Esta tarefa agrega recursos de usabilidade e visualização profissional ao player interativo do `aniseek` (`VideoCon` / `VideoController`).

#### 📋 Sub-lista de Objetivos da Tarefa 12

- [ ] **12.1. Navegação Direta (Go-To Frame / Timecode — Atalho `g`):**
  - Implementar comando de salto instantâneo para um frame específico (`frame_id`) ou timecode formatado (`HH:MM:SS:FF`).
  - Reposicionar os buffers concorrentes suavemente preservando a direção ativa de reprodução.
- [ ] **12.2. OSD / HUD Overlay Dinâmico (Atalho `h` ou `o`):**
  - Implementar sobreposição visual leve diretamente no frame renderizado (ou título expandido):
    - Taxa real de FPS de decodificação vs. FPS nominal.
    - Ocupação percentual dos buffers esquerdo e direito.
    - Timecode atual e duração total.
    - Estado da seção (Seção X/Y, modo Preview ativo/inativo).
  - Opção de alternar a visibilidade do overlay via tecla de atalho.
