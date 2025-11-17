"""
Main V2 - Entrada Principal para Sistema Tapatan V2

Pipeline Completo:
1. Inicializar câmera e robô
2. Aguardar calibração (2 marcadores ArUco)
3. Loop de jogo:
   - Ler posição das peças
   - Validar movimentos
   - Executar no jogo
   - Enviar ao robô

Uso:
    python main_v2.py              # Modo interativo
    python main_v2.py --test       # Modo teste (simulado)
    python main_v2.py --debug      # Com logging detalhado

Status: Phase 5 - GameOrchestrator Integration
Próxima: Phase 6 - Testes com robô real
"""

import sys
import logging
import argparse
from typing import Optional

try:
    from v2.vision.calibration_orchestrator import CalibrationOrchestrator
    from v2.integration.game_orchestrator_v2 import GameOrchestratorV2, GameState
    from v2.services.board_coordinate_system_v2 import BoardCoordinateSystemV2
except ImportError:
    from vision.calibration_orchestrator import CalibrationOrchestrator
    from integration.game_orchestrator_v2 import GameOrchestratorV2, GameState
    from services.board_coordinate_system_v2 import BoardCoordinateSystemV2


class MainV2:
    """Classe principal para gerenciar o jogo Tapatan V2."""

    def __init__(self, test_mode: bool = False, debug: bool = False):
        """
        Inicializa sistema V2.

        Args:
            test_mode: Se True, usa câmera simulada
            debug: Se True, ativa logging detalhado
        """
        self.test_mode = test_mode
        self.debug = debug

        # Configurar logging
        level = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(
            level=level,
            format='[%(name)s] %(levelname)s: %(message)s',
        )
        self.logger = logging.getLogger("MainV2")

        # Componentes
        self.calibrator: Optional[CalibrationOrchestrator] = None
        self.game_orch: Optional[GameOrchestratorV2] = None
        self.camera = None
        self.robot_service = None

        self.logger.info("[MAIN_V2] Inicializando sistema Tapatan V2...")

    def setup(self) -> bool:
        """
        Configura todos os componentes.

        Returns:
            True se sucesso, False caso contrário
        """
        self.logger.info("[MAIN_V2] Configurando componentes...")

        try:
            # 1. Inicializar calibrador
            self.logger.info("[MAIN_V2] Criando CalibrationOrchestrator...")
            self.calibrator = CalibrationOrchestrator(distance_mm=270.0)

            # 2. Inicializar serviço de jogo
            self.logger.info("[MAIN_V2] Criando GameOrchestratorV2...")
            self.game_orch = GameOrchestratorV2(
                calibration_orchestrator=self.calibrator,
                robot_service=self.robot_service,  # Será None em teste
            )

            # 3. Inicializar câmera (se disponível)
            if not self.test_mode:
                self.logger.info("[MAIN_V2] Inicializando câmera...")
                try:
                    # from v2.vision.camera_simple import CameraSimple
                    # self.camera = CameraSimple()
                    self.logger.warning("[MAIN_V2] Câmera não disponível em dev environment")
                except Exception as e:
                    self.logger.warning(f"[MAIN_V2] Erro ao inicializar câmera: {e}")
                    self.test_mode = True

            # 4. Inicializar robô (se disponível)
            if not self.test_mode:
                self.logger.info("[MAIN_V2] Inicializando robô...")
                try:
                    # from services.robot_service import RobotService
                    # self.robot_service = RobotService()
                    self.logger.warning("[MAIN_V2] Robô não disponível em dev environment")
                except Exception as e:
                    self.logger.warning(f"[MAIN_V2] Erro ao inicializar robô: {e}")

            self.logger.info("[MAIN_V2] ✅ Componentes configurados com sucesso")
            return True

        except Exception as e:
            self.logger.error(f"[MAIN_V2] ❌ Erro ao configurar componentes: {e}")
            return False

    def calibrate(self) -> bool:
        """
        Aguarda calibração do sistema.

        Returns:
            True se calibrado, False caso contrário
        """
        if self.test_mode:
            self.logger.warning("[MAIN_V2] Modo teste: simulando calibração")
            # Simular calibração bem-sucedida
            import numpy as np
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            # Em modo teste, simular calibração
            return self.game_orch.calibrate_from_frame(frame) if self.game_orch else False

        self.logger.info("[MAIN_V2] Aguardando calibração...")
        self.logger.info("[MAIN_V2] Posicione 2 marcadores ArUco e pressione qualquer tecla...")

        # Em produção, usar câmera real
        # TODO: Implementar loop de câmera real quando disponível
        return False

    def play_game(self):
        """Loop principal do jogo."""
        if self.game_orch is None:
            self.logger.error("[MAIN_V2] GameOrchestrator não inicializado")
            return

        if not self.game_orch.is_calibrated():
            self.logger.error("[MAIN_V2] Sistema não está calibrado")
            return

        self.logger.info("[MAIN_V2] ✅ Sistema pronto para jogo!")
        self.logger.info("[MAIN_V2] ========================================")

        # Estado do jogo
        game_state = self.game_orch.get_game_state()
        self.logger.info(f"[MAIN_V2] Estado inicial:")
        self.logger.info(f"  - Calibrado: {game_state['is_calibrated']}")
        self.logger.info(f"  - Jogador: {game_state['current_player']}")

        # Loop de teste: executar alguns movimentos exemplo
        example_moves = [
            (0, 4),  # Colocar peça no centro
            (8, 7),  # Mover peça
        ]

        for from_pos, to_pos in example_moves:
            self.logger.info(f"[MAIN_V2] Testando movimento: {from_pos} → {to_pos}")

            result = self.game_orch.execute_move(from_pos, to_pos)

            if result.success:
                self.logger.info(
                    f"[MAIN_V2] ✅ Movimento bem-sucedido "
                    f"(robot={result.executed_by_robot})"
                )
            else:
                self.logger.warning(f"[MAIN_V2] ❌ Movimento falhado: {result.reason}")

        # Exibir estado final
        final_state = self.game_orch.get_game_state()
        self.logger.info(f"[MAIN_V2] Estado final:")
        self.logger.info(f"  - Movimentos: {len(final_state['move_history'])}")
        self.logger.info(f"  - Histórico: {final_state['move_history']}")

    def print_info(self):
        """Imprime informações detalhadas do sistema."""
        if self.game_orch is None:
            self.logger.warning("[MAIN_V2] GameOrchestrator não inicializado")
            return

        info = self.game_orch.get_detailed_info()

        self.logger.info("[MAIN_V2] ========================================")
        self.logger.info("[MAIN_V2] INFORMAÇÕES DO SISTEMA")
        self.logger.info("[MAIN_V2] ========================================")
        self.logger.info(f"Estado: {info['state']}")
        self.logger.info(f"Calibrado: {info['is_calibrated']}")
        self.logger.info(f"Tentativas calibração: {info['calibration_status']['calibration_attempts']}")
        self.logger.info(f"Calibrações bem-sucedidas: {info['calibration_status']['successful_calibrations']}")

        if info['board_positions']:
            self.logger.info("Posições do tabuleiro (mm):")
            for pos, coords in sorted(info['board_positions'].items()):
                self.logger.info(f"  Posição {pos}: ({coords[0]:.1f}, {coords[1]:.1f})")

    def run(self):
        """Executa sistema completo."""
        try:
            # Setup
            if not self.setup():
                self.logger.error("[MAIN_V2] Falha no setup")
                return False

            # Calibração
            if not self.calibrate():
                self.logger.error("[MAIN_V2] Falha na calibração")
                return False

            # Exibir informações
            self.print_info()

            # Executar jogo
            self.play_game()

            self.logger.info("[MAIN_V2] ✅ Sistema executado com sucesso!")
            return True

        except Exception as e:
            self.logger.error(f"[MAIN_V2] ❌ Erro durante execução: {e}", exc_info=True)
            return False


def main():
    """Função principal."""
    parser = argparse.ArgumentParser(
        description="Sistema Tapatan V2 com calibração e controle robótico"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Modo teste (simula câmera e robô)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Ativa logging detalhado",
    )

    args = parser.parse_args()

    # Criar e executar
    main_v2 = MainV2(test_mode=args.test, debug=args.debug)
    success = main_v2.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
