"""
Testes para GridCalculator

Testes isolados para mapeamento de grid 3x3.

Execution:
    pytest v2/vision/tests/test_grid.py -v
"""

import pytest
import logging
from unittest.mock import Mock
import sys
import os

# Adicionar v2 ao path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from vision.grid_calculator import GridCalculator


class TestGridCalculator:
    """Suite de testes para GridCalculator."""

    @pytest.fixture
    def grid(self):
        """Fixture: calculador de grid 3x3."""
        logger = logging.getLogger("test_grid")
        logger.setLevel(logging.DEBUG)
        return GridCalculator(grid_rows=3, grid_cols=3, frame_width=640, frame_height=480, logger=logger)

    # ========== Testes de Inicialização ==========

    def test_initialization_default_values(self, grid):
        """Testa inicialização com valores padrão."""
        assert grid.grid_rows == 3
        assert grid.grid_cols == 3
        assert grid.frame_width == 640
        assert grid.frame_height == 480
        assert grid.calculations_count == 0

    def test_initialization_custom_values(self):
        """Testa inicialização com valores customizados."""
        grid = GridCalculator(grid_rows=2, grid_cols=2, frame_width=800, frame_height=600)
        assert grid.grid_rows == 2
        assert grid.grid_cols == 2
        assert grid.frame_width == 800
        assert grid.frame_height == 600

    def test_cell_dimensions_calculated(self, grid):
        """Testa que dimensões das células são calculadas."""
        assert grid.cell_width == 640 / 3  # ~213.33
        assert grid.cell_height == 480 / 3  # ~160

    # ========== Testes de Mapeamento Centróide -> Célula ==========

    def test_centroid_to_cell_top_left(self, grid):
        """Testa mapeamento do canto superior esquerdo (célula 0)."""
        cell = grid.centroid_to_cell((0, 0))
        assert cell == 0

    def test_centroid_to_cell_center(self, grid):
        """Testa mapeamento do centro (célula 4)."""
        cell = grid.centroid_to_cell((320, 240))
        assert cell == 4

    def test_centroid_to_cell_bottom_right(self, grid):
        """Testa mapeamento do canto inferior direito (célula 8)."""
        cell = grid.centroid_to_cell((639, 479))
        assert cell == 8

    def test_centroid_to_cell_all_cells(self, grid):
        """Testa mapeamento para todas as 9 células."""
        expected_cells = [
            ((50, 50), 0),      # Superior esquerdo
            ((213, 50), 1),     # Superior centro
            ((426, 50), 2),     # Superior direito
            ((50, 240), 3),     # Meio esquerdo
            ((213, 240), 4),    # Centro
            ((426, 240), 5),    # Meio direito
            ((50, 430), 6),     # Inferior esquerdo
            ((213, 430), 7),    # Inferior centro
            ((426, 430), 8),    # Inferior direito
        ]

        for centroid, expected_cell in expected_cells:
            cell = grid.centroid_to_cell(centroid)
            assert cell == expected_cell

    def test_centroid_to_cell_out_of_bounds_negative(self, grid):
        """Testa mapeamento com coordenadas negativas."""
        cell = grid.centroid_to_cell((-10, -10))
        assert cell == -1

    def test_centroid_to_cell_out_of_bounds_positive(self, grid):
        """Testa mapeamento com coordenadas acima do frame."""
        cell = grid.centroid_to_cell((700, 500))
        assert cell == -1

    def test_centroid_to_cell_boundary_edge(self, grid):
        """Testa mapeamento nas bordas das células."""
        # Teste na borda entre células 0 e 1
        cell_left = grid.centroid_to_cell((213, 0))
        cell_right = grid.centroid_to_cell((214, 0))

        assert cell_left in [0, 1]
        assert cell_right in [0, 1]

    # ========== Testes de Mapeamento Célula -> Centróide ==========

    def test_cell_to_centroid_center_cell(self, grid):
        """Testa mapeamento da célula central (4) para centróide."""
        centroid = grid.cell_to_centroid(4)
        assert isinstance(centroid, tuple)
        assert len(centroid) == 2
        # Centro do grid
        assert abs(centroid[0] - 320) < 2
        assert abs(centroid[1] - 240) < 2

    def test_cell_to_centroid_all_cells(self, grid):
        """Testa mapeamento de todas as células."""
        for cell in range(9):
            centroid = grid.cell_to_centroid(cell)
            assert isinstance(centroid, tuple)
            assert len(centroid) == 2
            # Centróide deve estar dentro do frame
            assert 0 <= centroid[0] < 640
            assert 0 <= centroid[1] < 480

    def test_cell_to_centroid_invalid_cell(self, grid):
        """Testa mapeamento com célula inválida."""
        centroid = grid.cell_to_centroid(-1)
        assert centroid == (0.0, 0.0)

        centroid = grid.cell_to_centroid(9)
        assert centroid == (0.0, 0.0)

    def test_cell_to_centroid_roundtrip(self, grid):
        """Testa que centróide -> célula -> centróide retorna aprox. original."""
        original_centroid = (213, 160)
        cell = grid.centroid_to_cell(original_centroid)
        recovered_centroid = grid.cell_to_centroid(cell)

        # Não será exatamente igual, mas próximo
        assert abs(recovered_centroid[0] - original_centroid[0]) < grid.cell_width / 2
        assert abs(recovered_centroid[1] - original_centroid[1]) < grid.cell_height / 2

    # ========== Testes de Cálculo de Estado ==========

    def test_calculate_state_empty(self, grid):
        """Testa estado com nenhuma detecção."""
        state = grid.calculate_state({})

        assert len(state) == 9
        for pos in range(9):
            assert state[pos] == "vazio"

    def test_calculate_state_single_detection(self, grid):
        """Testa estado com uma detecção."""
        detections = {1: (320, 240)}  # Célula 4
        state = grid.calculate_state(detections)

        assert state[4] == "peça_1"
        assert state[0] == "vazio"
        assert state[8] == "vazio"

    def test_calculate_state_multiple_detections(self, grid):
        """Testa estado com múltiplas detecções."""
        detections = {
            1: (100, 100),    # Célula 0
            2: (320, 240),    # Célula 4
            3: (540, 380),    # Célula 8
        }
        state = grid.calculate_state(detections)

        assert state[0] == "peça_1"
        assert state[4] == "peça_2"
        assert state[8] == "peça_3"
        assert state[1] == "vazio"

    def test_calculate_state_all_cells_filled(self, grid):
        """Testa estado com todas as células preenchidas."""
        detections = {}
        for i in range(9):
            centroid = grid.cell_to_centroid(i)
            detections[i + 1] = centroid

        state = grid.calculate_state(detections)

        for pos in range(9):
            assert state[pos] != "vazio"
            assert state[pos] != "ambíguo"

    def test_calculate_state_ambiguity(self, grid):
        """Testa estado com ambigüidade (2 marcadores mesma célula)."""
        detections = {
            1: (320, 240),  # Célula 4
            2: (321, 241),  # Célula 4 (muito perto)
        }
        state = grid.calculate_state(detections)

        # Pode ser ambíguo ou uma das peças (depende de rounding)
        assert state[4] in ["ambíguo", "peça_1", "peça_2"]

    def test_calculate_state_out_of_bounds_marker(self, grid):
        """Testa estado com marcador fora dos limites."""
        detections = {
            1: (700, 500),  # Fora do grid
            2: (320, 240),  # Célula 4
        }
        state = grid.calculate_state(detections)

        assert state[4] == "peça_2"
        assert state[0] == "vazio"

    # ========== Testes de Validação de Estado ==========

    def test_validate_state_valid_empty(self, grid):
        """Testa validação de estado vazio válido."""
        state = {i: "vazio" for i in range(9)}
        assert grid.validate_state(state) is True

    def test_validate_state_valid_filled(self, grid):
        """Testa validação de estado válido preenchido."""
        state = {i: f"peça_{i}" for i in range(9)}
        assert grid.validate_state(state) is True

    def test_validate_state_invalid_type(self, grid):
        """Testa validação com tipo inválido."""
        state = [0, 1, 2, 3, 4, 5, 6, 7, 8]
        assert grid.validate_state(state) is False

    def test_validate_state_missing_positions(self, grid):
        """Testa validação com posições faltando."""
        state = {0: "vazio", 1: "vazio"}  # Faltam 7 posições
        assert grid.validate_state(state) is False

    def test_validate_state_invalid_position_type(self, grid):
        """Testa validação com tipo de posição inválido."""
        state = {"0": "vazio", 1: "vazio"}  # "0" é string
        for i in range(2, 9):
            state[i] = "vazio"
        assert grid.validate_state(state) is False

    def test_validate_state_invalid_value(self, grid):
        """Testa validação com valor inválido."""
        state = {i: "vazio" if i != 0 else "inválido" for i in range(9)}
        assert grid.validate_state(state) is False

    # ========== Testes de Posições Ocupadas/Vazias ==========

    def test_get_occupied_positions_empty_grid(self, grid):
        """Testa posições ocupadas em grid vazio."""
        state = {i: "vazio" for i in range(9)}
        occupied = grid.get_occupied_positions(state)

        assert len(occupied) == 0

    def test_get_occupied_positions_partial_fill(self, grid):
        """Testa posições ocupadas com preenchimento parcial."""
        state = {i: "vazio" for i in range(9)}
        state[0] = "peça_1"
        state[4] = "peça_2"
        state[8] = "peça_3"

        occupied = grid.get_occupied_positions(state)

        assert occupied == {0, 4, 8}

    def test_get_empty_positions(self, grid):
        """Testa posições vazias."""
        state = {i: "vazio" for i in range(9)}
        state[0] = "peça_1"
        state[4] = "peça_2"

        empty = grid.get_empty_positions(state)

        assert empty == {1, 2, 3, 5, 6, 7, 8}

    def test_occupied_and_empty_complement(self, grid):
        """Testa que ocupadas + vazias = todas as posições."""
        state = {i: "vazio" if i % 2 == 0 else f"peça_{i}" for i in range(9)}

        occupied = grid.get_occupied_positions(state)
        empty = grid.get_empty_positions(state)

        assert occupied | empty == set(range(9))
        assert occupied & empty == set()

    # ========== Testes de Estatísticas ==========

    def test_get_stats(self, grid):
        """Testa obtenção de estatísticas."""
        stats = grid.get_stats()

        assert isinstance(stats, dict)
        assert "grid_size" in stats
        assert "total_cells" in stats
        assert "cell_size" in stats
        assert "calculations" in stats
        assert stats["total_cells"] == 9
        assert stats["calculations"] == 0

    def test_stats_after_calculation(self, grid):
        """Testa estatísticas após cálculo."""
        detections = {1: (100, 100)}
        grid.calculate_state(detections)

        stats = grid.get_stats()
        assert stats["calculations"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
