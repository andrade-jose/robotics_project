"""
BoardCoordinateSystem - Sistema Único de Coordenadas do Tabuleiro

RESPONSABILIDADE ÚNICA:
    Gerenciar todas as coordenadas físicas do tabuleiro 3x3 do jogo Tapatan.

FUNCIONALIDADES:
    - Gerar coordenadas temporárias (fallback)
    - Integrar com sistema de visão ArUco (dinâmico)
    - Validar coordenadas
    - Persistir/carregar de arquivo JSON
    - Aplicar offsets do robô
"""

from typing import Dict, Tuple, Optional
import json
import logging
from pathlib import Path


class BoardCoordinateSystem:
    """
    Sistema centralizado para gerenciamento de coordenadas do tabuleiro.

    Suporta 3 modos de operação:
    1. Coordenadas temporárias (fallback manual)
    2. Coordenadas dinâmicas via ArUco (preferencial)
    3. Coordenadas salvas em arquivo JSON (backup)
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Inicializa o sistema de coordenadas.

        Args:
            logger: Logger opcional para mensagens
        """
        self.coordinates: Dict[int, Tuple[float, float, float]] = {}
        self.logger = logger or logging.getLogger(__name__)

        # Offsets do robô em relação ao tabuleiro
        self.robot_offset_x: float = 0.0
        self.robot_offset_y: float = 0.0

        # Sistema de visão opcional
        self.vision_system = None

    # ==================== GERAÇÃO DE COORDENADAS ====================

    def generate_temporary_grid(self, spacing: float = 0.06, z_height: float = 0.05) -> Dict[int, Tuple[float, float, float]]:
        """
        Gera coordenadas temporárias em grid 3x3 centrado.

        Args:
            spacing: Espaçamento entre posições em metros (padrão: 6cm)
            z_height: Altura do tabuleiro em metros (padrão: 5cm)

        Returns:
            Dict com 9 posições {0-8: (x, y, z)}
        """
        coordinates = {}

        for i in range(9):
            row, col = divmod(i, 3)
            # Centralizar no grid: -1, 0, 1 * spacing
            x = (col - 1) * spacing
            y = (row - 1) * spacing
            z = z_height

            coordinates[i] = (x, y, z)

        self.coordinates = coordinates
        self.logger.info(f"⚠️ Coordenadas temporárias criadas: {len(coordinates)} posições")
        return coordinates

    def generate_from_vision(self, vision_system) -> bool:
        """
        Gera coordenadas dinâmicas usando sistema de visão ArUco.

        Args:
            vision_system: Instância do sistema de visão calibrado

        Returns:
            True se coordenadas foram geradas com sucesso
        """
        try:
            # Verificar se sistema de visão está disponível e calibrado
            if not hasattr(vision_system, 'is_calibrated') or not vision_system.is_calibrated:
                self.logger.warning("⚠️ Sistema de visão não calibrado")
                return False

            # Calcular posições do grid 3x3
            grid_positions = vision_system.calculate_grid_3x3_positions()

            if not grid_positions or len(grid_positions) != 9:
                self.logger.error(f"❌ Grid incompleto: {len(grid_positions) if grid_positions else 0}/9")
                return False

            # Converter coordenadas de visão para coordenadas do robô
            self.coordinates = {}

            for pos in grid_positions:
                # Converter mm → metros + aplicar offset do robô
                x_final = (pos['x_mm'] / 1000.0) + self.robot_offset_x
                y_final = (pos['y_mm'] / 1000.0) + self.robot_offset_y
                z_final = (pos['z_mm'] / 1000.0) + 0.05  # Altura do tabuleiro

                self.coordinates[pos['index']] = (x_final, y_final, z_final)

            self.logger.info(f"✅ Coordenadas dinâmicas geradas: {len(self.coordinates)}/9 posições")
            return True

        except Exception as e:
            self.logger.error(f"❌ Erro ao gerar coordenadas de visão: {e}")
            return False

    # ==================== VALIDAÇÃO ====================

    def validate_coordinates(self) -> Dict[str, any]:
        """
        Valida se as coordenadas do tabuleiro estão corretas.

        Returns:
            Dict com resultado da validação e detalhes
        """
        result = {
            'valid': False,
            'positions_ok': 0,
            'missing_positions': [],
            'distances_ok': True,
            'details': []
        }

        try:
            # Verificar se temos as 9 posições
            expected_positions = set(range(9))
            found_positions = set(self.coordinates.keys())

            result['positions_ok'] = len(found_positions)
            result['missing_positions'] = list(expected_positions - found_positions)

            if result['missing_positions']:
                result['details'].append(f"Posições faltando: {result['missing_positions']}")
                return result

            # Verificar consistência das distâncias
            distances = []
            for i in [0, 3, 6]:  # Primeira coluna de cada linha
                if i in self.coordinates and (i+1) in self.coordinates:
                    coord1 = self.coordinates[i]
                    coord2 = self.coordinates[i+1]
                    dist = ((coord2[0]-coord1[0])**2 + (coord2[1]-coord1[1])**2)**0.5
                    distances.append(dist)

            if distances:
                avg_dist = sum(distances) / len(distances)
                variation = max(distances) - min(distances)

                if variation > avg_dist * 0.1:  # Variação > 10%
                    result['distances_ok'] = False
                    result['details'].append(f"Distâncias inconsistentes: {variation*100:.1f}cm")
                else:
                    result['details'].append(f"Espaçamento OK: {avg_dist*100:.1f}cm")

            result['valid'] = (result['positions_ok'] == 9 and result['distances_ok'])

            if result['valid']:
                result['details'].append("✅ Tabuleiro válido")

            return result

        except Exception as e:
            result['details'].append(f"Erro na validação: {e}")
            return result

    def has_valid_coordinates(self) -> bool:
        """
        Verifica rapidamente se coordenadas estão definidas e completas.

        Returns:
            True se todas as 9 posições estão definidas
        """
        if len(self.coordinates) != 9:
            self.logger.warning(f"❌ Coordenadas incompletas: {len(self.coordinates)}/9")
            return False

        for i in range(9):
            if i not in self.coordinates:
                self.logger.warning(f"❌ Posição {i} não definida")
                return False

        return True

    # ==================== ACESSO A POSIÇÕES ====================

    def get_position(self, index: int) -> Optional[Tuple[float, float, float]]:
        """
        Retorna coordenadas de uma posição específica.

        Args:
            index: Índice da posição (0-8)

        Returns:
            Tupla (x, y, z) ou None se não existir
        """
        if index not in self.coordinates:
            self.logger.warning(f"⚠️ Posição {index} não encontrada")
            return None

        return self.coordinates[index]

    def get_all_coordinates(self) -> Dict[int, Tuple[float, float, float]]:
        """
        Retorna todas as coordenadas do tabuleiro.

        Returns:
            Dict completo {0-8: (x, y, z)}
        """
        return self.coordinates.copy()

    def set_coordinates(self, coordinates: Dict[int, Tuple[float, float, float]]):
        """
        Define coordenadas manualmente.

        Args:
            coordinates: Dict {posição: (x, y, z)} das 9 posições
        """
        self.coordinates = coordinates.copy()
        self.logger.info(f"📍 Coordenadas definidas: {len(coordinates)} posições")

    # ==================== PERSISTÊNCIA ====================

    def load_from_file(self, filepath: str) -> bool:
        """
        Carrega coordenadas de arquivo JSON.

        Args:
            filepath: Caminho do arquivo JSON

        Returns:
            True se carregamento foi bem-sucedido
        """
        try:
            path = Path(filepath)

            if not path.exists():
                self.logger.warning(f"⚠️ Arquivo não encontrado: {filepath}")
                return False

            with open(path, 'r') as f:
                data = json.load(f)

            # Converter chaves de string para int
            self.coordinates = {}
            for key, value in data.items():
                self.coordinates[int(key)] = tuple(value)

            self.logger.info(f"✅ Coordenadas carregadas de {filepath}: {len(self.coordinates)} posições")
            return True

        except Exception as e:
            self.logger.error(f"❌ Erro ao carregar coordenadas: {e}")
            return False

    def save_to_file(self, filepath: str) -> bool:
        """
        Salva coordenadas em arquivo JSON.

        Args:
            filepath: Caminho do arquivo JSON

        Returns:
            True se salvamento foi bem-sucedido
        """
        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)

            # Converter tuplas para listas para JSON
            data = {str(k): list(v) for k, v in self.coordinates.items()}

            with open(path, 'w') as f:
                json.dump(data, f, indent=2)

            self.logger.info(f"💾 Coordenadas salvas em {filepath}")
            return True

        except Exception as e:
            self.logger.error(f"❌ Erro ao salvar coordenadas: {e}")
            return False

    # ==================== INTEGRAÇÃO COM VISÃO E ROBÔ ====================

    def set_vision_system(self, vision_system):
        """
        Integra sistema de visão ArUco.

        Args:
            vision_system: Instância do sistema de visão
        """
        self.vision_system = vision_system

        # Se já estiver calibrado, gerar coordenadas imediatamente
        if hasattr(vision_system, 'is_calibrated') and vision_system.is_calibrated:
            self.generate_from_vision(vision_system)

    def set_robot_offset(self, offset_x: float, offset_y: float):
        """
        Define posicionamento do robô em relação ao tabuleiro.

        Args:
            offset_x: Offset em X (metros)
            offset_y: Offset em Y (metros)
        """
        self.robot_offset_x = offset_x
        self.robot_offset_y = offset_y
        self.logger.info(f"🤖 Offset robô: X={offset_x:.3f}m, Y={offset_y:.3f}m")

        # Se sistema de visão está calibrado, recarregar coordenadas com novo offset
        if self.vision_system and hasattr(self.vision_system, 'is_calibrated') and self.vision_system.is_calibrated:
            self.generate_from_vision(self.vision_system)

    # ==================== DEBUG E INFORMAÇÕES ====================

    def get_status(self) -> Dict[str, any]:
        """
        Retorna status das coordenadas para debug.

        Returns:
            Dict com informações de status
        """
        validation = self.validate_coordinates()

        return {
            'total_positions': len(self.coordinates),
            'has_vision_system': self.vision_system is not None,
            'vision_calibrated': self.vision_system.is_calibrated if self.vision_system else False,
            'robot_offset': {'x': self.robot_offset_x, 'y': self.robot_offset_y},
            'validation': validation,
            'sample_coordinates': {
                'pos_0': self.coordinates.get(0),
                'pos_4_center': self.coordinates.get(4),
                'pos_8': self.coordinates.get(8)
            }
        }

    def print_coordinates(self):
        """Imprime todas as coordenadas de forma legível."""
        print("\n" + "="*50)
        print("📍 COORDENADAS DO TABULEIRO")
        print("="*50)

        for i in range(3):
            for j in range(3):
                idx = i * 3 + j
                if idx in self.coordinates:
                    x, y, z = self.coordinates[idx]
                    print(f"Pos {idx}: ({x:+.4f}, {y:+.4f}, {z:.4f})", end="  ")
            print()

        validation = self.validate_coordinates()
        print("="*50)
        print(f"Status: {'✅ VÁLIDO' if validation['valid'] else '❌ INVÁLIDO'}")
        print("="*50 + "\n")

    def __repr__(self) -> str:
        """Representação em string do objeto."""
        return f"BoardCoordinateSystem(positions={len(self.coordinates)}/9, valid={self.has_valid_coordinates()})"
