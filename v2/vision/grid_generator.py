"""
GridGenerator - Geração de Grid 3x3 a partir de Transformação

Responsabilidades:
- Receber transformação câmera → tabuleiro (BoardTransformCalculator)
- Gerar as 9 posições centrais das casas do grid 3x3
- Fornecer mapeamento: position_id (0-8) → (board_x_mm, board_y_mm)
- Validar que grid está dentro de limites físicos

Grid Layout (posições 0-8):
    0 | 1 | 2
    ---------
    3 | 4 | 5
    ---------
    6 | 7 | 8

Física:
- Origem (0,0,0): centro do marcador 0 (canto inferior esquerdo)
- Eixo X: direção do marcador 1 (direita)
- Eixo Y: perpendicular (cima)
- Célula tamanho: distância_entre_marcadores / 3

Uso:
    from calibration_marker_detector import CalibrationMarkerDetector
    from board_transform_calculator import BoardTransformCalculator

    detector = CalibrationMarkerDetector(distance_mm=270.0)
    calibration = detector.detect(frame)

    transform = BoardTransformCalculator(calibration)
    grid = GridGenerator(transform)

    position_coords = grid.get_grid_positions()
    # Retorna: {0: (x_mm, y_mm), 1: (x_mm, y_mm), ...}
"""

import numpy as np
import logging
from typing import Optional, Dict, Tuple, List
from dataclasses import dataclass


@dataclass
class GridCell:
    """Célula do grid com posição e validações."""
    position: int  # 0-8
    center_mm: Tuple[float, float, float]  # (x, y, 0) em mm
    is_within_bounds: bool
    confidence: float


class GridGenerator:
    """
    Gerador de grid 3x3 a partir de transformação câmera → tabuleiro.

    Características:
    - Gera 9 posições centrais das casas
    - Valida que células estão dentro de limites
    - Fornece mapeamento posição ↔ coordenadas
    - Logging detalhado
    """

    def __init__(
        self,
        transform_calculator,  # BoardTransformCalculator
        grid_rows: int = 3,
        grid_cols: int = 3,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Inicializa gerador de grid.

        Args:
            transform_calculator: BoardTransformCalculator com transformação
            grid_rows: Linhas do grid (3)
            grid_cols: Colunas do grid (3)
            logger: Logger customizado
        """
        if transform_calculator is None:
            raise ValueError("BoardTransformCalculator não pode ser None")

        self.transform = transform_calculator
        self.grid_rows = grid_rows
        self.grid_cols = grid_cols
        self.grid_positions: Dict[int, GridCell] = {}
        self.is_generated = False

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

        # Gerar grid
        self._generate_grid()

    def _generate_grid(self) -> bool:
        """
        Gera as 9 posições do grid.

        Algoritmo:
        1. Obter informações da transformação (escala, eixos)
        2. Calcular tamanho de célula: distância_entre_marcadores / 3
        3. Para cada posição (0-8):
           - Calcular índice linha/coluna
           - Calcular coordenadas relativas: (col + 0.5) * cell_size
           - Converter para board_mm usando transform
           - Validar que está dentro de limites
        """
        try:
            transform_info = self.transform.get_transform_info()
            if not transform_info.get("is_initialized"):
                self.logger.error("[GRID] Transformação não inicializada")
                return False

            # Tamanho de célula em mm
            distance_mm = transform_info["distance_mm"]
            cell_size_mm = distance_mm / self.grid_cols

            self.logger.info(
                f"[GRID] Gerando grid {self.grid_rows}x{self.grid_cols} "
                f"(tamanho célula: {cell_size_mm:.2f}mm)"
            )

            # Gerar posições
            for position in range(self.grid_rows * self.grid_cols):
                row = position // self.grid_cols
                col = position % self.grid_cols

                # Coordenadas relativas: (col + 0.5) e (row + 0.5) para centro da célula
                # Obs: Y inverte porque em pixels Y cresce pra baixo, em board cresce pra cima
                board_x_mm = (col + 0.5) * cell_size_mm
                board_y_mm = (row + 0.5) * cell_size_mm

                # Validar que célula está dentro de limites
                max_x = distance_mm
                max_y = distance_mm
                is_within = (0 <= board_x_mm <= max_x) and (0 <= board_y_mm <= max_y)

                grid_cell = GridCell(
                    position=position,
                    center_mm=(board_x_mm, board_y_mm, 0.0),
                    is_within_bounds=is_within,
                    confidence=transform_info["confidence"],
                )

                self.grid_positions[position] = grid_cell

                self.logger.debug(
                    f"[GRID] Posição {position}: "
                    f"({board_x_mm:.1f}, {board_y_mm:.1f}) mm "
                    f"{'[OK]' if is_within else '[FORA]'}"
                )

            self.is_generated = True
            self.logger.info(f"[GRID] Grid gerado com {len(self.grid_positions)} células")
            return True

        except Exception as e:
            self.logger.error(f"[GRID] Erro ao gerar grid: {e}")
            return False

    def get_grid_positions(self) -> Dict[int, Tuple[float, float, float]]:
        """
        Retorna todas as 9 posições do grid.

        Returns:
            {position: (x_mm, y_mm, 0.0), ...}
        """
        if not self.is_generated:
            self.logger.warning("[GRID] Grid não foi gerado")
            return {}

        return {pos: cell.center_mm for pos, cell in self.grid_positions.items()}

    def get_cell_position(self, position: int) -> Optional[Tuple[float, float, float]]:
        """
        Retorna coordenadas de uma célula específica.

        Args:
            position: ID da célula (0-8)

        Returns:
            (x_mm, y_mm, 0.0) ou None se inválida
        """
        if not self.is_generated:
            self.logger.warning("[GRID] Grid não foi gerado")
            return None

        if position not in self.grid_positions:
            self.logger.warning(f"[GRID] Posição inválida: {position}")
            return None

        cell = self.grid_positions[position]
        if not cell.is_within_bounds:
            self.logger.warning(f"[GRID] Posição {position} fora dos limites")
            return None

        return cell.center_mm

    def position_to_pixel(self, position: int) -> Optional[Tuple[float, float]]:
        """
        Converte posição de célula → coordenadas pixel (para visualização).

        Args:
            position: ID da célula (0-8)

        Returns:
            (x_pixel, y_pixel) ou None se erro
        """
        board_coords = self.get_cell_position(position)
        if board_coords is None:
            return None

        pixel_coords = self.transform.board_to_pixel(board_coords)
        return pixel_coords

    def pixel_to_position(self, pixel_coords: Tuple[float, float]) -> Optional[int]:
        """
        Converte coordenadas pixel → posição de célula mais próxima.

        Algoritmo:
        1. Converter pixel → board
        2. Encontrar célula mais próxima
        3. Retornar posição se dentro de tolerância

        Args:
            pixel_coords: (x_pixel, y_pixel)

        Returns:
            Position (0-8) ou None se fora do grid
        """
        if not self.is_generated:
            self.logger.warning("[GRID] Grid não foi gerado")
            return None

        try:
            # Converter para coordenadas de tabuleiro
            board_coords = self.transform.pixel_to_board(pixel_coords)
            board_x, board_y, _ = board_coords

            # Validar que está dentro de limites
            distance_mm = self.transform.calibration.distance_mm
            if not (0 <= board_x <= distance_mm and 0 <= board_y <= distance_mm):
                self.logger.debug(
                    f"[GRID] Pixel {pixel_coords} → Board ({board_x:.1f}, {board_y:.1f}) "
                    f"está fora dos limites"
                )
                return None

            # Encontrar célula mais próxima
            cell_size_mm = distance_mm / self.grid_cols
            col = int(board_x / cell_size_mm)
            row = int(board_y / cell_size_mm)

            # Garantir limites
            col = max(0, min(col, self.grid_cols - 1))
            row = max(0, min(row, self.grid_rows - 1))

            position = row * self.grid_cols + col

            self.logger.debug(
                f"[GRID] Pixel {pixel_coords} → Board ({board_x:.1f}, {board_y:.1f}) "
                f"→ Posição {position}"
            )

            return position

        except Exception as e:
            self.logger.error(f"[GRID] Erro ao converter pixel→posição: {e}")
            return None

    def get_grid_bounds(self) -> Dict[str, float]:
        """
        Retorna limites físicos do grid.

        Returns:
            {
                'min_x': float,
                'max_x': float,
                'min_y': float,
                'max_y': float,
                'width_mm': float,
                'height_mm': float,
            }
        """
        if not self.is_generated:
            return {}

        transform_info = self.transform.get_transform_info()
        distance_mm = transform_info["distance_mm"]

        return {
            "min_x": 0.0,
            "max_x": distance_mm,
            "min_y": 0.0,
            "max_y": distance_mm,
            "width_mm": distance_mm,
            "height_mm": distance_mm,
        }

    def validate_grid(self) -> bool:
        """
        Valida que todas as 9 células estão dentro de limites.

        Returns:
            True se todas válidas, False caso contrário
        """
        if not self.is_generated:
            self.logger.warning("[GRID] Grid não foi gerado")
            return False

        all_within = all(cell.is_within_bounds for cell in self.grid_positions.values())

        if all_within:
            self.logger.info("[GRID] Todas as 9 células estão dentro dos limites")
        else:
            invalid_count = sum(1 for c in self.grid_positions.values() if not c.is_within_bounds)
            self.logger.warning(f"[GRID] {invalid_count} células fora dos limites")

        return all_within

    def get_stats(self) -> Dict:
        """Retorna estatísticas do grid."""
        if not self.is_generated:
            return {"is_generated": False}

        bounds = self.get_grid_bounds()
        valid_cells = sum(1 for c in self.grid_positions.values() if c.is_within_bounds)

        return {
            "is_generated": True,
            "grid_size": f"{self.grid_rows}x{self.grid_cols}",
            "total_cells": self.grid_rows * self.grid_cols,
            "valid_cells": valid_cells,
            "bounds": bounds,
            "cell_size_mm": bounds.get("width_mm", 0) / self.grid_cols if bounds else 0,
            "confidence": self.grid_positions[0].confidence if self.grid_positions else 0,
        }


# ============================================================================
# Teste
# ============================================================================

if __name__ == "__main__":
    print("[TESTE] GridGenerator")
    print("")

    try:
        # Importar o BoardTransformCalculator
        from board_transform_calculator import BoardTransformCalculator
        from dataclasses import dataclass

        # Criar mocks
        @dataclass
        class MockMarkerPose:
            marker_id: int
            center: tuple
            corners: np.ndarray
            normal: tuple
            orientation_angle: float

        @dataclass
        class MockCalibrationData:
            marker0_pose: MockMarkerPose
            marker1_pose: MockMarkerPose
            distance_mm: float
            distance_pixels: float
            scale: float
            is_valid: bool
            confidence: float

        # Criar calibração
        marker0 = MockMarkerPose(
            marker_id=0,
            center=(100.0, 100.0),
            corners=np.array([[80, 80], [120, 80], [120, 120], [80, 120]]),
            normal=(0.0, 0.0, 1.0),
            orientation_angle=0.0,
        )

        marker1 = MockMarkerPose(
            marker_id=1,
            center=(370.0, 100.0),
            corners=np.array([[350, 80], [390, 80], [390, 120], [350, 120]]),
            normal=(0.0, 0.0, 1.0),
            orientation_angle=0.0,
        )

        calibration = MockCalibrationData(
            marker0_pose=marker0,
            marker1_pose=marker1,
            distance_mm=270.0,
            distance_pixels=270.0,
            scale=1.0,
            is_valid=True,
            confidence=1.0,
        )

        # Criar transformador e grid
        transform = BoardTransformCalculator(calibration)
        grid = GridGenerator(transform)
        print("[OK] GridGenerator criado")

        # Mostrar posições
        print("\nPosições do grid (9 células):")
        positions = grid.get_grid_positions()
        for pos in range(9):
            coords = positions.get(pos)
            row = pos // 3
            col = pos % 3
            print(f"  Posição {pos} (linha {row}, col {col}): {coords}")

        # Mostrar limites
        print("\nLimites do grid:")
        bounds = grid.get_grid_bounds()
        for key, value in bounds.items():
            print(f"  - {key}: {value:.2f}")

        # Testar conversão pixel → posição
        print("\nTestes de conversão pixel → posição:")
        test_pixels = [
            (145.0, 145.0),  # Célula 0
            (235.0, 145.0),  # Célula 1
            (235.0, 235.0),  # Célula 4 (centro)
        ]

        for pixel_point in test_pixels:
            position = grid.pixel_to_position(pixel_point)
            print(f"  Pixel {pixel_point} → Posição {position}")

        # Validar grid
        is_valid = grid.validate_grid()
        print(f"\nGrid válido: {is_valid}")

        # Stats
        print("\n[INFO] Estatísticas:")
        stats = grid.get_stats()
        for key, value in stats.items():
            print(f"  - {key}: {value}")

    except Exception as e:
        print(f"[ERRO] {e}")
        import traceback

        traceback.print_exc()

    print("\n[OK] Teste concluído")
