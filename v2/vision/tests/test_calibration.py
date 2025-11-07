"""
Testes para Sistema de Calibração

Testes isolados para todos os componentes de calibração:
- CalibrationMarkerDetector
- BoardTransformCalculator
- GridGenerator
- WorkspaceValidator
- CalibrationOrchestrator

Execution:
    pytest v2/vision/tests/test_calibration.py -v
"""

import pytest
import logging
import numpy as np
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Adicionar v2 ao path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from vision.calibration_marker_detector import (
    CalibrationMarkerDetector,
    MarkerPose,
    CalibrationData,
)
from vision.board_transform_calculator import BoardTransformCalculator, TransformMatrix
from vision.grid_generator import GridGenerator
from vision.workspace_validator import WorkspaceValidator, WorkspaceConstraints
from vision.calibration_orchestrator import CalibrationOrchestrator, CalibrationState


class TestCalibrationMarkerDetector:
    """Suite de testes para CalibrationMarkerDetector."""

    @pytest.fixture
    def detector(self):
        """Fixture: detector com logger customizado."""
        logger = logging.getLogger("test_calibration_detector")
        logger.setLevel(logging.DEBUG)
        return CalibrationMarkerDetector(distance_mm=270.0, smoothing_frames=3, logger=logger)

    @pytest.fixture
    def mock_frame(self):
        """Fixture: frame de teste (640x480)."""
        return np.ones((480, 640, 3), dtype=np.uint8) * 255

    def test_initialization(self, detector):
        """Testa inicialização do detector."""
        assert detector.distance_mm == 270.0
        assert detector.smoothing_frames == 3
        assert detector.last_valid_calibration is None

    def test_detect_none_frame(self, detector):
        """Testa detecção com frame None."""
        result = detector.detect(None)
        assert result is None

    def test_detect_no_markers(self, detector, mock_frame):
        """Testa detecção quando não há marcadores."""
        with patch("vision.calibration_marker_detector.cv2.cvtColor"):
            with patch("vision.calibration_marker_detector.cv2.aruco.ArucoDetector") as mock_detector_class:
                mock_detector = MagicMock()
                mock_detector.detectMarkers.return_value = (None, None, None)
                detector.detector = mock_detector

                result = detector.detect(mock_frame)
                assert result is None

    def test_detect_not_exactly_two_markers(self, detector, mock_frame):
        """Testa que falha se não encontrar exatamente 2 marcadores."""
        with patch("vision.calibration_marker_detector.cv2.cvtColor"):
            with patch("vision.calibration_marker_detector.cv2.aruco.ArucoDetector"):
                mock_detector = MagicMock()
                # Apenas 1 marcador
                corners = [np.array([[10, 10], [50, 10], [50, 50], [10, 50]], dtype=np.float32)]
                ids = np.array([[0]], dtype=np.int32)
                mock_detector.detectMarkers.return_value = (corners, ids, None)
                detector.detector = mock_detector

                result = detector.detect(mock_frame)
                assert result is None

    def test_calculate_center(self, detector):
        """Testa cálculo de centro de marcador."""
        corners = np.array([[0, 0], [100, 0], [100, 100], [0, 100]], dtype=np.float32)
        center = detector._calculate_center(corners)
        assert center == (50.0, 50.0)

    def test_calculate_distance(self, detector):
        """Testa cálculo de distância entre centros."""
        center1 = (0.0, 0.0)
        center2 = (300.0, 0.0)
        distance = detector._calculate_distance(center1, center2)
        assert distance == 300.0

    def test_calculate_orientation(self, detector):
        """Testa cálculo de orientação."""
        corners = np.array([[0, 0], [100, 0], [100, 100], [0, 100]], dtype=np.float32)
        angle = detector._calculate_orientation(corners)
        assert isinstance(angle, float)

    def test_validate_calibration_valid(self, detector):
        """Testa validação de calibração válida."""
        marker0 = MarkerPose(
            marker_id=0,
            center=(100.0, 100.0),
            corners=np.array([[80, 80], [120, 80], [120, 120], [80, 120]]),
            normal=(0.0, 0.0, 1.0),
            orientation_angle=0.0,
        )
        marker1 = MarkerPose(
            marker_id=1,
            center=(370.0, 100.0),
            corners=np.array([[350, 80], [390, 80], [390, 120], [350, 120]]),
            normal=(0.0, 0.0, 1.0),
            orientation_angle=0.0,
        )
        calibration = CalibrationData(
            marker0_pose=marker0,
            marker1_pose=marker1,
            distance_mm=270.0,
            distance_pixels=270.0,
            scale=1.0,
            is_valid=True,
            confidence=1.0,
        )

        is_valid = detector.validate_calibration(calibration)
        assert is_valid is True

    def test_validate_calibration_distance_too_small(self, detector):
        """Testa rejeição de calibração com distância muito pequena."""
        marker0 = MarkerPose(
            marker_id=0,
            center=(100.0, 100.0),
            corners=np.array([[80, 80], [120, 80], [120, 120], [80, 120]]),
            normal=(0.0, 0.0, 1.0),
            orientation_angle=0.0,
        )
        marker1 = MarkerPose(
            marker_id=1,
            center=(110.0, 100.0),  # Apenas 10px afastado
            corners=np.array([[90, 80], [130, 80], [130, 120], [90, 120]]),
            normal=(0.0, 0.0, 1.0),
            orientation_angle=0.0,
        )
        calibration = CalibrationData(
            marker0_pose=marker0,
            marker1_pose=marker1,
            distance_mm=270.0,
            distance_pixels=10.0,  # Muito pequena
            scale=27.0,
            is_valid=True,
            confidence=1.0,
        )

        is_valid = detector.validate_calibration(calibration)
        assert is_valid is False

    def test_get_axis_vectors(self, detector):
        """Testa extração de vetores de eixo."""
        marker0 = MarkerPose(
            marker_id=0,
            center=(0.0, 0.0),
            corners=np.array([[-10, -10], [10, -10], [10, 10], [-10, 10]]),
            normal=(0.0, 0.0, 1.0),
            orientation_angle=0.0,
        )
        marker1 = MarkerPose(
            marker_id=1,
            center=(300.0, 0.0),
            corners=np.array([[290, -10], [310, -10], [310, 10], [290, 10]]),
            normal=(0.0, 0.0, 1.0),
            orientation_angle=0.0,
        )
        calibration = CalibrationData(
            marker0_pose=marker0,
            marker1_pose=marker1,
            distance_mm=270.0,
            distance_pixels=300.0,
            scale=0.9,
            is_valid=True,
            confidence=1.0,
        )

        axes = detector.get_axis_vectors(calibration)
        assert axes is not None
        assert "X" in axes
        assert "Y" in axes
        assert "Z" in axes
        assert "origin_pixels" in axes
        assert "scale" in axes


class TestBoardTransformCalculator:
    """Suite de testes para BoardTransformCalculator."""

    @pytest.fixture
    def mock_calibration(self):
        """Fixture: calibração simulada."""
        marker0 = MarkerPose(
            marker_id=0,
            center=(100.0, 100.0),
            corners=np.array([[80, 80], [120, 80], [120, 120], [80, 120]]),
            normal=(0.0, 0.0, 1.0),
            orientation_angle=0.0,
        )
        marker1 = MarkerPose(
            marker_id=1,
            center=(370.0, 100.0),
            corners=np.array([[350, 80], [390, 80], [390, 120], [350, 120]]),
            normal=(0.0, 0.0, 1.0),
            orientation_angle=0.0,
        )
        return CalibrationData(
            marker0_pose=marker0,
            marker1_pose=marker1,
            distance_mm=270.0,
            distance_pixels=270.0,
            scale=1.0,
            is_valid=True,
            confidence=1.0,
        )

    def test_initialization(self, mock_calibration):
        """Testa inicialização do transformador."""
        logger = logging.getLogger("test_transform")
        logger.setLevel(logging.DEBUG)
        transform = BoardTransformCalculator(mock_calibration, logger=logger)
        assert transform.is_initialized is True
        assert transform.transform_matrix is not None

    def test_pixel_to_board_origin(self, mock_calibration):
        """Testa conversão de pixel origem para board."""
        transform = BoardTransformCalculator(mock_calibration)
        board_coords = transform.pixel_to_board((100.0, 100.0))
        # Origem deve ser (0, 0)
        assert abs(board_coords[0] - 0.0) < 0.1
        assert abs(board_coords[1] - 0.0) < 0.1
        assert abs(board_coords[2] - 0.0) < 0.1

    def test_board_to_pixel_origin(self, mock_calibration):
        """Testa conversão de board origem para pixel."""
        transform = BoardTransformCalculator(mock_calibration)
        pixel_coords = transform.board_to_pixel((0.0, 0.0, 0.0))
        # Deve retornar ao pixel origem
        assert abs(pixel_coords[0] - 100.0) < 0.1
        assert abs(pixel_coords[1] - 100.0) < 0.1

    def test_roundtrip_conversion(self, mock_calibration):
        """Testa conversão roundtrip: pixel → board → pixel."""
        transform = BoardTransformCalculator(mock_calibration)
        original_pixel = (235.0, 100.0)

        # Converter para board e de volta
        board_coords = transform.pixel_to_board(original_pixel)
        pixel_back = transform.board_to_pixel(board_coords)

        # Verificar que retorna próximo do original
        dx = original_pixel[0] - pixel_back[0]
        dy = original_pixel[1] - pixel_back[1]
        distance = (dx**2 + dy**2) ** 0.5
        assert distance < 1.0  # Tolerância de 1 pixel

    def test_validate_transform(self, mock_calibration):
        """Testa validação de transformação."""
        transform = BoardTransformCalculator(mock_calibration)
        is_valid = transform.validate_transform()
        assert is_valid is True


class TestGridGenerator:
    """Suite de testes para GridGenerator."""

    @pytest.fixture
    def mock_calibration(self):
        """Fixture: calibração simulada."""
        marker0 = MarkerPose(
            marker_id=0,
            center=(100.0, 100.0),
            corners=np.array([[80, 80], [120, 80], [120, 120], [80, 120]]),
            normal=(0.0, 0.0, 1.0),
            orientation_angle=0.0,
        )
        marker1 = MarkerPose(
            marker_id=1,
            center=(370.0, 100.0),
            corners=np.array([[350, 80], [390, 80], [390, 120], [350, 120]]),
            normal=(0.0, 0.0, 1.0),
            orientation_angle=0.0,
        )
        return CalibrationData(
            marker0_pose=marker0,
            marker1_pose=marker1,
            distance_mm=270.0,
            distance_pixels=270.0,
            scale=1.0,
            is_valid=True,
            confidence=1.0,
        )

    @pytest.fixture
    def transform(self, mock_calibration):
        """Fixture: transformador."""
        return BoardTransformCalculator(mock_calibration)

    def test_initialization(self, transform):
        """Testa inicialização do gerador de grid."""
        logger = logging.getLogger("test_grid_gen")
        logger.setLevel(logging.DEBUG)
        grid = GridGenerator(transform, logger=logger)
        assert grid.is_generated is True
        assert len(grid.grid_positions) == 9

    def test_grid_positions_count(self, transform):
        """Testa que grid tem 9 posições."""
        grid = GridGenerator(transform)
        positions = grid.get_grid_positions()
        assert len(positions) == 9

    def test_grid_positions_valid(self, transform):
        """Testa que todas as posições são válidas."""
        grid = GridGenerator(transform)
        for position in range(9):
            coords = grid.get_cell_position(position)
            assert coords is not None
            assert len(coords) == 3
            assert coords[2] == 0.0  # Z sempre 0

    def test_pixel_to_position(self, transform):
        """Testa conversão de pixel para posição de célula."""
        grid = GridGenerator(transform)
        # Pixel na célula 0 (origem)
        position = grid.pixel_to_position((100.0, 100.0))
        assert position == 0

    def test_position_to_pixel(self, transform):
        """Testa conversão de posição para pixel."""
        grid = GridGenerator(transform)
        pixel_coords = grid.position_to_pixel(0)
        assert pixel_coords is not None
        assert len(pixel_coords) == 2

    def test_validate_grid(self, transform):
        """Testa validação de grid."""
        grid = GridGenerator(transform)
        is_valid = grid.validate_grid()
        assert is_valid is True

    def test_grid_bounds(self, transform):
        """Testa obtenção de limites do grid."""
        grid = GridGenerator(transform)
        bounds = grid.get_grid_bounds()
        assert "min_x" in bounds
        assert "max_x" in bounds
        assert "min_y" in bounds
        assert "max_y" in bounds


class TestWorkspaceValidator:
    """Suite de testes para WorkspaceValidator."""

    @pytest.fixture
    def mock_calibration(self):
        """Fixture: calibração simulada."""
        marker0 = MarkerPose(
            marker_id=0,
            center=(100.0, 100.0),
            corners=np.array([[80, 80], [120, 80], [120, 120], [80, 120]]),
            normal=(0.0, 0.0, 1.0),
            orientation_angle=0.0,
        )
        marker1 = MarkerPose(
            marker_id=1,
            center=(370.0, 100.0),
            corners=np.array([[350, 80], [390, 80], [390, 120], [350, 120]]),
            normal=(0.0, 0.0, 1.0),
            orientation_angle=0.0,
        )
        return CalibrationData(
            marker0_pose=marker0,
            marker1_pose=marker1,
            distance_mm=270.0,
            distance_pixels=270.0,
            scale=1.0,
            is_valid=True,
            confidence=1.0,
        )

    @pytest.fixture
    def validator(self, mock_calibration):
        """Fixture: validador."""
        transform = BoardTransformCalculator(mock_calibration)
        grid = GridGenerator(transform)
        return WorkspaceValidator(grid, safety_margin_mm=10.0)

    def test_initialization(self, validator):
        """Testa inicialização do validador."""
        assert validator.constraints is not None
        assert validator.piece_positions == set()

    def test_is_position_valid(self, validator):
        """Testa validação de posições."""
        for position in range(9):
            assert validator.is_position_valid(position) is True

    def test_is_position_invalid(self, validator):
        """Testa rejeição de posições inválidas."""
        assert validator.is_position_valid(-1) is False
        assert validator.is_position_valid(9) is False
        assert validator.is_position_valid(100) is False

    def test_can_move_valid(self, validator):
        """Testa movimento válido."""
        assert validator.can_move(0, 1) is True
        assert validator.can_move(0, 4) is True
        assert validator.can_move(4, 8) is True

    def test_can_move_same_position(self, validator):
        """Testa rejeição de movimento para mesma posição."""
        assert validator.can_move(0, 0) is False

    def test_can_move_occupied(self, validator):
        """Testa rejeição de movimento para posição ocupada."""
        occupied = {4}
        assert validator.can_move(0, 4, occupied) is False
        assert validator.can_move(0, 1, occupied) is True

    def test_update_piece_positions(self, validator):
        """Testa atualização de posições ocupadas."""
        validator.update_piece_positions({0, 4, 8})
        assert len(validator.piece_positions) == 3

    def test_get_valid_moves(self, validator):
        """Testa obtenção de movimentos válidos."""
        validator.update_piece_positions({0, 8})
        valid_moves = validator.get_valid_moves(4)
        assert isinstance(valid_moves, set)
        assert 0 not in valid_moves  # Ocupada
        assert 8 not in valid_moves  # Ocupada
        assert len(valid_moves) > 0

    def test_validate_all_positions(self, validator):
        """Testa validação de todas as posições."""
        is_valid = validator.validate_all_positions()
        assert is_valid is True


class TestCalibrationOrchestrator:
    """Suite de testes para CalibrationOrchestrator."""

    @pytest.fixture
    def orchestrator(self):
        """Fixture: orquestrador."""
        logger = logging.getLogger("test_orchestrator")
        logger.setLevel(logging.DEBUG)
        return CalibrationOrchestrator(distance_mm=270.0, smoothing_frames=3, logger=logger)

    def test_initialization(self, orchestrator):
        """Testa inicialização do orquestrador."""
        assert orchestrator.state == CalibrationState.NOT_CALIBRATED
        assert orchestrator.calibration_attempts == 0
        assert orchestrator.successful_calibrations == 0

    def test_get_calibration_status(self, orchestrator):
        """Testa obtenção de status."""
        status = orchestrator.get_calibration_status()
        assert "state" in status
        assert status["is_calibrated"] is False
        assert status["calibration_attempts"] == 0

    def test_get_grid_position_not_calibrated(self, orchestrator):
        """Testa acesso a posição de grid sem calibração."""
        position = orchestrator.get_grid_position(0)
        assert position is None

    def test_get_valid_moves_not_calibrated(self, orchestrator):
        """Testa acesso a movimentos válidos sem calibração."""
        valid_moves = orchestrator.get_valid_moves(0)
        assert valid_moves == set()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
