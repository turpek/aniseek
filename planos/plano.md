# Master Plan: Aniseek

Este documento centraliza todos os objetivos arquiteturais, otimizações estruturais, correções de bugs e o progresso do desenvolvimento do motor de leitura e manipulação de frames (`aniseek`).

---

## 📋 Lista de Tarefas (Status Atual)

- [x] 1. Desacoplamento do backend de decodificação via interface `IFrameSource` (`OpenCVVideoSource`).
- [x] 2. Otimização de busca binária e pulos leves de cabeçalho (`grab`) com `FrameMapper`.
- [x] 3. Sistema cooperativo de duplo buffer concorrente (`VideoBufferRight` & `VideoBufferLeft`).
- [x] 4. Módulo de input desacoplado com `PynputKeyReader` (suporte a `Ctrl`), `CV2KeyReader` (fallback) e atalhos padronizados.
- [ ] 5. **Bugfix no `SectionManager.remove_section` / `VideoManager.create`:** Falha `AttributeError: 'NoneType' object has no attribute '_calculate_mapping'` ao remover seção quando pausado (`Ctrl + x`).

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
   * **Abordagem A (Proibitiva):** Não permitir a remoção da última seção do vídeo (isto é, um vídeo deve ter no mínimo uma seção ativa). Caso o usuário tente remover com apenas 1 seção restante, o método retorna `False` e emite um log informando que a última seção não pode ser removida.
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
