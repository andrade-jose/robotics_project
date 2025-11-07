"""
Testes para ArUcoDetector

Testes isolados para detecção de marcadores ArUco.

Execution:
    pytest v2/vision/tests/test_aruco.py -v
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import numpy as np

# Adicionar v2 ao path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from vision.aruco_detector import ArUcoDetector, Detection


class TestArUcoDetector:
    """Suite de testes para ArUcoDetector."""

    @pytest.fixture
    def detector(self):
        """Fixture: detector com logger customizado."""
        logger = logging.getLogger("test_aruco")
        logger.setLevel(logging.DEBUG)
        return ArUcoDetector(aruco_dict_size=6, marker_size=250, logger=logger)

    @pytest.fixture
    def mock_frame(self):
        """Fixture: frame de teste (640x480)."""
        return np.ones((480, 640, 3), dtype=np.uint8) * 255

    @pytest.fixture
    def mock_cv2(self):
        """Fixture: mock do OpenCV."""
        with patch("vision.aruco_detector.cv2") as mock:
            yield mock

    # ========== Testes de Inicialização ==========

    def test_initialization_default_values(self, detector):
        """Testa inicialização com valores padrão."""
        assert detector.aruco_dict_size == 6
        assert detector.marker_size == 250
        assert detector.detections_count == 0

    def test_initialization_custom_values(self):
        """Testa inicialização com valores customizados."""
        detector = ArUcoDetector(aruco_dict_size=5, marker_size=100)
        assert detector.aruco_dict_size == 5
        assert detector.marker_size == 100

    def test_initialization_with_logger(self):
        """Testa inicialização com logger customizado."""
        custom_logger = logging.getLogger("custom_aruco")
        detector = ArUcoDetector(logger=custom_logger)
        assert detector.logger is custom_logger

    # ========== Testes de Detecção ==========

    def test_detect_no_markers(self, detector, mock_frame):
        """Testa detecção quando não há marcadores."""
        with patch("vision.aruco_detector.cv2.cvtColor") as mock_cvtColor:
            with patch("vision.aruco_detector.cv2.aruco.ArucoDetector") as mock_detector_class:
                mock_detector = MagicMock()
                mock_detector.detectMarkers.return_value = (None, None, None)
                detector.detector = mock_detector

                mock_cvtColor.return_value = np.ones((480, 640), dtype=np.uint8)

                detections = detector.detect(mock_frame)

                assert isinstance(detections, dict)
                assert len(detections) == 0

    def test_detect_with_markers(self, detector, mock_frame):
        """Testa detecção com marcadores presentes."""
        # Setup mock
        mock_detector = MagicMock()
        corners = [np.array([[10, 10], [50, 10], [50, 50], [10, 50]], dtype=np.float32)]
        ids = np.array([[5]], dtype=np.int32)
        mock_detector.detectMarkers.return_value = (corners, ids, None)
        detector.detector = mock_detector

        with patch("vision.aruco_detector.cv2.cvtColor") as mock_cvtColor:
            mock_cvtColor.return_value = np.ones((480, 640), dtype=np.uint8)

            detections = detector.detect(mock_frame)

            assert len(detections) == 1
            assert 5 in detections
            detection = detections[5]
            assert detection.marker_id == 5
            assert isinstance(detection.centroid, tuple)
            assert len(detection.centroid) == 2

    def test_detect_multiple_markers(self, detector, mock_frame):
        """Testa detecção com múltiplos marcadores."""
        mock_detector = MagicMock()

        # Dois marcadores
        corners = [
            np.array([[10, 10], [50, 10], [50, 50], [10, 50]], dtype=np.float32),
            np.array([[100, 100], [150, 100], [150, 150], [100, 150]], dtype=np.float32),
        ]
        ids = np.array([[5], [7]], dtype=np.int32)
        mock_detector.detectMarkers.return_value = (corners, ids, None)
        detector.detector = mock_detector

        with patch("vision.aruco_detector.cv2.cvtColor") as mock_cvtColor:
            mock_cvtColor.return_value = np.ones((480, 640), dtype=np.uint8)

            detections = detector.detect(mock_frame)

            assert len(detections) == 2
            assert 5 in detections
            assert 7 in detections

    def test_detect_none_frame(self, detector):
        """Testa detecção com frame None."""
        detections = detector.detect(None)

        assert isinstance(detections, dict)
        assert len(detections) == 0

    def test_detect_invalid_frame_shape(self, detector):
        """Testa detecção com frame inválido."""
        invalid_frame = np.ones((480,), dtype=np.uint8)

        detections = detector.detect(invalid_frame)

        assert isinstance(detections, dict)
        assert len(detections) == 0

    def test_detect_exception_handling(self, detector, mock_frame):
        """Testa tratamento de exceção durante detecção."""
        mock_detector = MagicMock()
        mock_detector.detectMarkers.side_effect = Exception("Erro de detecção")
        detector.detector = mock_detector

        with patch("vision.aruco_detector.cv2.cvtColor") as mock_cvtColor:
            mock_cvtColor.return_value = np.ones((480, 640), dtype=np.uint8)

            detections = detector.detect(mock_frame)

            assert isinstance(detections, dict)
            assert len(detections) == 0

    # ========== Testes de Centróide ==========

    def test_calculate_centroid_valid_corners(self, detector):
        """Testa cálculo de centróide com cantos válidos."""
        corners = [(0, 0), (100, 0), (100, 100), (0, 100)]
        centroid = detector._calculate_centroid(corners)

        assert isinstance(centroid, tuple)
        assert len(centroid) == 2
        assert centroid[0] == 50.0
        assert centroid[1] == 50.0

    def test_calculate_centroid_small_marker(self, detector):
        """Testa centróide de marcador pequeno."""
        corners = [(10, 10), (20, 10), (20, 20), (10, 20)]
        centroid = detector._calculate_centroid(corners)

        assert centroid[0] == 15.0
        assert centroid[1] == 15.0

    def test_calculate_centroid_invalid_corner_count(self, detector):
        """Testa centróide com número inválido de cantos."""
        corners = [(0, 0), (100, 0), (100, 100)]  # Apenas 3
        centroid = detector._calculate_centroid(corners)

        assert centroid == (0.0, 0.0)

    def test_calculate_centroid_exception(self, detector):
        """Testa exceção no cálculo de centróide."""
        corners = [None, None, None, None]
        centroid = detector._calculate_centroid(corners)

        assert centroid == (0.0, 0.0)

    # ========== Testes de Validação ==========

    def test_validate_detections_empty(self, detector):
        """Testa validação de detecções vazias."""
        detections = {}
        assert detector.validate_detections(detections) is True

    def test_validate_detections_valid(self, detector):
        """Testa validação com detecções válidas."""
        detections = {
            5: Detection(marker_id=5, centroid=(30, 30), corners=[(0, 0), (60, 0), (60, 60), (0, 60)]),
            7: Detection(marker_id=7, centroid=(100, 100), corners=[(80, 80), (120, 80), (120, 120), (80, 120)]),
        }
        assert detector.validate_detections(detections) is True

    def test_validate_detections_invalid_type(self, detector):
        """Testa validação com tipo inválido."""
        detections = [5, 7]  # Lista ao invés de dict
        assert detector.validate_detections(detections) is False

    def test_validate_detections_invalid_id(self, detector):
        """Testa validação com ID inválido."""
        detections = {
            -1: Detection(marker_id=-1, centroid=(30, 30), corners=[]),
        }
        assert detector.validate_detections(detections) is False

    def test_validate_detections_invalid_centroid(self, detector):
        """Testa validação com centróide inválido."""
        detections = {
            5: Detection(marker_id=5, centroid=(30,), corners=[]),  # Apenas 1 coord
        }
        assert detector.validate_detections(detections) is False

    def test_validate_detections_negative_coordinates(self, detector):
        """Testa validação com coordenadas negativas."""
        detections = {
            5: Detection(marker_id=5, centroid=(-10, 30), corners=[]),
        }
        assert detector.validate_detections(detections) is False

    # ========== Testes de Desenho ==========

    def test_draw_detections_valid(self, detector, mock_frame):
        """Testa desenho de detecções válidas."""
        detections = {
            5: Detection(
                marker_id=5,
                centroid=(320, 240),
                corners=[(310, 230), (330, 230), (330, 250), (310, 250)],
            ),
        }

        with patch("vision.aruco_detector.cv2.circle") as mock_circle:
            with patch("vision.aruco_detector.cv2.putText") as mock_putText:
                result = detector.draw_detections(mock_frame.copy(), detections)

                assert result is not None
                assert result.shape == mock_frame.shape

    def test_draw_detections_none_frame(self, detector):
        """Testa desenho com frame None."""
        detections = {5: Detection(marker_id=5, centroid=(30, 30), corners=[])}
        result = detector.draw_detections(None, detections)

        assert result is None

    def test_draw_detections_exception(self, detector, mock_frame):
        """Testa tratamento de exceção ao desenhar."""
        detections = {5: Detection(marker_id=5, centroid=(None, None), corners=[])}

        with patch("vision.aruco_detector.cv2.circle") as mock_circle:
            mock_circle.side_effect = Exception("Erro de desenho")
            result = detector.draw_detections(mock_frame.copy(), detections)

            assert result is not None

    # ========== Testes de Estatísticas ==========

    def test_get_stats(self, detector):
        """Testa obtenção de estatísticas."""
        stats = detector.get_stats()

        assert isinstance(stats, dict)
        assert "total_detections" in stats
        assert "aruco_dict_size" in stats
        assert "marker_size" in stats
        assert stats["total_detections"] == 0
        assert stats["aruco_dict_size"] == 6
        assert stats["marker_size"] == 250

    def test_stats_after_detection(self, detector, mock_frame):
        """Testa estatísticas após detecção."""
        mock_detector = MagicMock()
        corners = [np.array([[10, 10], [50, 10], [50, 50], [10, 50]], dtype=np.float32)]
        ids = np.array([[5]], dtype=np.int32)
        mock_detector.detectMarkers.return_value = (corners, ids, None)
        detector.detector = mock_detector

        with patch("vision.aruco_detector.cv2.cvtColor") as mock_cvtColor:
            mock_cvtColor.return_value = np.ones((480, 640), dtype=np.uint8)
            detector.detect(mock_frame)

        stats = detector.get_stats()
        assert stats["total_detections"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
