# Documentação dos Leitores de Vídeo (`aniseek`)

O `aniseek` oferece uma arquitetura de leitura de frames de alta performance desacoplada de interfaces gráficas, utilizando buffers concorrentes em segundo plano (`threads`) e saltos rápidos sem sobrecarga de CPU via `cap.grab()` gerenciados pelo `FrameMapper`.

A biblioteca expõe três classes principais de leitores em seu pacote público (`aniseek`):

1. **`ForwardReader`**: Leitor unidirecional otimizado para avanço (`+1`).
2. **`ReverseReader`**: Leitor unidirecional otimizado para retrocesso (`-1`).
3. **`VideoReader`**: Leitor bidirecional cooperativo com duplo buffer e troca de marcha instantânea (`proceed` / `rewind`).

Todas as três classes herdam de **`BaseVideoReader`**, compartilhando a mesma interface uniforme de inicialização, amostragem, protocolo iterador e context manager (`with`).

---

## 1. Parâmetros Comuns de Configuração (`BaseVideoReader`)

Todos os leitores aceitam os seguintes parâmetros no construtor:

| Parâmetro | Tipo | Padrão | Descrição |
| :--- | :--- | :--- | :--- |
| `video` | `str \| Path \| cv2.VideoCapture` | *Obrigatório* | Caminho para o arquivo de vídeo ou uma instância existente de `cv2.VideoCapture`. |
| `start` | `int \| float \| str \| None` | `None` (0) | Ponto inicial: aceita índice de frame (`int`), segundos (`float`) ou timestamp (`str` ex: `"01:30"`). |
| `end` | `int \| float \| str \| None` | `None` (total) | Ponto final limite: aceita índice de frame (`int`), segundos (`float`) ou timestamp (`str` ex: `"02:45"`). |
| `step` | `int` | `1` | Intervalo entre frames amostrados (pula intermediários com `cap.grab()`). |
| `frames` | `list[int] \| None` | `None` | Lista explícita e arbitrária de índices de frames a decodificar. Sobrepõe `start`/`end`/`step`. |
| `buffersize` | `int` | `30` | Capacidade máxima da fila em memória para pré-carregamento concorrente. |

> [!TIP]
> **Conversão Automática e Determinística:**
> Se `start` ou `end` forem informados em formato temporal (`float` ou `str`), o leitor utiliza internamente a função [`resolve_frame_range`](file:///home/gui/python/aniseek/src/aniseek/time_utils.py) para convertê-los em índices inteiros exatos usando o `fps` real do vídeo. Assim, todo o pipeline interno e os buffers continuam trabalhando puramente com números inteiros (`int`).

### Propriedades e Métodos Disponíveis em Todos os Leitores:

- **`reader.read() -> tuple[bool, ndarray | None]`**: Lê o próximo frame na direção atual. Retorna `(True, frame)` se a decodificação foi bem-sucedida ou `(False, None)` caso a decodificação falhe ou a tarefa tenha chegado ao fim.
- **`reader.is_task_complete -> bool`**: **A única verdade do ciclo de vida.** Retorna `True` estritamente quando todos os frames planejados pela amostragem/fatiamento foram consumidos.
- **`reader.frame_id -> int | None`**: Retorna o índice real absoluto do último frame retornado por `read()`.
- **`reader.total_frames -> int`**: Total de frames brutos do vídeo informados pelo container.
- **`reader.fps -> float`**: Taxa de quadros por segundo do vídeo.
- **`len(reader) -> int`**: Quantidade total de frames que serão entregues na amostragem atual.
- **`for ret, frame in reader:`**: Suporte nativo a loop iterador. Itera continuamente até `is_task_complete`.
- **`with ... as reader:`**: Context manager que garante liberação automática de threads e descritores de vídeo via `.close()`.

---

> [!IMPORTANT]
> ### ⚠️ A Regra de Ouro: `is_task_complete` é a única verdade!
> No ecossistema OpenCV, containers de vídeo (como MP4/H.264/HEVC) frequentemente apresentam imprecisões no final do arquivo ou pequenos engasgos na decodificação de frames intermediários (retornando `None`).
>
> **Nunca utilize `break` ao receber `ret == False` ou `frame is None`!**
> Se você aplicar um `break`, um único frame com falha descartará todos os frames subsequentes que ainda poderiam ser lidos (causando imagens incompletas em rotinas de costura panorâmica/*stitch* ou interrupções precoces de pipelines).
>
> **O padrão resiliente:** use sempre `is_task_complete` para governar o loop e utilize `continue` caso um frame individual falhe.

---

## 2. `ForwardReader` (Leitura Direta)

O `ForwardReader` utiliza internamente um único buffer concorrente (`VideoBufferRight`) que avança linearmente do primeiro ao último frame especificado. É a escolha ideal quando a tarefa exige apenas processamento sequencial para frente.

### Características:
- **Consumo de Memória:** Baixo (apenas 1 fila de tamanho `buffersize`).
- **Sentido:** Estritamente crescente (`start -> end`).
- **Otimização:** Descarta frames pulados via `cap.grab()` sem carregar decodificação de imagem na CPU/GPU.

### Exemplo de Uso Resiliente:

```python
from pathlib import Path
from aniseek import ForwardReader

video_path = Path("video.mp4")

# 1. Leitura padrão via while (controlado estritamente por is_task_complete)
with ForwardReader(video_path, start=100, end=300, step=2) as reader:
    print(f"Total de frames amostrados: {len(reader)}")

    while not reader.is_task_complete:
        ret, frame = reader.read()
        if not ret or frame is None:
            # Pula eventuais falhas do decoder sem abortar a tarefa
            continue
        process_frame(reader.frame_id, frame)

# 2. Leitura idiomática via protocolo de iterador
# O próprio iterador continua consumindo até reader.is_task_complete
with ForwardReader(video_path, frames=[10, 25, 30, 150, 500]) as reader:
    for ret, frame in reader:
        if not ret or frame is None:
            continue
        process_frame(reader.frame_id, frame)
```

---

## 3. `ReverseReader` (Leitura Reversa)

O `ReverseReader` opera com o `VideoBufferLeft`, projetado para decodificar e entregar frames em ordem decrescente. Como decodificadores de vídeo não conseguem decodificar nativamente para trás sem keyframes, o `VideoBufferLeft` divide a leitura em blocos no sentido inverso e alimenta uma fila de saída em ordem decrescente de forma assíncrona.

### Características:
- **Consumo de Memória:** Baixo (apenas 1 fila de buffer reverso).
- **Sentido:** Estritamente decrescente (`end - 1 -> start`).
- **Casos de Uso:** Análise retrospectiva de eventos, rotulagem do final para o início, buscas reversas.

### Exemplo de Uso:

```python
from aniseek import ReverseReader

# Lê os últimos 60 frames em ordem decrescente (ex: do frame 999 até 940)
with ReverseReader("video.mp4", start=940, end=1000) as reader:
    while not reader.is_task_complete:
        ret, frame = reader.read()
        if not ret or frame is None:
            continue
        print(f"Frame lido em ordem reversa: {reader.frame_id}")
```

---

## 4. `VideoReader` (Leitura Bidirecional Cooperativa)

O `VideoReader` é a estrutura mais avançada da biblioteca, voltada para aplicações interativas (players, ferramentas de anotação e interfaces de revisão). Ele mantém dois buffers concorrentes simultâneos (`VideoBufferRight` e `VideoBufferLeft`) operando sob um padrão **Servant / Master**.

### Como Funciona o Cache Cooperativo:
- O buffer ativo (**Servant**) entrega frames para o consumidor através do método `.read()`.
- Simultaneamente, cada frame entregue é espelhado em memória para o buffer inativo (**Master**) através do método interno `master.put(frame_id, frame)`.
- Quando a aplicação chama `.proceed()` ou `.rewind()`, ocorre apenas a **inversão dos ponteiros** (`servant, master = master, servant`).
- **Resultado:** A inversão de marcha acontece com **latência zero**, sem necessidade de reposicionar o `VideoCapture` ou redecodificar os últimos frames que já estavam na memória.

### Métodos e Propriedades Exclusivos do `VideoReader`:

- **`reader.direction -> Direction`**: Retorna o sentido de reprodução ativo no momento (`Direction.FORWARD` ou `Direction.REVERSE`).
- **`reader.proceed()`**: Altera o sentido ativo para avanço (`+1`).
- **`reader.rewind()`**: Altera o sentido ativo para retrocesso (`-1`).
- **`reader.is_forward -> bool`**: Retorna `True` se o sentido atual for avanço.
- **`reader.is_reverse -> bool`**: Retorna `True` se o sentido atual for retrocesso.
- **Parâmetro `direction` no construtor**: Permite iniciar diretamente em `Direction.FORWARD` (padrão) ou `Direction.REVERSE` (strings `"forward"` e `"reverse"` também são aceitas por retrocompatibilidade).

### Exemplo de Uso:

```python
from aniseek import Direction, VideoReader

# Inicia a leitura configurada para avanço padrão (ou Direction.REVERSE)
with VideoReader("video.mp4", start=0, end=500, direction=Direction.FORWARD) as reader:
    print(f"Direção inicial: {reader.direction}")  # Direction.FORWARD
    # Avança os primeiros 50 frames
    for _ in range(50):
        ret, frame = reader.read()
        if not ret or frame is None:
            continue
        print(f"Avançando: frame {reader.frame_id}")

    # Alterna instantaneamente para trás
    print("Trocando sentido para REWIND...")
    reader.rewind()

    # Lê 20 frames para trás (reaproveita cache dos frames decodificados)
    for _ in range(20):
        ret, frame = reader.read()
        if not ret or frame is None:
            continue
        print(f"Retrocedendo: frame {reader.frame_id}")

    # Retoma avanço
    print("Retomando PROCEED...")
    reader.proceed()
    ret, frame = reader.read()
    print(f"Novo frame em avanço: {reader.frame_id}")
```

---

## 5. Tabela Comparativa de Escolha

| Recurso | `ForwardReader` | `ReverseReader` | `VideoReader` |
| :--- | :---: | :---: | :---: |
| **Sentido Suportado** | Apenas Avanço (`+1`) | Apenas Retrocesso (`-1`) | Bidirecional (`+1` e `-1`) |
| **Alternância Dinâmica** | ❌ Não | ❌ Não | ✅ Sim (`proceed()` / `rewind()`) |
| **Buffers Concorrentes** | 1 (`Right`) | 1 (`Left`) | 2 (`Right` + `Left`) |
| **Uso de Memória** | Mínimo | Mínimo | Moderado (~2x `buffersize`) |
| **Fatiamento (`start`/`end`/`step`)** | ✅ Sim | ✅ Sim | ✅ Sim |
| **Lista de Frames Arbitrária** | ✅ Sim | ✅ Sim | ✅ Sim |
| **Indicação `is_task_complete`** | ✅ Sim (Soberano) | ✅ Sim (Soberano) | ✅ Sim (Soberano) |
| **Context Manager (`with`)** | ✅ Sim | ✅ Sim | ✅ Sim |
| **Caso Recomendado** | Pipelines lineares e inferência de IA | Inspeções retrospectivas pontuais | Navegação interativa em UI / Players |
