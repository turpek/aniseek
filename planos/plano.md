# Master Plan: Aniseek

Este documento centraliza todos os objetivos arquiteturais, otimizações estruturais, correções de bugs e o progresso do desenvolvimento do motor de leitura e manipulação de frames (`aniseek`).

---

## 📋 Lista de Tarefas (Status Atual)

- [x] 1. Desacoplamento do backend de decodificação via interface `IFrameSource` (`OpenCVVideoSource`).
- [x] 2. Otimização de busca binária e pulos leves de cabeçalho (`grab`) com `FrameMapper`.
- [x] 3. Sistema cooperativo de duplo buffer concorrente (`VideoBufferRight` & `VideoBufferLeft`).
- [x] 4. Módulo de input desacoplado com `PynputKeyReader` (suporte a `Ctrl`), `CV2KeyReader` (fallback) e atalhos padronizados.
- [ ] 5. **Bugfix no `SectionManager.remove_section` / `VideoManager.create`:** Falha `AttributeError: 'NoneType' object has no attribute '_calculate_mapping'` ao remover seção quando pausado (`Ctrl + x`).
- [ ] 6. **Refatoração e Usabilidade do Subsistema de Seções & Modo Preview da Montagem Final.**

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

Há dois pontos fundamentais de regra de negócio a serem formalizados:

1. **Permissão de Remoção da Última Seção:**
   * **Abordagem A (Proibitiva - Recomendada):** Não permitir a remoção da última seção do vídeo (isto é, um vídeo deve ter no mínimo uma seção ativa). Caso o usuário tente remover com apenas 1 seção restante, o método retorna `False` e emite um log/aviso informando que a última seção não pode ser removida.
   * **Abordagem B (Permissiva):** Permitir a remoção completa. Neste caso, o `VideoManager` e o `VideoController` precisam entrar em um estado de "vídeo vazio / sem seções válidas", onde nenhum frame é exibido e novas operações de divisão/leitura são desativadas ou tratadas com segurança.

2. **Guard Clauses Defensivas em `SectionManager`:**
   * Métodos como `load_mementos_frames` e `store_mementos_frames` devem checar se `self._right.top is not None` antes de tentar calcular mappings ou carregar mementos de frames.

---

#### 4. Escopo da Investigação e Plano de Ação

- [ ] **Reprodução em Teste Unitário:**
  - Criar um teste dedicado em `tests/test_section.py` e/ou `tests/test_controller.py` reproduzindo a chamada de `remove_section()` quando resta apenas 1 seção na pilha.
- [ ] **Implementação das Guard Clauses:**
  - Adicionar validação em `SectionManager.load_mementos_frames()` e `store_mementos_frames()` para lidar de forma segura com `self._right.empty()`.
- [ ] **Definição e Aplicação da Regra de Remoção:**
  - Aplicar a política acordada em `SectionManager.remove_section()` e `VideoController.remove_section()`.
- [ ] **Validação com o Vídeo Real:**
  - Executar o script `scratch/test_real_video.py`, pausar com a tecla `espaço` e acionar `Ctrl + x`, garantindo que não ocorra crash.
- [ ] **Verificação de Qualidade:**
  - Executar a suíte de testes com `uv run pytest` e checagem de lint/formatação (`ruff` / `autopep8`).

---

### Task 6: Refatoração de Usabilidade das Seções e Modo Preview da Montagem Final

Esta tarefa visa transformar a interação com o subsistema de seções em uma experiência ergonômica, previsível e sem atritos de interface, resolvendo assimetrias de comandos e implementando o modo de visualização global da montagem.

#### 📋 Sub-lista de Objetivos da Tarefa 6

- [ ] **6.1. Dividir Seção (`Split — Ctrl + s`) Sensível ao Sentido do Buffer:**
  - Aterrissar o cursor no sentido do movimento (`proceed` $\rightarrow$ início da seção da direita; `rewind` $\rightarrow$ fim da seção da esquerda).
  - Bloquear divisão inválida nos limites extremos (`frame_id == start` ou `frame_id == end - 1`) com feedback amigável.
- [ ] **6.2. Juntar Seções (`Join — Ctrl + j`) Contextual e Bidirecional:**
  - Permitir união sem necessidade de navegar manualmente para a seção seguinte.
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

#### Detalhamento Técnico dos Pontos da Tarefa 6

##### 1. Dividir Seção (`Split — Ctrl + s`) Sensível ao Sentido do Buffer
* **Comportamento Atual:** A divisão gera duas seções e joga o cursor compulsoriamente no início da segunda metade, ignorando se o usuário estava rebobinando ou avançando.
* **Comportamento Esperado:**
  * Se o usuário estava em **`proceed` (+1)**: o cursor aterrissa no **primeiro frame da seção da direita** (`frame_id + 1`), dando continuidade ao fluxo natural de avanço.
  * Se o usuário estava em **`rewind` (-1)**: o cursor aterrissa no **último frame da seção da esquerda** (`frame_id`), permitindo continuar inspecionando para trás.
  * **Validação de Limites:** Se o usuário tentar dividir no primeiro frame (`frame_id == start`) ou no último (`frame_id == end - 1`), a operação deve ser rejeitada com aviso explicativo, prevenindo seções de tamanho zero ou corrupção de ranges.

##### 2. Juntar Seções (`Join — Ctrl + j`) Contextual e Bidirecional (Sem Timer)
* **Comportamento Atual:** O método só une com a seção anterior em `self._left`. Na Seção 1, o comando falha e exige que o usuário avance para a Seção 2 antes de juntar.
* **Comportamento Esperado:**
  * **Ponta Esquerda (Seção 1):** Junta automaticamente com a próxima seção (direita).
  * **Ponta Direita (Última Seção):** Junta automaticamente com a seção anterior (esquerda).
  * **Seções Intermediárias:** A direção do player dita a união:
    * Se em `proceed` $\rightarrow$ une com a próxima seção (direita).
    * Se em `rewind` $\rightarrow$ une com a seção anterior (esquerda).
  * Elimina timeouts, timers e confirmações lentas, mantendo resposta imediata.

##### 3. Navegação entre Seções (`Next / Prev — Ctrl + d / Ctrl + a`) no Frame Mais Próximo
* **Comportamento Atual:** `Ctrl + a` joga o cursor no frame 0 da seção anterior, distante do ponto de corte.
* **Comportamento Esperado:**
  * **`Ctrl + d` (Próxima):** Salta para o **início** da próxima seção (`start`).
  * **`Ctrl + a` (Anterior):** Salta para o **fim** da seção anterior (`end - 1`), mantendo o usuário na fronteira imediata do corte.
  * **Navegação de Extremos:**
    * Tecla `Home`: Salta para o início da seção atual (`start`).
    * Tecla `End`: Salta para o fim da seção atual (`end - 1`).

##### 4. Feedback Visual Imediato e Correção de Congelamento na Pausa com Espaço
* **Comportamento Atual:** Durante pause ativo (`delay = 0`), a flag `no_read()` barra novas leituras, e os buffers recriados no `create()` não são iniciados via `run()`. A tela permanece congelada no frame antigo.
* **Comportamento Esperado:**
  * Todas as operações de seção (`next_section`, `prev_section`, `split_section`, `join_section`, `remove_section`) devem invocar `self.__player.set_read()`.
  * `VideoManager.create()` deve disparar `self.servant.run()` e garantir que o primeiro frame esteja pronto.
  * O título da janela OpenCV deve ser atualizado dinamicamente via `cv2.setWindowTitle`:
    ```text
    videoseq - [Seção 2/3 | Frames 534-1200 | Frame Atual: 620] (PAUSADO)
    ```

##### 5. Modo Preview da Montagem Final (`Rough Cut Preview` — Tecla `v`)
* **Conceito:**
  * Atua como uma lente de visualização global que monta a linha do tempo contínua de todas as seções ativas (`_left` + `_right`), ocultando automaticamente seções deletadas e frames no `Trash`.
* **Preservação de Estado:**
  * Alternar a tecla `v` não altera: `frame_id`, direção (`proceed`/`rewind`), estado de pausa (`espaço`/`b`) ou velocidade de reprodução (`delay`).
* **Sincronização de Seção ao Sair:**
  * Se o usuário percorrer o vídeo em modo Preview e desativá-lo em um frame de outra seção, essa seção é automaticamente promovida a seção ativa no topo de `_right`.
