"""
Testes Unitários para BoardCoordinateSystem
Tests for the board coordinate system that maps game positions to robot poses.
"""

import pytest
from pathlib import Path
import json
from typing import List, Dict

from services.board_coordinate_system import BoardCoordinateSystem


class TestBoardCoordinateSystemInitialization:
    """Testes de inicialização do sistema de coordenadas."""

    def test_init_with_default_values(self):
        """Testa inicialização com valores padrão."""
        board = BoardCoordinateSystem()

        # Generate default grid
        board.generate_temporary_grid(spacing=0.10, z_height=0.05)

        assert len(board.coordinates) == 9
        # Center position (4) should be at HOME (-0.200, -0.267)
        center_pos = board.get_position(4)
        assert center_pos[0] == pytest.approx(-0.200, abs=0.001)
        assert center_pos[1] == pytest.approx(-0.267, abs=0.001)

    def test_init_with_custom_values(self):
        """Testa inicialização com valores customizados."""
        board = BoardCoordinateSystem()
        board.generate_temporary_grid(spacing=0.06, z_height=0.2)

        # Check that coordinates were generated
        assert len(board.coordinates) == 9
        # All z should be 0.2
        for i in range(9):
            assert board.get_position(i)[2] == pytest.approx(0.2, abs=0.001)

    def test_all_positions_initialized(self):
        """Verifica que todas as 9 posições são inicializadas."""
        board = BoardCoordinateSystem()
        board.generate_temporary_grid()

        for i in range(9):
            assert i in board.coordinates
            assert len(board.coordinates[i]) == 3  # [x, y, z]


class TestBoardCoordinateSystemPositions:
    """Testes de cálculo e recuperação de posições."""

    @pytest.fixture
    def board(self):
        """Fixture de BoardCoordinateSystem para testes."""
        board = BoardCoordinateSystem()
        board.generate_temporary_grid(spacing=0.05, z_height=0.15)
        return board

    def test_get_valid_position(self, board):
        """Testa recuperação de posição válida."""
        pose = board.get_position(4)  # Posição central

        assert pose is not None
        assert len(pose) == 3  # [x, y, z]
        assert pose[0] == pytest.approx(-0.200, abs=0.001)  # x = center_x (HOME)
        assert pose[1] == pytest.approx(-0.267, abs=0.001)  # y = center_y (HOME)
        assert pose[2] == pytest.approx(0.15, abs=0.001)  # z = z_height

    def test_get_invalid_position(self, board):
        """Testa recuperação de posição inválida."""
        assert board.get_position(-1) is None
        assert board.get_position(9) is None
        assert board.get_position(100) is None

    def test_corner_positions(self, board):
        """Testa cálculo das 4 posições de canto."""
        # Board centered at HOME (-0.200, -0.267) with 0.05m spacing
        # Layout: divmod(i, 3) gives (row, col)
        # Position 0: row=0, col=0 -> x = -0.200 + (0-1)*0.05 = -0.250, y = -0.267 + (0-1)*0.05 = -0.317
        # Position 2: row=0, col=2 -> x = -0.200 + (0-1)*0.05 = -0.250, y = -0.267 + (2-1)*0.05 = -0.217
        # Position 6: row=2, col=0 -> x = -0.200 + (2-1)*0.05 = -0.150, y = -0.267 + (0-1)*0.05 = -0.317
        # Position 8: row=2, col=2 -> x = -0.200 + (2-1)*0.05 = -0.150, y = -0.267 + (2-1)*0.05 = -0.217

        pos0 = board.get_position(0)
        assert pos0[0] == pytest.approx(-0.200 - 0.05, abs=0.001)  # x = center - spacing
        assert pos0[1] == pytest.approx(-0.267 - 0.05, abs=0.001)  # y = center - spacing

        # Posição 2 (row 0, col 2)
        pos2 = board.get_position(2)
        assert pos2[0] == pytest.approx(-0.200 - 0.05, abs=0.001)  # x = center - spacing (row determines x)
        assert pos2[1] == pytest.approx(-0.267 + 0.05, abs=0.001)  # y = center + spacing (col determines y)

        # Posição 6 (row 2, col 0)
        pos6 = board.get_position(6)
        assert pos6[0] == pytest.approx(-0.200 + 0.05, abs=0.001)  # x = center + spacing (row determines x)
        assert pos6[1] == pytest.approx(-0.267 - 0.05, abs=0.001)  # y = center - spacing (col determines y)

        # Posição 8 (row 2, col 2)
        pos8 = board.get_position(8)
        assert pos8[0] == pytest.approx(-0.200 + 0.05, abs=0.001)  # x = center + spacing
        assert pos8[1] == pytest.approx(-0.267 + 0.05, abs=0.001)  # y = center + spacing

    def test_center_position(self, board):
        """Testa que posição 4 (centro) está no centro do tabuleiro."""
        center = board.get_position(4)

        assert center[0] == pytest.approx(-0.200, abs=0.001)  # HOME x
        assert center[1] == pytest.approx(-0.267, abs=0.001)  # HOME y

    def test_get_all_positions(self, board):
        """Testa recuperação de todas as posições."""
        all_positions = board.get_all_coordinates()

        assert len(all_positions) == 9
        assert all(i in all_positions for i in range(9))
        assert all(len(pose) == 3 for pose in all_positions.values())  # [x, y, z]

    def test_orientation_constant(self, board):
        """Testa que as coordenadas têm 3 componentes (x, y, z)."""
        all_positions = board.get_all_coordinates()

        for pose in all_positions.values():
            assert len(pose) == 3  # [x, y, z]


class TestBoardCoordinateSystemValidation:
    """Testes de validação de posições."""

    @pytest.fixture
    def board(self):
        board = BoardCoordinateSystem()
        board.generate_temporary_grid()
        return board

    def test_validate_coordinates_valid(self, board):
        """Testa validação de coordenadas válidas."""
        validation = board.validate_coordinates()
        assert validation['valid'] is True
        assert validation['positions_ok'] == 9

    def test_validate_coordinates_incomplete(self):
        """Testa validação de coordenadas incompletas."""
        board = BoardCoordinateSystem()
        # Don't generate grid - coordinates will be empty
        validation = board.validate_coordinates()
        assert validation['valid'] is False
        assert validation['positions_ok'] == 0

    def test_has_valid_coordinates(self, board):
        """Testa se coordenadas são válidas."""
        assert board.has_valid_coordinates() is True

    def test_has_valid_coordinates_incomplete(self):
        """Testa has_valid_coordinates com grid incompleto."""
        board = BoardCoordinateSystem()
        assert board.has_valid_coordinates() is False


class TestBoardCoordinateSystemPersistence:
    """Testes de persistência (salvar/carregar)."""

    @pytest.fixture
    def board(self):
        board = BoardCoordinateSystem()
        board.generate_temporary_grid()
        return board

    @pytest.fixture
    def temp_file(self, tmp_path):
        """Arquivo temporário para testes de persistência."""
        return tmp_path / "test_board_positions.json"

    def test_save_to_file(self, board, temp_file):
        """Testa salvamento de posições em arquivo."""
        result = board.save_to_file(str(temp_file))

        assert result is True
        assert temp_file.exists()

        # Verifica conteúdo do arquivo
        with open(temp_file, 'r') as f:
            data = json.load(f)
            assert len(data) == 9

    def test_load_from_file(self, board, temp_file):
        """Testa carregamento de posições de arquivo."""
        # Primeiro salva
        original_coords = board.get_all_coordinates().copy()
        board.save_to_file(str(temp_file))

        # Cria novo board vazio
        board2 = BoardCoordinateSystem()
        result = board2.load_from_file(str(temp_file))

        assert result is True
        assert board2.has_valid_coordinates() is True

        # Verifica se coordenadas foram restauradas
        loaded_coords = board2.get_all_coordinates()
        for i in range(9):
            for j in range(3):
                assert original_coords[i][j] == pytest.approx(loaded_coords[i][j], abs=0.0001)

    def test_load_from_file_not_found(self):
        """Testa carregamento quando arquivo não existe."""
        board = BoardCoordinateSystem()
        result = board.load_from_file("arquivo_inexistente.json")

        assert result is False

    def test_save_and_load_consistency(self, board, temp_file):
        """Testa que save/load mantém dados consistentes."""
        original_positions = board.get_all_coordinates().copy()

        # Salva
        board.save_to_file(str(temp_file))

        # Cria novo board e carrega
        board2 = BoardCoordinateSystem()
        board2.load_from_file(str(temp_file))

        loaded_positions = board2.get_all_coordinates()

        # Compara todas as posições
        for i in range(9):
            for j in range(3):
                assert loaded_positions[i][j] == pytest.approx(original_positions[i][j], abs=0.0001)


class TestBoardCoordinateSystemUpdate:
    """Testes de atualização de posições."""

    @pytest.fixture
    def board(self):
        board = BoardCoordinateSystem()
        board.generate_temporary_grid()
        return board

    def test_set_coordinates(self, board):
        """Testa definição de coordenadas."""
        new_coords = {
            i: (0.0 + i*0.1, 0.0 + i*0.05, 0.1) for i in range(9)
        }
        board.set_coordinates(new_coords)

        assert board.has_valid_coordinates() is True
        for i in range(9):
            assert board.get_position(i) == new_coords[i]

    def test_set_robot_offset(self, board):
        """Testa definição de offset do robô."""
        original_pos = board.get_position(4)
        board.set_robot_offset(0.05, -0.05)

        # Offset só afeta coordenadas de visão, não as temporárias
        # Mantém posição da mesma
        assert board.robot_offset_x == 0.05
        assert board.robot_offset_y == -0.05


class TestBoardCoordinateSystemCalculations:
    """Testes de cálculos matemáticos."""

    def test_spacing_calculation(self):
        """Testa que spacing é aplicado corretamente."""
        board = BoardCoordinateSystem()
        board.generate_temporary_grid(spacing=0.1, z_height=0.1)

        pos0 = board.get_position(0)  # row=0, col=0
        pos6 = board.get_position(6)  # row=2, col=0

        # Distância em x deve ser 2 * spacing (comparing rows: 0 and 2)
        distance_x = abs(pos6[0] - pos0[0])
        assert distance_x == pytest.approx(0.2, abs=0.001)

    def test_grid_symmetry(self):
        """Testa simetria do grid."""
        board = BoardCoordinateSystem()
        board.generate_temporary_grid(spacing=0.05, z_height=0.1)

        # Posições opostas devem ser simétricas em relação ao centro
        pos0 = board.get_position(0)
        pos8 = board.get_position(8)
        center = board.get_position(4)

        # Distância de pos0 ao centro deve ser igual a pos8 ao centro
        dist_0_center_x = abs(pos0[0] - center[0])
        dist_8_center_x = abs(pos8[0] - center[0])
        assert dist_0_center_x == pytest.approx(dist_8_center_x, abs=0.001)


class TestBoardCoordinateSystemEdgeCases:
    """Testes de casos extremos."""

    def test_zero_spacing(self):
        """Testa comportamento com spacing zero."""
        board = BoardCoordinateSystem()
        board.generate_temporary_grid(spacing=0.0, z_height=0.1)

        # Todas as posições devem estar no mesmo ponto x,y (HOME)
        all_positions = board.get_all_coordinates()
        x_coords = [pose[0] for pose in all_positions.values()]
        y_coords = [pose[1] for pose in all_positions.values()]

        # Todos os x devem ser -0.200
        assert all(pytest.approx(x, abs=0.001) == -0.200 for x in x_coords)
        # Todos os y devem ser -0.267
        assert all(pytest.approx(y, abs=0.001) == -0.267 for y in y_coords)

    def test_negative_spacing(self):
        """Testa comportamento com spacing negativo."""
        board = BoardCoordinateSystem()
        board.generate_temporary_grid(spacing=-0.05, z_height=0.1)

        # Deve funcionar, mas posições serão invertidas
        pos0 = board.get_position(0)
        pos8 = board.get_position(8)

        # Com spacing negativo, canto 0 deveria ser em posição oposta
        # pos0: row=0, col=0 -> x = -0.200 + (0-1)*(-0.05) = -0.200 + 0.05
        # pos8: row=2, col=2 -> x = -0.200 + (2-1)*(-0.05) = -0.200 - 0.05
        assert pos0[0] > -0.200
        assert pos8[0] < -0.200

    def test_large_spacing(self):
        """Testa com espaçamento grande."""
        board = BoardCoordinateSystem()
        board.generate_temporary_grid(spacing=1.0, z_height=0.1)

        all_positions = board.get_all_coordinates()
        assert len(all_positions) == 9
        assert all(board.has_valid_coordinates() for _ in [True])

    def test_high_z_height(self):
        """Testa com altura Z grande."""
        board = BoardCoordinateSystem()
        board.generate_temporary_grid(spacing=0.05, z_height=1.0)

        # Todas as posições devem estar a Z = 1.0
        all_positions = board.get_all_coordinates()
        for i in range(9):
            assert board.get_position(i)[2] == pytest.approx(1.0, abs=0.001)
