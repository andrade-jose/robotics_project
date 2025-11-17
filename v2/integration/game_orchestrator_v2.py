"""
GameOrchestratorV2 - Orquestrador Principal do Jogo Tapatan V2

Responsabilidades:
- Integrar CalibrationOrchestrator (Phase 4)
- Orquestrar lógica do jogo + calibração + movimentos do robô
- Gerenciar estados do jogo (calibração → pronto → em jogo)
- Validar movimentos usando workspace validator
- Enviar comandos ao robô com coordenadas calibradas

Pipeline:
1. Calibração: frame da câmera → CalibrationOrchestrator
2. Validação: movimento → BoardCoordinateSystemV2 → validar
3. Execução: movimento validado → RobotService → movimentar robô

Uso:
    orchestrator = GameOrchestratorV2(
        calibrator=calibration_orchestrator,
        robot_service=robot_service,
    )

    # Calibrar
    if orchestrator.calibrate_from_frame(frame):
        print("Sistema calibrado!")

    # Executar movimento
    if orchestrator.execute_move(from_pos=0, to_pos=4):
        print("Movimento bem-sucedido!")
"""

import logging
from typing import Optional, Set, Dict, Any, Tuple
from enum import Enum
from dataclasses import dataclass

try:
    from v2.vision.calibration_orchestrator import CalibrationOrchestrator
    from v2.services.board_coordinate_system_v2 import BoardCoordinateSystemV2
    from v2.logic_control.tapatan_logic import TabuleiraTapatan
except ImportError:
    from vision.calibration_orchestrator import CalibrationOrchestrator
    from services.board_coordinate_system_v2 import BoardCoordinateSystemV2
    from logic_control.tapatan_logic import TabuleiraTapatan


class GameState(Enum):
    """Estados do orquestrador de jogo."""
    NOT_INITIALIZED = "not_initialized"
    WAITING_CALIBRATION = "waiting_calibration"
    CALIBRATING = "calibrating"
    READY = "ready"
    IN_GAME = "in_game"
    GAME_OVER = "game_over"
    ERROR = "error"


@dataclass
class MoveResult:
    """Resultado de uma execução de movimento."""
    success: bool
    move_from: int
    move_to: int
    reason: Optional[str] = None  # Motivo se falhou
    executed_by_robot: bool = False


class GameOrchestratorV2:
    """
    Orquestrador principal do jogo V2 com integração de calibração.

    Características:
    - Pipeline completo: calibração → jogo → robô
    - Validação de movimentos usando workspace validator
    - Gerenciamento de estado do jogo
    - Logging detalhado
    - Interface simples e intuitiva
    """

    def __init__(
        self,
        calibration_orchestrator: CalibrationOrchestrator,
        robot_service=None,  # Optional: pode ser Mock para testes
        logger: Optional[logging.Logger] = None,
    ):
        """
        Inicializa orquestrador de jogo V2.

        Args:
            calibration_orchestrator: Orquestrador de calibração (Phase 4)
            robot_service: Serviço do robô (opcional para testes)
            logger: Logger customizado
        """
        self.calibrator = calibration_orchestrator
        self.robot_service = robot_service

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

        # Sistema de coordenadas sincronizado com calibração
        self.board_coords = BoardCoordinateSystemV2(
            calibration_orchestrator, logger=self.logger
        )

        # Lógica do jogo (Tapatan)
        self.game = TabuleiraTapatan()

        # Estado
        self.state = GameState.NOT_INITIALIZED
        self.move_history: list = []
        self.last_error: Optional[str] = None

        self.logger.info(
            "[GAME_ORCH_V2] Inicializado com calibração e controle robótico"
        )

    # ========== CALIBRAÇÃO ==========

    def calibrate_from_frame(self, frame) -> bool:
        """
        Tenta calibrar o sistema a partir de um frame da câmera.

        Pipeline:
        1. CalibrationOrchestrator processa frame
        2. Se sucesso → estado READY
        3. Se falha → continua em WAITING_CALIBRATION

        Args:
            frame: Imagem da câmera (numpy array BGR)

        Returns:
            True se calibração bem-sucedida, False caso contrário
        """
        if self.state == GameState.NOT_INITIALIZED:
            self.state = GameState.WAITING_CALIBRATION

        self.state = GameState.CALIBRATING
        self.logger.info("[GAME_ORCH_V2] Iniciando calibração...")

        try:
            # Executar pipeline de calibração (Phase 4)
            result = self.calibrator.calibrate(frame)

            if result.is_calibrated:
                self.state = GameState.READY
                status = self.calibrator.get_calibration_status()
                self.logger.info(
                    f"[GAME_ORCH_V2] ✅ Calibração bem-sucedida "
                    f"(confiança={result.confidence:.2f}, "
                    f"tentativas={status['calibration_attempts']})"
                )
                return True
            else:
                self.state = GameState.WAITING_CALIBRATION
                self.last_error = result.error_message
                self.logger.warning(
                    f"[GAME_ORCH_V2] ❌ Falha na calibração: {result.error_message}"
                )
                return False

        except Exception as e:
            self.state = GameState.ERROR
            self.last_error = str(e)
            self.logger.error(
                f"[GAME_ORCH_V2] ❌ Erro inesperado durante calibração: {e}"
            )
            return False

    def is_calibrated(self) -> bool:
        """Verifica se o sistema está calibrado."""
        return self.board_coords.is_calibrated()

    # ========== EXECUÇÃO DE MOVIMENTOS ==========

    def execute_move(
        self,
        from_position: int,
        to_position: int,
        send_to_robot: bool = True,
    ) -> MoveResult:
        """
        Executa um movimento completo: validação → jogo → robô.

        Pipeline:
        1. Validar movimento com calibração
        2. Validar movimento no jogo (Tapatan)
        3. Executar no jogo
        4. (Opcional) Enviar ao robô
        5. Retornar resultado

        Args:
            from_position: Posição inicial (0-8)
            to_position: Posição final (0-8)
            send_to_robot: Se True, envia ao robô após validação

        Returns:
            MoveResult com resultado da execução
        """
        self.logger.info(
            f"[GAME_ORCH_V2] Executando movimento: {from_position} → {to_position}"
        )

        # Verificar se está pronto para jogo
        if not self.is_calibrated():
            self.logger.error("[GAME_ORCH_V2] Sistema não está calibrado")
            return MoveResult(
                success=False,
                move_from=from_position,
                move_to=to_position,
                reason="Sistema não está calibrado",
                executed_by_robot=False,
            )

        # Etapa 1: Validar movimento com calibração
        occupied = self._get_occupied_positions()

        if not self.board_coords.validate_move(from_position, to_position, occupied):
            self.logger.error(
                f"[GAME_ORCH_V2] ❌ Movimento inválido na validação de coordenadas: "
                f"{from_position} → {to_position}"
            )
            return MoveResult(
                success=False,
                move_from=from_position,
                move_to=to_position,
                reason="Movimento inválido (fora dos limites ou ocupado)",
                executed_by_robot=False,
            )

        # Etapa 2: Validar movimento no jogo (Tapatan)
        if not self.game.is_valid_move(from_position, to_position):
            self.logger.error(
                f"[GAME_ORCH_V2] ❌ Movimento não permitido no jogo: "
                f"{from_position} → {to_position}"
            )
            return MoveResult(
                success=False,
                move_from=from_position,
                move_to=to_position,
                reason="Movimento não permitido no jogo (Tapatan)",
                executed_by_robot=False,
            )

        # Etapa 3: Executar no jogo
        try:
            self.game.make_move(from_position, to_position)
            self.logger.info(
                f"[GAME_ORCH_V2] ✅ Movimento executado no jogo: "
                f"{from_position} → {to_position}"
            )
        except Exception as e:
            self.logger.error(
                f"[GAME_ORCH_V2] ❌ Erro ao executar movimento no jogo: {e}"
            )
            return MoveResult(
                success=False,
                move_from=from_position,
                move_to=to_position,
                reason=f"Erro no jogo: {str(e)}",
                executed_by_robot=False,
            )

        # Etapa 4: Enviar ao robô (se configurado e habilitado)
        executed_by_robot = False
        if send_to_robot and self.robot_service:
            if self._send_to_robot(to_position):
                executed_by_robot = True
                self.logger.info(
                    f"[GAME_ORCH_V2] ✅ Movimento enviado ao robô: {to_position}"
                )
            else:
                self.logger.warning(
                    f"[GAME_ORCH_V2] ⚠️ Movimento validado no jogo, "
                    f"mas falha ao enviar ao robô"
                )

        # Etapa 5: Registrar movimento
        self.move_history.append({
            "from": from_position,
            "to": to_position,
            "success": True,
            "robot_executed": executed_by_robot,
        })

        return MoveResult(
            success=True,
            move_from=from_position,
            move_to=to_position,
            reason=None,
            executed_by_robot=executed_by_robot,
        )

    def _send_to_robot(self, target_position: int) -> bool:
        """
        Envia comando ao robô para mover para uma posição.

        Args:
            target_position: Posição alvo (0-8)

        Returns:
            True se comando enviado com sucesso, False caso contrário
        """
        if not self.robot_service:
            self.logger.warning("[GAME_ORCH_V2] RobotService não configurado")
            return False

        try:
            # Obter coordenadas físicas (mm)
            target_mm = self.board_coords.get_board_position_mm(target_position)

            if target_mm is None:
                self.logger.error(
                    f"[GAME_ORCH_V2] Não consegui obter coordenadas para posição {target_position}"
                )
                return False

            # Tentar enviar ao robô
            # Assumindo que robot_service tem método move_to_position(x_mm, y_mm)
            # ou algo equivalente
            if hasattr(self.robot_service, 'move_to_position'):
                self.robot_service.move_to_position(target_mm[0], target_mm[1])
                return True
            elif hasattr(self.robot_service, 'move_tcp'):
                # Alternativa: usar move_tcp com coordenadas
                self.robot_service.move_tcp(target_mm[0], target_mm[1], z=0)
                return True
            else:
                self.logger.warning(
                    "[GAME_ORCH_V2] RobotService não tem método de movimento configurado"
                )
                return False

        except Exception as e:
            self.logger.error(
                f"[GAME_ORCH_V2] Erro ao enviar movimento ao robô: {e}"
            )
            return False

    # ========== ESTADO DO JOGO ==========

    def get_game_state(self) -> Dict[str, Any]:
        """
        Retorna estado completo do jogo.

        Returns:
            Dict com estado atual (calibração, tabuleiro, jogador, etc.)
        """
        return {
            "orchestrator_state": self.state.value,
            "is_calibrated": self.is_calibrated(),
            "board_state": self.game.board if hasattr(self.game, 'board') else None,
            "current_player": (
                self.game.current_player if hasattr(self.game, 'current_player') else None
            ),
            "game_status": self.game.status if hasattr(self.game, 'status') else None,
            "move_history": self.move_history,
            "last_error": self.last_error,
            "calibration_info": self.board_coords.get_calibration_info(),
        }

    def _get_occupied_positions(self) -> Set[int]:
        """
        Extrai posições ocupadas do tabuleiro.

        Returns:
            Set de posições (0-8) que têm peças
        """
        occupied = set()

        if not hasattr(self.game, 'board'):
            return occupied

        for position, piece in enumerate(self.game.board):
            # Verificar se posição tem peça (não está vazia)
            if piece is not None and str(piece).upper() != 'EMPTY':
                occupied.add(position)

        return occupied

    # ========== INFORMAÇÕES E DEBUGGING ==========

    def get_detailed_info(self) -> Dict[str, Any]:
        """
        Retorna informações detalhadas do sistema.

        Returns:
            Dict com info completa para debugging
        """
        return {
            "state": self.state.value,
            "is_calibrated": self.is_calibrated(),
            "calibration_status": self.calibrator.get_calibration_status(),
            "board_positions": self.board_coords.get_all_board_positions_mm(),
            "game_state": self.get_game_state(),
            "move_history_length": len(self.move_history),
            "last_error": self.last_error,
        }

    def reset_game(self):
        """Reseta o jogo para estado inicial."""
        try:
            self.game = TabuleiraTapatan()
            self.move_history = []
            self.last_error = None
            self.state = GameState.READY if self.is_calibrated() else GameState.WAITING_CALIBRATION
            self.logger.info("[GAME_ORCH_V2] Jogo resetado")
        except Exception as e:
            self.logger.error(f"[GAME_ORCH_V2] Erro ao resetar jogo: {e}")

    def get_valid_moves_for_position(self, position: int) -> Set[int]:
        """
        Retorna movimentos válidos a partir de uma posição.

        Args:
            position: Posição inicial (0-8)

        Returns:
            Set de posições válidas ou empty set
        """
        if not self.is_calibrated():
            return set()

        occupied = self._get_occupied_positions()
        return self.board_coords.get_valid_moves(position, occupied)

    def __repr__(self) -> str:
        """Representação em string."""
        calib_status = "✅ CALIBRADO" if self.is_calibrated() else "❌ NÃO CALIBRADO"
        return (
            f"GameOrchestratorV2(state={self.state.value}, "
            f"calibration={calib_status}, "
            f"moves={len(self.move_history)})"
        )