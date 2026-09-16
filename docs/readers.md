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
| `start` | `int \| None` | `None` (0) | Índice do primeiro frame da amostragem (inclusivo). |
| `end` | `int \| None` | `None` (total) | Índice limite do frame (exclusivo, como em slices do Python). |
| `step` | `int` | `1` | Intervalo entre frames amostrados (pula intermediários com `cap.grab()`). |
| `frames` | `list[int] \| None` | `None` | Lista explícita e arbitrária de índices de frames a decodificar. Sobrepõe `start`/`end`/`step`. |
| `buffersize` | `int` | `30` | Capacidade máxima da fila em memória para pré-carregamento concorrente. |

### Propriedades e Métodos Disponíveis em Todos os Leitores:

- **`reader.read() -> tuple[bool, ndarray | None]`**: Lê o próximo frame na direção atual. Retorna `(True, frame)` ou `(False, None)` se a leitura terminou.
- **`reader.is_task_complete -> bool`**: Retorna `True` assim que todos os frames da amostragem/fatiamento foram entregues.
- **`reader.frame_id -> int | None`**: Retorna o índice real absoluto do último frame retornado por `read()`.
- **`reader.total_frames -> int`**: Total de frames brutos do vídeo.
- **`reader.fps -> float`**: Taxa de quadros por segundo do vídeo.
- **`len(reader) -> int`**: Quantidade total de frames que serão entregues na amostragem atual.
- **`for ret, frame in reader:`**: Suporte nativo a loop iterador.
- **`with ... as reader:`**: Context manager que garante liberação automática de threads e descritores de vídeo via `.close()`.

---

## 2. `ForwardReader` (Leitura Direta)

O `ForwardReader` utiliza internamente um único buffer concorrente (`VideoBufferRight`) que avança linearmente do primeiro ao último frame especificado. É a escolha ideal quando a tarefa exige apenas processamento sequencial para frente.

### Características:
- **Consumo de Memória:** Baixo (apenas 1 fila de tamanho `buffersize`).
- **Sentido:** Estritamente crescente (`start -> end`).
- **Otimização:** Descarta frames pulados via `cap.grab()` sem carregar decodificação de imagem na CPU/GPU.

### Exemplo de Uso:

```python
from pathlib import Path
from aniseek import ForwardReader

video_path = Path("video.mp4")

# 1. Leitura padrão com fatiamento (frames 100 a 300, pulando de 2 em 2)
with ForwardReader(video_path, start=100, end=300, step=2) as reader:
    print(f"Total de frames amostrados: {len(reader)}")

    while not reader.is_task_complete:
        ret, frame = reader.read()
        if not ret or frame is None:
            break
        print(f"Frame lido com sucesso: {reader.frame_id}")

# 2. Leitura com lista arbitrária de frames usando protocolo de iterador
with ForwardReader(video_path, frames=[10, 25, 30, 150, 500]) as reader:
    for ret, frame in reader:
        # 'ret' é booleano indicando sucesso e 'frame' é o numpy.ndarray
        process_frame(reader.frame_id, frame)
```

---

## 3. `ReverseReader` (Leitura Reversa)

O `ReverseReader` opera com o `VideoBufferLeft`, projetado para decodificar e entregar frames em ordem decrescente. Como decodificadores de vídeo (H.264, HEVC, etc.) não conseguem decodificar nativamente para trás sem keyframes, o `VideoBufferLeft` divide a leitura em blocos no sentido inverso e alimenta uma fila de saída em ordem decrescente de forma assíncrona.

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
        if not ret:
            break
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

- **`reader.proceed()`**: Altera o sentido ativo para avanço (`+1`).
- **`reader.rewind()`**: Altera o sentido ativo para retrocesso (`-1`).
- **`reader.is_forward -> bool`**: Retorna `True` se o sentido atual for avanço.
- **`reader.is_reverse -> bool`**: Retorna `True` se o sentido atual for retrocesso.
- **Parâmetro `direction` no construtor**: Permite iniciar diretamente em `"forward"` (padrão) ou `"reverse"`.

### Exemplo de Uso:

```python
from aniseek import VideoReader

with VideoReader("video.mp4", start=0, end=500) as reader:
    # Avança os primeiros 50 frames
    for _ in range(50):
        ret, frame = reader.read()
        print(f"Avançando: frame {reader.frame_id}")

    # Alterna instantaneamente para trás
    print("Trocando sentido para REWIND...")
    reader.rewind()

    # Lê 20 frames para trás (reaproveita cache dos frames decodificados)
    for _ in range(20):
        ret, frame = reader.read()
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
| **Indicação `is_task_complete`** | ✅ Sim | ✅ Sim | ✅ Sim |
| **Context Manager (`with`)** | ✅ Sim | ✅ Sim | ✅ Sim |
| **Caso Recomendado** | Pipelines lineares e inferência de IA | Inspeções retrospectivas pontuais | Navegação interativa em UI / Players |
