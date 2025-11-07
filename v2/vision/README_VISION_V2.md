# V2 Vision System - Do Zero

**Status**: Planned (Phase 3)

## 🎯 Objetivo

Reescrever o sistema de visão do zero com:
- Modularização completa
- Testes isolados para cada componente
- Sem dependências cruzadas
- Sincronizado com BoardCoordinateSystem

## 🏗️ Arquitetura Planejada

```
camera_simple.py
    ↓ captura frames
    ↓
aruco_detector.py
    ↓ detecta marcadores
    ↓
grid_calculator.py
    ↓ mapeia grid 3x3
    ↓
vision_manager.py (orquestrador)
    ↓
integration/vision_integration_v2.py (integração com jogo)
```

## 📝 Módulos a Implementar

### 1. `camera_simple.py` (Semana 1)
Apenas captura de câmera, sem processamento.

**Responsabilidades**:
- Inicializar câmera
- Capturar frames
- Gerenciar recursos
- Logging básico

**Dependências**: OpenCV (cv2)

**Testes**: `tests/test_camera.py`

**Exemplo de uso**:
```python
from vision.camera_simple import CameraSimple

camera = CameraSimple(camera_index=0)
camera.initialize()
frame = camera.capture_frame()  # retorna numpy array ou None
camera.release()
```

---

### 2. `aruco_detector.py` (Semana 1)
Detecção pura de marcadores ArUco.

**Responsabilidades**:
- Detectar marcadores ArUco (6x6 250)
- Retornar centróides (x, y)
- Validar detecções
- Logging

**Dependências**: OpenCV (cv2), NumPy

**Testes**: `tests/test_aruco.py`

**Exemplo de uso**:
```python
from vision.aruco_detector import ArUcoDetector

detector = ArUcoDetector(aruco_dict_size=6, marker_size=250)
detections = detector.detect(frame)  # lista de (marker_id, centroid_x, centroid_y)
```

---

### 3. `grid_calculator.py` (Semana 1)
Mapear detecções para grid 3x3.

**Responsabilidades**:
- Receber centróides
- Mapear para grid 3x3 (positions 0-8)
- Validar posições
- Retornar estado do tabuleiro

**Dependências**: NumPy

**Testes**: `tests/test_grid.py`

**Exemplo de uso**:
```python
from vision.grid_calculator import GridCalculator

grid = GridCalculator(grid_rows=3, grid_cols=3)
state = grid.calculate_state(detections)
# retorna: {0: 'vazio', 1: 'peça_1', 2: 'peça_2', ...}
```

---

### 4. `vision_manager.py` (Semana 2)
Orquestra os 3 módulos acima.

**Responsabilidades**:
- Inicializar todos os componentes
- Loop de captura e processamento
- Gerenciar estado da visão
- Sincronizar com jogo
- Thread-safe se necessário

**Dependências**: Módulos acima

**Exemplo de uso**:
```python
from vision.vision_manager import VisionManager

manager = VisionManager()
manager.start()
state = manager.get_current_state()
manager.stop()
```

---

## 🧪 Testes

### `tests/test_camera.py`
- [ ] Testar inicialização
- [ ] Testar captura de frames
- [ ] Testar release de recursos

### `tests/test_aruco.py`
- [ ] Testar detecção com imagem conhecida
- [ ] Testar marcadores simulados
- [ ] Testar casos de erro (sem marcadores)

### `tests/test_grid.py`
- [ ] Testar mapeamento de centróides
- [ ] Testar validação de posições
- [ ] Testar casos extremos

---

## 🔄 Integração com Jogo

### Após Vision_Manager pronto:
1. Criar `integration/vision_integration_v2.py`
2. Adaptar `MenuManager` para usar v2
3. Adaptar `GameOrchestrator` para receber estado de visão
4. Testar lado-a-lado com game loop

---

## 📊 Diferenças v1 vs v2

| Aspecto | v1 | v2 |
|---------|----|----|
| Estrutura | Monolítica | Modular (4 componentes) |
| Método capture | `read_frame()` | `capture_frame()` |
| Testes | Não isolados | Isolados por módulo |
| Integração | Acoplada | Desacoplada |
| Sincronização | Fallback | Síncrona |

---

## ⏱️ Cronograma

```
Semana 1:
  - Seg/Ter: camera_simple.py + testes
  - Qua/Qui: aruco_detector.py + testes
  - Sex: grid_calculator.py + testes

Semana 2:
  - Seg/Ter: vision_manager.py
  - Qua/Qui: Integration + adaptações
  - Sex: Testes lado-a-lado com v1

Semana 3:
  - Seg/Ter: Bug fixes
  - Qua/Qui: Documentação
  - Sex: Preparar para decisão final
```

---

## 🚀 Próximos Passos (Phase 3)

1. Começar com `camera_simple.py`
2. Implementar com TDD (test-first)
3. Cada módulo testável isoladamente
4. Sem pressão - v1 é fallback em qualquer momento

**Quando começar**: Após aprovação de Phase 2 setup
