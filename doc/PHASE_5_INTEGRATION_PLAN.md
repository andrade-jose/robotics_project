# Phase 5: Integração com GameOrchestrator - Plano Detalhado

**Data**: 10 de novembro de 2025
**Fase Anterior**: Phase 4 - Calibration System V2 (✅ Completo)
**Estimativa**: 3-4 dias de desenvolvimento
**Status**: 🚀 PRONTO PARA COMEÇAR

---

## 1. VISÃO GERAL

Phase 4 entregou um sistema de calibração completo com:
- ✅ CalibrationOrchestrator (detector + transform + grid + validator)
- ✅ 35 testes passando
- ✅ ~2.000 linhas de código de qualidade profissional
- ✅ Documentação completa

**Objetivo de Phase 5**: Integrar este sistema com o `GameOrchestrator` para que o jogo possa:
1. Usar calibração real da câmera
2. Validar movimentos usando workspace validation
3. Obter posições do grid para controlar o robô

---

## 2. ARQUITETURA DE INTEGRAÇÃO

### Estado Atual (Phase 4 - Isolado)

```
┌─────────────────────────────────────────────┐
│         CalibrationOrchestrator             │
├─────────────────────────────────────────────┤
│ • CalibrationMarkerDetector                 │
│ • BoardTransformCalculator                  │
│ • GridGenerator                             │
│ • WorkspaceValidator                        │
└─────────────────────────────────────────────┘
     ↑
  (frame)
```

### Objetivo de Phase 5 (Integrado)

```
┌──────────────────────┐
│   Camera (V2)        │
└──────────┬───────────┘
           │ frame
           ↓
┌──────────────────────────────────────┐
│   CalibrationOrchestrator (Phase 4)  │
└──────────┬───────────────────────────┘
           │
           ├─→ CalibrationData
           │
           ├─→ grid_positions (9x coords)
           │
           └─→ is_move_valid()

               ↓
┌──────────────────────────────────────┐
│  GameOrchestrator (V2 - NOVO)        │
├──────────────────────────────────────┤
│ • Usa calibration para validar moves │
│ • Obtém posições do grid             │
│ • Integra com TapatanGame            │
│ • Envia movimentos ao RobotService   │
└──────────────────────────────────────┘
```

---

## 3. TAREFAS DE PHASE 5

### 3.1 Criar BoardCoordinateSystem V2 (1 dia)

**Arquivo**: `v2/services/board_coordinate_system_v2.py`

```python
class BoardCoordinateSystemV2:
    """Novo sistema de coordenadas sincronizado com calibração."""

    def __init__(self, calibration_orchestrator: CalibrationOrchestrator):
        """Inicializa com orquestrador de calibração."""
        self.calibrator = calibration_orchestrator
        self._last_calibration = None

    def is_calibrated(self) -> bool:
        """Verifica se está calibrado."""
        return self.calibrator.is_calibrated

    def get_board_position_mm(self, grid_position: int) -> Tuple[float, float]:
        """Obtém coordenada física (mm) para posição do grid (0-8)."""
        if not self.is_calibrated():
            raise ValueError("Sistema não está calibrado")
        # Usa GridGenerator do calibrator
        return self.calibrator.get_position_coordinates(grid_position)

    def get_grid_position(self, pixel_coords: Tuple[int, int]) -> int:
        """Converte pixel da câmera para posição do grid (0-8)."""
        if not self.is_calibrated():
            raise ValueError("Sistema não está calibrado")
        # Usa BoardTransformCalculator do calibrator
        board_coords = self.calibrator.pixel_to_board(pixel_coords)
        position = self.calibrator.board_to_position(board_coords)
        return position

    def validate_move(self, from_pos: int, to_pos: int,
                     occupied_positions: Set[int]) -> bool:
        """Valida movimento usando WorkspaceValidator."""
        if not self.is_calibrated():
            raise ValueError("Sistema não está calibrado")
        # Usa WorkspaceValidator do calibrator
        return self.calibrator.is_move_valid(from_pos, to_pos, occupied_positions)
```

**Checklist**:
- [ ] Criar arquivo `v2/services/board_coordinate_system_v2.py`
- [ ] Implementar classe `BoardCoordinateSystemV2`
- [ ] Adicionar 4 métodos principais
- [ ] Criar testes em `v2/services/tests/test_board_coordinate_system_v2.py`
- [ ] Documentar em docstrings

**Tempo**: 4-6 horas

---

### 3.2 Criar GameOrchestrator V2 (1 dia)

**Arquivo**: `v2/integration/game_orchestrator_v2.py`

```python
class GameOrchestratorV2:
    """Orquestrador do jogo V2 com calibração integrada."""

    def __init__(self,
                 calibration_orchestrator: CalibrationOrchestrator,
                 robot_service: IRobotService,
                 ui_service: Optional[IUIService] = None):
        """Inicializa com dependências."""
        self.calibrator = calibration_orchestrator
        self.robot_service = robot_service
        self.ui_service = ui_service

        # Componentes do jogo
        self.board_coords = BoardCoordinateSystemV2(calibration_orchestrator)
        self.game = TapatanGame()  # Do v1, funciona igual
        self.game_state = GameState.WAITING_CALIBRATION

    def calibrate_from_frame(self, frame: np.ndarray) -> bool:
        """Tenta calibrar a partir de um frame."""
        result = self.calibrator.calibrate(frame)
        if result.is_calibrated:
            self.game_state = GameState.READY
            self._log("✅ Calibração bem-sucedida")
            return True
        else:
            self._log("❌ Falha na calibração")
            return False

    def execute_move(self, from_pos: int, to_pos: int) -> bool:
        """Executa movimento: valida → jogo → robô."""
        # 1. Validar movimento usando calibração
        occupied = self._get_occupied_positions()
        if not self.board_coords.validate_move(from_pos, to_pos, occupied):
            self._log(f"❌ Movimento inválido: {from_pos} → {to_pos}")
            return False

        # 2. Validar movimento no jogo
        if not self.game.is_valid_move(from_pos, to_pos):
            self._log(f"❌ Movimento não permitido no jogo: {from_pos} → {to_pos}")
            return False

        # 3. Executar no jogo
        self.game.make_move(from_pos, to_pos)

        # 4. Enviar ao robô (coordenadas mm)
        target_mm = self.board_coords.get_board_position_mm(to_pos)
        if not self._send_to_robot(target_mm):
            self._log(f"❌ Erro ao enviar movimento ao robô")
            return False

        self._log(f"✅ Movimento executado: {from_pos} → {to_pos}")
        return True

    def get_game_state(self) -> Dict:
        """Retorna estado atual do jogo."""
        return {
            'is_calibrated': self.board_coords.is_calibrated(),
            'board_state': self.game.board,
            'current_player': self.game.current_player,
            'game_status': self.game.status
        }

    def _get_occupied_positions(self) -> Set[int]:
        """Extrai posições ocupadas do tabuleiro."""
        occupied = set()
        for pos, piece in enumerate(self.game.board):
            if piece != GamePiece.EMPTY:
                occupied.add(pos)
        return occupied

    def _send_to_robot(self, target_mm: Tuple[float, float]) -> bool:
        """Envia comando ao robô (coordenadas mm)."""
        try:
            # Assumindo que robot_service.move_to_position() existe
            self.robot_service.move_to_position(target_mm[0], target_mm[1])
            return True
        except Exception as e:
            self._log(f"❌ Erro ao enviar ao robô: {e}")
            return False

    def _log(self, message: str):
        """Log com contexto."""
        print(f"[GAME_ORCH_V2] {message}")
        # TODO: Usar logger real
```

**Checklist**:
- [ ] Criar arquivo `v2/integration/game_orchestrator_v2.py`
- [ ] Implementar classe `GameOrchestratorV2`
- [ ] Adicionar 5+ métodos principais
- [ ] Criar testes em `v2/integration/tests/test_game_orchestrator_v2.py`
- [ ] Documentar fluxo de integração

**Tempo**: 5-7 horas

---

### 3.3 Criar Integration Tests (Câmera → Jogo) (1 dia)

**Arquivo**: `v2/integration/tests/test_integration_v2.py`

```python
class TestIntegrationV2:
    """Testes de integração: calibração → jogo → robô."""

    @pytest.fixture
    def setup(self):
        """Setup com mocks."""
        calibrator = CalibrationOrchestrator(distance_mm=270.0)
        robot_service = Mock(spec=IRobotService)
        game_orch = GameOrchestratorV2(calibrator, robot_service)
        return {
            'calibrator': calibrator,
            'robot_service': robot_service,
            'game_orch': game_orch
        }

    def test_calibration_flow(self, setup):
        """Testa fluxo de calibração."""
        # 1. Frame inicial sem marcadores → não calibrado
        assert not setup['game_orch'].board_coords.is_calibrated()

        # 2. Frame com 2 marcadores → calibrado
        frame = self._create_mock_frame_with_markers()
        assert setup['game_orch'].calibrate_from_frame(frame)
        assert setup['game_orch'].board_coords.is_calibrated()

    def test_move_validation(self, setup):
        """Testa validação de movimento."""
        # Calibrar
        frame = self._create_mock_frame_with_markers()
        setup['game_orch'].calibrate_from_frame(frame)

        # Movimento válido
        assert setup['game_orch'].execute_move(0, 3)

        # Movimento inválido (mesma posição)
        assert not setup['game_orch'].execute_move(3, 3)

    def test_robot_integration(self, setup):
        """Testa integração com robô."""
        # Calibrar
        frame = self._create_mock_frame_with_markers()
        setup['game_orch'].calibrate_from_frame(frame)

        # Executar movimento (deve chamar robot_service.move_to_position)
        setup['game_orch'].execute_move(0, 4)

        # Verificar que robot_service foi chamado
        setup['robot_service'].move_to_position.assert_called()
```

**Checklist**:
- [ ] Criar arquivo `v2/integration/tests/test_integration_v2.py`
- [ ] Implementar 5-7 testes de integração
- [ ] Mock de câmera e robô
- [ ] Testar fluxos completos
- [ ] Validar chamadas ao RobotService

**Tempo**: 3-4 horas

---

### 3.4 Criar Main V2 com Integração (6 horas)

**Arquivo**: `v2/main_v2.py` (ou atualizar `main.py`)

```python
def main_v2():
    """Versão V2 com integração completa."""

    # 1. Inicializar serviços
    camera = CameraManager()  # Usar do v2
    calibrator = CalibrationOrchestrator(distance_mm=270.0)
    robot_service = RobotService()  # Do v1, funciona igual
    ui_service = UIService()  # Do v1

    # 2. Criar GameOrchestrator V2
    game_orch = GameOrchestratorV2(calibrator, robot_service, ui_service)

    # 3. Loop principal
    while True:
        # Capturar frame
        frame = camera.capture_frame()

        # Tentar calibrar
        if not game_orch.board_coords.is_calibrated():
            game_orch.calibrate_from_frame(frame)
            if game_orch.board_coords.is_calibrated():
                print("✅ Sistema calibrado, pronto para jogo!")
                continue

        # Processar entrada do usuário ou IA
        move = game_orch.game.get_next_move()  # IA ou humano
        if move:
            success = game_orch.execute_move(move.from_pos, move.to_pos)
            if not success:
                print(f"❌ Movimento falhado: {move}")

        # UI atualizar
        if ui_service:
            state = game_orch.get_game_state()
            ui_service.update(state)
```

**Checklist**:
- [ ] Criar ou atualizar `v2/main_v2.py`
- [ ] Implementar loop principal
- [ ] Integrar com UI
- [ ] Testes manuais de fluxo
- [ ] Documentar modo de uso

**Tempo**: 2-3 horas

---

### 3.5 Documentação de Phase 5 (4 horas)

**Arquivo**: `v2/PHASE_5_INTEGRATION_COMPLETE.md`

```markdown
# Phase 5: Integração com GameOrchestrator - Concluído

**Data**: [data]
**Status**: ✅ CONCLUÍDO
**Arquivos Criados**: 4
**Linhas de Código**: ~1.500

## O que foi entregue

1. BoardCoordinateSystemV2
   - Sincronizado com calibração
   - Converte pixel ↔ posição do grid
   - Valida movimentos

2. GameOrchestratorV2
   - Orquestra todo o fluxo do jogo
   - Integra calibração + jogo + robô
   - Interface limpa e bem documentada

3. Integration Tests
   - 7+ testes de ponta-a-ponta
   - Mocks de câmera e robô
   - Validação de fluxos

4. Documentação Completa
   - Architecture V2
   - Guia de uso
   - Exemplos de código
```

**Checklist**:
- [ ] Criar documentação de Phase 5
- [ ] Adicionar exemplos de uso
- [ ] Documentar fluxo de integração
- [ ] Listar próximos passos (Phase 6)

**Tempo**: 2-3 horas

---

## 4. TIMELINE DE PHASE 5

```
Dia 1:
  [ ] Manhã: BoardCoordinateSystemV2 (4-6h)
  [ ] Tarde: Testes para BCS V2 (2-3h)

Dia 2:
  [ ] Manhã: GameOrchestratorV2 (5-7h)
  [ ] Tarde: Testes para GameOrch V2 (2-3h)

Dia 3:
  [ ] Manhã: Integration Tests (3-4h)
  [ ] Tarde: Main V2 e testes manuais (2-3h)

Dia 4:
  [ ] Documentação e refinamentos (4h)
  [ ] Commit e tag de Phase 5 (1h)

TOTAL: 3-4 dias
```

---

## 5. CRITÉRIOS DE SUCESSO

✅ BoardCoordinateSystemV2 implementado e testado
✅ GameOrchestratorV2 implementado e testado
✅ Integration tests passando (calibração → jogo → robô)
✅ Main V2 funciona com fluxo completo
✅ Documentação clara e completa
✅ Código compilável sem erros
✅ Testes: 50+ passing (incluindo Phase 4)

---

## 6. BLOCKERS POTENCIAIS

| Blocker | Mitigação |
|---------|-----------|
| RobotService não tem método `move_to_position()` | Usar método existente ou criar wrapper |
| Formato de coordenadas incompatível | Converter no GameOrchestrator |
| Camera não disponível | Usar mock frame nos testes |
| UI incompatível com V2 | Criar adaptador ou usar mock |

---

## 7. PRÓXIMO PASSO APÓS PHASE 5

### Phase 6: Testes com Robô Real (1-2 semanas)

- [ ] Integração com UR3e real
- [ ] Testes de movimentos reais
- [ ] Validação de segurança e limites
- [ ] Decisão final: V1 vs V2

---

## 8. COMO EXECUTAR PHASE 5

1. Ler este documento completamente
2. Implementar tarefas na ordem listada
3. Rodar testes após cada tarefa
4. Fazer commits incrementais
5. Documentar qualquer descoberta

**Comando para começar**:
```bash
cd c:\Venv\robotics_project
git checkout main
python -m pytest v2/vision/tests/ -v  # Verificar Phase 4 ainda OK
# Começar com 3.1: BoardCoordinateSystemV2
```

---

**Próximo passo**: Implementar BoardCoordinateSystemV2 (Tarefa 3.1)

Recomendação: Começar **agora** (estimado 1 dia para terminar Tarefas 3.1 + 3.2)

---

**Assinado**: Claude Code
**Data**: 10 de novembro de 2025
**Status**: 🚀 **PRONTO PARA INICIAR PHASE 5**