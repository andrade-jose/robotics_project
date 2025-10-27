"""
Testes Unitários para RobotService
Tests for the main robot service facade that coordinates all robot operations.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call

from services.robot_service import RobotService
from services.pose_validation_service import ValidationResult


class TestRobotServiceInitialization:
    """Testes de inicialização do RobotService."""

    @patch('services.robot_service.URController')
    @patch('services.robot_service.PoseValidationService')
    def test_init_creates_dependencies(self, mock_validator_class, mock_controller_class):
        """Testa que inicialização cria dependências."""
        robot_ip = "192.168.1.100"

        service = RobotService(robot_ip)

        # Verifica que controlador foi criado com IP correto
        mock_controller_class.assert_called_once()
        assert service.robot_ip == robot_ip

    @patch('services.robot_service.URController')
    def test_init_with_dependencies_injection(self, mock_controller_class):
        """Testa inicialização com injeção de dependências."""
        mock_controller = Mock()
        mock_validator = Mock()

        service = RobotService(
            robot_ip="192.168.1.100",
            controller=mock_controller,
            validator=mock_validator
        )

        # Deve usar as dependências injetadas
        assert service.controller == mock_controller
        assert service.validator == mock_validator


class TestRobotServiceConnection:
    """Testes de conexão com robô."""

    @pytest.fixture
    def service(self, mock_robot_controller, mock_validator):
        """Fixture de RobotService com mocks."""
        service = RobotService("192.168.1.100")
        service.controller = mock_robot_controller
        service.validator = mock_validator
        return service

    def test_initialize_connects_robot(self, service, mock_robot_controller):
        """Testa que initialize conecta ao robô."""
        mock_robot_controller.connect.return_value = True

        result = service.initialize()

        assert result is True
        mock_robot_controller.connect.assert_called_once()

    def test_initialize_fails_if_connection_fails(self, service, mock_robot_controller):
        """Testa falha na inicialização se conexão falhar."""
        mock_robot_controller.connect.return_value = False

        result = service.initialize()

        assert result is False

    def test_shutdown_disconnects_robot(self, service, mock_robot_controller):
        """Testa que shutdown desconecta do robô."""
        mock_robot_controller.disconnect.return_value = True

        result = service.shutdown()

        assert result is True
        mock_robot_controller.disconnect.assert_called_once()

    def test_is_connected_delegates_to_controller(self, service, mock_robot_controller):
        """Testa que is_connected delega para controller."""
        mock_robot_controller.is_connected.return_value = True

        result = service.is_connected()

        assert result is True
        mock_robot_controller.is_connected.assert_called_once()


class TestRobotServiceMovement:
    """Testes de movimento do robô."""

    @pytest.fixture
    def service(self, mock_robot_controller, mock_validator):
        service = RobotService("192.168.1.100")
        service.controller = mock_robot_controller
        service.validator = mock_validator
        return service

    def test_move_to_pose_with_valid_pose(self, service, mock_robot_controller, mock_validator, valid_pose):
        """Testa movimento para pose válida."""
        mock_validator.validate_complete.return_value = ValidationResult(
            is_valid=True, errors=[], warnings=[], pose=valid_pose
        )
        mock_robot_controller.move_to_pose.return_value = True

        result = service.move_to_pose(valid_pose)

        assert result is True
        mock_validator.validate_complete.assert_called_once_with(valid_pose)
        mock_robot_controller.move_to_pose.assert_called_once()

    def test_move_to_pose_rejects_invalid_pose(self, service, mock_validator):
        """Testa que movimento rejeita pose inválida."""
        invalid_pose = [1.5, 0.2, 0.5, 0, 0, 0]
        mock_validator.validate_complete.return_value = ValidationResult(
            is_valid=False, errors=["X fora do workspace"], warnings=[], pose=None
        )

        result = service.move_to_pose(invalid_pose)

        assert result is False
        # Não deve chamar controller.move_to_pose
        service.controller.move_to_pose.assert_not_called()

    def test_move_to_board_position(self, service, mock_robot_controller):
        """Testa movimento para posição do tabuleiro."""
        with patch.object(service, 'board_coords') as mock_board:
            mock_board.get_position.return_value = [0.3, 0.2, 0.15, 0, 0, 0]
            mock_robot_controller.move_to_pose.return_value = True

            result = service.move_to_board_position(4)  # Posição central

            assert result is True
            mock_board.get_position.assert_called_once_with(4)

    def test_return_to_home(self, service, mock_robot_controller, home_pose):
        """Testa retorno à posição home."""
        service.home_pose = home_pose
        mock_robot_controller.move_to_pose.return_value = True

        result = service.return_to_home()

        assert result is True
        mock_robot_controller.move_to_pose.assert_called_once()


class TestRobotServiceGameOperations:
    """Testes de operações do jogo."""

    @pytest.fixture
    def service(self, mock_robot_controller, mock_validator):
        service = RobotService("192.168.1.100")
        service.controller = mock_robot_controller
        service.validator = mock_validator
        return service

    def test_place_piece(self, service):
        """Testa colocação de peça no tabuleiro."""
        position = 4  # Centro
        player = 1

        with patch.object(service, 'move_to_board_position') as mock_move:
            mock_move.return_value = True

            result = service.place_piece(position, player)

            assert result is True
            mock_move.assert_called_with(position)

    def test_move_piece(self, service):
        """Testa movimento de peça de uma posição para outra."""
        from_pos = 0
        to_pos = 4

        with patch.object(service, 'move_to_board_position') as mock_move:
            mock_move.return_value = True

            result = service.move_piece(from_pos, to_pos)

            assert result is True
            # Deve mover para origem, pegar peça, mover para destino
            assert mock_move.call_count >= 2

    def test_pick_piece_from_depot(self, service):
        """Testa pegar peça do depósito."""
        player = 1

        with patch.object(service, 'move_to_pose') as mock_move:
            mock_move.return_value = True

            result = service.pick_piece_from_depot(player)

            assert result is True


class TestRobotServiceCalibration:
    """Testes de calibração."""

    @pytest.fixture
    def service(self, mock_robot_controller, mock_validator):
        service = RobotService("192.168.1.100")
        service.controller = mock_robot_controller
        service.validator = mock_validator
        return service

    def test_calibrate_board_position(self, service, mock_robot_controller):
        """Testa calibração de posição do tabuleiro."""
        position = 4
        mock_robot_controller.get_current_pose.return_value = [0.3, 0.2, 0.15, 0, 0, 0]

        with patch.object(service, 'board_coords') as mock_board:
            mock_board.update_position.return_value = True

            result = service.calibrate_board_position(position)

            assert result is True
            mock_robot_controller.get_current_pose.assert_called_once()
            mock_board.update_position.assert_called_once_with(position, [0.3, 0.2, 0.15, 0, 0, 0])

    def test_save_calibration(self, service):
        """Testa salvamento de calibração."""
        with patch.object(service, 'board_coords') as mock_board:
            mock_board.save_positions.return_value = True

            result = service.save_calibration()

            assert result is True
            mock_board.save_positions.assert_called_once()

    def test_load_calibration(self, service):
        """Testa carregamento de calibração."""
        with patch.object(service, 'board_coords') as mock_board:
            mock_board.load_positions.return_value = True

            result = service.load_calibration()

            assert result is True
            mock_board.load_positions.assert_called_once()


class TestRobotServiceValidation:
    """Testes de validação delegada."""

    @pytest.fixture
    def service(self, mock_robot_controller, mock_validator):
        service = RobotService("192.168.1.100")
        service.controller = mock_robot_controller
        service.validator = mock_validator
        return service

    def test_validate_pose_delegates_to_validator(self, service, mock_validator, valid_pose):
        """Testa que validate_pose delega para validator."""
        mock_validator.validate_complete.return_value = ValidationResult(
            is_valid=True, errors=[], warnings=[], pose=valid_pose
        )

        result = service.validate_pose(valid_pose)

        assert result.is_valid is True
        mock_validator.validate_complete.assert_called_once_with(valid_pose)


class TestRobotServiceErrorHandling:
    """Testes de tratamento de erros."""

    @pytest.fixture
    def service(self, mock_robot_controller, mock_validator):
        service = RobotService("192.168.1.100")
        service.controller = mock_robot_controller
        service.validator = mock_validator
        return service

    def test_move_to_pose_handles_controller_exception(self, service, mock_robot_controller, mock_validator, valid_pose):
        """Testa tratamento de exceção do controller."""
        mock_validator.validate_complete.return_value = ValidationResult(
            is_valid=True, errors=[], warnings=[], pose=valid_pose
        )
        mock_robot_controller.move_to_pose.side_effect = Exception("Robot communication error")

        result = service.move_to_pose(valid_pose)

        # Deve retornar False em caso de exceção
        assert result is False

    def test_emergency_stop(self, service, mock_robot_controller):
        """Testa parada de emergência."""
        mock_robot_controller.emergency_stop.return_value = True

        result = service.emergency_stop()

        assert result is True
        mock_robot_controller.emergency_stop.assert_called_once()


class TestRobotServiceStateManagement:
    """Testes de gerenciamento de estado."""

    @pytest.fixture
    def service(self, mock_robot_controller, mock_validator):
        service = RobotService("192.168.1.100")
        service.controller = mock_robot_controller
        service.validator = mock_validator
        return service

    def test_get_current_pose(self, service, mock_robot_controller):
        """Testa obtenção da pose atual."""
        expected_pose = [0.3, 0.2, 0.5, 0, 0, 0]
        mock_robot_controller.get_current_pose.return_value = expected_pose

        pose = service.get_current_pose()

        assert pose == expected_pose
        mock_robot_controller.get_current_pose.assert_called_once()

    def test_get_robot_status(self, service, mock_robot_controller):
        """Testa obtenção de status do robô."""
        mock_robot_controller.is_connected.return_value = True

        status = service.get_robot_status()

        assert 'connected' in status
        assert status['connected'] is True


class TestRobotServiceIntegration:
    """Testes de integração entre componentes."""

    @pytest.fixture
    def service(self, mock_robot_controller, mock_validator):
        service = RobotService("192.168.1.100")
        service.controller = mock_robot_controller
        service.validator = mock_validator
        return service

    def test_complete_game_move_flow(self, service, mock_robot_controller, mock_validator):
        """Testa fluxo completo de movimento de jogo."""
        # Setup
        from_pos = 0
        to_pos = 4
        mock_validator.validate_complete.return_value = ValidationResult(
            is_valid=True, errors=[], warnings=[], pose=[0.3, 0.2, 0.15, 0, 0, 0]
        )
        mock_robot_controller.move_to_pose.return_value = True

        with patch.object(service, 'board_coords') as mock_board:
            mock_board.get_position.return_value = [0.3, 0.2, 0.15, 0, 0, 0]

            # Execute
            result = service.move_piece(from_pos, to_pos)

            # Verify
            assert result is True
            assert mock_robot_controller.move_to_pose.call_count >= 2

    def test_calibration_workflow(self, service, mock_robot_controller):
        """Testa fluxo completo de calibração."""
        # Calibra todas as 9 posições
        mock_robot_controller.get_current_pose.return_value = [0.3, 0.2, 0.15, 0, 0, 0]

        with patch.object(service, 'board_coords') as mock_board:
            mock_board.update_position.return_value = True
            mock_board.save_positions.return_value = True

            # Calibra cada posição
            for pos in range(9):
                service.calibrate_board_position(pos)

            # Salva calibração
            result = service.save_calibration()

            assert result is True
            assert mock_board.update_position.call_count == 9
            mock_board.save_positions.assert_called_once()
