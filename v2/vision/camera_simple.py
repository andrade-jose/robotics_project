"""
CameraSimple - Módulo de captura de câmera

Responsabilidades:
- Inicializar câmera
- Capturar frames
- Gerenciar recursos (release)
- Logging básico

Sem processamento de imagem - apenas captura.
Simples, testável, isolado.

Uso:
    camera = CameraSimple(camera_index=0)
    if camera.initialize():
        frame = camera.capture_frame()
        if frame is not None:
            print(f"Frame shape: {frame.shape}")
        camera.release()
"""

import cv2
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class CameraInfo:
    """Informações sobre câmera disponível."""
    index: int
    is_available: bool
    resolution: tuple = (640, 480)
    fps: int = 30
    backend: str = "Unknown"


class CameraSimple:
    """
    Capturador de câmera simples.

    Características:
    - Sem processamento de imagem
    - Thread-safe (uso sequencial)
    - Logging detalhado
    - Tratamento de erros robusto
    """

    def __init__(
        self,
        camera_index: int = 0,
        resolution: tuple = (640, 480),
        fps: int = 30,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Inicializa gerenciador de câmera.

        Args:
            camera_index: Índice da câmera (0 = padrão)
            resolution: Resolução (width, height)
            fps: Frames por segundo desejado
            logger: Logger customizado (ou usa default)
        """
        self.camera_index = camera_index
        self.resolution = resolution
        self.fps = fps
        self.capture = None
        self.is_initialized = False
        self.frames_captured = 0

        # Logger
        if logger is None:
            self.logger = logging.getLogger(__name__)
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter("[%(levelname)s] %(message)s")
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
                self.logger.setLevel(logging.INFO)
        else:
            self.logger = logger

    def scan_available_cameras(self) -> list:
        """
        Escaneia câmeras disponíveis no sistema.

        Returns:
            Lista de CameraInfo com câmeras encontradas
        """
        self.logger.info("[CAMERA] Escaneando câmeras disponíveis...")
        available = []

        # Testar até 5 câmeras
        for i in range(5):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = int(cap.get(cv2.CAP_PROP_FPS))
                    if fps == 0:
                        fps = 30

                    info = CameraInfo(
                        index=i,
                        is_available=True,
                        resolution=(w, h),
                        fps=fps,
                    )
                    available.append(info)
                    self.logger.info(
                        f"[CAMERA] Câmera {i} encontrada: "
                        f"{w}x{h} @ {fps}fps"
                    )
                cap.release()
            else:
                cap.release()

        if not available:
            self.logger.warning("[CAMERA] Nenhuma câmera encontrada!")
        else:
            self.logger.info(f"[CAMERA] Total: {len(available)} câmera(s)")

        return available

    def initialize_camera(self, camera_index: Optional[int] = None) -> bool:
        """
        Inicializa a câmera.

        Args:
            camera_index: Índice da câmera (sobrescreve default)

        Returns:
            True se inicializado com sucesso, False caso contrário
        """
        if self.is_initialized:
            self.logger.warning("[CAMERA] Câmera já foi inicializada!")
            return True

        if camera_index is not None:
            self.camera_index = camera_index

        try:
            self.logger.info(f"[CAMERA] Inicializando câmera {self.camera_index}...")

            self.capture = cv2.VideoCapture(self.camera_index)

            if not self.capture.isOpened():
                self.logger.error(
                    f"[CAMERA] Falha ao abrir câmera {self.camera_index}"
                )
                return False

            # Configurar resolução
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])

            # Configurar FPS
            self.capture.set(cv2.CAP_PROP_FPS, self.fps)

            # Tentar capturar um frame para verificar
            ret, frame = self.capture.read()
            if not ret or frame is None:
                self.logger.error("[CAMERA] Falha ao capturar frame inicial")
                self.capture.release()
                return False

            # Atualizar resolução real
            actual_w = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.resolution = (actual_w, actual_h)

            self.is_initialized = True
            self.frames_captured = 0

            self.logger.info(
                f"[CAMERA] Câmera {self.camera_index} inicializada com sucesso! "
                f"Resolução: {self.resolution}"
            )

            return True

        except Exception as e:
            self.logger.error(f"[CAMERA] Erro ao inicializar: {e}")
            return False

    def capture_frame(self) -> Optional[object]:
        """
        Captura um frame da câmera.

        Returns:
            numpy array (frame) ou None se falhar
        """
        if not self.is_initialized:
            self.logger.warning("[CAMERA] Câmera não foi inicializada!")
            return None

        if self.capture is None:
            self.logger.error("[CAMERA] Câmera não está disponível!")
            return None

        try:
            ret, frame = self.capture.read()

            if not ret or frame is None:
                self.logger.warning("[CAMERA] Falha ao capturar frame")
                return None

            self.frames_captured += 1
            return frame

        except Exception as e:
            self.logger.error(f"[CAMERA] Erro ao capturar frame: {e}")
            return None

    def get_camera_status(self) -> Dict[str, Any]:
        """
        Retorna status da câmera.

        Returns:
            Dict com informações sobre a câmera
        """
        if not self.is_initialized or self.capture is None:
            return {
                "is_initialized": False,
                "camera_index": self.camera_index,
                "frames_captured": 0,
            }

        try:
            w = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(self.capture.get(cv2.CAP_PROP_FPS))

            return {
                "is_initialized": True,
                "camera_index": self.camera_index,
                "resolution": (w, h),
                "fps": fps,
                "frames_captured": self.frames_captured,
                "backend": "OpenCV",
            }
        except Exception as e:
            self.logger.error(f"[CAMERA] Erro ao obter status: {e}")
            return {
                "is_initialized": True,
                "camera_index": self.camera_index,
                "frames_captured": self.frames_captured,
                "error": str(e),
            }

    def release(self):
        """Libera recursos da câmera."""
        if self.capture is not None:
            try:
                self.capture.release()
                self.logger.info(
                    f"[CAMERA] Câmera {self.camera_index} liberada "
                    f"({self.frames_captured} frames capturados)"
                )
            except Exception as e:
                self.logger.error(f"[CAMERA] Erro ao liberar câmera: {e}")
            finally:
                self.capture = None
                self.is_initialized = False

    def __enter__(self):
        """Context manager entry."""
        if not self.initialize_camera():
            raise RuntimeError("Falha ao inicializar câmera no context manager")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()

    def __del__(self):
        """Destrutor - garante limpeza."""
        if self.capture is not None:
            self.release()


# ============================================================================
# Teste se executado diretamente
# ============================================================================

if __name__ == "__main__":
    print("[TESTE] Teste do CameraSimple")
    print("")

    try:
        # Criar câmera
        camera = CameraSimple(camera_index=0)

        # Escanear câmeras disponíveis
        cameras = camera.scan_available_cameras()
        print(f"[OK] Câmeras encontradas: {len(cameras)}")
        for cam in cameras:
            print(f"  - Câmera {cam.index}: {cam.resolution[0]}x{cam.resolution[1]} @ {cam.fps}fps")
        print("")

        # Tentar inicializar
        if camera.initialize_camera():
            print("[OK] Câmera inicializada com sucesso")

            # Capturar alguns frames
            for i in range(5):
                frame = camera.capture_frame()
                if frame is not None:
                    print(f"[OK] Frame {i + 1}: {frame.shape}")
                else:
                    print(f"[ERRO] Frame {i + 1}: falha ao capturar")

            # Status final
            status = camera.get_camera_status()
            print(f"\n[STATUS] Câmera:")
            for key, value in status.items():
                print(f"  - {key}: {value}")

        else:
            print("[ERRO] Falha ao inicializar câmera")

    except Exception as e:
        print(f"[ERRO] Erro no teste: {e}")
        import traceback

        traceback.print_exc()

    finally:
        try:
            camera.release()
        except:
            pass
        print("\n[OK] Teste concluído")
