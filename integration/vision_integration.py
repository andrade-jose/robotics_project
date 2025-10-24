"""
VisionIntegration - Integração com Sistema de Visão ArUco
==========================================================
Responsável por toda a integração com o sistema de visão:
- Inicialização e gerenciamento da câmera
- Loop de captura e detecção em thread separada
- Calibração automática e manual
- Conversão de coordenadas para posições do tabuleiro
"""

import time
import threading
from typing import Optional, Dict, Any

try:
    import cv2
    from vision import ArUcoVisionSystem, CameraManager, VisualMonitor, create_vision_system
    VISION_AVAILABLE = True
except ImportError:
    VISION_AVAILABLE = False
    ArUcoVisionSystem = None
    CameraManager = None
    VisualMonitor = None


class VisionIntegration:
    """
    Gerencia toda a integração com o sistema de visão ArUco.

    Responsabilidades:
    - Inicializar e finalizar o sistema de visão
    - Executar loop de captura em thread separada
    - Processar detecções e calibração
    - Converter coordenadas da visão para posições do jogo
    - Fornecer estado atual do sistema de visão
    """

    def __init__(self):
        """Inicializa o componente de integração com visão."""
        # Componentes do sistema de visão
        self.vision_system: Optional[ArUcoVisionSystem] = None
        self.camera_manager: Optional[CameraManager] = None
        self.visual_monitor: Optional[VisualMonitor] = None

        # Thread e controle
        self.vision_thread: Optional[threading.Thread] = None
        self.vision_active = False
        self.vision_calibrated = False

        # Estado da visão
        self.current_detections: Dict[str, Any] = {}
        self.board_positions_detected: Dict[int, Any] = {}
        self.show_vision_window = False

    # ========== INICIALIZAÇÃO E FINALIZAÇÃO ==========

    def inicializar_sistema_visao(self) -> bool:
        """
        Inicializa o sistema de visão integrado.

        Returns:
            True se inicializado com sucesso, False caso contrário
        """
        if not VISION_AVAILABLE:
            print("❌ Sistema de visão não está disponível (bibliotecas ausentes).")
            return False

        try:
            print("📹 Inicializando sistema de visão...")
            self.vision_system, self.camera_manager, self.visual_monitor = create_vision_system()

            if not self.camera_manager.initialize_camera():
                print("⚠️ Câmera não disponível - jogo continuará sem visão")
                return False

            print("✅ Sistema de visão inicializado!")
            return True

        except Exception as e:
            print(f"❌ Erro ao inicializar visão: {e}")
            return False

    def parar_sistema_visao(self):
        """Para a thread de visão e libera a câmera."""
        self.vision_active = False

        if self.vision_thread and self.vision_thread.is_alive():
            self.vision_thread.join(timeout=2)

        if self.camera_manager:
            self.camera_manager.release()

        if VISION_AVAILABLE:
            cv2.destroyAllWindows()

        print("📹 Sistema de visão finalizado")

    # ========== THREAD DE VISÃO ==========

    def iniciar_visao_em_thread(self):
        """Inicia o sistema de visão em uma thread separada."""
        if not self.vision_system or not self.camera_manager:
            return

        self.vision_active = True
        self.vision_thread = threading.Thread(target=self._loop_visao, daemon=True)
        self.vision_thread.start()
        print("🎥 Sistema de visão ativo em background")

    def _loop_visao(self):
        """Loop principal da visão executado na thread."""
        while self.vision_active:
            try:
                # Captura frame da câmera
                frame = self.camera_manager.capture_frame()
                if frame is None:
                    time.sleep(0.1)
                    continue

                # Detecta marcadores ArUco
                detections = self.vision_system.detect_markers(frame)
                self.current_detections = detections

                # Atualiza posições das peças no tabuleiro
                self._atualizar_posicoes_jogo(detections)

                # Calibração automática se não calibrado
                if not self.vision_calibrated and len(detections.get('reference_markers', {})) >= 2:
                    if self.vision_system.calibrate_system(detections):
                        self.vision_calibrated = True
                        print("\n🎯 Sistema de visão calibrado automaticamente!")

                # Mostra janela de visualização se habilitada
                if self.show_vision_window:
                    display_frame = self.visual_monitor.draw_detection_overlay(frame, detections)
                    cv2.imshow("Tapatan Vision System", display_frame)

                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        self.vision_active = False
                        break
                    elif key == ord('c'):
                        self._calibrar_visao_manual(detections)
                    elif key == ord('s'):
                        filename = f"tapatan_vision_{int(time.time())}.jpg"
                        cv2.imwrite(filename, display_frame)
                        print(f"📸 Screenshot salvo como {filename}")

                time.sleep(0.03)  # ~30 FPS

            except Exception as e:
                print(f"❌ Erro no loop de visão: {e}")
                time.sleep(1)

        if self.show_vision_window:
            cv2.destroyAllWindows()

    # ========== PROCESSAMENTO DE DETECÇÕES ==========

    def _atualizar_posicoes_jogo(self, detections: dict):
        """
        Atualiza o estado das peças detectadas no tabuleiro.

        Args:
            detections: Dicionário com as detecções dos marcadores
        """
        self.board_positions_detected.clear()

        for group_name in ['group1_markers', 'group2_markers']:
            for marker_id, marker_info in detections.get(group_name, {}).items():
                # Obtém coordenadas do tabuleiro normalizadas
                board_coords = self.vision_system.get_board_coordinates(marker_info)
                if board_coords is not None:
                    # Converte para posição do tabuleiro (0-8)
                    board_position = self._coords_to_board_position(board_coords)
                    if board_position is not None:
                        player_group = 1 if group_name == 'group1_markers' else 2
                        self.board_positions_detected[board_position] = {
                            'player': player_group,
                            'marker_id': marker_id,
                            'coordinates': board_coords
                        }

    @staticmethod
    def _coords_to_board_position(coords: tuple) -> Optional[int]:
        """
        Converte coordenadas normalizadas para uma posição (0-8) no tabuleiro.

        Args:
            coords: Tupla (x, y) com coordenadas normalizadas [-1, 1]

        Returns:
            Posição no tabuleiro (0-8) ou None se inválido
        """
        try:
            x, y = coords

            # Converte de [-1, 1] para [0, 2] (índices de coluna/linha)
            col = int((x + 1.0) / 2.0 * 3)
            row = int((y + 1.0) / 2.0 * 3)

            # Garante limites válidos
            col = max(0, min(2, col))
            row = max(0, min(2, row))

            # Converte para posição linear (0-8)
            return row * 3 + col

        except (TypeError, ValueError) as e:
            print(f"❌ Erro na conversão de coordenadas: {e}")
            return None

    # ========== CALIBRAÇÃO ==========

    def _calibrar_visao_manual(self, detections: dict):
        """
        Realiza a calibração manual da visão.

        Args:
            detections: Dicionário com as detecções atuais
        """
        if self.vision_system.calibrate_system(detections):
            self.vision_calibrated = True
            print("\n✅ Sistema de visão calibrado manualmente!")
            summary = self.visual_monitor.show_detection_summary(detections)
            print(f"📊 Status: {summary}")
        else:
            print("\n❌ Calibração manual falhou - verifique marcadores de referência")

    # ========== ESTADO DO SISTEMA ==========

    def obter_estado_visao(self) -> dict:
        """
        Retorna um dicionário com o estado atual do sistema de visão.

        Returns:
            Dicionário com informações do estado da visão:
            - available: bool - Se o sistema está disponível
            - calibrated: bool - Se está calibrado
            - active: bool - Se está ativo
            - detections_count: int - Número de detecções
            - board_positions: dict - Posições das peças detectadas
            - last_detection_time: float - Timestamp da última detecção
        """
        if not self.vision_system:
            return {'available': False}

        return {
            'available': True,
            'calibrated': self.vision_calibrated,
            'active': self.vision_active,
            'detections_count': self.current_detections.get('detection_count', 0),
            'board_positions': self.board_positions_detected.copy(),
            'last_detection_time': self.current_detections.get('timestamp', 0)
        }

    # ========== QUERIES ==========

    def is_available(self) -> bool:
        """Verifica se o sistema de visão está disponível."""
        return VISION_AVAILABLE and self.vision_system is not None