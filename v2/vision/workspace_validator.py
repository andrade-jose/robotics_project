"""
WorkspaceValidator - Validação de Espaço de Trabalho

Responsabilidades:
- Definir limites físicos e de segurança do espaço de trabalho
- Validar que posições de jogo estão dentro de limites
- Validar movimentos (origem → destino)
- Detectar colisões e conflitos com limites

Espaço de Trabalho:
1. Board bounds (limites do tabuleiro 3x3)
2. Safety margin (margem de segurança ao redor do tabuleiro)
3. Robot workspace (alcance máximo do robô)
4. Collision zones (zonas de risco/colisão)

Uso:
    from grid_generator import GridGenerator
    validator = WorkspaceValidator(grid)

    # Validar posição
    is_valid = validator.is_position_valid(0)  # Posição 0

    # Validar movimento
    can_move = validator.can_move(from_position=0, to_position=4)

    # Obter zona de segurança
    safe_zone = validator.get_safety_margins()
"""

import logging
from typing import Optional, Dict, Tuple, Set
from dataclasses import dataclass


@dataclass
class WorkspaceConstraints:
    """Restrições do espaço de trabalho."""
    min_x_mm: float  # Limite X mínimo
    max_x_mm: float  # Limite X máximo
    min_y_mm: float  # Limite Y mínimo
    max_y_mm: float  # Limite Y máximo
    safety_margin_mm: float  # Margem de segurança
    collision_zones: list  # Lista de zonas de colisão


class WorkspaceValidator:
    """
    Validador de espaço de trabalho.

    Características:
    - Define limites físicos do board e margens de segurança
    - Valida posições individuais
    - Valida movimentos (colisão com outras peças)
    - Fornece informações de segurança
    - Logging detalhado
    """

    def __init__(
        self,
        grid_generator,  # GridGenerator com 9 posições
        safety_margin_mm: float = 10.0,  # Margem de segurança (10mm)
        logger: Optional[logging.Logger] = None,
    ):
        """
        Inicializa validador de workspace.

        Args:
            grid_generator: GridGenerator com posições do grid
            safety_margin_mm: Margem de segurança ao redor do board (mm)
            logger: Logger customizado
        """
        if grid_generator is None:
            raise ValueError("GridGenerator não pode ser None")

        self.grid = grid_generator
        self.safety_margin_mm = safety_margin_mm
        self.constraints: Optional[WorkspaceConstraints] = None
        self.piece_positions: Set[int] = set()  # Posições ocupadas

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

        # Construir restrições
        self._build_constraints()

    def _build_constraints(self) -> bool:
        """
        Constrói as restrições do workspace.

        Algoritmo:
        1. Obter limites do grid (obtém do BoardTransformCalculator)
        2. Aplicar margem de segurança
        3. Armazenar como WorkspaceConstraints
        """
        try:
            bounds = self.grid.get_grid_bounds()
            if not bounds:
                self.logger.error("[WORKSPACE] Não conseguiu obter limites do grid")
                return False

            # Aplicar margem de segurança
            min_x = bounds["min_x"] - self.safety_margin_mm
            max_x = bounds["max_x"] + self.safety_margin_mm
            min_y = bounds["min_y"] - self.safety_margin_mm
            max_y = bounds["max_y"] + self.safety_margin_mm

            self.constraints = WorkspaceConstraints(
                min_x_mm=min_x,
                max_x_mm=max_x,
                min_y_mm=min_y,
                max_y_mm=max_y,
                safety_margin_mm=self.safety_margin_mm,
                collision_zones=[],  # Nenhuma zona de colisão por enquanto
            )

            self.logger.info(
                f"[WORKSPACE] Restrições construídas "
                f"X: [{min_x:.1f}, {max_x:.1f}] mm, "
                f"Y: [{min_y:.1f}, {max_y:.1f}] mm, "
                f"Margem de segurança: {self.safety_margin_mm:.1f} mm"
            )
            return True

        except Exception as e:
            self.logger.error(f"[WORKSPACE] Erro ao construir restrições: {e}")
            return False

    def is_position_valid(self, position: int) -> bool:
        """
        Valida se uma posição é válida.

        Verificações:
        - Posição entre 0-8
        - Posição dentro dos limites do grid
        - (Futura: posição não ocupada)

        Args:
            position: ID da posição (0-8)

        Returns:
            True se válida, False caso contrário
        """
        if not self.constraints:
            self.logger.warning("[WORKSPACE] Restrições não construídas")
            return False

        if position < 0 or position > 8:
            self.logger.warning(f"[WORKSPACE] Posição inválida: {position} (fora de 0-8)")
            return False

        # Obter coordenadas da célula
        cell_coords = self.grid.get_cell_position(position)
        if cell_coords is None:
            self.logger.warning(f"[WORKSPACE] Não conseguiu obter coordenadas da posição {position}")
            return False

        x_mm, y_mm, _ = cell_coords

        # Verificar limites
        if not (
            self.constraints.min_x_mm <= x_mm <= self.constraints.max_x_mm and
            self.constraints.min_y_mm <= y_mm <= self.constraints.max_y_mm
        ):
            self.logger.warning(
                f"[WORKSPACE] Posição {position} ({x_mm:.1f}, {y_mm:.1f}) "
                f"fora dos limites"
            )
            return False

        return True

    def is_coordinates_valid(self, board_x_mm: float, board_y_mm: float) -> bool:
        """
        Valida se coordenadas (x, y) estão dentro do workspace.

        Args:
            board_x_mm: Coordenada X em mm
            board_y_mm: Coordenada Y em mm

        Returns:
            True se dentro dos limites, False caso contrário
        """
        if not self.constraints:
            self.logger.warning("[WORKSPACE] Restrições não construídas")
            return False

        is_valid = (
            self.constraints.min_x_mm <= board_x_mm <= self.constraints.max_x_mm and
            self.constraints.min_y_mm <= board_y_mm <= self.constraints.max_y_mm
        )

        if not is_valid:
            self.logger.debug(
                f"[WORKSPACE] Coordenadas ({board_x_mm:.1f}, {board_y_mm:.1f}) "
                f"fora dos limites"
            )

        return is_valid

    def can_move(
        self,
        from_position: int,
        to_position: int,
        occupied_positions: Optional[Set[int]] = None,
    ) -> bool:
        """
        Valida se um movimento é permitido.

        Verificações:
        - Posições de origem e destino são válidas
        - Destino não está ocupado (se informado)
        - Movimento não viola limites

        Args:
            from_position: Posição inicial (0-8)
            to_position: Posição final (0-8)
            occupied_positions: Set de posições ocupadas (opcional)

        Returns:
            True se movimento é permitido, False caso contrário
        """
        if not self.constraints:
            self.logger.warning("[WORKSPACE] Restrições não construídas")
            return False

        # Validar posições
        if not self.is_position_valid(from_position):
            self.logger.warning(f"[WORKSPACE] Posição de origem {from_position} inválida")
            return False

        if not self.is_position_valid(to_position):
            self.logger.warning(f"[WORKSPACE] Posição de destino {to_position} inválida")
            return False

        # Não permitir movimento para a mesma posição
        if from_position == to_position:
            self.logger.warning("[WORKSPACE] Origem e destino são iguais")
            return False

        # Verificar se destino está ocupado
        if occupied_positions is not None:
            if to_position in occupied_positions:
                self.logger.warning(
                    f"[WORKSPACE] Posição de destino {to_position} está ocupada"
                )
                return False

        self.logger.debug(
            f"[WORKSPACE] Movimento de {from_position} → {to_position} permitido"
        )
        return True

    def update_piece_positions(self, occupied_positions: Set[int]):
        """
        Atualiza lista de posições ocupadas (peças).

        Args:
            occupied_positions: Set de posições (0-8) com peças
        """
        # Validar todas as posições
        valid_positions = set()
        for pos in occupied_positions:
            if self.is_position_valid(pos):
                valid_positions.add(pos)
            else:
                self.logger.warning(f"[WORKSPACE] Posição ocupada inválida: {pos}")

        self.piece_positions = valid_positions
        self.logger.debug(f"[WORKSPACE] Posições atualizadas: {sorted(self.piece_positions)}")

    def get_valid_moves(self, from_position: int) -> Set[int]:
        """
        Retorna todas as posições válidas para movimento a partir de uma posição.

        Args:
            from_position: Posição inicial (0-8)

        Returns:
            Set de posições válidas (não ocupadas)
        """
        valid_moves = set()

        for to_position in range(9):
            if self.can_move(from_position, to_position, self.piece_positions):
                valid_moves.add(to_position)

        self.logger.debug(
            f"[WORKSPACE] Movimentos válidos de {from_position}: {sorted(valid_moves)}"
        )
        return valid_moves

    def get_safety_margins(self) -> Dict:
        """
        Retorna informações de margem de segurança.

        Returns:
            Dict com detalhes da zona de segurança
        """
        if not self.constraints:
            return {}

        bounds = self.grid.get_grid_bounds()

        return {
            "board_min_x_mm": bounds.get("min_x", 0),
            "board_max_x_mm": bounds.get("max_x", 0),
            "board_min_y_mm": bounds.get("min_y", 0),
            "board_max_y_mm": bounds.get("max_y", 0),
            "workspace_min_x_mm": self.constraints.min_x_mm,
            "workspace_max_x_mm": self.constraints.max_x_mm,
            "workspace_min_y_mm": self.constraints.min_y_mm,
            "workspace_max_y_mm": self.constraints.max_y_mm,
            "safety_margin_mm": self.safety_margin_mm,
            "workspace_width_mm": self.constraints.max_x_mm - self.constraints.min_x_mm,
            "workspace_height_mm": self.constraints.max_y_mm - self.constraints.min_y_mm,
        }

    def validate_all_positions(self) -> bool:
        """
        Valida que todas as 9 posições são válidas.

        Returns:
            True se todas as 9 posições estão dentro dos limites
        """
        all_valid = all(self.is_position_valid(pos) for pos in range(9))

        if all_valid:
            self.logger.info("[WORKSPACE] Todas as 9 posições estão dentro dos limites")
        else:
            invalid_positions = [pos for pos in range(9) if not self.is_position_valid(pos)]
            self.logger.warning(f"[WORKSPACE] Posições inválidas: {invalid_positions}")

        return all_valid

    def get_stats(self) -> Dict:
        """Retorna estatísticas do workspace."""
        if not self.constraints:
            return {"is_initialized": False}

        return {
            "is_initialized": True,
            "total_positions": 9,
            "valid_positions": sum(1 for pos in range(9) if self.is_position_valid(pos)),
            "occupied_positions": len(self.piece_positions),
            "free_positions": 9 - len(self.piece_positions),
            "constraints": {
                "min_x_mm": self.constraints.min_x_mm,
                "max_x_mm": self.constraints.max_x_mm,
                "min_y_mm": self.constraints.min_y_mm,
                "max_y_mm": self.constraints.max_y_mm,
            },
            "safety_margin_mm": self.safety_margin_mm,
        }


# ============================================================================
# Teste
# ============================================================================

if __name__ == "__main__":
    print("[TESTE] WorkspaceValidator")
    print("")

    try:
        from grid_generator import GridGenerator
        from board_transform_calculator import BoardTransformCalculator
        from dataclasses import dataclass
        import numpy as np

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

        # Criar componentes
        transform = BoardTransformCalculator(calibration)
        grid = GridGenerator(transform)
        validator = WorkspaceValidator(grid, safety_margin_mm=10.0)
        print("[OK] WorkspaceValidator criado")

        # Validar todas as posições
        print("\nValidação de posições (0-8):")
        for pos in range(9):
            is_valid = validator.is_position_valid(pos)
            print(f"  Posição {pos}: {'[OK]' if is_valid else '[INVÁLIDA]'}")

        # Testar movimentos
        print("\nTestes de movimento:")
        test_moves = [(0, 1), (0, 4), (4, 8), (0, 0)]
        for from_pos, to_pos in test_moves:
            can_move = validator.can_move(from_pos, to_pos)
            print(f"  {from_pos} → {to_pos}: {'[OK]' if can_move else '[BLOQUEADO]'}")

        # Atualizar posições ocupadas
        print("\nMovimentos válidos com posições ocupadas:")
        validator.update_piece_positions({0, 8})
        valid_moves = validator.get_valid_moves(0)
        print(f"  De posição 0 (ocupada): movimentos válidos = {sorted(valid_moves)}")

        valid_moves = validator.get_valid_moves(4)
        print(f"  De posição 4 (livre): movimentos válidos = {sorted(valid_moves)}")

        # Mostrar margens de segurança
        print("\nMargens de segurança:")
        margins = validator.get_safety_margins()
        for key, value in margins.items():
            if isinstance(value, float):
                print(f"  - {key}: {value:.2f}")
            else:
                print(f"  - {key}: {value}")

        # Stats
        print("\n[INFO] Estatísticas:")
        stats = validator.get_stats()
        for key, value in stats.items():
            if key != "constraints":
                print(f"  - {key}: {value}")

    except Exception as e:
        print(f"[ERRO] {e}")
        import traceback

        traceback.print_exc()

    print("\n[OK] Teste concluído")
