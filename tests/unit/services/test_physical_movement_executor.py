"""
Testes Unitários para PhysicalMovementExecutor
Tests for the physical movement executor that handles all robot physical movements.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

from services.physical_movement_executor import PhysicalMovementExecutor


class TestPhysicalMovementExecutorInitialization:
    """Testes de inicialização do executor."""

    def test_init_with_dependencies(self, mock_robot_controller, mock_board_coords, config_robo):
        """Testa inicialização com dependências."""
        executor = PhysicalMovementExecutor(
            robot_service=mock_robot_controller,
            board_coords=mock_board_coords,
            config_robo=config_robo
        )

        assert executor.robot_service == mock_robot_controller
        assert executor.board_coords == mock_board_coords
        assert executor.config_robo == config_robo


class TestPhysicalMovementExecutorSimpleMovement:
    """Testes de movimento simples."""

    @pytest.fixture
    def executor(self, mock_robot_controller, mock_board_coords, config_robo):
        return PhysicalMovementExecutor(
            robot_service=mock_robot_controller,
            board_coords=mock_board_coords,
            config_robo=config_robo
        )

    def test_executar_movimento_simples(self, executor, mock_robot_controller, mock_board_coords):
        """Testa execução de movimento simples para uma posição."""
        position = 4
        mock_board_coords.get_position.return_value = (-0.200, -0.267, 0.15)
        mock_robot_controller.move_to_pose.return_value = True

        result = executor.executar_movimento_simples(position)

        assert result is True
        mock_board_coords.get_position.assert_called_with(position)
        mock_robot_controller.move_to_pose.assert_called()

    def test_executar_movimento_simples_invalid_position(self, executor, mock_board_coords):
        """Testa movimento simples para posição inválida."""
        mock_board_coords.get_position.return_value = None

        result = executor.executar_movimento_simples(99)

        assert result is False


class TestPhysicalMovementExecutorPieceMovement:
    """Testes de movimento de peça."""

    @pytest.fixture
    def executor(self, mock_robot_controller, mock_board_coords, config_robo):
        return PhysicalMovementExecutor(
            robot_service=mock_robot_controller,
            board_coords=mock_board_coords,
            config_robo=config_robo
        )

    def test_executar_movimento_peca(self, executor, mock_robot_controller, mock_board_coords):
        """Testa movimento de peça entre posições."""
        origem = 0
        destino = 4
        mock_board_coords.get_position.side_effect = [
            (-0.250, -0.317, 0.15),  # origem (pos 0)
            (-0.200, -0.267, 0.15)   # destino (pos 4)
        ]
        mock_robot_controller.pick_and_place.return_value = True

        result = executor.executar_movimento_peca(origem, destino)

        assert result is True
        assert mock_board_coords.get_position.call_count == 2
        mock_robot_controller.pick_and_place.assert_called_once()

    def test_executar_movimento_peca_same_position(self, executor, mock_robot_controller, mock_board_coords):
        """Testa movimento para a mesma posição."""
        origin = destino = 4
        mock_board_coords.get_position.side_effect = [
            (-0.200, -0.267, 0.15),
            (-0.200, -0.267, 0.15)
        ]
        mock_robot_controller.pick_and_place.return_value = True

        result = executor.executar_movimento_peca(origin, destino)
        # Still executes, just moves to same position
        assert result is True

    def test_executar_movimento_peca_invalid_positions(self, executor, mock_board_coords):
        """Testa movimento com posições inválidas."""
        mock_board_coords.get_position.return_value = None

        result = executor.executar_movimento_peca(-1, 9)

        assert result is False


class TestPhysicalMovementExecutorGameMove:
    """Testes de execução de jogada."""

    @pytest.fixture
    def executor(self, mock_robot_controller, mock_board_coords, config_robo):
        return PhysicalMovementExecutor(
            robot_service=mock_robot_controller,
            board_coords=mock_board_coords,
            config_robo=config_robo
        )

    def test_executar_movimento_jogada_movimento_phase(self, executor, mock_robot_controller, mock_board_coords):
        """Testa execução de jogada na fase de movimento."""
        jogada = {
            "origem": 0,
            "destino": 4
        }
        fase = "movimento"

        mock_board_coords.get_position.side_effect = [
            (-0.250, -0.317, 0.15),  # origem
            (-0.200, -0.267, 0.15)   # destino
        ]
        mock_robot_controller.pick_and_place.return_value = True

        result = executor.executar_movimento_jogada(jogada, fase)

        assert result is True

    def test_executar_movimento_jogada_invalid_phase(self, executor):
        """Testa execução com fase inválida."""
        jogada = {}
        fase = "invalid"

        result = executor.executar_movimento_jogada(jogada, fase)

        assert result is False

    def test_executar_movimento_jogada_missing_data(self, executor):
        """Testa execução com dados faltando."""
        jogada = {}
        fase = "movimento"

        result = executor.executar_movimento_jogada(jogada, fase)

        assert result is False


class TestPhysicalMovementExecutorSafetyMovements:
    """Testes de movimentos de segurança."""

    @pytest.fixture
    def executor(self, mock_robot_controller, mock_board_coords, config_robo):
        return PhysicalMovementExecutor(
            robot_service=mock_robot_controller,
            board_coords=mock_board_coords,
            config_robo=config_robo
        )

    def test_move_direct_without_waypoint(self, executor, mock_robot_controller, mock_board_coords):
        """Testa movimento direto sem pontos de passagem."""
        mock_board_coords.get_position.return_value = (-0.200, -0.267, 0.15)
        mock_robot_controller.move_to_pose.return_value = True

        result = executor.executar_movimento_simples(4)

        assert result is True
        # Move simples chama move_to_pose uma vez
        assert mock_robot_controller.move_to_pose.called


class TestPhysicalMovementExecutorErrorHandling:
    """Testes de tratamento de erros."""

    @pytest.fixture
    def executor(self, mock_robot_controller, mock_board_coords, config_robo):
        return PhysicalMovementExecutor(
            robot_service=mock_robot_controller,
            board_coords=mock_board_coords,
            config_robo=config_robo
        )

    def test_handles_robot_communication_error(self, executor, mock_robot_controller, mock_board_coords):
        """Testa tratamento de erro de comunicação com robô."""
        mock_board_coords.get_position.return_value = (-0.200, -0.267, 0.15)
        mock_robot_controller.move_to_pose.return_value = False

        result = executor.executar_movimento_simples(4)

        assert result is False

    def test_handles_invalid_board_position(self, executor, mock_board_coords):
        """Testa tratamento de posição inválida do tabuleiro."""
        mock_board_coords.get_position.return_value = None

        result = executor.executar_movimento_simples(99)

        assert result is False

    def test_rollback_on_partial_failure(self, executor, mock_robot_controller, mock_board_coords):
        """Testa rollback em caso de falha parcial."""
        # Simula falha na execução do pick_and_place
        mock_board_coords.get_position.side_effect = [
            (-0.250, -0.317, 0.15),  # origem
            (-0.200, -0.267, 0.15)   # destino
        ]
        mock_robot_controller.pick_and_place.return_value = False

        result = executor.executar_movimento_peca(0, 4)

        assert result is False
