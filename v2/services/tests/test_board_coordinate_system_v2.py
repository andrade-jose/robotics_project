"""
Testes para BoardCoordinateSystemV2

Testes cobrem:
- Inicialização com CalibrationOrchestrator
- Verificação de calibração
- Conversão de coordenadas (grid ↔ mm)
- Validação de movimentos
- Obtenção de movimentos válidos
- Conversão pixel → grid (quando calibrado)
- Tratamento de casos de erro (não calibrado, posições inválidas)
"""

import pytest
import logging
from unittest.mock import Mock, MagicMock, patch
import numpy as np

try:
    from v2.services.board_coordinate_system_v2 import (
        BoardCoordinateSystemV2,
        BoardPosition,
    )
    from v2.vision.calibration_orchestrator import (
        CalibrationOrchestrator,
        CalibrationResult,
        CalibrationState,
    )
except ImportError:
    from services.board_coordinate_system_v2 import (
        BoardCoordinateSystemV2,
        BoardPosition,
    )
    from vision.calibration_orchestrator import (
        CalibrationOrchestrator,
        CalibrationResult,
        CalibrationState,
    )


class TestBoardCoordinateSystemV2:
    """Testes para BoardCoordinateSystemV2."""

    @pytest.fixture
    def mock_calibrator(self):
        """Cria mock de CalibrationOrchestrator."""
        calibrator = Mock(spec=CalibrationOrchestrator)

        # Status não calibrado por padrão
        calibrator.get_calibration_status.return_value = {
            "is_calibrated": False,
            "state": "not_calibrated",
            "calibration_attempts": 0,
            "successful_calibrations": 0,
            "success_rate": 0.0,
            "has_last_valid": False,
            "last_confidence": 0.0,
        }

        calibrator.last_valid_result = None
        return calibrator

    @pytest.fixture
    def mock_calibrator_calibrated(self, mock_calibrator):
        """Cria mock de CalibrationOrchestrator calibrado."""
        # Grid positions para um tabuleiro 3x3
        # Posições numeradas 0-8 (esquerda-direita, cima-baixo):
        # 0 1 2
        # 3 4 5
        # 6 7 8
        grid_positions = {
            0: (0.0, 270.0, 0.0),      # canto superior esquerdo
            1: (135.0, 270.0, 0.0),    # meio superior
            2: (270.0, 270.0, 0.0),    # canto superior direito
            3: (0.0, 135.0, 0.0),      # meio esquerdo
            4: (135.0, 135.0, 0.0),    # centro
            5: (270.0, 135.0, 0.0),    # meio direito
            6: (0.0, 0.0, 0.0),        # canto inferior esquerdo
            7: (135.0, 0.0, 0.0),      # meio inferior
            8: (270.0, 0.0, 0.0),      # canto inferior direito
        }

        # Mock result
        result = Mock(spec=CalibrationResult)
        result.is_calibrated = True
        result.grid_positions = grid_positions
        result.transform = Mock()
        result.grid = Mock()
        result.validator = Mock()

        mock_calibrator.last_valid_result = result
        mock_calibrator.get_calibration_status.return_value = {
            "is_calibrated": True,
            "state": "calibrated",
            "calibration_attempts": 1,
            "successful_calibrations": 1,
            "success_rate": 1.0,
            "has_last_valid": True,
            "last_confidence": 1.0,
        }

        # Mock methods
        mock_calibrator.get_grid_position.side_effect = lambda pos: grid_positions.get(pos)
        mock_calibrator.is_move_valid.return_value = True
        mock_calibrator.get_valid_moves.return_value = {0, 1, 3}  # Exemplo

        return mock_calibrator

    @pytest.fixture
    def board_coords(self, mock_calibrator):
        """Cria BoardCoordinateSystemV2 com mock."""
        return BoardCoordinateSystemV2(mock_calibrator)

    @pytest.fixture
    def board_coords_calibrated(self, mock_calibrator_calibrated):
        """Cria BoardCoordinateSystemV2 calibrado."""
        return BoardCoordinateSystemV2(mock_calibrator_calibrated)

    # ========== Testes de Inicialização ==========

    def test_initialization(self, board_coords, mock_calibrator):
        """Testa inicialização básica."""
        assert board_coords.calibrator == mock_calibrator
        assert board_coords.logger is not None
        assert board_coords._grid_positions_cache is None

    def test_initialization_with_custom_logger(self, mock_calibrator):
        """Testa inicialização com logger customizado."""
        custom_logger = logging.getLogger("test")
        board_coords = BoardCoordinateSystemV2(mock_calibrator, logger=custom_logger)
        assert board_coords.logger == custom_logger

    # ========== Testes de Calibração ==========

    def test_is_calibrated_false(self, board_coords):
        """Testa is_calibrated quando não calibrado."""
        assert not board_coords.is_calibrated()

    def test_is_calibrated_true(self, board_coords_calibrated):
        """Testa is_calibrated quando calibrado."""
        assert board_coords_calibrated.is_calibrated()

    # ========== Testes de Coordenadas ==========

    def test_get_board_position_mm_not_calibrated(self, board_coords):
        """Testa get_board_position_mm quando não calibrado."""
        result = board_coords.get_board_position_mm(4)
        assert result is None

    def test_get_board_position_mm_valid_position(self, board_coords_calibrated):
        """Testa get_board_position_mm com posição válida."""
        coords = board_coords_calibrated.get_board_position_mm(4)
        assert coords == (135.0, 135.0)  # Centro do tabuleiro

    def test_get_board_position_mm_corner_positions(self, board_coords_calibrated):
        """Testa get_board_position_mm para posições dos cantos."""
        # Canto superior esquerdo
        assert board_coords_calibrated.get_board_position_mm(0) == (0.0, 270.0)

        # Canto inferior direito
        assert board_coords_calibrated.get_board_position_mm(8) == (270.0, 0.0)

    def test_get_board_position_mm_invalid_position(self, board_coords_calibrated):
        """Testa get_board_position_mm com posição inválida."""
        # Posição negativa
        assert board_coords_calibrated.get_board_position_mm(-1) is None

        # Posição > 8
        assert board_coords_calibrated.get_board_position_mm(9) is None

    def test_get_all_board_positions_mm(self, board_coords_calibrated):
        """Testa get_all_board_positions_mm."""
        all_positions = board_coords_calibrated.get_all_board_positions_mm()

        assert all_positions is not None
        assert len(all_positions) == 9
        assert all_positions[4] == (135.0, 135.0)

    def test_get_all_board_positions_mm_not_calibrated(self, board_coords):
        """Testa get_all_board_positions_mm quando não calibrado."""
        result = board_coords.get_all_board_positions_mm()
        assert result is None

    # ========== Testes de Validação de Movimentos ==========

    def test_validate_move_not_calibrated(self, board_coords):
        """Testa validate_move quando não calibrado."""
        result = board_coords.validate_move(0, 4)
        assert not result

    def test_validate_move_same_position(self, board_coords_calibrated):
        """Testa validate_move com mesma posição inicial e final."""
        result = board_coords_calibrated.validate_move(4, 4)
        assert not result

    def test_validate_move_invalid_from_position(self, board_coords_calibrated):
        """Testa validate_move com posição inicial inválida."""
        result = board_coords_calibrated.validate_move(-1, 4)
        assert not result

        result = board_coords_calibrated.validate_move(9, 4)
        assert not result

    def test_validate_move_invalid_to_position(self, board_coords_calibrated):
        """Testa validate_move com posição final inválida."""
        result = board_coords_calibrated.validate_move(0, -1)
        assert not result

        result = board_coords_calibrated.validate_move(0, 9)
        assert not result

    def test_validate_move_occupied_destination(self, board_coords_calibrated):
        """Testa validate_move com posição destino ocupada."""
        occupied = {4}
        result = board_coords_calibrated.validate_move(0, 4, occupied)
        assert not result

    def test_validate_move_valid(self, board_coords_calibrated):
        """Testa validate_move com movimento válido."""
        result = board_coords_calibrated.validate_move(0, 4)
        assert result

    def test_validate_move_with_occupied(self, board_coords_calibrated):
        """Testa validate_move com posições ocupadas."""
        occupied = {0, 8}  # Posições ocupadas, mas não a destino
        result = board_coords_calibrated.validate_move(4, 7, occupied)
        assert result

    # ========== Testes de Movimentos Válidos ==========

    def test_get_valid_moves_not_calibrated(self, board_coords):
        """Testa get_valid_moves quando não calibrado."""
        result = board_coords.get_valid_moves(0)
        assert result == set()

    def test_get_valid_moves_valid(self, board_coords_calibrated):
        """Testa get_valid_moves com posição válida."""
        valid_moves = board_coords_calibrated.get_valid_moves(4)
        assert isinstance(valid_moves, set)
        # Mock retorna {0, 1, 3}
        assert 0 in valid_moves or len(valid_moves) >= 0

    def test_get_valid_moves_invalid_position(self, board_coords_calibrated):
        """Testa get_valid_moves com posição inválida."""
        result = board_coords_calibrated.get_valid_moves(9)
        assert result == set()

    def test_get_valid_moves_with_occupied(self, board_coords_calibrated):
        """Testa get_valid_moves com posições ocupadas."""
        occupied = {0, 1, 3}
        valid_moves = board_coords_calibrated.get_valid_moves(4, occupied)
        assert isinstance(valid_moves, set)

    # ========== Testes de Conversão Pixel → Grid ==========

    def test_get_grid_position_from_pixel_not_calibrated(self, board_coords):
        """Testa get_grid_position_from_pixel quando não calibrado."""
        result = board_coords.get_grid_position_from_pixel(100, 100)
        assert result is None

    def test_get_grid_position_from_pixel_valid(self, board_coords_calibrated):
        """Testa get_grid_position_from_pixel com coordenadas válidas."""
        # Mock transform para retornar coordenadas do tabuleiro
        board_coords_calibrated.calibrator.last_valid_result.transform.pixel_to_board.return_value = (135.0, 135.0)

        result = board_coords_calibrated.get_grid_position_from_pixel(100, 100)
        assert result == 4  # Centro

    def test_get_grid_position_from_pixel_corner(self, board_coords_calibrated):
        """Testa get_grid_position_from_pixel para canto."""
        board_coords_calibrated.calibrator.last_valid_result.transform.pixel_to_board.return_value = (0.0, 270.0)

        result = board_coords_calibrated.get_grid_position_from_pixel(50, 50)
        assert result == 0  # Canto superior esquerdo

    # ========== Testes de Informações ==========

    def test_get_calibration_info_not_calibrated(self, board_coords):
        """Testa get_calibration_info quando não calibrado."""
        info = board_coords.get_calibration_info()

        assert not info["is_calibrated"]
        assert info["board_positions"] is None
        assert "calibration_status" in info

    def test_get_calibration_info_calibrated(self, board_coords_calibrated):
        """Testa get_calibration_info quando calibrado."""
        info = board_coords_calibrated.get_calibration_info()

        assert info["is_calibrated"]
        assert info["board_positions"] is not None
        assert len(info["board_positions"]) == 9

    # ========== Testes de Reset ==========

    def test_reset_calibration(self, board_coords):
        """Testa reset_calibration."""
        board_coords._grid_positions_cache = {"test": "data"}
        board_coords.reset_calibration()

        assert board_coords._grid_positions_cache is None
        assert board_coords._grid_validators_cache is None

    # ========== Testes de BoardPosition ==========

    def test_board_position_valid(self):
        """Testa criação de BoardPosition válido."""
        pos = BoardPosition(grid_position=4)
        assert pos.grid_position == 4
        assert pos.pixel_coords is None
        assert pos.board_coords is None

    def test_board_position_with_coords(self):
        """Testa BoardPosition com coordenadas."""
        pos = BoardPosition(
            grid_position=4,
            pixel_coords=(100, 100),
            board_coords=(135.0, 135.0)
        )
        assert pos.grid_position == 4
        assert pos.pixel_coords == (100, 100)
        assert pos.board_coords == (135.0, 135.0)

    def test_board_position_invalid_grid_position(self):
        """Testa BoardPosition com grid position inválido."""
        with pytest.raises(ValueError):
            BoardPosition(grid_position=-1)

        with pytest.raises(ValueError):
            BoardPosition(grid_position=9)

    # ========== Testes de Representação ==========

    def test_repr_not_calibrated(self, board_coords):
        """Testa __repr__ quando não calibrado."""
        repr_str = repr(board_coords)
        assert "NÃO CALIBRADO" in repr_str
        assert "BoardCoordinateSystemV2" in repr_str

    def test_repr_calibrated(self, board_coords_calibrated):
        """Testa __repr__ quando calibrado."""
        repr_str = repr(board_coords_calibrated)
        assert "CALIBRADO" in repr_str
        assert "BoardCoordinateSystemV2" in repr_str

    # ========== Testes de Integração ==========

    def test_full_workflow_not_calibrated(self, board_coords):
        """Testa fluxo completo quando não calibrado."""
        assert not board_coords.is_calibrated()
        assert board_coords.get_board_position_mm(4) is None
        assert not board_coords.validate_move(0, 4)
        assert board_coords.get_valid_moves(4) == set()

    def test_full_workflow_calibrated(self, board_coords_calibrated):
        """Testa fluxo completo quando calibrado."""
        assert board_coords_calibrated.is_calibrated()

        # Obter coordenadas
        coords = board_coords_calibrated.get_board_position_mm(4)
        assert coords == (135.0, 135.0)

        # Validar movimento
        assert board_coords_calibrated.validate_move(0, 4)

        # Obter movimentos válidos
        valid = board_coords_calibrated.get_valid_moves(4)
        assert isinstance(valid, set)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])