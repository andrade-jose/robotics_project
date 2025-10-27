"""
Testes Unitários para PhysicalMovementExecutor
Tests for the physical movement executor that handles all robot physical movements.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

from services.physical_movement_executor import PhysicalMovementExecutor


class TestPhysicalMovementExecutorInitialization:
    """Testes de inicialização do executor."""

    def test_init_with_dependencies(self, mock_robot_controller, mock_board_coords):
        """Testa inicialização com dependências."""
        executor = PhysicalMovementExecutor(
            robot_service=mock_robot_controller,
            board_coords=mock_board_coords
        )

        assert executor.robot_service == mock_robot_controller
        assert executor.board_coords == mock_board_coords


class TestPhysicalMovementExecutorSimpleMovement:
    """Testes de movimento simples."""

    @pytest.fixture
    def executor(self, mock_robot_controller, mock_board_coords):
        return PhysicalMovementExecutor(
            robot_service=mock_robot_controller,
            board_coords=mock_board_coords
        )

    def test_executar_movimento_simples(self, executor, mock_robot_controller, mock_board_coords):
        """Testa execução de movimento simples para uma posição."""
        position = 4
        mock_board_coords.get_position.return_value = [0.3, 0.2, 0.15, 0, 0, 0]
        mock_robot_controller.move_to_pose.return_value = True

        result = executor.executar_movimento_simples(position)

        assert result is True
        mock_board_coords.get_position.assert_called_once_with(position)
        mock_robot_controller.move_to_pose.assert_called_once()

    def test_executar_movimento_simples_invalid_position(self, executor, mock_board_coords):
        """Testa movimento simples para posição inválida."""
        mock_board_coords.get_position.return_value = None

        result = executor.executar_movimento_simples(99)

        assert result is False


class TestPhysicalMovementExecutorPlacement:
    """Testes de colocação de peças."""

    @pytest.fixture
    def executor(self, mock_robot_controller, mock_board_coords):
        return PhysicalMovementExecutor(
            robot_service=mock_robot_controller,
            board_coords=mock_board_coords
        )

    def test_executar_colocacao_player1(self, executor, mock_robot_controller, mock_board_coords):
        """Testa colocação de peça do jogador 1."""
        position = 0
        player = 1
        mock_board_coords.get_position.return_value = [0.25, -0.25, 0.15, 0, 0, 0]
        mock_robot_controller.move_to_pose.return_value = True

        result = executor.executar_colocacao(position, player)

        assert result is True
        # Deve ter movido para pegar peça do depósito e colocar no tabuleiro
        assert mock_robot_controller.move_to_pose.call_count >= 2

    def test_executar_colocacao_player2(self, executor, mock_robot_controller, mock_board_coords):
        """Testa colocação de peça do jogador 2."""
        position = 8
        player = 2
        mock_board_coords.get_position.return_value = [0.35, -0.15, 0.15, 0, 0, 0]
        mock_robot_controller.move_to_pose.return_value = True

        result = executor.executar_colocacao(position, player)

        assert result is True
        assert mock_robot_controller.move_to_pose.call_count >= 2

    def test_executar_colocacao_invalid_player(self, executor):
        """Testa colocação com jogador inválido."""
        result = executor.executar_colocacao(0, 3)  # Jogador 3 não existe

        assert result is False

    def test_executar_colocacao_movement_fails(self, executor, mock_robot_controller, mock_board_coords):
        """Testa falha durante colocação."""
        mock_board_coords.get_position.return_value = [0.3, 0.2, 0.15, 0, 0, 0]
        mock_robot_controller.move_to_pose.return_value = False

        result = executor.executar_colocacao(0, 1)

        assert result is False


class TestPhysicalMovementExecutorPieceMovement:
    """Testes de movimento de peças."""

    @pytest.fixture
    def executor(self, mock_robot_controller, mock_board_coords):
        return PhysicalMovementExecutor(
            robot_service=mock_robot_controller,
            board_coords=mock_board_coords
        )

    def test_executar_movimento_peca(self, executor, mock_robot_controller, mock_board_coords):
        """Testa movimento de peça de uma posição para outra."""
        from_pos = 0
        to_pos = 1
        mock_board_coords.get_position.side_effect = [
            [0.25, -0.25, 0.15, 0, 0, 0],  # from_pos
            [0.30, -0.25, 0.15, 0, 0, 0]   # to_pos
        ]
        mock_robot_controller.move_to_pose.return_value = True

        result = executor.executar_movimento_peca(from_pos, to_pos)

        assert result is True
        # Deve mover para origem, pegar, e mover para destino
        assert mock_robot_controller.move_to_pose.call_count >= 2

    def test_executar_movimento_peca_same_position(self, executor):
        """Testa movimento para a mesma posição."""
        result = executor.executar_movimento_peca(4, 4)

        # Deve retornar False (movimento inválido)
        assert result is False

    def test_executar_movimento_peca_invalid_positions(self, executor, mock_board_coords):
        """Testa movimento com posições inválidas."""
        mock_board_coords.get_position.return_value = None

        result = executor.executar_movimento_peca(0, 99)

        assert result is False


class TestPhysicalMovementExecutorGameMove:
    """Testes de execução de jogadas completas."""

    @pytest.fixture
    def executor(self, mock_robot_controller, mock_board_coords):
        return PhysicalMovementExecutor(
            robot_service=mock_robot_controller,
            board_coords=mock_board_coords
        )

    def test_executar_movimento_jogada_placement_phase(self, executor):
        """Testa execução de jogada na fase de colocação."""
        jogada = {'de': None, 'para': 4, 'jogador': 1}
        fase = 'colocacao'

        with patch.object(executor, 'executar_colocacao') as mock_colocacao:
            mock_colocacao.return_value = True

            result = executor.executar_movimento_jogada(jogada, fase)

            assert result is True
            mock_colocacao.assert_called_once_with(4, 1)

    def test_executar_movimento_jogada_movement_phase(self, executor):
        """Testa execução de jogada na fase de movimento."""
        jogada = {'de': 0, 'para': 1, 'jogador': 1}
        fase = 'movimento'

        with patch.object(executor, 'executar_movimento_peca') as mock_movimento:
            mock_movimento.return_value = True

            result = executor.executar_movimento_jogada(jogada, fase)

            assert result is True
            mock_movimento.assert_called_once_with(0, 1)

    def test_executar_movimento_jogada_invalid_phase(self, executor):
        """Testa execução com fase inválida."""
        jogada = {'de': 0, 'para': 1, 'jogador': 1}
        fase = 'fase_invalida'

        result = executor.executar_movimento_jogada(jogada, fase)

        assert result is False

    def test_executar_movimento_jogada_missing_data(self, executor):
        """Testa execução com dados faltando."""
        jogada = {'para': 4}  # Falta 'jogador'
        fase = 'colocacao'

        result = executor.executar_movimento_jogada(jogada, fase)

        assert result is False


class TestPhysicalMovementExecutorDepotPositions:
    """Testes de gerenciamento de posições de depósito."""

    @pytest.fixture
    def executor(self, mock_robot_controller, mock_board_coords):
        return PhysicalMovementExecutor(
            robot_service=mock_robot_controller,
            board_coords=mock_board_coords
        )

    def test_set_piece_depot_position_player1(self, executor):
        """Testa configuração de depósito do jogador 1."""
        depot_pose = [0.1, -0.4, 0.2, 0, 0, 0]

        executor.set_piece_depot_position(1, depot_pose)

        assert executor.piece_depot_player1 == depot_pose

    def test_set_piece_depot_position_player2(self, executor):
        """Testa configuração de depósito do jogador 2."""
        depot_pose = [0.5, -0.4, 0.2, 0, 0, 0]

        executor.set_piece_depot_position(2, depot_pose)

        assert executor.piece_depot_player2 == depot_pose

    def test_set_piece_depot_position_invalid_player(self, executor):
        """Testa configuração com jogador inválido."""
        depot_pose = [0.1, -0.4, 0.2, 0, 0, 0]

        result = executor.set_piece_depot_position(3, depot_pose)

        assert result is False


class TestPhysicalMovementExecutorSafetyMovements:
    """Testes de movimentos com segurança (waypoints)."""

    @pytest.fixture
    def executor(self, mock_robot_controller, mock_board_coords):
        return PhysicalMovementExecutor(
            robot_service=mock_robot_controller,
            board_coords=mock_board_coords
        )

    def test_move_with_intermediate_waypoint(self, executor, mock_robot_controller):
        """Testa movimento com waypoint intermediário."""
        start_pose = [0.25, -0.25, 0.15, 0, 0, 0]
        end_pose = [0.35, -0.15, 0.15, 0, 0, 0]
        mock_robot_controller.move_to_pose.return_value = True

        # Movimento deve incluir waypoint de segurança (z elevado)
        result = executor._move_with_safety_height(start_pose, end_pose)

        assert result is True
        # Deve ter feito 3 movimentos: subir, mover, descer
        assert mock_robot_controller.move_to_pose.call_count == 3

    def test_move_direct_without_waypoint(self, executor, mock_robot_controller):
        """Testa movimento direto sem waypoint."""
        pose = [0.3, 0.2, 0.15, 0, 0, 0]
        mock_robot_controller.move_to_pose.return_value = True

        result = executor._move_direct(pose)

        assert result is True
        mock_robot_controller.move_to_pose.assert_called_once_with(pose)


class TestPhysicalMovementExecutorErrorHandling:
    """Testes de tratamento de erros."""

    @pytest.fixture
    def executor(self, mock_robot_controller, mock_board_coords):
        return PhysicalMovementExecutor(
            robot_service=mock_robot_controller,
            board_coords=mock_board_coords
        )

    def test_handles_robot_communication_error(self, executor, mock_robot_controller, mock_board_coords):
        """Testa tratamento de erro de comunicação com robô."""
        mock_board_coords.get_position.return_value = [0.3, 0.2, 0.15, 0, 0, 0]
        mock_robot_controller.move_to_pose.side_effect = Exception("Robot offline")

        result = executor.executar_movimento_simples(0)

        assert result is False

    def test_handles_invalid_board_position(self, executor, mock_board_coords):
        """Testa tratamento de posição de tabuleiro inválida."""
        mock_board_coords.get_position.return_value = None

        result = executor.executar_movimento_simples(99)

        assert result is False

    def test_rollback_on_partial_failure(self, executor, mock_robot_controller, mock_board_coords):
        """Testa rollback em caso de falha parcial."""
        mock_board_coords.get_position.side_effect = [
            [0.25, -0.25, 0.15, 0, 0, 0],
            [0.35, -0.15, 0.15, 0, 0, 0]
        ]
        # Primeiro movimento OK, segundo falha
        mock_robot_controller.move_to_pose.side_effect = [True, False]

        result = executor.executar_movimento_peca(0, 1)

        # Deve retornar False
        assert result is False
