"""
PoseValidationService - Serviço Único de Validação de Poses

RESPONSABILIDADE ÚNICA:
    Centralizar todas as validações de poses do robô UR.

FUNCIONALIDADES:
    - Validação de formato
    - Validação de workspace (limites cartesianos)
    - Validação de rotação (limites angulares)
    - Validação de alcançabilidade
    - Validação de limites de segurança UR
    - Validação completa multi-camadas
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
from interfaces.robot_interfaces import IRobotValidator
import math
import logging


@dataclass
class ValidationResult:
    """Resultado detalhado de uma validação de pose."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    details: Dict[str, any]

    def __str__(self) -> str:
        status = "✅ VÁLIDA" if self.is_valid else "❌ INVÁLIDA"
        result = f"Validação: {status}\n"

        if self.errors:
            result += f"Erros ({len(self.errors)}):\n"
            for error in self.errors:
                result += f"  - {error}\n"

        if self.warnings:
            result += f"Avisos ({len(self.warnings)}):\n"
            for warning in self.warnings:
                result += f"  - {warning}\n"

        return result


class PoseValidationService(IRobotValidator):
    """
    Serviço centralizado para validação de poses do robô UR.

    Executa validações em múltiplas camadas:
    1. Formato da pose
    2. Limites do workspace (x, y, z)
    3. Limites de rotação (rx, ry, rz)
    4. Alcançabilidade (distância de movimento)
    5. Limites de segurança UR (isPoseWithinSafetyLimits)
    """

    def __init__(self,
                 workspace_limits: Dict[str, float],
                 max_movement_distance: float = 1.0,
                 logger: Optional[logging.Logger] = None):
        """
        Inicializa o serviço de validação.

        Args:
            workspace_limits: Limites do workspace {x_min, x_max, y_min, y_max, z_min, z_max}
            max_movement_distance: Distância máxima de movimento em metros
            logger: Logger opcional para mensagens
        """
        self.workspace_limits = workspace_limits
        self.max_movement_distance = max_movement_distance
        self.logger = logger or logging.getLogger(__name__)

        # Controlador UR para validação de segurança (injetado depois)
        self.ur_controller = None

    # ==================== CONFIGURAÇÃO ====================

    def set_ur_controller(self, controller):
        """
        Injeta o controlador UR para validações de segurança.

        Args:
            controller: Instância do URController
        """
        self.ur_controller = controller

    # ==================== VALIDAÇÃO COMPLETA ====================

    def validate_complete(self, pose: List[float], current_pose: Optional[List[float]] = None) -> ValidationResult:
        """
        Executa validação completa em múltiplas camadas.

        Args:
            pose: Pose a validar [x, y, z, rx, ry, rz]
            current_pose: Pose atual opcional para validação de alcançabilidade

        Returns:
            ValidationResult com resultado detalhado
        """
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            details={}
        )

        self.logger.info(f"🔍 Validando pose: {self._format_pose(pose)}")

        # 1. Validação de formato
        format_result = self._validate_format(pose)
        result.details['format'] = format_result
        if not format_result['valid']:
            result.is_valid = False
            result.errors.extend(format_result['errors'])
            return result  # Não continuar se formato inválido

        # 2. Validação de workspace
        workspace_result = self._validate_workspace(pose)
        result.details['workspace'] = workspace_result
        if not workspace_result['valid']:
            result.is_valid = False
            result.errors.extend(workspace_result['errors'])

        # 3. Validação de rotação
        rotation_result = self._validate_rotation(pose)
        result.details['rotation'] = rotation_result
        if not rotation_result['valid']:
            result.is_valid = False
            result.errors.extend(rotation_result['errors'])
        if rotation_result['warnings']:
            result.warnings.extend(rotation_result['warnings'])

        # 4. Validação de alcançabilidade (se pose atual fornecida)
        if current_pose:
            reachability_result = self._validate_reachability(pose, current_pose)
            result.details['reachability'] = reachability_result
            if not reachability_result['valid']:
                result.is_valid = False
                result.errors.extend(reachability_result['errors'])
            if reachability_result['warnings']:
                result.warnings.extend(reachability_result['warnings'])

        # 5. Validação de segurança UR (se controlador disponível)
        if self.ur_controller and result.is_valid:
            safety_result = self._validate_ur_safety_limits(pose)
            result.details['ur_safety'] = safety_result
            if not safety_result['valid']:
                result.is_valid = False
                result.errors.extend(safety_result['errors'])

        # Log final
        if result.is_valid:
            self.logger.info(f"✅ Pose VALIDADA: {self._format_pose(pose)}")
        else:
            self.logger.warning(f"❌ Pose REJEITADA: {len(result.errors)} erros")
            for error in result.errors:
                self.logger.warning(f"  - {error}")

        return result

    # ==================== VALIDAÇÕES INDIVIDUAIS ====================

    def _validate_format(self, pose: List[float]) -> Dict[str, any]:
        """Valida formato básico da pose."""
        result = {'valid': True, 'errors': []}

        # Verificar se é uma lista
        if not isinstance(pose, (list, tuple)):
            result['valid'] = False
            result['errors'].append(f"Pose deve ser lista/tupla, recebeu {type(pose).__name__}")
            return result

        # Verificar tamanho
        if len(pose) != 6:
            result['valid'] = False
            result['errors'].append(f"Pose deve ter 6 elementos [x,y,z,rx,ry,rz], recebeu {len(pose)}")
            return result

        # Verificar se todos são números
        for i, value in enumerate(pose):
            if not isinstance(value, (int, float)):
                result['valid'] = False
                result['errors'].append(f"Elemento {i} deve ser número, recebeu {type(value).__name__}")

        return result

    def _validate_workspace(self, pose: List[float]) -> Dict[str, any]:
        """Valida se pose está dentro dos limites do workspace."""
        result = {'valid': True, 'errors': []}

        x, y, z = pose[0], pose[1], pose[2]

        # Validar X
        if not (self.workspace_limits['x_min'] <= x <= self.workspace_limits['x_max']):
            result['valid'] = False
            result['errors'].append(
                f"X fora dos limites: {x:.3f}m (válido: {self.workspace_limits['x_min']:.3f} a {self.workspace_limits['x_max']:.3f})"
            )

        # Validar Y
        if not (self.workspace_limits['y_min'] <= y <= self.workspace_limits['y_max']):
            result['valid'] = False
            result['errors'].append(
                f"Y fora dos limites: {y:.3f}m (válido: {self.workspace_limits['y_min']:.3f} a {self.workspace_limits['y_max']:.3f})"
            )

        # Validar Z
        if not (self.workspace_limits['z_min'] <= z <= self.workspace_limits['z_max']):
            result['valid'] = False
            result['errors'].append(
                f"Z fora dos limites: {z:.3f}m (válido: {self.workspace_limits['z_min']:.3f} a {self.workspace_limits['z_max']:.3f})"
            )

        if result['valid']:
            result['position'] = {'x': x, 'y': y, 'z': z}

        return result

    def _validate_rotation(self, pose: List[float]) -> Dict[str, any]:
        """Valida limites de rotação (angle-axis)."""
        result = {'valid': True, 'errors': [], 'warnings': []}

        rx, ry, rz = pose[3], pose[4], pose[5]

        # Calcular magnitude da rotação
        rotation_magnitude = math.sqrt(rx**2 + ry**2 + rz**2)
        result['rotation_magnitude'] = rotation_magnitude

        # Validar magnitude (não pode exceder π)
        if rotation_magnitude > math.pi:
            result['valid'] = False
            result['errors'].append(
                f"Magnitude de rotação muito grande: {rotation_magnitude:.3f} rad > π rad"
            )

        # Avisar se rotação é muito grande (> 2.5 rad)
        elif rotation_magnitude > 2.5:
            result['warnings'].append(
                f"Rotação grande: {rotation_magnitude:.3f} rad (pode causar singularidades)"
            )

        return result

    def _validate_reachability(self, pose: List[float], current_pose: List[float]) -> Dict[str, any]:
        """Valida se pose é alcançável a partir da pose atual."""
        result = {'valid': True, 'errors': [], 'warnings': []}

        # Calcular distância euclidiana
        distance = math.sqrt(
            (pose[0] - current_pose[0])**2 +
            (pose[1] - current_pose[1])**2 +
            (pose[2] - current_pose[2])**2
        )
        result['distance'] = distance

        # Verificar distância máxima
        if distance > self.max_movement_distance:
            result['valid'] = False
            result['errors'].append(
                f"Movimento muito grande: {distance:.3f}m > {self.max_movement_distance:.3f}m"
            )

        # Avisar se movimento é grande (> 50% do máximo)
        elif distance > (self.max_movement_distance * 0.5):
            result['warnings'].append(
                f"Movimento grande: {distance:.3f}m ({distance/self.max_movement_distance*100:.1f}% do máximo)"
            )

        return result

    def _validate_ur_safety_limits(self, pose: List[float]) -> Dict[str, any]:
        """Valida usando isPoseWithinSafetyLimits() do UR."""
        result = {'valid': True, 'errors': []}

        try:
            if not self.ur_controller:
                result['warnings'] = ["Controlador UR não disponível para validação de segurança"]
                return result

            # Usar função oficial do UR RTDE
            is_safe = self.ur_controller.rtde_c.isPoseWithinSafetyLimits(pose)

            if not is_safe:
                result['valid'] = False
                result['errors'].append(
                    "Pose rejeitada pelos limites de segurança do UR (isPoseWithinSafetyLimits)"
                )

            result['ur_validated'] = is_safe

        except Exception as e:
            self.logger.error(f"Erro na validação UR: {e}")
            result['valid'] = False
            result['errors'].append(f"Erro ao validar com UR: {str(e)}")

        return result

    # ==================== VALIDAÇÕES SIMPLIFICADAS ====================

    def validate_format(self, pose: List[float]) -> bool:
        """Validação rápida apenas de formato."""
        result = self._validate_format(pose)
        return result['valid']

    def validate_workspace(self, pose: List[float]) -> bool:
        """Validação rápida apenas de workspace."""
        format_ok = self.validate_format(pose)
        if not format_ok:
            return False

        result = self._validate_workspace(pose)
        return result['valid']

    def validate_reachability(self, pose: List[float], current_pose: List[float]) -> bool:
        """Validação rápida apenas de alcançabilidade."""
        result = self._validate_reachability(pose, current_pose)
        return result['valid']

    # ==================== INTERFACE METHODS (IRobotValidator) ====================

    def validate_pose(self, pose: List[float]) -> Tuple[bool, str]:
        """
        Valida uma pose completa (implementação de IRobotValidator).

        Args:
            pose: Lista de 6 valores [x, y, z, rx, ry, rz]

        Returns:
            Tupla (válido, mensagem_erro)
        """
        result = self.validate_complete(pose)
        error_msg = "\n".join(result.errors) if result.errors else ""
        return (result.is_valid, error_msg)

    def validate_coordinates(self, x: float, y: float, z: float) -> Tuple[bool, str]:
        """
        Valida apenas coordenadas XYZ (implementação de IRobotValidator).

        Args:
            x, y, z: Coordenadas cartesianas

        Returns:
            Tupla (válido, mensagem_erro)
        """
        # Cria pose temporária com coordenadas e orientação padrão
        temp_pose = [x, y, z, 0.0, 0.0, 0.0]
        coord_result = self._validate_workspace(temp_pose)

        if coord_result['valid']:
            return (True, "")
        else:
            errors = coord_result.get('errors', [])
            error_msg = "\n".join(errors) if errors else "Coordenadas fora do workspace"
            return (False, error_msg)

    def validate_orientation(self, rx: float, ry: float, rz: float) -> Tuple[bool, str]:
        """
        Valida apenas orientação/rotação (implementação de IRobotValidator).

        Args:
            rx, ry, rz: Ângulos de rotação

        Returns:
            Tupla (válido, mensagem_erro)
        """
        # Cria pose temporária com orientação e coordenadas padrão
        temp_pose = [0.0, 0.0, 0.0, rx, ry, rz]
        rotation_result = self._validate_rotation(temp_pose)

        if rotation_result['valid']:
            return (True, "")
        else:
            errors = rotation_result.get('errors', [])
            error_msg = "\n".join(errors) if errors else "Orientação inválida"
            return (False, error_msg)

    def check_reachability(self, pose: List[float]) -> bool:
        """
        Verifica se o robô pode alcançar a pose (implementação de IRobotValidator).

        Args:
            pose: Lista de 6 valores [x, y, z, rx, ry, rz]

        Returns:
            True se alcançável, False caso contrário
        """
        if self.ur_controller:
            current_pose = self.ur_controller.get_current_pose()
            if current_pose:
                return self.validate_reachability(pose, current_pose)
        return True  # Se não tem controller, assume como alcançável

    def check_safety_limits(self, pose: List[float]) -> Tuple[bool, str]:
        """
        Verifica limites de segurança (implementação de IRobotValidator).

        Args:
            pose: Lista de 6 valores [x, y, z, rx, ry, rz]

        Returns:
            Tupla (seguro, mensagem_alerta)
        """
        safety_result = self._validate_ur_safety_limits(pose)

        if safety_result['valid']:
            return (True, "")
        else:
            errors = safety_result.get('errors', [])
            error_msg = "\n".join(errors) if errors else "Pose fora dos limites de segurança"
            return (False, error_msg)

    # ==================== UTILITÁRIOS ====================

    def _format_pose(self, pose: List[float]) -> str:
        """Formata pose para log."""
        if len(pose) != 6:
            return str(pose)
        return f"[{pose[0]:.3f}, {pose[1]:.3f}, {pose[2]:.3f}, {pose[3]:.3f}, {pose[4]:.3f}, {pose[5]:.3f}]"

    def get_workspace_info(self) -> Dict[str, any]:
        """Retorna informações sobre o workspace configurado."""
        return {
            'x_range': (self.workspace_limits['x_min'], self.workspace_limits['x_max']),
            'y_range': (self.workspace_limits['y_min'], self.workspace_limits['y_max']),
            'z_range': (self.workspace_limits['z_min'], self.workspace_limits['z_max']),
            'x_span': self.workspace_limits['x_max'] - self.workspace_limits['x_min'],
            'y_span': self.workspace_limits['y_max'] - self.workspace_limits['y_min'],
            'z_span': self.workspace_limits['z_max'] - self.workspace_limits['z_min'],
            'max_movement_distance': self.max_movement_distance
        }

    def __repr__(self) -> str:
        """Representação em string do serviço."""
        return f"PoseValidationService(workspace={self.workspace_limits}, max_dist={self.max_movement_distance}m)"
