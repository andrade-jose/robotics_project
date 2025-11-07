# Calibration System V2 - Documentação Completa

## 1. Visão Geral

O sistema de calibração V2 implementa um pipeline de 2 marcadores ArUco para calibração automática do tabuleiro de Tapatan (3x3).

### Física do Sistema

- **Marcador 0 (Origem)**: Canto inferior esquerdo → Define (0,0,0)
- **Marcador 1 (X-axis)**: Canto superior direito → Define direção X
- **Eixo Y**: Perpendicular a X no plano (rotação 90°)
- **Eixo Z**: Normal ao plano (sempre cima, (0,0,1))
- **Grid**: 3×3 células geradas através de interpolação linear

### Pipeline Completo

```
Frame
  ↓
[1] CalibrationMarkerDetector
  ├─ Detecta exatamente 2 marcadores ArUco
  ├─ Extrai poses (centro, cantos, ângulo)
  ├─ Aplica média móvel (3-5 frames)
  └─ Retorna CalibrationData
  ↓
[2] BoardTransformCalculator
  ├─ Constrói matriz de transformação
  ├─ Pixel → Board (mm)
  ├─ Validação de roundtrip
  └─ Retorna TransformMatrix
  ↓
[3] GridGenerator
  ├─ Gera 9 posições do grid 3x3
  ├─ Centro de cada célula (x_mm, y_mm, 0.0)
  ├─ Valida que células estão dentro dos limites
  └─ Retorna Dict {position: (x, y, z)}
  ↓
[4] WorkspaceValidator
  ├─ Define limites de workspace
  ├─ Aplica margem de segurança
  ├─ Valida posições individuais
  ├─ Valida movimentos (colisão)
  └─ Retorna validações
  ↓
CalibrationOrchestrator
  └─ Orquestra pipeline completo
```

## 2. Componentes do Sistema

### 2.1 CalibrationMarkerDetector

**Arquivo**: `calibration_marker_detector.py`

**Responsabilidades**:
- Detectar exatamente 2 marcadores ArUco (código 250, 6x6 bits)
- Extrair poses (centro pixel, cantos, vetor normal, ângulo)
- Aplicar suavização via média móvel (3-5 frames)
- Validar que detecção é fisicamente plausível
- Extrair vetores dos eixos X, Y, Z

**Classes**:
```python
@dataclass
class MarkerPose:
    marker_id: int
    center: Tuple[float, float]      # (x, y) pixels
    corners: np.ndarray              # 4 cantos do marcador
    normal: Tuple[float, float, float] # (0,0,1) para Z=0
    orientation_angle: float         # Ângulo em graus

@dataclass
class CalibrationData:
    marker0_pose: MarkerPose         # Origem (canto inf. esq.)
    marker1_pose: MarkerPose         # X-axis (canto sup. dir.)
    distance_mm: float               # Distância real entre marcadores
    distance_pixels: float           # Distância em pixels
    scale: float                     # pixels_to_mm ratio
    is_valid: bool
    confidence: float                # 0-1, aumenta com smoothing
```

**Métodos Principais**:
```python
# Detector
detector = CalibrationMarkerDetector(distance_mm=270.0, smoothing_frames=3)
calibration = detector.detect(frame)  # → CalibrationData | None

# Validação
is_valid = detector.validate_calibration(calibration)

# Extração de eixos
axes = detector.get_axis_vectors(calibration)
# Retorna: {'X': vec, 'Y': vec, 'Z': vec, 'origin_pixels': (x,y), 'scale': float}

# Visualização
frame_marked = detector.draw_calibration(frame, calibration)
```

**Características**:
- ✅ Detecção robusta com feedback
- ✅ Suavização por média móvel (deque com maxlen=smoothing_frames)
- ✅ Fallback para última calibração válida se frame não tem 2 marcadores
- ✅ Validação de distância plausível (50-2000px)
- ✅ Visualização para debugging

---

### 2.2 BoardTransformCalculator

**Arquivo**: `board_transform_calculator.py`

**Responsabilidades**:
- Construir matriz de transformação a partir de CalibrationData
- Converter pixel → coordenadas de tabuleiro (mm)
- Converter tabuleiro → pixel (operação inversa)
- Validar transformação via roundtrip

**Classes**:
```python
@dataclass
class TransformMatrix:
    origin_pixels: Tuple[float, float] # Centro do marcador 0
    scale: float                       # pixels_to_mm
    axis_x: np.ndarray                 # Vetor unitário X
    axis_y: np.ndarray                 # Vetor unitário Y
    axis_z: np.ndarray                 # Vetor unitário Z (0,0,1)
    is_valid: bool
    confidence: float
```

**Métodos Principais**:
```python
# Transformador
transform = BoardTransformCalculator(calibration_data)

# Converter pixel → board (mm)
board_x, board_y, board_z = transform.pixel_to_board((pixel_x, pixel_y))

# Converter board → pixel (inverso)
pixel_x, pixel_y = transform.board_to_pixel((board_x, board_y, 0.0))

# Validar transformação
is_valid = transform.validate_transform()  # Roundtrip pixel→board→pixel

# Obter informações
info = transform.get_transform_info()
```

**Algoritmo de Transformação**:

1. **Pixel → Board**:
   ```
   rel_vector = (pixel_x - origin_x, pixel_y - origin_y, 0.0)
   board_x = dot(rel_vector, axis_x) * scale
   board_y = dot(rel_vector, axis_y) * scale
   board_z = 0.0
   ```

2. **Board → Pixel**:
   ```
   x_rel_norm = board_x / scale
   y_rel_norm = board_y / scale
   rel_vector = x_rel_norm * axis_x + y_rel_norm * axis_y
   pixel_x = origin_x + rel_vector[0]
   pixel_y = origin_y + rel_vector[1]
   ```

---

### 2.3 GridGenerator

**Arquivo**: `grid_generator.py`

**Responsabilidades**:
- Gerar 9 posições do grid 3x3 em coordenadas físicas (mm)
- Converter entre posição de célula ↔ pixel ↔ coordenadas board
- Validar que todas as células estão dentro de limites
- Fornecer mapeamento de posições

**Classes**:
```python
@dataclass
class GridCell:
    position: int                      # 0-8
    center_mm: Tuple[float, float, float] # (x, y, 0) em mm
    is_within_bounds: bool
    confidence: float
```

**Layout do Grid**:
```
0 | 1 | 2
---------
3 | 4 | 5
---------
6 | 7 | 8
```

**Métodos Principais**:
```python
# Gerador
grid = GridGenerator(transform_calculator)

# Obter todas as 9 posições
positions = grid.get_grid_positions()  # {0: (x,y,z), 1: (x,y,z), ...}

# Obter posição específica
coords = grid.get_cell_position(position)  # (x_mm, y_mm, 0.0)

# Converter pixel → posição mais próxima
position = grid.pixel_to_position((pixel_x, pixel_y))

# Converter posição → pixel (para visualização)
pixel_x, pixel_y = grid.position_to_pixel(position)

# Validar grid
is_valid = grid.validate_grid()  # Todas as 9 células dentro dos limites

# Obter limites
bounds = grid.get_grid_bounds()
```

**Cálculo de Posições**:
```
cell_size = distance_mm / 3

Para cada posição (0-8):
  row = position // 3
  col = position % 3
  board_x = (col + 0.5) * cell_size
  board_y = (row + 0.5) * cell_size
  center_mm = (board_x, board_y, 0.0)
```

---

### 2.4 WorkspaceValidator

**Arquivo**: `workspace_validator.py`

**Responsabilidades**:
- Definir limites físicos e de segurança do workspace
- Validar posições individuais (dentro dos limites)
- Validar movimentos (não colidir com peças)
- Atualizar estado de peças ocupadas
- Calcular movimentos válidos a partir de uma posição

**Classes**:
```python
@dataclass
class WorkspaceConstraints:
    min_x_mm: float              # Limite X mínimo
    max_x_mm: float              # Limite X máximo
    min_y_mm: float              # Limite Y mínimo
    max_y_mm: float              # Limite Y máximo
    safety_margin_mm: float      # Margem de segurança
    collision_zones: list        # Zonas de colisão futuras
```

**Métodos Principais**:
```python
# Validador
validator = WorkspaceValidator(grid, safety_margin_mm=10.0)

# Validar posição
is_valid = validator.is_position_valid(position)

# Validar coordenadas
is_valid = validator.is_coordinates_valid(board_x_mm, board_y_mm)

# Validar movimento
can_move = validator.can_move(from_pos, to_pos, occupied_positions={0, 8})

# Atualizar peças no tabuleiro
validator.update_piece_positions({0, 4, 8})

# Obter movimentos válidos a partir de uma posição
valid_moves = validator.get_valid_moves(from_position)  # Set[int]

# Obter margens de segurança
margins = validator.get_safety_margins()

# Validar todas as 9 posições
is_all_valid = validator.validate_all_positions()
```

---

### 2.5 CalibrationOrchestrator

**Arquivo**: `calibration_orchestrator.py`

**Responsabilidades**:
- Orquestrar pipeline completo de calibração
- Gerenciar estado de calibração (NOT_CALIBRATED → CALIBRATING → CALIBRATED)
- Fornecer interface simples para uso do jogo
- Fallback para última calibração válida
- Logging detalhado

**Estados**:
```python
class CalibrationState(Enum):
    NOT_CALIBRATED = "not_calibrated"
    CALIBRATING = "calibrating"
    CALIBRATED = "calibrated"
    FAILED = "failed"
```

**Métodos Principais**:
```python
# Orquestrador
orchestrator = CalibrationOrchestrator(
    distance_mm=270.0,           # Distância entre marcadores
    smoothing_frames=3,
    safety_margin_mm=10.0
)

# Executar calibração completa
result = orchestrator.calibrate(frame)
# Retorna: CalibrationResult com estado completo

# Usar grid e validador
if result.is_calibrated:
    position_coords = result.grid_positions[0]
    valid_moves = orchestrator.get_valid_moves(from_position, occupied_positions)
    can_move = orchestrator.is_move_valid(from_pos, to_pos, occupied_positions)

# Consultar status
status = orchestrator.get_calibration_status()
detailed_info = orchestrator.get_detailed_info()
```

---

## 3. Fluxo de Uso Completo

### 3.1 Inicialização e Calibração

```python
from v2.vision.calibration_orchestrator import CalibrationOrchestrator

# Criar orquestrador
calibrator = CalibrationOrchestrator(
    distance_mm=270.0,  # Distância real entre os 2 marcadores
    smoothing_frames=3   # Usar média móvel de 3 frames
)

# Calibrar a partir de um frame
result = calibrator.calibrate(frame)

if result.is_calibrated:
    print(f"Calibração bem-sucedida (confiança={result.confidence:.2f})")
    print(f"Grid positions: {result.grid_positions}")
else:
    print(f"Calibração falhou: {result.error_message}")
```

### 3.2 Usar Para o Jogo

```python
# Verificar se sistema está calibrado
status = calibrator.get_calibration_status()
if status["is_calibrated"]:
    # Validar movimento
    from_pos = 0  # Posição atual
    to_pos = 4    # Posição desejada
    occupied = {8}  # Peças ocupando posição 8

    if calibrator.is_move_valid(from_pos, to_pos, occupied):
        # Movimento válido - executar
        print(f"Movimento {from_pos} → {to_pos} é válido")
    else:
        print(f"Movimento {from_pos} → {to_pos} é inválido")

    # Obter todos os movimentos válidos
    valid_moves = calibrator.get_valid_moves(from_pos, occupied)
    print(f"Movimentos válidos de {from_pos}: {valid_moves}")
```

### 3.3 Integração com VisionManager

```python
from v2.vision.vision_manager import VisionManager
from v2.vision.calibration_orchestrator import CalibrationOrchestrator

# Criar ambos
vision_manager = VisionManager(use_threading=False)
calibrator = CalibrationOrchestrator(distance_mm=270.0)

# Iniciar visão
vision_manager.start()

# Calibrar a partir do primeiro frame
frame = vision_manager.camera.capture_frame()
calib_result = calibrator.calibrate(frame)

if calib_result.is_calibrated:
    print("Sistema calibrado e pronto para jogo")

    # Usar para validar movimentos durante jogo
    while game_is_running:
        # ... lógica do jogo ...
        if user_requests_move(from_pos, to_pos):
            if calibrator.is_move_valid(from_pos, to_pos, occupied_positions):
                # Executar movimento
                pass
```

---

## 4. Testes

**Arquivo**: `tests/test_calibration.py`

**Cobertura**: 35 testes totais

### 4.1 Executar Testes

```bash
# Todos os testes de calibração
pytest v2/vision/tests/test_calibration.py -v

# Testes específicos
pytest v2/vision/tests/test_calibration.py::TestCalibrationMarkerDetector -v
pytest v2/vision/tests/test_calibration.py::TestBoardTransformCalculator -v
pytest v2/vision/tests/test_calibration.py::TestGridGenerator -v
pytest v2/vision/tests/test_calibration.py::TestWorkspaceValidator -v
pytest v2/vision/tests/test_calibration.py::TestCalibrationOrchestrator -v
```

### 4.2 Suites de Teste

1. **TestCalibrationMarkerDetector** (10 testes)
   - Inicialização
   - Detecção com diferentes cenários
   - Cálculo de centro, distância, orientação
   - Validação de calibração
   - Extração de eixos

2. **TestBoardTransformCalculator** (5 testes)
   - Inicialização
   - Conversão pixel → board
   - Conversão board → pixel
   - Validação de roundtrip

3. **TestGridGenerator** (7 testes)
   - Inicialização
   - Contagem de 9 posições
   - Validade de posições
   - Conversão pixel → posição
   - Conversão posição → pixel
   - Validação de grid
   - Limites do grid

4. **TestWorkspaceValidator** (9 testes)
   - Inicialização
   - Validação de posições
   - Validação de movimentos
   - Atualização de peças
   - Movimentos válidos
   - Validação de todas as posições

5. **TestCalibrationOrchestrator** (4 testes)
   - Inicialização
   - Status de calibração
   - Acesso sem calibração

---

## 5. Parâmetros Configuráveis

### 5.1 CalibrationMarkerDetector

```python
detector = CalibrationMarkerDetector(
    aruco_dict_size=6,          # Tamanho do dicionário (6x6 bits)
    marker_size=250,            # Código do marcador
    distance_mm=270.0,          # Distância real entre marcadores
    smoothing_frames=3,         # Frames para média móvel (3-5)
    logger=None                 # Logger customizado
)
```

### 5.2 WorkspaceValidator

```python
validator = WorkspaceValidator(
    grid_generator,             # GridGenerator
    safety_margin_mm=10.0,      # Margem de segurança (10mm)
    logger=None                 # Logger customizado
)
```

### 5.3 CalibrationOrchestrator

```python
orchestrator = CalibrationOrchestrator(
    distance_mm=270.0,          # Distância entre marcadores
    smoothing_frames=3,         # Frames para média móvel
    safety_margin_mm=10.0,      # Margem de segurança
    logger=None                 # Logger customizado
)
```

---

## 6. Logging e Debugging

Todos os componentes registram eventos detalhados com prefixo [TAG]:

```
[CALIB]      - CalibrationMarkerDetector
[TRANSFORM]  - BoardTransformCalculator
[GRID]       - GridGenerator
[WORKSPACE]  - WorkspaceValidator
```

### 6.1 Ativar Logging Detalhado

```python
import logging

# Configurar para DEBUG
logging.basicConfig(level=logging.DEBUG)

# Ou para logger específico
logger = logging.getLogger("calibration_system")
logger.setLevel(logging.DEBUG)
```

---

## 7. Tratamento de Erros

### 7.1 Cenários de Falha

| Cenário | Comportamento |
|---------|---------------|
| Não encontra 2 marcadores | Retorna None, usa última calibração válida |
| Transformação inválida | Falha no pipeline, retorna erro |
| Grid fora dos limites | Falha na validação |
| Workspace inválido | Falha na validação de workspace |

### 7.2 Fallback para Última Calibração Válida

```python
# Se calibração falha, usa última válida
result = orchestrator.calibrate(frame)
# Se resultado.is_calibrated = False:
#   - Mas has_last_valid = True
#   - Sistema continua usando última calibração ✓
#   - Permite tolerância a falhas temporárias
```

---

## 8. Validação Física

O sistema valida:

1. **Distância entre marcadores**: 50-2000 pixels
2. **Escala positiva**: scale > 0
3. **Transformação válida**: roundtrip pixel→board→pixel < 1px erro
4. **Grid válido**: todas as 9 células dentro dos limites
5. **Workspace válido**: todas as posições alcançáveis com margem de segurança

---

## 9. Próximas Etapas

Para integração com o sistema de jogo:

1. ✅ Sistema de calibração completo
2. ⏳ Integração com GameOrchestrator (usar validador)
3. ⏳ Integração com RobotService (converter posições para coordenadas do robô)
4. ⏳ Testes de ponta-a-ponta (câmera → jogo → robô)
5. ⏳ Tuning de parâmetros (margem de segurança, smoothing frames, etc.)

---

## 10. Resumo Técnico

| Componente | LOC | Métodos | Responsabilidade |
|-----------|-----|---------|------------------|
| CalibrationMarkerDetector | 400+ | 8 | Detectar 2 marcadores |
| BoardTransformCalculator | 300+ | 6 | Transformação pixel→board |
| GridGenerator | 380+ | 10 | Gerar 9 posições grid |
| WorkspaceValidator | 350+ | 10 | Validar movimentos |
| CalibrationOrchestrator | 280+ | 8 | Orquestrar pipeline |
| Tests | 600+ | 35 | Cobertura completa |

**Total**: ~2.000+ linhas de código, 35 testes, 100% passing
