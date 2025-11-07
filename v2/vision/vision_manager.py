"""
VisionManager - Orquestrador do sistema de visão V2

Responsabilidades:
- Orquestrar camera_simple, aruco_detector, grid_calculator
- Gerenciar loop de visão (thread ou sequencial)
- Sincronizar com jogo
- Logging e diagnósticos

Modular: cada componente testável isoladamente.
Simples: sem processamento complexo, apenas orquestra.

Uso:
    manager = VisionManager()
    manager.start()
    state = manager.get_current_state()
    manager.stop()
"""

import logging
import threading
import time
from typing import Optional, Dict
from dataclasses import dataclass

from .camera_simple import CameraSimple
from .aruco_detector import ArUcoDetector
from .grid_calculator import GridCalculator


@dataclass
class VisionState:
    """Estado atual do sistema de visão."""
    timestamp: float
    board_state: Dict[int, str]  # {position: 'vazio'|'peça_X'|'ambíguo'}
    frame_count: int
    detections_count: int
    is_valid: bool


class VisionManager:
    """
    Orquestrador do sistema de visão V2.

    Características:
    - Orquestra 3 módulos modularesdo sistema de visão
    - Thread-safe para leitura de estado
    - Fallback gracioso se câmera falhar
    - Logging detalhado
    """

    def __init__(
        self,
        camera_index: int = 0,
        resolution: tuple = (640, 480),
        fps: int = 30,
        use_threading: bool = False,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Inicializa orquestrador de visão.

        Args:
            camera_index: Índice da câmera
            resolution: Resolução (width, height)
            fps: Frames por segundo
            use_threading: Se True, usa thread para processamento
            logger: Logger customizado
        """
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

        # Componentes
        self.camera = CameraSimple(
            camera_index=camera_index,
            resolution=resolution,
            fps=fps,
            logger=self.logger,
        )
        self.detector = ArUcoDetector(logger=self.logger)
        self.grid = GridCalculator(
            frame_width=resolution[0],
            frame_height=resolution[1],
            logger=self.logger,
        )

        # Estado
        self.is_running = False
        self.use_threading = use_threading
        self.vision_thread = None
        self.current_state = None
        self.frame_count = 0
        self.detections_count = 0
        self.last_error = None

        # Thread safety
        self.state_lock = threading.RLock()

        self.logger.info("[VISION] VisionManager inicializado")

    def start(self) -> bool:
        """
        Inicia sistema de visão.

        Returns:
            True se iniciado com sucesso, False caso contrário
        """
        try:
            self.logger.info("[VISION] Iniciando sistema de visão...")

            # Inicializar câmera
            if not self.camera.initialize_camera():
                self.logger.error("[VISION] Falha ao inicializar câmera")
                return False

            self.is_running = True
            self.frame_count = 0
            self.detections_count = 0

            # Processar primeiro frame para ter estado inicial
            if not self._process_single_frame():
                self.logger.warning("[VISION] Falha ao processar primeiro frame")

            if self.use_threading:
                self.vision_thread = threading.Thread(target=self._vision_loop, daemon=True)
                self.vision_thread.start()
                self.logger.info("[VISION] Thread de visão iniciada")

            self.logger.info("[VISION] Sistema de visão iniciado com sucesso")
            return True

        except Exception as e:
            self.logger.error(f"[VISION] Erro ao iniciar: {e}")
            self.last_error = str(e)
            return False

    def stop(self):
        """Para sistema de visão."""
        try:
            self.logger.info("[VISION] Parando sistema de visão...")

            self.is_running = False

            if self.use_threading and self.vision_thread is not None:
                self.vision_thread.join(timeout=2.0)
                self.logger.info("[VISION] Thread de visão parada")

            self.camera.release()
            self.logger.info("[VISION] Sistema de visão parado")

        except Exception as e:
            self.logger.error(f"[VISION] Erro ao parar: {e}")

    def _vision_loop(self):
        """Loop principal de visão (executa em thread)."""
        self.logger.info("[VISION] Loop de visão iniciado")

        try:
            while self.is_running:
                self._process_single_frame()
                time.sleep(1.0 / self.camera.fps)

        except Exception as e:
            self.logger.error(f"[VISION] Erro no loop: {e}")
            self.last_error = str(e)
            self.is_running = False

        self.logger.info("[VISION] Loop de visão encerrado")

    def _process_single_frame(self) -> bool:
        """
        Processa um único frame.

        Returns:
            True se processado com sucesso, False caso contrário
        """
        try:
            # Capturar frame
            frame = self.camera.capture_frame()
            if frame is None:
                self.logger.debug("[VISION] Frame None - câmera pode estar desconectada")
                return False

            self.frame_count += 1

            # Detectar marcadores
            detections = self.detector.detect(frame)

            if detections:
                self.detections_count += 1

            # Calcular estado do grid
            board_state = self.grid.calculate_state(detections)

            # Validar estado
            is_valid = self.grid.validate_state(board_state)

            # Atualizar estado thread-safe
            with self.state_lock:
                self.current_state = VisionState(
                    timestamp=time.time(),
                    board_state=board_state,
                    frame_count=self.frame_count,
                    detections_count=self.detections_count,
                    is_valid=is_valid,
                )

            return True

        except Exception as e:
            self.logger.error(f"[VISION] Erro ao processar frame: {e}")
            self.last_error = str(e)
            return False

    def get_current_state(self) -> Optional[VisionState]:
        """
        Retorna estado atual da visão.

        Returns:
            VisionState ou None se não foi processado nenhum frame
        """
        with self.state_lock:
            return self.current_state

    def process_frame_sync(self, frame) -> Optional[Dict[int, str]]:
        """
        Processa um frame de forma síncrona (sem threading).

        Args:
            frame: numpy array (imagem OpenCV)

        Returns:
            Dict de estado do board ou None se erro
        """
        try:
            detections = self.detector.detect(frame)
            board_state = self.grid.calculate_state(detections)

            if self.grid.validate_state(board_state):
                return board_state
            else:
                self.logger.warning("[VISION] Estado inválido após processamento")
                return None

        except Exception as e:
            self.logger.error(f"[VISION] Erro ao processar frame: {e}")
            return None

    def get_stats(self) -> dict:
        """Retorna estatísticas do sistema de visão."""
        camera_stats = self.camera.get_camera_status()
        detector_stats = self.detector.get_stats()
        grid_stats = self.grid.get_stats()

        return {
            "camera": camera_stats,
            "detector": detector_stats,
            "grid": grid_stats,
            "frames_processed": self.frame_count,
            "detections_total": self.detections_count,
            "is_running": self.is_running,
            "use_threading": self.use_threading,
            "last_error": self.last_error,
        }

    def __enter__(self):
        """Context manager entry."""
        if not self.start():
            raise RuntimeError("Falha ao iniciar VisionManager em context manager")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


# ============================================================================
# Teste se executado diretamente
# ============================================================================

if __name__ == "__main__":
    print("[TESTE] Teste do VisionManager")
    print("")

    try:
        # Modo 1: Uso com context manager
        print("[TESTE] Modo 1: Context manager (com threading)")
        with VisionManager(use_threading=False) as manager:
            print("[OK] VisionManager inicializado")

            # Processar alguns frames
            for i in range(3):
                state = manager.get_current_state()
                if state:
                    print(f"[FRAME {i+1}] Estado do board: ocupadas={len(manager.grid.get_occupied_positions(state.board_state))}/9")
                time.sleep(0.1)

        print("[OK] VisionManager finalizado")

        # Modo 2: Uso manual
        print("\n[TESTE] Modo 2: Inicialização manual")
        manager = VisionManager(use_threading=False)

        if manager.start():
            print("[OK] VisionManager iniciado")

            # Processar frames
            for i in range(3):
                state = manager.get_current_state()
                if state:
                    print(f"[FRAME {i+1}] Timestamp: {state.timestamp:.2f}")

            # Stats
            stats = manager.get_stats()
            print(f"\n[STATS] VisionManager:")
            print(f"  - Frames processados: {stats['frames_processed']}")
            print(f"  - Detecções totais: {stats['detections_total']}")
            print(f"  - Câmera: {stats['camera']['is_initialized']}")

            manager.stop()
            print("[OK] VisionManager parado")

        else:
            print("[ERRO] Falha ao iniciar VisionManager")

    except Exception as e:
        print(f"[ERRO] Erro no teste: {e}")
        import traceback

        traceback.print_exc()

    print("\n[OK] Teste concluído")
