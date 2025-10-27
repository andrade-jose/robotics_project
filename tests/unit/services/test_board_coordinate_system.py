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

        assert board.num_positions == 9
        assert len(board.positions) == 9
        assert board.center_x == 0.3
        assert board.center_y == -0.2
        assert board.spacing == 0.05

    def test_init_with_custom_values(self):
        """Testa inicialização com valores customizados."""
        board = BoardCoordinateSystem(
            center_x=0.4,
            center_y=-0.3,
            spacing=0.06,
            z_height=0.2
        )

        assert board.center_x == 0.4
        assert board.center_y == -0.3
        assert board.spacing == 0.06

    def test_all_positions_initialized(self):
        """Verifica que todas as 9 posições são inicializadas."""
        board = BoardCoordinateSystem()

        for i in range(9):
            assert i in board.positions
            assert len(board.positions[i]) == 6  # [x, y, z, rx, ry, rz]


class TestBoardCoordinateSystemPositions:
    """Testes de cálculo e recuperação de posições."""

    @pytest.fixture
    def board(self):
        """Fixture de BoardCoordinateSystem para testes."""
        return BoardCoordinateSystem(
            center_x=0.3,
            center_y=-0.2,
            spacing=0.05,
            z_height=0.15
        )

    def test_get_valid_position(self, board):
        """Testa recuperação de posição válida."""
        pose = board.get_position(4)  # Posição central

        assert pose is not None
        assert len(pose) == 6
        assert pose[0] == pytest.approx(0.3, abs=0.001)  # x = center_x
        assert pose[1] == pytest.approx(-0.2, abs=0.001)  # y = center_y
        assert pose[2] == pytest.approx(0.15, abs=0.001)  # z = z_height

    def test_get_invalid_position(self, board):
        """Testa recuperação de posição inválida."""
        assert board.get_position(-1) is None
        assert board.get_position(9) is None
        assert board.get_position(100) is None

    def test_corner_positions(self, board):
        """Testa cálculo das 4 posições de canto."""
        # Posição 0 (canto superior esquerdo)
        pos0 = board.get_position(0)
        assert pos0[0] == pytest.approx(0.3 - 0.05, abs=0.001)  # x = center - spacing
        assert pos0[1] == pytest.approx(-0.2 - 0.05, abs=0.001)  # y = center - spacing

        # Posição 2 (canto superior direito)
        pos2 = board.get_position(2)
        assert pos2[0] == pytest.approx(0.3 + 0.05, abs=0.001)  # x = center + spacing

        # Posição 6 (canto inferior esquerdo)
        pos6 = board.get_position(6)
        assert pos6[1] == pytest.approx(-0.2 + 0.05, abs=0.001)  # y = center + spacing

        # Posição 8 (canto inferior direito)
        pos8 = board.get_position(8)
        assert pos8[0] == pytest.approx(0.3 + 0.05, abs=0.001)
        assert pos8[1] == pytest.approx(-0.2 + 0.05, abs=0.001)

    def test_center_position(self, board):
        """Testa que posição 4 (centro) está no centro do tabuleiro."""
        center = board.get_position(4)

        assert center[0] == pytest.approx(board.center_x, abs=0.001)
        assert center[1] == pytest.approx(board.center_y, abs=0.001)

    def test_get_all_positions(self, board):
        """Testa recuperação de todas as posições."""
        all_positions = board.get_all_positions()

        assert len(all_positions) == 9
        assert all(i in all_positions for i in range(9))
        assert all(len(pose) == 6 for pose in all_positions.values())

    def test_orientation_constant(self, board):
        """Testa que orientação (rx, ry, rz) é constante para todas posições."""
        all_positions = board.get_all_positions()

        for pose in all_positions.values():
            assert pose[3] == 0  # rx
            assert pose[4] == 0  # ry
            assert pose[5] == 0  # rz


class TestBoardCoordinateSystemValidation:
    """Testes de validação de posições."""

    @pytest.fixture
    def board(self):
        return BoardCoordinateSystem()

    def test_is_position_valid_true(self, board):
        """Testa validação de posições válidas."""
        for i in range(9):
            assert board.is_position_valid(i) is True

    def test_is_position_valid_false(self, board):
        """Testa validação de posições inválidas."""
        assert board.is_position_valid(-1) is False
        assert board.is_position_valid(9) is False
        assert board.is_position_valid(100) is False

    def test_is_position_valid_with_string(self, board):
        """Testa validação com entrada string."""
        # Deve retornar False para tipos inválidos
        assert board.is_position_valid("0") is False
        assert board.is_position_valid(None) is False


class TestBoardCoordinateSystemPersistence:
    """Testes de persistência (salvar/carregar)."""

    @pytest.fixture
    def board(self):
        return BoardCoordinateSystem()

    @pytest.fixture
    def temp_file(self, tmp_path):
        """Arquivo temporário para testes de persistência."""
        return tmp_path / "test_board_positions.json"

    def test_save_positions(self, board, temp_file):
        """Testa salvamento de posições em arquivo."""
        result = board.save_positions(str(temp_file))

        assert result is True
        assert temp_file.exists()

        # Verifica conteúdo do arquivo
        with open(temp_file, 'r') as f:
            data = json.load(f)
            assert 'positions' in data
            assert len(data['positions']) == 9

    def test_load_positions(self, board, temp_file):
        """Testa carregamento de posições de arquivo."""
        # Primeiro salva
        board.save_positions(str(temp_file))

        # Modifica posições
        board.positions[0] = [0.1, 0.1, 0.1, 0, 0, 0]

        # Carrega de volta
        result = board.load_positions(str(temp_file))

        assert result is True
        # Posição deve ter sido restaurada
        assert board.positions[0] != [0.1, 0.1, 0.1, 0, 0, 0]

    def test_load_positions_file_not_found(self, board):
        """Testa carregamento quando arquivo não existe."""
        result = board.load_positions("arquivo_inexistente.json")

        assert result is False

    def test_save_and_load_consistency(self, board, temp_file):
        """Testa que save/load mantém dados consistentes."""
        original_positions = board.get_all_positions().copy()

        # Salva e carrega
        board.save_positions(str(temp_file))
        board.positions = {}  # Limpa posições
        board.load_positions(str(temp_file))

        loaded_positions = board.get_all_positions()

        # Compara todas as posições
        for i in range(9):
            assert loaded_positions[i] == pytest.approx(original_positions[i], abs=0.0001)


class TestBoardCoordinateSystemUpdate:
    """Testes de atualização de posições."""

    @pytest.fixture
    def board(self):
        return BoardCoordinateSystem()

    def test_update_position_valid(self, board):
        """Testa atualização de posição válida."""
        new_pose = [0.4, -0.3, 0.2, 0, 0, 0]
        result = board.update_position(0, new_pose)

        assert result is True
        assert board.get_position(0) == new_pose

    def test_update_position_invalid_index(self, board):
        """Testa atualização com índice inválido."""
        new_pose = [0.4, -0.3, 0.2, 0, 0, 0]

        assert board.update_position(-1, new_pose) is False
        assert board.update_position(9, new_pose) is False

    def test_update_position_invalid_pose(self, board):
        """Testa atualização com pose inválida."""
        invalid_pose = [0.4, -0.3]  # Faltam elementos

        result = board.update_position(0, invalid_pose)

        assert result is False

    def test_update_multiple_positions(self, board):
        """Testa atualização de múltiplas posições."""
        new_positions = {
            0: [0.1, 0.1, 0.1, 0, 0, 0],
            4: [0.3, -0.2, 0.15, 0, 0, 0],
            8: [0.5, -0.4, 0.2, 0, 0, 0]
        }

        for pos, pose in new_positions.items():
            board.update_position(pos, pose)

        for pos, pose in new_positions.items():
            assert board.get_position(pos) == pose


class TestBoardCoordinateSystemCalculations:
    """Testes de cálculos matemáticos."""

    def test_spacing_calculation(self):
        """Testa que spacing é aplicado corretamente."""
        board = BoardCoordinateSystem(center_x=0.0, center_y=0.0, spacing=0.1)

        pos0 = board.get_position(0)  # Canto superior esquerdo
        pos2 = board.get_position(2)  # Canto superior direito

        # Distância em x deve ser 2 * spacing
        distance_x = abs(pos2[0] - pos0[0])
        assert distance_x == pytest.approx(0.2, abs=0.001)

    def test_grid_symmetry(self):
        """Testa simetria do grid."""
        board = BoardCoordinateSystem(center_x=0.0, center_y=0.0)

        # Posições opostas devem ser simétricas
        pos0 = board.get_position(0)
        pos8 = board.get_position(8)

        assert pos0[0] == pytest.approx(-pos8[0], abs=0.001)
        assert pos0[1] == pytest.approx(-pos8[1], abs=0.001)


class TestBoardCoordinateSystemEdgeCases:
    """Testes de casos extremos."""

    def test_zero_spacing(self):
        """Testa comportamento com spacing zero."""
        board = BoardCoordinateSystem(spacing=0.0)

        # Todas as posições devem estar no mesmo ponto x,y
        all_positions = board.get_all_positions()
        x_coords = [pose[0] for pose in all_positions.values()]
        y_coords = [pose[1] for pose in all_positions.values()]

        assert len(set(x_coords)) == 1  # Todos os x são iguais
        assert len(set(y_coords)) == 1  # Todos os y são iguais

    def test_negative_spacing(self):
        """Testa comportamento com spacing negativo."""
        board = BoardCoordinateSystem(spacing=-0.05)

        # Deve funcionar, mas posições serão invertidas
        pos0 = board.get_position(0)
        pos8 = board.get_position(8)

        # Com spacing negativo, canto superior esquerdo vira inferior direito
        assert pos0[0] > board.center_x
        assert pos0[1] > board.center_y

    def test_extreme_coordinates(self):
        """Testa com coordenadas extremas."""
        board = BoardCoordinateSystem(
            center_x=10.0,
            center_y=-10.0,
            spacing=1.0
        )

        pos4 = board.get_position(4)
        assert pos4[0] == pytest.approx(10.0, abs=0.001)
        assert pos4[1] == pytest.approx(-10.0, abs=0.001)
