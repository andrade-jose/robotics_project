"""
Testes para GameOrchestratorV2

Testes cobrem:
- Inicialização com CalibrationOrchestrator
- Fluxo de calibração
- Execução de movimentos (validação → jogo → robô)
- Estado do jogo
- Tratamento de erros (não calibrado, movimento inválido, etc.)
- Integração com RobotService
"""

import pytest
import logging
from unittest.mock import Mock, MagicMock, patch
import numpy as np

try:
    from v2.integration.game_orchestrator_v2 import (
        GameOrchestratorV2,
        GameState,
        MoveResult,
    )
    from v2.vision.calibration_orchestrator import (
        CalibrationOrchestrator,
        CalibrationResult,
        CalibrationState,
    )
except ImportError:
    from integration.game_orchestrator_v2 import (
        GameOrchestratorV2,
        GameState,
        MoveResult,
    )
    from vision.calibration_orchestrator import (
        CalibrationOrchestrator,
        CalibrationResult,
        CalibrationState,
    )


class TestGameOrchestratorV2:
    """Testes para GameOrchestratorV2."""

    @pytest.fixture
    def mock_calibrator(self):
        """Cria mock de CalibrationOrchestrator."""
        calibrator = Mock(spec=CalibrationOrchestrator)

        # Grid positions para uso quando calibrado
        grid_positions = {
            0: (0.0, 270.0, 0.0),
            1: (135.0, 270.0, 0.0),
            2: (270.0, 270.0, 0.0),
            3: (0.0, 135.0, 0.0),
            4: (135.0, 135.0, 0.0),
            5: (270.0, 135.0, 0.0),
            6: (0.0, 0.0, 0.0),
            7: (135.0, 0.0, 0.0),
            8: (270.0, 0.0, 0.0),
        }

        # Status não calibrado por padrão
        calibrator.get_calibration_status.return_value = {
            "is_calibrated": False,
            "state": "not_calibrated",
            "calibration_attempts": 0,
            "successful_calibrations": 0,
        }

        calibrator.last_valid_result = None

        # Setup para quando calibrate() for chamado (simula calibração bem-sucedida)
        def mock_calibrate(frame):
            # Atualizar status para calibrado
            result = Mock(spec=CalibrationResult)
            result.is_calibrated = True
            result.grid_positions = grid_positions
            result.transform = Mock()
            result.grid = Mock()
            result.validator = Mock()
            result.confidence = 1.0
            result.error_message = None

            # Atualizar estado do mock
            calibrator.last_valid_result = result
            calibrator.get_calibration_status.return_value = {
                "is_calibrated": True,
                "state": "calibrated",
                "calibration_attempts": 1,
                "successful_calibrations": 1,
            }
            calibrator.get_grid_position.side_effect = lambda pos: grid_positions.get(pos)
            calibrator.is_move_valid.return_value = True
            calibrator.get_valid_moves.return_value = {0, 1, 3}

            return result

        calibrator.calibrate.side_effect = mock_calibrate
        return calibrator

    @pytest.fixture
    def mock_calibrator_calibrated(self):
        """Cria mock de CalibrationOrchestrator calibrado."""
        calibrator = Mock(spec=CalibrationOrchestrator)

        grid_positions = {
            0: (0.0, 270.0, 0.0),
            1: (135.0, 270.0, 0.0),
            2: (270.0, 270.0, 0.0),
            3: (0.0, 135.0, 0.0),
            4: (135.0, 135.0, 0.0),
            5: (270.0, 135.0, 0.0),
            6: (0.0, 0.0, 0.0),
            7: (135.0, 0.0, 0.0),
            8: (270.0, 0.0, 0.0),
        }

        result = Mock(spec=CalibrationResult)
        result.is_calibrated = True
        result.grid_positions = grid_positions
        result.transform = Mock()
        result.grid = Mock()
        result.validator = Mock()
        result.confidence = 1.0
        result.error_message = None

        calibrator.last_valid_result = result
        calibrator.get_calibration_status.return_value = {
            "is_calibrated": True,
            "state": "calibrated",
            "calibration_attempts": 1,
            "successful_calibrations": 1,
        }

        calibrator.calibrate.return_value = result
        calibrator.get_grid_position.side_effect = lambda pos: grid_positions.get(pos)
        calibrator.is_move_valid.return_value = True
        calibrator.get_valid_moves.return_value = {0, 1, 3}

        return calibrator

    @pytest.fixture
    def mock_robot_service(self):
        """Cria mock de RobotService."""
        robot = Mock()
        robot.move_to_position = Mock(return_value=True)
        robot.move_tcp = Mock(return_value=True)
        return robot

    @pytest.fixture
    def mock_game(self):
        """Cria mock de TapatanGame."""
        game = Mock()
        game.board = [None] * 9  # 9 posições vazias
        game.current_player = 1
        game.status = "playing"
        game.is_valid_move = Mock(return_value=True)
        game.make_move = Mock()
        return game

    @pytest.fixture
    def game_orch(self, mock_calibrator, mock_robot_service):
        """Cria GameOrchestratorV2 com mocks."""
        orch = GameOrchestratorV2(mock_calibrator, robot_service=mock_robot_service)
        # Substituir game por mock
        orch.game = Mock()
        orch.game.board = [None] * 9
        orch.game.current_player = 1
        orch.game.status = "playing"
        orch.game.is_valid_move = Mock(return_value=True)
        orch.game.make_move = Mock()
        return orch

    @pytest.fixture
    def game_orch_calibrated(self, mock_calibrator_calibrated, mock_robot_service):
        """Cria GameOrchestratorV2 calibrado."""
        orch = GameOrchestratorV2(mock_calibrator_calibrated, robot_service=mock_robot_service)
        orch.game = Mock()
        orch.game.board = [None] * 9
        orch.game.current_player = 1
        orch.game.status = "playing"
        orch.game.is_valid_move = Mock(return_value=True)
        orch.game.make_move = Mock()
        return orch

    # ========== Testes de Inicialização ==========

    def test_initialization(self, game_orch, mock_calibrator, mock_robot_service):
        """Testa inicialização básica."""
        assert game_orch.calibrator == mock_calibrator
        assert game_orch.robot_service == mock_robot_service
        assert game_orch.board_coords is not None
        assert game_orch.game is not None
        assert game_orch.state == GameState.NOT_INITIALIZED
        assert game_orch.move_history == []

    def test_initialization_without_robot_service(self, mock_calibrator):
        """Testa inicialização sem RobotService."""
        orch = GameOrchestratorV2(mock_calibrator, robot_service=None)
        assert orch.robot_service is None
        assert orch.board_coords is not None

    def test_initialization_with_custom_logger(self, mock_calibrator):
        """Testa inicialização com logger customizado."""
        custom_logger = logging.getLogger("test")
        orch = GameOrchestratorV2(mock_calibrator, logger=custom_logger)
        assert orch.logger == custom_logger

    # ========== Testes de Calibração ==========

    def test_calibrate_from_frame_success(self, mock_calibrator_calibrated, mock_robot_service):
        """Testa calibração bem-sucedida."""
        # Usar mock_calibrator_calibrated que já está calibrado
        game_orch = GameOrchestratorV2(mock_calibrator_calibrated, robot_service=mock_robot_service)
        game_orch.game = Mock()

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = game_orch.calibrate_from_frame(frame)

        assert result is True
        assert game_orch.state == GameState.READY
        assert game_orch.is_calibrated()

    def test_calibrate_from_frame_failure(self, mock_robot_service):
        """Testa calibração falhada."""
        # Criar mock novo para teste de falha
        calibrator_fail = Mock(spec=CalibrationOrchestrator)
        calibrator_fail.get_calibration_status.return_value = {
            "is_calibrated": False,
            "state": "not_calibrated",
            "calibration_attempts": 0,
            "successful_calibrations": 0,
        }
        calibrator_fail.last_valid_result = None

        # Mock retorna falha na calibração
        calibrator_fail.calibrate.return_value = Mock(
            is_calibrated=False,
            error_message="Marcadores não detectados",
            confidence=0.0,
        )

        game_orch = GameOrchestratorV2(calibrator_fail, robot_service=mock_robot_service)
        game_orch.game = Mock()

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = game_orch.calibrate_from_frame(frame)

        assert result is False
        assert game_orch.state == GameState.WAITING_CALIBRATION
        assert game_orch.last_error == "Marcadores não detectados"

    def test_is_calibrated(self, mock_calibrator, mock_calibrator_calibrated, mock_robot_service):
        """Testa is_calibrated()."""
        # Com calibrador não calibrado
        orch1 = GameOrchestratorV2(mock_calibrator, robot_service=mock_robot_service)
        orch1.game = Mock()
        assert not orch1.is_calibrated()

        # Com calibrador calibrado
        orch2 = GameOrchestratorV2(mock_calibrator_calibrated, robot_service=mock_robot_service)
        orch2.game = Mock()
        assert orch2.is_calibrated()

    # ========== Testes de Execução de Movimentos ==========

    def test_execute_move_not_calibrated(self, game_orch):
        """Testa execute_move quando não calibrado."""
        result = game_orch.execute_move(0, 4)

        assert not result.success
        assert result.move_from == 0
        assert result.move_to == 4
        assert "não está calibrado" in result.reason.lower()
        assert not result.executed_by_robot

    def test_execute_move_valid(self, game_orch_calibrated):
        """Testa execute_move com movimento válido."""
        result = game_orch_calibrated.execute_move(0, 4)

        assert result.success
        assert result.move_from == 0
        assert result.move_to == 4
        assert result.reason is None
        # Robot service deve ter sido chamado
        assert game_orch_calibrated.robot_service.move_to_position.called

    def test_execute_move_without_robot_service(self, mock_calibrator_calibrated):
        """Testa execute_move sem RobotService configurado."""
        orch = GameOrchestratorV2(mock_calibrator_calibrated, robot_service=None)
        orch.game = Mock()
        orch.game.board = [None] * 9
        orch.game.is_valid_move = Mock(return_value=True)
        orch.game.make_move = Mock()

        result = orch.execute_move(0, 4, send_to_robot=True)

        # Deve suceder no jogo, mas sem envio ao robô
        assert result.success
        assert not result.executed_by_robot

    def test_execute_move_invalid_game(self, game_orch_calibrated):
        """Testa execute_move com movimento inválido no jogo."""
        game_orch_calibrated.game.is_valid_move.return_value = False

        result = game_orch_calibrated.execute_move(0, 4)

        assert not result.success
        assert "não permitido no jogo" in result.reason.lower()

    def test_execute_move_without_sending_to_robot(self, game_orch_calibrated):
        """Testa execute_move com send_to_robot=False."""
        result = game_orch_calibrated.execute_move(0, 4, send_to_robot=False)

        assert result.success
        assert not result.executed_by_robot
        # RobotService não deve ter sido chamado
        assert not game_orch_calibrated.robot_service.move_to_position.called

    def test_execute_move_records_history(self, game_orch_calibrated):
        """Testa se movimento é registrado no histórico."""
        game_orch_calibrated.execute_move(0, 4)

        assert len(game_orch_calibrated.move_history) == 1
        assert game_orch_calibrated.move_history[0]['from'] == 0
        assert game_orch_calibrated.move_history[0]['to'] == 4
        assert game_orch_calibrated.move_history[0]['success'] is True

    # ========== Testes de Estado do Jogo ==========

    def test_get_game_state_not_calibrated(self, game_orch):
        """Testa get_game_state quando não calibrado."""
        state = game_orch.get_game_state()

        assert state['orchestrator_state'] == 'not_initialized'
        assert not state['is_calibrated']
        assert state['move_history'] == []

    def test_get_game_state_calibrated(self, game_orch_calibrated):
        """Testa get_game_state quando calibrado."""
        game_orch_calibrated.state = GameState.READY

        state = game_orch_calibrated.get_game_state()

        assert state['orchestrator_state'] == 'ready'
        assert state['is_calibrated']
        assert 'calibration_info' in state

    def test_get_detailed_info(self, game_orch_calibrated):
        """Testa get_detailed_info()."""
        info = game_orch_calibrated.get_detailed_info()

        assert 'state' in info
        assert 'is_calibrated' in info
        assert 'calibration_status' in info
        assert 'board_positions' in info
        assert 'game_state' in info

    # ========== Testes de Movimentos Válidos ==========

    def test_get_valid_moves_not_calibrated(self, game_orch):
        """Testa get_valid_moves_for_position quando não calibrado."""
        moves = game_orch.get_valid_moves_for_position(4)
        assert moves == set()

    def test_get_valid_moves_calibrated(self, game_orch_calibrated):
        """Testa get_valid_moves_for_position quando calibrado."""
        moves = game_orch_calibrated.get_valid_moves_for_position(4)
        assert isinstance(moves, set)

    # ========== Testes de Reset ==========

    def test_reset_game(self, game_orch_calibrated):
        """Testa reset_game()."""
        # Adicionar movimento ao histórico
        game_orch_calibrated.move_history = [{"from": 0, "to": 4}]
        game_orch_calibrated.last_error = "Algum erro"

        game_orch_calibrated.reset_game()

        assert game_orch_calibrated.move_history == []
        assert game_orch_calibrated.last_error is None

    # ========== Testes de Representação ==========

    def test_repr_not_calibrated(self, game_orch):
        """Testa __repr__ quando não calibrado."""
        repr_str = repr(game_orch)
        assert "GameOrchestratorV2" in repr_str
        assert "NÃO CALIBRADO" in repr_str

    def test_repr_calibrated(self, game_orch_calibrated):
        """Testa __repr__ quando calibrado."""
        repr_str = repr(game_orch_calibrated)
        assert "GameOrchestratorV2" in repr_str
        assert "CALIBRADO" in repr_str

    # ========== Testes de Fluxo Completo ==========

    def test_full_game_flow(self, mock_calibrator, mock_robot_service):
        """Testa fluxo completo: calibração → movimento."""
        # Usar mock_calibrator inicial (não calibrado) que será "calibrado" no passo 2
        orch = GameOrchestratorV2(mock_calibrator, mock_robot_service)
        orch.game = Mock()
        orch.game.board = [None] * 9
        orch.game.is_valid_move = Mock(return_value=True)
        orch.game.make_move = Mock()

        # 1. Verificar não calibrado
        assert not orch.is_calibrated()

        # 2. Calibrar
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        assert orch.calibrate_from_frame(frame)
        assert orch.is_calibrated()

        # 3. Executar movimento
        result = orch.execute_move(0, 4)
        assert result.success

        # 4. Verificar histórico
        assert len(orch.move_history) == 1

    def test_multiple_moves_flow(self, game_orch_calibrated):
        """Testa múltiplos movimentos em sequência."""
        # Executar 3 movimentos
        moves = [(0, 4), (4, 8), (8, 3)]

        for from_pos, to_pos in moves:
            result = game_orch_calibrated.execute_move(from_pos, to_pos)
            assert result.success

        assert len(game_orch_calibrated.move_history) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])