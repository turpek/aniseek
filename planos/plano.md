# Master Plan: Aniseek

Este documento centraliza todos os objetivos arquiteturais, otimizações estruturais, correções de bugs e o progresso do desenvolvimento do motor de leitura e manipulação de frames (`aniseek`).

---

## 📋 Lista de Tarefas (Status Atual)

- [x] 1. Desacoplamento do backend de decodificação via interface `IFrameSource` (`OpenCVVideoSource`).
- [x] 2. Otimização de busca binária e pulos leves de cabeçalho (`grab`) com `FrameMapper`.
- [x] 3. Sistema cooperativo de duplo buffer concorrente (`VideoBufferRight` & `VideoBufferLeft`).
- [x] 4. Módulo de input desacoplado com `PynputKeyReader` (suporte a `Ctrl`), `CV2KeyReader` (fallback) e atalhos padronizados.
- [ ] 5. **Bugfix no `SectionManager.remove_section` / `VideoManager.create`:** Falha `AttributeError: 'NoneType' object has no attribute '_calculate_mapping'` ao remover seção quando pausado (`Ctrl + x`).
- [ ] 6. **Refatoração de Usabilidade das Seções & Modo Preview da Montagem Final (UX / Funcional).**
- [ ] 7. **Refatoração Arquitetural e Manutenibilidade do Subsistema de Seções (Clean Code / Arquitetura Interna).**

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

- [ ] **6.1. Dividir Seção (`Split — Ctrl + s`) Sensível ao Sentido do Buffer:**
  - Aterrissar o cursor no sentido do movimento (`proceed` $\rightarrow$ início da seção da direita; `rewind` $\rightarrow$ fim da seção da esquerda).
  - Bloquear divisão inválida nos limites extremos (`frame_id == start` ou `frame_id == end - 1`) com feedback amigável.
- [ ] **6.2. Juntar Seções (`Join — Ctrl + j`) Contextual e Bidirecional:**
  - Regra de ponta automática (primeira junta com próxima; última junta com anterior).
  - Regra de meio automática orientada pelo sentido da reprodução (`proceed` $\rightarrow$ direita; `rewind` $\rightarrow$ esquerda).
  - Operação determinística e sem timers.
- [ ] **6.3. Navegação entre Seções (`Next / Prev — Ctrl + d / Ctrl + a`) no Frame Mais Próximo:**
  - `Ctrl + d`: Aterrissa no início da próxima seção (`start`).
  - `Ctrl + a`: Aterrissa no fim da seção anterior (`end - 1`).
  - Atalhos universais `Home` e `End` para saltar para o início e fim da seção atual.
- [ ] **6.4. Feedback Visual Imediato e Correção de Congelamento na Pausa com Espaço:**
  - Chamar `set_read()` em todas as operações de seção para destravar o `no_read()`.
  - Inicializar os buffers com `servant.run()` no `VideoManager.create()`.
  - Atualização dinâmica do título da janela OpenCV (`videoseq - [Seção X/Y | Frame A/B] (PAUSADO)`).
- [ ] **6.5. Modo Preview da Montagem Final (`Rough Cut Preview` — Tecla `v`):**
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

- [ ] **7.1. Simplificação da Entidade Base `VideoSection`:**
  - Construtor direto sem dependência obrigatória de adapters (`start`, `end`, `removed_frames`, `black_list_frames`).
  - Métodos `split(frame_id)` e `join(other)` analíticos e diretos em memória.
  - Métodos de serialização `from_dict(data)` e `to_dict()`.
  - Ordenação determinística de `mapping` via `sorted(frames - removed)`.
  - Eliminação de `ISectionAdapter`, `JSONSectionAdapter`, `FakeSectionAdapter`, `SectionUnionAdapter` e `SectionSplitProcess`.
- [ ] **7.2. Modernização do `SectionManager` (Lista com Cursor):**
  - Substituição do modelo de 2 pilhas (`SimpleStack(_left)` e `SimpleStack(_right)`) por `_sections: list[VideoSection]` e `_current_index: int`.
  - Acesso direto $O(1)$ à seção ativa (`current_section`), próxima e anterior.
  - Implementação de `can_next()`, `can_prev()`, `can_join_next()`, `can_join_prev()`.
  - Implementação de `get_preview_mapping()` para montagem contínua.
- [ ] **7.3. Simplificação do Histórico de Undo / Memento:**
  - Eliminação da classe `SectionWrapper`.
  - Substituição das 9 classes/interfaces de Memento de seções por uma pilha simples de snapshots/ações (`_undo_stack: deque`).
- [ ] **7.4. Simplificação da Persistência JSON:**
  - Consolidação das 8 classes de I/O (`SectionService`, `TemplateFactory`, `SectionManagerProcessFactory`, `JSONSectionSave`, `JSONReader`, `JSONWriter`, etc.) em um módulo coeso de armazenamento (`SectionStorage` ou métodos estáticos em `SectionManager`).
- [ ] **7.5. Migração e Limpeza dos Testes Unitários:**
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
