"""
CalibrationOrchestrator - Orquestrador do Sistema de Calibração

Responsabilidades:
- Orquestrar todos os componentes de calibração
- Executar pipeline completo: detecção → transformação → grid → validação
- Gerenciar estado de calibração (não calibrado → em andamento → calibrado)
- Fornecer interface simples para sistema de jogo

Pipeline de Calibração:
1. CalibrationMarkerDetector: Detecta 2 marcadores, extrai poses, aplica smoothing
2. BoardTransformCalculator: Constrói matriz de transformação pixel → board_mm
3. GridGenerator: Gera 9 posições do grid 3x3 em coordenadas físicas
4. WorkspaceValidator: Valida espaço de trabalho e limites de segurança

Estados:
- NOT_CALIBRATED: Sistema aguardando calibração
- CALIBRATING: Processo de calibração em andamento
- CALIBRATED: Calibração concluída com sucesso
- FAILED: Calibração falhou

Uso:
    orchestrator = CalibrationOrchestrator(distance_mm=270.0)

    # Executar pipeline de calibração
    result = orchestrator.calibrate(frame)
    if result.is_calibrated:
        # Usar grid e validador
        grid_positions = result.grid_positions
        valid_moves = result.validator.get_valid_moves(current_pos)
"""

import logging
from enum import Enum
from typing import Optional, Dict, Set
from dataclasses import dataclass

from .calibration_marker_detector import CalibrationMarkerDetector
from .board_transform_calculator import BoardTransformCalculator
from .grid_generator import GridGenerator
from .workspace_validator import WorkspaceValidator


class CalibrationState(Enum):
    """Estados do sistema de calibração."""
    NOT_CALIBRATED = "not_calibrated"
    CALIBRATING = "calibrating"
    CALIBRATED = "calibrated"
    FAILED = "failed"


@dataclass
class CalibrationResult:
    """Resultado do processo de calibração."""
    is_calibrated: bool
    state: CalibrationState
    confidence: float  # 0-1
    grid_positions: Optional[Dict]  # {position: (x_mm, y_mm, 0)}
    detector: Optional[CalibrationMarkerDetector]
    transform: Optional[BoardTransformCalculator]
    grid: Optional[GridGenerator]
    validator: Optional[WorkspaceValidator]
    error_message: Optional[str]


class CalibrationOrchestrator:
    """
    Orquestrador de sistema de calibração.

    Características:
    - Pipeline completo: detecção → transformação → grid → validação
    - Gerenciamento de estado de calibração
    - Interface simples para uso do jogo
    - Logging detalhado de todo o processo
    - Fallback para última calibração válida
    """

    def __init__(
        self,
        distance_mm: float = 270.0,
        smoothing_frames: int = 3,
        safety_margin_mm: float = 10.0,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Inicializa orquestrador de calibração.

        Args:
            distance_mm: Distância real entre os 2 marcadores (270mm padrão para Tapatan)
            smoothing_frames: Número de frames para média móvel (3-5)
            safety_margin_mm: Margem de segurança ao redor do board (10mm)
            logger: Logger customizado
        """
        self.distance_mm = distance_mm
        self.smoothing_frames = smoothing_frames
        self.safety_margin_mm = safety_margin_mm

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

        # Estado
        self.state = CalibrationState.NOT_CALIBRATED
        self.last_valid_result: Optional[CalibrationResult] = None
        self.calibration_attempts = 0
        self.successful_calibrations = 0

        self.logger.info(
            f"[CALIB] CalibrationOrchestrator inicializado "
            f"(distância={distance_mm}mm, smoothing={smoothing_frames})"
        )

    def calibrate(self, frame) -> CalibrationResult:
        """
        Executa pipeline completo de calibração.

        Etapas:
        1. Detector: Encontra 2 marcadores, extrai poses, aplica smoothing
        2. Transform: Constrói matriz de transformação pixel → board_mm
        3. Grid: Gera 9 posições do grid 3x3
        4. Validator: Valida espaço de trabalho

        Args:
            frame: Imagem da câmera (numpy array BGR)

        Returns:
            CalibrationResult com estado completo da calibração
        """
        self.calibration_attempts += 1
        self.state = CalibrationState.CALIBRATING

        try:
            # Etapa 1: Detecção de marcadores
            self.logger.debug(f"[CALIB] Tentativa {self.calibration_attempts}: Detectando marcadores...")
            detector = CalibrationMarkerDetector(
                distance_mm=self.distance_mm,
                smoothing_frames=self.smoothing_frames,
                logger=self.logger,
            )

            calibration_data = detector.detect(frame)
            if calibration_data is None:
                return self._create_result(
                    is_calibrated=False,
                    state=CalibrationState.FAILED,
                    error="Marcadores não detectados (necessário exatamente 2)",
                )

            self.logger.debug(f"[CALIB] Marcadores detectados (confiança={calibration_data.confidence:.2f})")

            # Etapa 2: Transformação câmera → board
            self.logger.debug("[CALIB] Construindo matriz de transformação...")
            try:
                transform = BoardTransformCalculator(calibration_data, logger=self.logger)
                if not transform.is_initialized:
                    return self._create_result(
                        is_calibrated=False,
                        state=CalibrationState.FAILED,
                        error="Falha ao construir matriz de transformação",
                    )
            except Exception as e:
                return self._create_result(
                    is_calibrated=False,
                    state=CalibrationState.FAILED,
                    error=f"Erro ao criar transformação: {str(e)}",
                )

            self.logger.debug("[CALIB] Transformação construída com sucesso")

            # Validar transformação
            if not transform.validate_transform():
                return self._create_result(
                    is_calibrated=False,
                    state=CalibrationState.FAILED,
                    error="Validação de transformação falhou (roundtrip inválido)",
                )

            # Etapa 3: Geração de grid 3x3
            self.logger.debug("[CALIB] Gerando grid 3x3...")
            try:
                grid = GridGenerator(transform, logger=self.logger)
                if not grid.is_generated:
                    return self._create_result(
                        is_calibrated=False,
                        state=CalibrationState.FAILED,
                        error="Falha ao gerar grid",
                    )
            except Exception as e:
                return self._create_result(
                    is_calibrated=False,
                    state=CalibrationState.FAILED,
                    error=f"Erro ao criar grid: {str(e)}",
                )

            self.logger.debug("[CALIB] Grid gerado com sucesso")

            # Validar que todas as 9 células estão dentro dos limites
            if not grid.validate_grid():
                return self._create_result(
                    is_calibrated=False,
                    state=CalibrationState.FAILED,
                    error="Grid inválido: algumas células fora dos limites",
                )

            # Etapa 4: Validação de workspace
            self.logger.debug("[CALIB] Validando espaço de trabalho...")
            try:
                validator = WorkspaceValidator(grid, self.safety_margin_mm, logger=self.logger)
                if not validator.validate_all_positions():
                    return self._create_result(
                        is_calibrated=False,
                        state=CalibrationState.FAILED,
                        error="Validação de workspace falhou",
                    )
            except Exception as e:
                return self._create_result(
                    is_calibrated=False,
                    state=CalibrationState.FAILED,
                    error=f"Erro ao criar validador: {str(e)}",
                )

            self.logger.debug("[CALIB] Espaço de trabalho validado")

            # Sucesso! Pipeline completo
            self.state = CalibrationState.CALIBRATED
            self.successful_calibrations += 1

            grid_positions = grid.get_grid_positions()

            result = CalibrationResult(
                is_calibrated=True,
                state=CalibrationState.CALIBRATED,
                confidence=calibration_data.confidence,
                grid_positions=grid_positions,
                detector=detector,
                transform=transform,
                grid=grid,
                validator=validator,
                error_message=None,
            )

            # Armazenar como última calibração válida
            self.last_valid_result = result

            self.logger.info(
                f"[CALIB] Calibração bem-sucedida! "
                f"(tentativa {self.calibration_attempts}, confiança={calibration_data.confidence:.2f})"
            )

            return result

        except Exception as e:
            self.logger.error(f"[CALIB] Erro inesperado durante calibração: {e}")
            return self._create_result(
                is_calibrated=False,
                state=CalibrationState.FAILED,
                error=f"Erro inesperado: {str(e)}",
            )

    def _create_result(
        self,
        is_calibrated: bool,
        state: CalibrationState,
        error: Optional[str] = None,
    ) -> CalibrationResult:
        """Helper para criar CalibrationResult com fallback."""
        if is_calibrated:
            return CalibrationResult(
                is_calibrated=True,
                state=state,
                confidence=1.0,
                grid_positions=None,
                detector=None,
                transform=None,
                grid=None,
                validator=None,
                error_message=None,
            )

        # Se falhou, tentar usar última calibração válida
        if self.last_valid_result is not None and not is_calibrated:
            self.logger.warning(
                f"[CALIB] Usando última calibração válida "
                f"(falha: {error})"
            )
            return self.last_valid_result

        # Nenhuma calibração válida disponível
        if error:
            self.logger.error(f"[CALIB] {error}")

        return CalibrationResult(
            is_calibrated=False,
            state=state,
            confidence=0.0,
            grid_positions=None,
            detector=None,
            transform=None,
            grid=None,
            validator=None,
            error_message=error,
        )

    def get_grid_position(self, position: int) -> Optional[tuple]:
        """
        Retorna coordenadas de uma célula do grid.

        Args:
            position: ID da célula (0-8)

        Returns:
            (x_mm, y_mm, 0.0) ou None se não calibrado
        """
        if self.last_valid_result is None or self.last_valid_result.grid_positions is None:
            self.logger.warning("[CALIB] Sistema não calibrado")
            return None

        return self.last_valid_result.grid_positions.get(position)

    def get_valid_moves(
        self,
        from_position: int,
        occupied_positions: Optional[Set[int]] = None,
    ) -> Set[int]:
        """
        Retorna posições válidas para movimento.

        Args:
            from_position: Posição inicial (0-8)
            occupied_positions: Set de posições ocupadas (opcional)

        Returns:
            Set de posições válidas ou empty set se não calibrado
        """
        if (
            self.last_valid_result is None or
            self.last_valid_result.validator is None
        ):
            self.logger.warning("[CALIB] Sistema não calibrado")
            return set()

        if occupied_positions:
            self.last_valid_result.validator.update_piece_positions(occupied_positions)

        return self.last_valid_result.validator.get_valid_moves(from_position)

    def is_move_valid(
        self,
        from_position: int,
        to_position: int,
        occupied_positions: Optional[Set[int]] = None,
    ) -> bool:
        """
        Valida um movimento específico.

        Args:
            from_position: Posição inicial (0-8)
            to_position: Posição final (0-8)
            occupied_positions: Set de posições ocupadas

        Returns:
            True se movimento é válido, False caso contrário
        """
        if self.last_valid_result is None or self.last_valid_result.validator is None:
            self.logger.warning("[CALIB] Sistema não calibrado")
            return False

        return self.last_valid_result.validator.can_move(
            from_position, to_position, occupied_positions
        )

    def get_calibration_status(self) -> Dict:
        """Retorna status atual da calibração."""
        return {
            "state": self.state.value,
            "is_calibrated": self.state == CalibrationState.CALIBRATED,
            "calibration_attempts": self.calibration_attempts,
            "successful_calibrations": self.successful_calibrations,
            "success_rate": (
                self.successful_calibrations / self.calibration_attempts
                if self.calibration_attempts > 0
                else 0.0
            ),
            "has_last_valid": self.last_valid_result is not None,
            "last_confidence": (
                self.last_valid_result.confidence if self.last_valid_result else 0.0
            ),
        }

    def get_detailed_info(self) -> Dict:
        """Retorna informações detalhadas do sistema de calibração."""
        if self.last_valid_result is None:
            return {"status": "not_calibrated"}

        info = {
            "status": "calibrated",
            "state": self.state.value,
            "confidence": self.last_valid_result.confidence,
            "grid_positions": self.last_valid_result.grid_positions,
        }

        # Adicionar informações do transformador
        if self.last_valid_result.transform:
            info["transform"] = self.last_valid_result.transform.get_transform_info()

        # Adicionar informações do grid
        if self.last_valid_result.grid:
            info["grid"] = self.last_valid_result.grid.get_stats()

        # Adicionar informações do workspace
        if self.last_valid_result.validator:
            info["workspace"] = self.last_valid_result.validator.get_stats()

        return info


# ============================================================================
# Teste
# ============================================================================

if __name__ == "__main__":
    print("[TESTE] CalibrationOrchestrator")
    print("")

    try:
        # Criar orquestrador
        orchestrator = CalibrationOrchestrator(distance_mm=270.0, smoothing_frames=3)
        print("[OK] CalibrationOrchestrator criado")

        # Simular frame (requer câmera para teste real)
        print("\n[AVISO] Requer câmera com 2 marcadores ArUco para teste funcional")

        # Mostrar status
        print("\nStatus antes de calibração:")
        status = orchestrator.get_calibration_status()
        for key, value in status.items():
            print(f"  - {key}: {value}")

        print("\n[INFO] Para calibração real, use: orchestrator.calibrate(frame)")

    except Exception as e:
        print(f"[ERRO] {e}")
        import traceback

        traceback.print_exc()

    print("\n[OK] Teste concluído")
