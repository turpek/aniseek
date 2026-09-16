import time
from queue import LifoQueue
from threading import Event, Lock, Thread

import cv2


class VideoBuffer(Thread):
    def __init__(self, cap, stack, *, name='buffer'):
        super().__init__()
        self.cap = cap
        self.name = name
        self.stack = stack
        self._stopped = False
        self.restock_event = Event()  # Event to trigger restock
        self.lock = Lock()

    def run(self):
        while not self._stopped:
            self.restock_event.wait()  # Wait until the restock event is set
            if not self._stopped:
                self.fill_stack()
            self.restock_event.clear()  # Clear the event after restocking

    def fill_stack(self):
        start_time = time.time()
        with self.lock:  # Ensure thread-safe access to the stack
            while not self.stack.full() and not self._stopped:
                ret, frame = self.cap.read()
                if not ret:
                    self._stopped = True
                    break
                self.stack.put(frame)
        end_time = time.time()
        print(f'\nLidos {self.stack.qsize()} frames em {end_time - start_time:.2f}s')
        print(f'{self.stack.qsize() / (end_time - start_time):.2f} FPS')

    def stop(self):
        self._stopped = True
        self.restock_event.set()  # Ensure the thread can exit if it's waiting


# Exemplo de uso
cap = cv2.VideoCapture('model.mp4')
frames = LifoQueue(maxsize=100)
video_buffer = VideoBuffer(cap, frames)
video_buffer.start()

# Para ler frames de trás para frente usando a pilha
while True:
    if frames.empty():
        video_buffer.restock_event.set()  # Trigger restocking if stack is empty
        video_buffer.restock_event.wait()  # Wait for restocking to complete

    frame = frames.get()
    if frame is None:
        break
    # Processar o frame (exibir, salvar, etc.)
    cv2.imshow('Frame', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

video_buffer.stop()
cap.release()
cv2.destroyAllWindows()
