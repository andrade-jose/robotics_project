"""
GridCalculator - Módulo de mapeamento de grid

Responsabilidades:
- Receber centróides de marcadores
- Mapear para grid 3x3 (posições 0-8)
- Validar posições
- Retornar estado do tabuleiro

Sem dependências de câmera ou detecção - apenas mapeia coordenadas.
Simples, testável, isolado.

Uso:
    grid = GridCalculator(grid_rows=3, grid_cols=3)
    state = grid.calculate_state(detections)
    # Retorna: {0: 'vazio', 1: 'peça_1', 2: 'peça_2', ...}
"""

import logging
from typing import Dict, Tuple, Optional, Set
from dataclasses import dataclass


@dataclass
class GridCell:
    """Célula do grid."""
    position: int  # 0-8
    centroid: Tuple[float, float]  # (x, y)
    occupied: bool = False
    confidence: float = 1.0


class GridCalculator:
    """
    Calculador de grid para tabuleiro 3x3.

    Características:
    - Mapeia centróides de marcadores para grid 3x3
    - Validação de posições
    - Tratamento de ambigüidades
    - Logging detalhado

    Grid layout (posições 0-8):
        0 | 1 | 2
        ---------
        3 | 4 | 5
        ---------
        6 | 7 | 8
    """

    def __init__(
        self,
        grid_rows: int = 3,
        grid_cols: int = 3,
        frame_width: int = 640,
        frame_height: int = 480,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Inicializa calculador de grid.

        Args:
            grid_rows: Número de linhas (3)
            grid_cols: Número de colunas (3)
            frame_width: Largura do frame
            frame_height: Altura do frame
            logger: Logger customizado (ou usa default)
        """
        self.grid_rows = grid_rows
        self.grid_cols = grid_cols
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.calculations_count = 0

        # Calcular limites das células
        self.cell_width = frame_width / grid_cols
        self.cell_height = frame_height / grid_rows

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

        self.logger.info(
            f"[GRID] GridCalculator inicializado: {grid_rows}x{grid_cols} "
            f"({frame_width}x{frame_height}px)"
        )

    def centroid_to_cell(self, centroid: Tuple[float, float]) -> int:
        """
        Mapeia um centróide para uma célula do grid.

        Args:
            centroid: (x, y) em pixels

        Returns:
            Posição da célula (0-8) ou -1 se fora dos limites
        """
        x, y = centroid

        # Validar limites
        if x < 0 or x >= self.frame_width or y < 0 or y >= self.frame_height:
            self.logger.debug(f"[GRID] Centróide fora dos limites: ({x}, {y})")
            return -1

        # Calcular célula
        col = int(x / self.cell_width)
        row = int(y / self.cell_height)

        # Garantir limites
        col = min(col, self.grid_cols - 1)
        row = min(row, self.grid_rows - 1)

        position = row * self.grid_cols + col

        return position

    def cell_to_centroid(self, position: int) -> Tuple[float, float]:
        """
        Mapeia uma posição de célula para centróide.

        Args:
            position: Posição da célula (0-8)

        Returns:
            (x, y) do centro da célula
        """
        if position < 0 or position >= self.grid_rows * self.grid_cols:
            self.logger.warning(f"[GRID] Posição inválida: {position}")
            return (0.0, 0.0)

        row = position // self.grid_cols
        col = position % self.grid_cols

        x = col * self.cell_width + self.cell_width / 2
        y = row * self.cell_height + self.cell_height / 2

        return (x, y)

    def calculate_state(self, detections: Dict[int, Tuple[float, float]]) -> Dict[int, str]:
        """
        Calcula estado do tabuleiro a partir de detecções.

        Args:
            detections: Dict {marker_id: (centroid_x, centroid_y)}

        Returns:
            Dict {position: 'vazio'|'peça_1'|'peça_2'|...}
        """
        self.calculations_count += 1

        # Inicializar estado vazio
        state = {i: "vazio" for i in range(self.grid_rows * self.grid_cols)}

        if not detections:
            self.logger.debug("[GRID] Nenhuma detecção - tabuleiro vazio")
            return state

        # Mapear detecções para células
        occupancy = {}  # {position: [marker_ids]}

        for marker_id, centroid in detections.items():
            position = self.centroid_to_cell(centroid)

            if position < 0:
                self.logger.debug(f"[GRID] Marcador {marker_id} fora dos limites")
                continue

            if position not in occupancy:
                occupancy[position] = []

            occupancy[position].append(marker_id)

        # Atualizar estado
        for position, marker_ids in occupancy.items():
            if len(marker_ids) == 1:
                # Uma única peça - usar o marcador
                marker_id = marker_ids[0]
                state[position] = f"peça_{marker_id}"
            else:
                # Múltiplas peças na mesma célula (ambigüidade)
                self.logger.warning(
                    f"[GRID] Ambigüidade na posição {position}: "
                    f"{len(marker_ids)} marcadores"
                )
                state[position] = "ambíguo"

        return state

    def validate_state(self, state: Dict[int, str]) -> bool:
        """
        Valida estado do tabuleiro.

        Args:
            state: Dict de estado

        Returns:
            True se válido, False caso contrário
        """
        if not isinstance(state, dict):
            self.logger.warning("[GRID] Estado não é um dict!")
            return False

        expected_positions = set(range(self.grid_rows * self.grid_cols))
        actual_positions = set(state.keys())

        if actual_positions != expected_positions:
            self.logger.warning("[GRID] Posições faltando ou extras no estado!")
            return False

        for position, value in state.items():
            if not isinstance(position, int):
                self.logger.warning(f"[GRID] Posição não é int: {position}")
                return False

            if not isinstance(value, str):
                self.logger.warning(f"[GRID] Valor não é string: {value}")
                return False

            # Validar valor
            if value not in ["vazio", "ambíguo"] and not value.startswith("peça_"):
                self.logger.warning(f"[GRID] Valor inválido: {value}")
                return False

        return True

    def get_occupied_positions(self, state: Dict[int, str]) -> Set[int]:
        """
        Retorna posições ocupadas do tabuleiro.

        Args:
            state: Dict de estado

        Returns:
            Set de posições ocupadas
        """
        occupied = set()

        for position, value in state.items():
            if value != "vazio" and value != "ambíguo":
                occupied.add(position)

        return occupied

    def get_empty_positions(self, state: Dict[int, str]) -> Set[int]:
        """
        Retorna posições vazias do tabuleiro.

        Args:
            state: Dict de estado

        Returns:
            Set de posições vazias
        """
        return set(range(self.grid_rows * self.grid_cols)) - self.get_occupied_positions(state)

    def get_stats(self) -> dict:
        """Retorna estatísticas do calculador."""
        return {
            "grid_size": f"{self.grid_rows}x{self.grid_cols}",
            "total_cells": self.grid_rows * self.grid_cols,
            "cell_size": f"{self.cell_width:.1f}x{self.cell_height:.1f}px",
            "calculations": self.calculations_count,
        }


# ============================================================================
# Teste se executado diretamente
# ============================================================================

if __name__ == "__main__":
    print("[TESTE] Teste do GridCalculator")
    print("")

    try:
        # Criar calculador
        grid = GridCalculator(grid_rows=3, grid_cols=3, frame_width=640, frame_height=480)
        print("[OK] GridCalculator criado com sucesso")

        # Testar mapeamento de centróide para célula
        test_cases = [
            ((0, 0), 0),  # Canto superior esquerdo
            ((320, 240), 4),  # Centro
            ((639, 479), 8),  # Canto inferior direito
        ]

        print("\nTestes de mapeamento centróide -> célula:")
        for centroid, expected_cell in test_cases:
            cell = grid.centroid_to_cell(centroid)
            status = "[OK]" if cell == expected_cell else "[ERRO]"
            print(f"  {status} {centroid} -> célula {cell} (esperado {expected_cell})")

        # Testar mapeamento de célula para centróide
        print("\nTestes de mapeamento célula -> centróide:")
        for i in range(9):
            centroid = grid.cell_to_centroid(i)
            print(f"  [OK] Célula {i} -> {centroid}")

        # Testar cálculo de estado
        print("\nTeste de cálculo de estado:")
        detections = {
            1: (100, 100),  # Célula 0
            2: (320, 240),  # Célula 4
            3: (540, 380),  # Célula 8
        }
        state = grid.calculate_state(detections)

        print(f"  Detecções: {detections}")
        print(f"  Estado resultante:")
        for pos in range(9):
            print(f"    Posição {pos}: {state[pos]}")

        # Validar estado
        is_valid = grid.validate_state(state)
        print(f"\n  Estado válido: {is_valid}")

        # Stats
        stats = grid.get_stats()
        print(f"\n[STATUS] GridCalculator:")
        for key, value in stats.items():
            print(f"  - {key}: {value}")

    except Exception as e:
        print(f"[ERRO] Erro no teste: {e}")
        import traceback

        traceback.print_exc()

    print("\n[OK] Teste concluído")
