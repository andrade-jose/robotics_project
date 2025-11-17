"""
BoardCoordinateSystemV2 - Sistema de Coordenadas Sincronizado com Calibração

Responsabilidades:
- Integrar com CalibrationOrchestrator para obter coordenadas físicas
- Converter entre diferentes sistemas de coordenadas (pixel, grid, mm)
- Validar movimentos usando WorkspaceValidator da calibração
- Fornecer interface simples para GameOrchestrator

Coordenadas:
- Pixel: Coordenadas da câmera (x_px, y_px)
- Grid Position: Índice do grid (0-8) em arranjo 3x3
- Board MM: Coordenadas físicas em milímetros (x_mm, y_mm, z=0)

Pipeline:
1. CalibrationOrchestrator calibra com frame → obtém grid_positions
2. BoardCoordinateSystemV2 usa grid_positions para conversões
3. GameOrchestrator valida e executa movimentos

Uso:
    orchestrator = CalibrationOrchestrator(distance_mm=270.0)
    board_coords = BoardCoordinateSystemV2(orchestrator)

    # Obter coordenada física de uma posição
    if board_coords.is_calibrated():
        mm_coords = board_coords.get_board_position_mm(position=4)  # Centro

    # Validar movimento
    occupied = {0, 4, 8}
    valid = board_coords.validate_move(0, 3, occupied)
"""

import logging
from typing import Optional, Set, Tuple, Dict
from dataclasses import dataclass

try:
    from v2.vision.calibration_orchestrator import CalibrationOrchestrator
except ImportError:
    from vision.calibration_orchestrator import CalibrationOrchestrator


@dataclass
class BoardPosition:
    """Representa uma posição no tabuleiro em diferentes coordenadas."""
    grid_position: int  # 0-8
    pixel_coords: Optional[Tuple[float, float]] = None  # (x_px, y_px)
    board_coords: Optional[Tuple[float, float]] = None  # (x_mm, y_mm)

    def __post_init__(self):
        if self.grid_position < 0 or self.grid_position > 8:
            raise ValueError(f"Grid position deve estar entre 0-8, got {self.grid_position}")


class BoardCoordinateSystemV2:
    """
    Sistema de coordenadas do tabuleiro sincronizado com calibração.

    Características:
    - Interface simples para conversão de coordenadas
    - Validação de movimentos usando workspace validator
    - Gerenciamento de estado calibrado/não-calibrado
    - Logging detalhado para debug
    """

    def __init__(
        self,
        calibration_orchestrator: CalibrationOrchestrator,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Inicializa sistema de coordenadas.

        Args:
            calibration_orchestrator: Orquestrador de calibração (Phase 4)
            logger: Logger customizado
        """
        self.calibrator = calibration_orchestrator

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

        # Cache de grid positions
        self._grid_positions_cache: Optional[Dict] = None
        self._grid_validators_cache = None

        self.logger.info("[BOARD_COORDS_V2] Inicializado com CalibrationOrchestrator")

    def is_calibrated(self) -> bool:
        """
        Verifica se o sistema está calibrado.

        Returns:
            True se calibrado, False caso contrário
        """
        status = self.calibrator.get_calibration_status()
        return status.get("is_calibrated", False)

    def get_board_position_mm(self, grid_position: int) -> Optional[Tuple[float, float]]:
        """
        Obtém coordenada física (mm) para uma posição do grid.

        Args:
            grid_position: Posição do grid (0-8)

        Returns:
            (x_mm, y_mm) ou None se não calibrado ou posição inválida
        """
        if not self.is_calibrated():
            self.logger.warning(
                f"[BOARD_COORDS_V2] Sistema não calibrado, "
                f"não posso retornar coordenadas para posição {grid_position}"
            )
            return None

        if grid_position < 0 or grid_position > 8:
            self.logger.error(
                f"[BOARD_COORDS_V2] Posição inválida: {grid_position} (deve ser 0-8)"
            )
            return None

        # Obter grid positions da calibração
        coords = self.calibrator.get_grid_position(grid_position)

        if coords is None:
            self.logger.warning(
                f"[BOARD_COORDS_V2] Não consegui obter coordenadas para posição {grid_position}"
            )
            return None

        # coords é (x, y, 0) - extrair apenas x, y
        return (coords[0], coords[1])

    def get_all_board_positions_mm(self) -> Optional[Dict[int, Tuple[float, float]]]:
        """
        Obtém todas as 9 posições do grid em coordenadas mm.

        Returns:
            Dict {position: (x_mm, y_mm)} ou None se não calibrado
        """
        if not self.is_calibrated():
            self.logger.warning("[BOARD_COORDS_V2] Sistema não calibrado")
            return None

        # Obter grid positions do calibrator
        if self.calibrator.last_valid_result is None:
            return None

        all_positions = self.calibrator.last_valid_result.grid_positions

        if all_positions is None:
            return None

        # Converter de (x, y, 0) para (x, y)
        result = {}
        for pos, coords in all_positions.items():
            result[pos] = (coords[0], coords[1])

        return result

    def validate_move(
        self,
        from_position: int,
        to_position: int,
        occupied_positions: Optional[Set[int]] = None,
    ) -> bool:
        """
        Valida se um movimento é permitido.

        Critérios:
        1. Sistema deve estar calibrado
        2. Posições devem estar entre 0-8
        3. from != to (não pode mover para mesma posição)
        4. to não pode estar ocupado
        5. Movimento deve ser válido segundo workspace validator

        Args:
            from_position: Posição inicial (0-8)
            to_position: Posição final (0-8)
            occupied_positions: Set de posições ocupadas no tabuleiro

        Returns:
            True se movimento é válido, False caso contrário
        """
        # Validar calibração
        if not self.is_calibrated():
            self.logger.warning(
                f"[BOARD_COORDS_V2] Não posso validar movimento: "
                f"sistema não está calibrado"
            )
            return False

        # Validar posições
        if from_position < 0 or from_position > 8:
            self.logger.error(
                f"[BOARD_COORDS_V2] Posição inicial inválida: {from_position}"
            )
            return False

        if to_position < 0 or to_position > 8:
            self.logger.error(
                f"[BOARD_COORDS_V2] Posição final inválida: {to_position}"
            )
            return False

        # Não pode mover para mesma posição
        if from_position == to_position:
            self.logger.debug(
                f"[BOARD_COORDS_V2] Movimento inválido: "
                f"posição inicial e final são iguais ({from_position})"
            )
            return False

        # Não pode mover para posição ocupada
        if occupied_positions and to_position in occupied_positions:
            self.logger.debug(
                f"[BOARD_COORDS_V2] Movimento inválido: "
                f"posição destino {to_position} está ocupada"
            )
            return False

        # Usar workspace validator da calibração
        is_valid = self.calibrator.is_move_valid(
            from_position, to_position, occupied_positions
        )

        self.logger.debug(
            f"[BOARD_COORDS_V2] Movimento {from_position} → {to_position}: "
            f"{'VÁLIDO' if is_valid else 'INVÁLIDO'}"
        )

        return is_valid

    def get_valid_moves(
        self,
        from_position: int,
        occupied_positions: Optional[Set[int]] = None,
    ) -> Set[int]:
        """
        Obtém todas as posições válidas para movimento a partir de uma posição.

        Args:
            from_position: Posição inicial (0-8)
            occupied_positions: Set de posições ocupadas

        Returns:
            Set de posições válidas ou empty set se não calibrado
        """
        if not self.is_calibrated():
            self.logger.warning(
                f"[BOARD_COORDS_V2] Sistema não calibrado, "
                f"retornando empty set de movimentos válidos"
            )
            return set()

        if from_position < 0 or from_position > 8:
            self.logger.error(
                f"[BOARD_COORDS_V2] Posição inválida: {from_position}"
            )
            return set()

        # Usar workspace validator
        valid_moves = self.calibrator.get_valid_moves(
            from_position, occupied_positions
        )

        self.logger.debug(
            f"[BOARD_COORDS_V2] Movimentos válidos de {from_position}: {valid_moves}"
        )

        return valid_moves

    def get_grid_position_from_pixel(
        self,
        pixel_x: float,
        pixel_y: float,
    ) -> Optional[int]:
        """
        Converte coordenadas pixel para posição do grid.

        Aproxima a posição pixel para a célula do grid mais próxima.

        Args:
            pixel_x: Coordenada X em pixels
            pixel_y: Coordenada Y em pixels

        Returns:
            Posição do grid (0-8) ou None se não calibrado
        """
        if not self.is_calibrated():
            self.logger.warning("[BOARD_COORDS_V2] Sistema não calibrado")
            return None

        if self.calibrator.last_valid_result is None:
            return None

        transform = self.calibrator.last_valid_result.transform
        grid = self.calibrator.last_valid_result.grid

        if transform is None or grid is None:
            return None

        try:
            # Converter pixel para coordenadas do tabuleiro
            board_coords = transform.pixel_to_board((pixel_x, pixel_y))

            # Encontrar posição do grid mais próxima
            closest_position = None
            closest_distance = float('inf')

            all_positions = self.get_all_board_positions_mm()
            if all_positions is None:
                return None

            for position, (grid_x, grid_y) in all_positions.items():
                distance = (
                    (board_coords[0] - grid_x) ** 2 +
                    (board_coords[1] - grid_y) ** 2
                ) ** 0.5

                if distance < closest_distance:
                    closest_distance = distance
                    closest_position = position

            if closest_position is not None:
                self.logger.debug(
                    f"[BOARD_COORDS_V2] Pixel ({pixel_x}, {pixel_y}) → "
                    f"Posição {closest_position} (distância: {closest_distance:.2f}mm)"
                )

            return closest_position

        except Exception as e:
            self.logger.error(
                f"[BOARD_COORDS_V2] Erro ao converter pixel para posição: {e}"
            )
            return None

    def get_calibration_info(self) -> Dict:
        """
        Retorna informações detalhadas do sistema de calibração.

        Returns:
            Dict com informações de calibração e coordenadas
        """
        status = self.calibrator.get_calibration_status()

        result = {
            "is_calibrated": self.is_calibrated(),
            "calibration_status": status,
            "board_positions": None,
        }

        if self.is_calibrated():
            result["board_positions"] = self.get_all_board_positions_mm()

        return result

    def reset_calibration(self):
        """
        Força reset do sistema de calibração.

        Nota: Isso apenas limpa caches locais. Para resetar completamente,
        crie novo CalibrationOrchestrator.
        """
        self._grid_positions_cache = None
        self._grid_validators_cache = None
        self.logger.info("[BOARD_COORDS_V2] Cache de coordenadas limpo")

    def __repr__(self) -> str:
        """Representação em string."""
        status = "CALIBRADO" if self.is_calibrated() else "NÃO CALIBRADO"
        calib_info = self.calibrator.get_calibration_status()
        return (
            f"BoardCoordinateSystemV2(status={status}, "
            f"attempts={calib_info.get('calibration_attempts', 0)}, "
            f"successes={calib_info.get('successful_calibrations', 0)})"
        )