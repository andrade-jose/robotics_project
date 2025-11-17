# PLANO DE AÇÃO: RECONSTRUIR SISTEMA DE VISÃO DO ZERO

Se decidirmos reconstruir o sistema de visão completamente, este é o plano incremental com testes após cada implementação.

---

## FASE 1: FUNDAÇÃO - CAPTURA DE VÍDEO

### Objetivo
Ter câmera funcionando e capturando frames corretamente.

### Implementação

**Arquivo:** `vision/vision_v2_camera.py`

```python
class CameraV2:
    """Versão 2 simplificada de captura de câmera"""

    def __init__(self, camera_index=0, frame_width=640, frame_height=480):
        self.camera_index = camera_index
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.cap = None
        self.is_open = False

    def initialize(self):
        """Tenta inicializar câmera"""
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
                self.is_open = True
                return True
            return False
        except Exception as e:
            print(f"[ERRO] Falha ao inicializar câmera: {e}")
            return False

    def get_frame(self):
        """Obtém próximo frame"""
        if not self.is_open:
            return None

        ret, frame = self.cap.read()
        if ret:
            return frame
        return None

    def release(self):
        """Libera recurso"""
        if self.cap:
            self.cap.release()
            self.is_open = False
```

### Teste 1: Teste de Captura Básica

**Arquivo:** `test_vision_fase1.py`

```python
import cv2
from vision.vision_v2_camera import CameraV2

def test_camera_capture():
    """Teste 1: Verificar se câmera funciona"""
    print("[TESTE 1] Captura de câmera")

    camera = CameraV2(camera_index=0)
    if not camera.initialize():
        print("[FALHA] Câmera não inicializou")
        return False

    print("[OK] Câmera inicializada")

    # Tenta capturar 5 frames
    for i in range(5):
        frame = camera.get_frame()
        if frame is None:
            print(f"[FALHA] Frame {i+1} é None")
            camera.release()
            return False
        print(f"[OK] Frame {i+1}: {frame.shape}")

    camera.release()
    print("[OK] Teste de captura passou")
    return True

if __name__ == "__main__":
    test_camera_capture()
```

### Executar Teste
```bash
python test_vision_fase1.py
```

### Esperado
```
[TESTE 1] Captura de câmera
[OK] Câmera inicializada
[OK] Frame 1: (480, 640, 3)
[OK] Frame 2: (480, 640, 3)
[OK] Frame 3: (480, 640, 3)
[OK] Frame 4: (480, 640, 3)
[OK] Frame 5: (480, 640, 3)
[OK] Teste de captura passou
```

---

## FASE 2: DETECÇÃO - MARCADORES ARUCO

### Objetivo
Detectar marcadores ArUco em frame.

### Implementação

**Arquivo:** `vision/vision_v2_aruco.py`

```python
import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional, Dict, List

@dataclass
class MarkerDetected:
    """Informação de um marcador detectado"""
    marker_id: int
    center: tuple  # (x, y) em pixels
    corners: np.ndarray  # 4 corners em pixels

@dataclass
class GridCalculation:
    """Cálculo do grid 3x3"""
    reference_markers: Dict[int, MarkerDetected]  # ID -> MarkerDetected
    grid_positions: List[tuple]  # 9 posições calculadas
    confidence: float  # 0-1

class ArUcoDetectorV2:
    """Detector de ArUco versão 2"""

    def __init__(self):
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
        self.parameters = cv2.aruco.DetectorParameters()
        self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.parameters)
        self.markers_detected = {}

    def detect_markers(self, frame):
        """Detecta marcadores ArUco em frame"""
        corners, ids, rejected = self.detector.detectMarkers(frame)

        self.markers_detected.clear()

        if ids is None:
            return {}  # Nenhum marcador

        for i, marker_id in enumerate(ids.flatten()):
            corner = corners[i][0]  # 4 corners
            center_x = np.mean(corner[:, 0])
            center_y = np.mean(corner[:, 1])

            marker = MarkerDetected(
                marker_id=int(marker_id),
                center=(int(center_x), int(center_y)),
                corners=corner
            )
            self.markers_detected[int(marker_id)] = marker

        return self.markers_detected

    def get_detection_summary(self):
        """Retorna resumo das detecções"""
        return {
            'total_markers': len(self.markers_detected),
            'marker_ids': list(self.markers_detected.keys()),
            'centers': [m.center for m in self.markers_detected.values()]
        }

    def draw_detections(self, frame):
        """Desenha marcadores no frame"""
        frame_copy = frame.copy()

        for marker_id, marker in self.markers_detected.items():
            # Desenhar quadrado
            pts = marker.corners.astype(np.int32)
            cv2.polylines(frame_copy, [pts], True, (0, 255, 0), 2)

            # Desenhar ID
            cv2.putText(frame_copy, str(marker_id),
                       marker.center,
                       cv2.FONT_HERSHEY_SIMPLEX,
                       0.5, (255, 0, 0), 2)

        return frame_copy
```

### Teste 2: Detecção de Marcadores

**Arquivo:** `test_vision_fase2.py`

```python
import cv2
from vision.vision_v2_camera import CameraV2
from vision.vision_v2_aruco import ArUcoDetectorV2

def test_marker_detection():
    """Teste 2: Detectar marcadores ArUco"""
    print("[TESTE 2] Detecção de marcadores ArUco")

    camera = CameraV2()
    if not camera.initialize():
        print("[FALHA] Câmera não inicializou")
        return False

    detector = ArUcoDetectorV2()

    # Captura 10 frames e mostra detecções
    print("[INFO] Apontando câmera para marcadores ArUco...")
    for i in range(10):
        frame = camera.get_frame()
        if frame is None:
            print(f"[FALHA] Frame {i+1} é None")
            camera.release()
            return False

        markers = detector.detect_markers(frame)
        summary = detector.get_detection_summary()

        print(f"[FRAME {i+1}] Marcadores: {summary['total_markers']}, IDs: {summary['marker_ids']}")

        if summary['total_markers'] > 0:
            print(f"[OK] Detectados {summary['total_markers']} marcadores")

            # Desenhar e mostrar
            frame_with_detections = detector.draw_detections(frame)
            cv2.imshow("Detecções ArUco", frame_with_detections)
            cv2.waitKey(100)

    camera.release()
    cv2.destroyAllWindows()
    print("[OK] Teste de detecção passou")
    return True

if __name__ == "__main__":
    test_marker_detection()
```

### Executar Teste
```bash
python test_vision_fase2.py
```

### Esperado
```
[TESTE 2] Detecção de marcadores ArUco
[INFO] Apontando câmera para marcadores ArUco...
[FRAME 1] Marcadores: 0, IDs: []
[FRAME 2] Marcadores: 2, IDs: [0, 1]
[OK] Detectados 2 marcadores
[FRAME 3] Marcadores: 2, IDs: [0, 1]
[OK] Detectados 2 marcadores
...
[OK] Teste de detecção passou
```

---

## FASE 3: CALIBRAÇÃO - MAPEAR GRID 3X3

### Objetivo
Converter posições de pixel para grid 3x3 de coordenadas físicas.

### Implementação

**Arquivo:** `vision/vision_v2_grid.py`

```python
import numpy as np
from typing import Optional, List, Tuple

class GridCalculatorV2:
    """Calcula grid 3x3 baseado em marcadores de referência"""

    def __init__(self, reference_distance_mm=100):
        """
        reference_distance_mm: Distância conhecida entre 2 marcadores
                               (por padrão 10cm entre marcadores de referência)
        """
        self.reference_distance_mm = reference_distance_mm
        self.reference_markers = {}  # ID -> (x_pixel, y_pixel)
        self.pixels_per_mm = None
        self.grid_positions = None  # 9 posições em pixels

    def calibrate(self, detected_markers):
        """Calibra o sistema com marcadores detectados"""

        # Precisa de pelo menos 2 marcadores para calibrar
        if len(detected_markers) < 2:
            print("[AVISO] Precisa de pelo menos 2 marcadores para calibrar")
            return False

        # Obter IDs dos 2 primeiros marcadores
        marker_ids = sorted(detected_markers.keys())[:2]

        markers = [detected_markers[mid] for mid in marker_ids]

        # Calcular distância em pixels
        pos1 = markers[0].center
        pos2 = markers[1].center

        distance_pixels = np.sqrt((pos1[0]-pos2[0])**2 + (pos1[1]-pos2[1])**2)

        # Calcular escala
        self.pixels_per_mm = distance_pixels / self.reference_distance_mm

        print(f"[CALIBRACAO] Escala: {self.pixels_per_mm:.2f} pixels/mm")

        return True

    def calculate_grid(self, detected_markers):
        """Calcula grid 3x3 baseado em marcadores"""

        if not self.pixels_per_mm:
            print("[ERRO] Sistema não calibrado")
            return False

        if len(detected_markers) < 2:
            print("[ERRO] Precisa de pelo menos 2 marcadores")
            return False

        # Ordenar por posição
        markers_list = sorted(
            detected_markers.items(),
            key=lambda x: (x[1].center[1], x[1].center[0])  # Por Y depois X
        )

        # Obter primeiro marcador como referência (canto superior esquerdo)
        ref_marker = markers_list[0][1]
        ref_x, ref_y = ref_marker.center

        # Calcular espaçamento do grid em pixels
        # Se 2 marcadores com 100mm de distância, e 10cm = 100mm
        # Grid 3x3 com espaçamento de 50mm entre posições
        spacing_pixels = (100 / 3) * self.pixels_per_mm  # Espaçamento do grid

        # Gerar 9 posições do grid 3x3
        self.grid_positions = []
        for row in range(3):
            for col in range(3):
                x = ref_x + col * spacing_pixels
                y = ref_y + row * spacing_pixels
                self.grid_positions.append((int(x), int(y)))

        print(f"[OK] Grid calculado: 9 posições")
        return True

    def get_grid_positions(self):
        """Retorna as 9 posições do grid"""
        return self.grid_positions

    def get_position_from_detection(self, x_pixel, y_pixel):
        """Converte posição em pixel para índice de grid (0-8)"""
        if not self.grid_positions:
            return None

        # Encontrar posição do grid mais próxima
        min_distance = float('inf')
        closest_index = None

        for idx, (gx, gy) in enumerate(self.grid_positions):
            distance = np.sqrt((x_pixel - gx)**2 + (y_pixel - gy)**2)
            if distance < min_distance:
                min_distance = distance
                closest_index = idx

        if min_distance < 50:  # Threshold de 50 pixels
            return closest_index

        return None
```

### Teste 3: Calibração e Grid

**Arquivo:** `test_vision_fase3.py`

```python
import cv2
import numpy as np
from vision.vision_v2_camera import CameraV2
from vision.vision_v2_aruco import ArUcoDetectorV2
from vision.vision_v2_grid import GridCalculatorV2

def test_grid_calculation():
    """Teste 3: Calcular grid 3x3"""
    print("[TESTE 3] Cálculo de grid 3x3")

    camera = CameraV2()
    detector = ArUcoDetectorV2()
    calculator = GridCalculatorV2(reference_distance_mm=100)

    if not camera.initialize():
        print("[FALHA] Câmera não inicializou")
        return False

    print("[INFO] Aguardando calibração com 2 marcadores...")

    calibrated = False
    for i in range(50):
        frame = camera.get_frame()
        markers = detector.detect_markers(frame)

        if len(markers) >= 2 and not calibrated:
            if calculator.calibrate(markers):
                calibrated = True
                print("[OK] Sistema calibrado")
                break

    if not calibrated:
        print("[FALHA] Não conseguiu calibrar")
        camera.release()
        return False

    # Agora calcular grid
    frame = camera.get_frame()
    markers = detector.detect_markers(frame)

    if calculator.calculate_grid(markers):
        positions = calculator.get_grid_positions()
        print(f"[OK] Grid com 9 posições:")
        for idx, pos in enumerate(positions):
            print(f"     Posição {idx}: {pos}")

    # Visualizar
    frame_copy = detector.draw_detections(frame)

    # Desenhar grid
    for idx, (x, y) in enumerate(calculator.get_grid_positions()):
        cv2.circle(frame_copy, (x, y), 10, (0, 0, 255), 2)
        cv2.putText(frame_copy, str(idx), (x, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    cv2.imshow("Grid 3x3", frame_copy)
    cv2.waitKey(2000)
    cv2.destroyAllWindows()

    camera.release()
    print("[OK] Teste de grid passou")
    return True

if __name__ == "__main__":
    test_grid_calculation()
```

### Executar Teste
```bash
python test_vision_fase3.py
```

---

## FASE 4: INTEGRAÇÃO - CONECTAR AO JOGO

### Objetivo
Integrar a visão com o sistema de jogo existente.

### Implementação

**Arquivo:** `vision/vision_v2_integration.py`

```python
import threading
import time
from vision.vision_v2_camera import CameraV2
from vision.vision_v2_aruco import ArUcoDetectorV2
from vision.vision_v2_grid import GridCalculatorV2

class VisionV2:
    """Versão 2 simplificada de integração de visão"""

    def __init__(self):
        self.camera = None
        self.detector = None
        self.calculator = None
        self.is_running = False
        self.thread = None
        self.last_detections = {}
        self.board_positions = {}  # Mapping: grid_index -> (jogador, confiança)

    def initialize(self):
        """Inicializa sistema de visão"""
        try:
            self.camera = CameraV2()
            if not self.camera.initialize():
                print("[ERRO] Câmera não inicializou")
                return False

            self.detector = ArUcoDetectorV2()
            self.calculator = GridCalculatorV2()

            print("[OK] Sistema de visão inicializado")
            return True
        except Exception as e:
            print(f"[ERRO] Erro ao inicializar visão: {e}")
            return False

    def calibrate(self):
        """Calibra o sistema com marcadores"""
        print("[INFO] Calibrando sistema de visão...")

        for i in range(100):
            frame = self.camera.get_frame()
            markers = self.detector.detect_markers(frame)

            if len(markers) >= 2:
                if self.calculator.calibrate(markers):
                    if self.calculator.calculate_grid(markers):
                        print("[OK] Calibração concluída")
                        return True

        print("[AVISO] Calibração incompleta, mas continuando...")
        return False

    def start_vision_loop(self):
        """Inicia loop de visão em thread"""
        self.is_running = True
        self.thread = threading.Thread(target=self._vision_loop, daemon=True)
        self.thread.start()
        print("[OK] Loop de visão iniciado")

    def _vision_loop(self):
        """Loop principal de processamento de visão"""
        while self.is_running:
            try:
                frame = self.camera.get_frame()
                if frame is None:
                    continue

                # Detectar marcadores
                markers = self.detector.detect_markers(frame)
                self.last_detections = markers

                # Calcular posições do grid
                if markers:
                    self.calculator.calculate_grid(markers)

                time.sleep(0.033)  # ~30 FPS
            except Exception as e:
                print(f"[ERRO] Erro no loop de visão: {e}")

    def stop_vision_loop(self):
        """Para loop de visão"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2)
        print("[OK] Loop de visão parado")

    def get_state(self):
        """Retorna estado atual da visão"""
        return {
            'markers_detected': len(self.last_detections),
            'marker_ids': list(self.last_detections.keys()),
            'calibrated': self.calculator.pixels_per_mm is not None,
            'grid_positions': self.calculator.get_grid_positions()
        }

    def release(self):
        """Libera recursos"""
        self.stop_vision_loop()
        if self.camera:
            self.camera.release()
```

### Teste 4: Integração Completa

**Arquivo:** `test_vision_fase4.py`

```python
import time
from vision.vision_v2_integration import VisionV2

def test_vision_integration():
    """Teste 4: Integração completa"""
    print("[TESTE 4] Integração de visão com o jogo")

    vision = VisionV2()

    if not vision.initialize():
        print("[FALHA] Não conseguiu inicializar")
        return False

    if not vision.calibrate():
        print("[AVISO] Calibração incompleta")

    vision.start_vision_loop()

    # Executar por 5 segundos
    print("[INFO] Executando visão por 5 segundos...")
    for i in range(5):
        state = vision.get_state()
        print(f"[{i+1}s] Marcadores: {state['markers_detected']}, "
              f"Calibrado: {state['calibrated']}")
        time.sleep(1)

    vision.stop_vision_loop()
    vision.release()

    print("[OK] Teste de integração passou")
    return True

if __name__ == "__main__":
    test_vision_integration()
```

### Executar Teste
```bash
python test_vision_fase4.py
```

---

## RESUMO DO PLANO

| Fase | Objetivo | Arquivo Novo | Teste | Status |
|------|----------|--------------|-------|--------|
| 1 | Captura de vídeo | vision_v2_camera.py | test_vision_fase1.py | ✓ |
| 2 | Detecção ArUco | vision_v2_aruco.py | test_vision_fase2.py | ✓ |
| 3 | Grid 3x3 | vision_v2_grid.py | test_vision_fase3.py | ✓ |
| 4 | Integração | vision_v2_integration.py | test_vision_fase4.py | ✓ |

---

## COMO USAR ESTE PLANO

### Se Tudo Funcionar na Fase Atual
✅ Mantenha a implementação atual, melhor não mexer

### Se Erro Ocorrer Novamente
1. Parar na fase do erro
2. Debugar isoladamente
3. Criar versão V2 para teste
4. Após funcionar, integrar ao sistema principal
5. Remover versão antiga (deprecated)

### Exemplo: Erro na Fase 2
```bash
# Criar versão V2 da câmera e ArUco
# Testar fase 1 e 2 isoladamente
python test_vision_fase1.py
python test_vision_fase2.py

# Se fase 2 falhar:
# - Debugar ArUcoDetectorV2
# - Adicionar logs detalhados
# - Testar com diferentes câmeras

# Após funcionar:
# - Remover código antigo
# - Atualizar imports
# - Retomar sistema principal
```

---

## VANTAGENS DESTA ABORDAGEM

1. **Modular** - Cada fase é independente
2. **Testável** - Teste após cada implementação
3. **Incremental** - Não precisa de tudo funcionar para testar
4. **Debugável** - Isolamento do problema
5. **Reversível** - Se algo quebrar, volta para versão anterior
6. **Documentado** - Cada fase tem objetivo claro

---

**Se decidir refazer a visão, comece pela FASE 1 e execute `test_vision_fase1.py`.**