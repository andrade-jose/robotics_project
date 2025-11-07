"""
Testes para CameraSimple

Testes isolados para captura de câmera sem dependências externas.

Execution:
    pytest v2/vision/tests/test_camera.py -v
    pytest v2/vision/tests/test_camera.py::TestCameraSimple::test_initialization -v
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Adicionar v2 ao path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from vision.camera_simple import CameraSimple, CameraInfo


class TestCameraSimple:
    """Suite de testes para CameraSimple."""

    @pytest.fixture
    def camera(self):
        """Fixture: câmera com logger customizado."""
        logger = logging.getLogger("test_camera")
        logger.setLevel(logging.DEBUG)
        return CameraSimple(camera_index=0, logger=logger)

    @pytest.fixture
    def mock_cv2(self):
        """Fixture: mock do OpenCV."""
        with patch("vision.camera_simple.cv2") as mock:
            yield mock

    # ========== Testes de Inicialização ==========

    def test_initialization_default_values(self, camera):
        """Testa inicialização com valores padrão."""
        assert camera.camera_index == 0
        assert camera.resolution == (640, 480)
        assert camera.fps == 30
        assert not camera.is_initialized
        assert camera.capture is None
        assert camera.frames_captured == 0

    def test_initialization_custom_values(self):
        """Testa inicialização com valores customizados."""
        camera = CameraSimple(camera_index=1, resolution=(1280, 720), fps=60)
        assert camera.camera_index == 1
        assert camera.resolution == (1280, 720)
        assert camera.fps == 60

    def test_initialization_with_logger(self):
        """Testa inicialização com logger customizado."""
        custom_logger = logging.getLogger("custom")
        camera = CameraSimple(logger=custom_logger)
        assert camera.logger is custom_logger

    # ========== Testes de Inicialização de Câmera ==========

    def test_initialize_camera_success(self, camera, mock_cv2):
        """Testa inicialização bem-sucedida da câmera."""
        # Mock OpenCV
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, Mock())  # ret=True, frame=mock
        mock_cap.get.side_effect = lambda prop: 640 if prop == 3 else 480 if prop == 4 else 30
        mock_cv2.VideoCapture.return_value = mock_cap
        mock_cv2.CAP_PROP_FRAME_WIDTH = 3
        mock_cv2.CAP_PROP_FRAME_HEIGHT = 4
        mock_cv2.CAP_PROP_FPS = 5

        # Test
        result = camera.initialize_camera()

        assert result is True
        assert camera.is_initialized is True
        assert camera.capture is not None
        mock_cv2.VideoCapture.assert_called_once_with(0)

    def test_initialize_camera_already_initialized(self, camera, mock_cv2):
        """Testa que não re-inicializa se já foi inicializado."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, Mock())
        mock_cap.get.return_value = 0
        mock_cv2.VideoCapture.return_value = mock_cap

        # Primeira inicialização
        camera.initialize_camera()
        call_count_first = mock_cv2.VideoCapture.call_count

        # Segunda inicialização (deve retornar True sem fazer nada)
        result = camera.initialize_camera()

        assert result is True
        assert mock_cv2.VideoCapture.call_count == call_count_first

    def test_initialize_camera_failure_not_opened(self, camera, mock_cv2):
        """Testa falha quando câmera não abre."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_cv2.VideoCapture.return_value = mock_cap

        result = camera.initialize_camera()

        assert result is False
        assert camera.is_initialized is False
        assert camera.capture is None

    def test_initialize_camera_failure_no_frame(self, camera, mock_cv2):
        """Testa falha quando não consegue capturar frame."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (False, None)  # Falha na captura
        mock_cv2.VideoCapture.return_value = mock_cap

        result = camera.initialize_camera()

        assert result is False
        assert camera.is_initialized is False
        mock_cap.release.assert_called_once()

    def test_initialize_camera_custom_index(self, camera, mock_cv2):
        """Testa inicialização com índice de câmera customizado."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, Mock())
        mock_cap.get.return_value = 0
        mock_cv2.VideoCapture.return_value = mock_cap

        camera.initialize_camera(camera_index=2)

        mock_cv2.VideoCapture.assert_called_once_with(2)
        assert camera.camera_index == 2

    # ========== Testes de Captura de Frame ==========

    def test_capture_frame_success(self, camera, mock_cv2):
        """Testa captura bem-sucedida de frame."""
        mock_cap = MagicMock()
        mock_frame = Mock()
        mock_cap.read.return_value = (True, mock_frame)
        camera.capture = mock_cap
        camera.is_initialized = True

        frame = camera.capture_frame()

        assert frame is mock_frame
        assert camera.frames_captured == 1
        mock_cap.read.assert_called_once()

    def test_capture_frame_not_initialized(self, camera):
        """Testa captura quando câmera não está inicializada."""
        frame = camera.capture_frame()

        assert frame is None
        assert camera.frames_captured == 0

    def test_capture_frame_failure(self, camera, mock_cv2):
        """Testa falha ao capturar frame."""
        mock_cap = MagicMock()
        mock_cap.read.return_value = (False, None)
        camera.capture = mock_cap
        camera.is_initialized = True

        frame = camera.capture_frame()

        assert frame is None
        assert camera.frames_captured == 0

    def test_capture_frame_multiple_times(self, camera, mock_cv2):
        """Testa captura múltipla de frames."""
        mock_cap = MagicMock()
        mock_frame = Mock()
        mock_cap.read.return_value = (True, mock_frame)
        camera.capture = mock_cap
        camera.is_initialized = True

        # Capturar 5 frames
        for i in range(5):
            frame = camera.capture_frame()
            assert frame is not None
            assert camera.frames_captured == i + 1

    # ========== Testes de Status ==========

    def test_get_camera_status_not_initialized(self, camera):
        """Testa status quando câmera não está inicializada."""
        status = camera.get_camera_status()

        assert status["is_initialized"] is False
        assert status["camera_index"] == 0
        assert status["frames_captured"] == 0

    def test_get_camera_status_initialized(self, camera, mock_cv2):
        """Testa status quando câmera está inicializada."""
        mock_cap = MagicMock()
        mock_cap.get.side_effect = lambda prop: 1280 if prop == 3 else 720 if prop == 4 else 60
        camera.capture = mock_cap
        camera.is_initialized = True
        camera.frames_captured = 10

        mock_cv2.CAP_PROP_FRAME_WIDTH = 3
        mock_cv2.CAP_PROP_FRAME_HEIGHT = 4
        mock_cv2.CAP_PROP_FPS = 5

        status = camera.get_camera_status()

        assert status["is_initialized"] is True
        assert status["camera_index"] == 0
        assert status["resolution"] == (1280, 720)
        assert status["fps"] == 60
        assert status["frames_captured"] == 10

    # ========== Testes de Release ==========

    def test_release_success(self, camera, mock_cv2):
        """Testa liberação bem-sucedida."""
        mock_cap = MagicMock()
        camera.capture = mock_cap
        camera.is_initialized = True
        camera.frames_captured = 5

        camera.release()

        assert camera.capture is None
        assert camera.is_initialized is False
        mock_cap.release.assert_called_once()

    def test_release_when_not_initialized(self, camera):
        """Testa release quando não está inicializado."""
        camera.release()
        assert camera.capture is None
        assert camera.is_initialized is False

    def test_release_idempotent(self, camera, mock_cv2):
        """Testa que release pode ser chamado múltiplas vezes."""
        mock_cap = MagicMock()
        camera.capture = mock_cap
        camera.is_initialized = True

        camera.release()
        camera.release()  # Não deve causar erro

        assert camera.capture is None

    # ========== Testes de Context Manager ==========

    def test_context_manager_success(self, camera, mock_cv2):
        """Testa uso como context manager."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, Mock())
        mock_cap.get.return_value = 0
        mock_cv2.VideoCapture.return_value = mock_cap

        with CameraSimple(camera_index=0) as cam:
            assert cam.is_initialized is True
            frame = cam.capture_frame()
            assert frame is not None

        assert camera.is_initialized is False

    def test_context_manager_failure(self, camera, mock_cv2):
        """Testa context manager com falha na inicialização."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_cv2.VideoCapture.return_value = mock_cap

        with pytest.raises(RuntimeError):
            with CameraSimple(camera_index=0) as cam:
                pass

    # ========== Testes de Scan de Câmeras ==========

    def test_scan_available_cameras_found(self, camera, mock_cv2):
        """Testa scan quando câmeras são encontradas."""
        mock_cap = MagicMock()
        mock_cap.isOpened.side_effect = [True, True, False, False, False]
        mock_cap.read.return_value = (True, Mock())
        mock_cap.get.side_effect = lambda prop: 640 if prop == 3 else 480 if prop == 4 else 30
        mock_cv2.VideoCapture.return_value = mock_cap
        mock_cv2.CAP_PROP_FRAME_WIDTH = 3
        mock_cv2.CAP_PROP_FRAME_HEIGHT = 4
        mock_cv2.CAP_PROP_FPS = 5

        cameras = camera.scan_available_cameras()

        assert len(cameras) == 2
        assert cameras[0].index == 0
        assert cameras[1].index == 1

    def test_scan_available_cameras_none_found(self, camera, mock_cv2):
        """Testa scan quando nenhuma câmera é encontrada."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_cv2.VideoCapture.return_value = mock_cap

        cameras = camera.scan_available_cameras()

        assert len(cameras) == 0

    # ========== Testes de Resiliência ==========

    def test_capture_frame_exception_handling(self, camera, mock_cv2):
        """Testa tratamento de exceção ao capturar frame."""
        mock_cap = MagicMock()
        mock_cap.read.side_effect = Exception("Erro de câmera")
        camera.capture = mock_cap
        camera.is_initialized = True

        frame = camera.capture_frame()

        assert frame is None

    def test_multiple_initialize_release_cycles(self, camera, mock_cv2):
        """Testa múltiplos ciclos de inicialização e release."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, Mock())
        mock_cap.get.return_value = 0
        mock_cv2.VideoCapture.return_value = mock_cap

        for _ in range(3):
            assert camera.initialize_camera() is True
            assert camera.is_initialized is True
            camera.release()
            assert camera.is_initialized is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
