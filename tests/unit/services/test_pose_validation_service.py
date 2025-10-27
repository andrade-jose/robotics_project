"""
Testes Unitários para PoseValidationService
Tests for the pose validation service with 5 validation layers.
"""

import pytest
from typing import List

from services.pose_validation_service import PoseValidationService, ValidationResult


class TestPoseValidationServiceInitialization:
    """Testes de inicialização do serviço de validação."""

    def test_init_with_workspace_limits(self, workspace_limits):
        """Testa inicialização com limites de workspace."""
        validator = PoseValidationService(workspace_limits)

        assert validator.workspace_limits == workspace_limits
        assert validator.workspace_limits['x'] == (-0.5, 0.5)
        assert validator.workspace_limits['y'] == (-0.5, 0.5)
        assert validator.workspace_limits['z'] == (0.0, 0.8)

    def test_init_with_ur_limits(self, workspace_limits, safe_ur_limits):
        """Testa inicialização com limites UR."""
        validator = PoseValidationService(workspace_limits, safe_ur_limits)

        assert validator.ur_limits == safe_ur_limits
        assert validator.ur_limits['rx'] == (-3.15, 3.15)


class TestPoseFormatValidation:
    """Testes de validação de formato de pose (Layer 1)."""

    @pytest.fixture
    def validator(self, workspace_limits):
        return PoseValidationService(workspace_limits)

    def test_valid_pose_format(self, validator, valid_pose):
        """Testa pose com formato válido (6 elementos)."""
        result = validator.validate_format(valid_pose)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_invalid_pose_too_short(self, validator):
        """Testa pose com poucos elementos."""
        invalid_pose = [0.3, 0.2, 0.5]  # Faltam rx, ry, rz

        result = validator.validate_format(invalid_pose)

        assert result.is_valid is False
        assert len(result.errors) > 0
        assert "formato" in result.errors[0].lower() or "6 elementos" in result.errors[0].lower()

    def test_invalid_pose_too_long(self, validator):
        """Testa pose com muitos elementos."""
        invalid_pose = [0.3, 0.2, 0.5, 0, 0, 0, 0, 0]  # Elementos extras

        result = validator.validate_format(invalid_pose)

        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_invalid_pose_none(self, validator):
        """Testa pose None."""
        result = validator.validate_format(None)

        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_invalid_pose_empty_list(self, validator):
        """Testa lista vazia."""
        result = validator.validate_format([])

        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_invalid_pose_non_numeric(self, validator):
        """Testa pose com valores não numéricos."""
        invalid_pose = [0.3, "abc", 0.5, 0, 0, 0]

        result = validator.validate_format(invalid_pose)

        assert result.is_valid is False


class TestWorkspaceValidation:
    """Testes de validação de workspace (Layer 2)."""

    @pytest.fixture
    def validator(self, workspace_limits):
        return PoseValidationService(workspace_limits)

    def test_pose_inside_workspace(self, validator, valid_pose):
        """Testa pose dentro do workspace."""
        result = validator.validate_workspace(valid_pose)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_pose_x_out_of_bounds_high(self, validator):
        """Testa pose com x acima do limite."""
        pose = [0.6, 0.2, 0.5, 0, 0, 0]  # x = 0.6, limite é 0.5

        result = validator.validate_workspace(pose)

        assert result.is_valid is False
        assert any("x" in err.lower() for err in result.errors)

    def test_pose_x_out_of_bounds_low(self, validator):
        """Testa pose com x abaixo do limite."""
        pose = [-0.6, 0.2, 0.5, 0, 0, 0]  # x = -0.6, limite é -0.5

        result = validator.validate_workspace(pose)

        assert result.is_valid is False
        assert any("x" in err.lower() for err in result.errors)

    def test_pose_y_out_of_bounds(self, validator):
        """Testa pose com y fora dos limites."""
        pose = [0.3, 0.6, 0.5, 0, 0, 0]  # y = 0.6, limite é 0.5

        result = validator.validate_workspace(pose)

        assert result.is_valid is False
        assert any("y" in err.lower() for err in result.errors)

    def test_pose_z_out_of_bounds(self, validator):
        """Testa pose com z fora dos limites."""
        pose = [0.3, 0.2, 0.9, 0, 0, 0]  # z = 0.9, limite é 0.8

        result = validator.validate_workspace(pose)

        assert result.is_valid is False
        assert any("z" in err.lower() for err in result.errors)

    def test_pose_at_boundary_min(self, validator):
        """Testa pose exatamente no limite mínimo."""
        pose = [-0.5, -0.5, 0.0, 0, 0, 0]

        result = validator.validate_workspace(pose)

        assert result.is_valid is True

    def test_pose_at_boundary_max(self, validator):
        """Testa pose exatamente no limite máximo."""
        pose = [0.5, 0.5, 0.8, 0, 0, 0]

        result = validator.validate_workspace(pose)

        assert result.is_valid is True

    def test_multiple_coordinates_out_of_bounds(self, validator):
        """Testa pose com múltiplas coordenadas fora dos limites."""
        pose = [0.6, 0.6, 0.9, 0, 0, 0]  # x, y, z todos fora

        result = validator.validate_workspace(pose)

        assert result.is_valid is False
        assert len(result.errors) >= 3  # Deve reportar todos os erros


class TestOrientationValidation:
    """Testes de validação de orientação (Layer 3)."""

    @pytest.fixture
    def validator(self, workspace_limits, safe_ur_limits):
        return PoseValidationService(workspace_limits, safe_ur_limits)

    def test_valid_orientation(self, validator):
        """Testa orientação válida."""
        pose = [0.3, 0.2, 0.5, 0, 0, 0]

        result = validator.validate_orientation(pose)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_orientation_rx_out_of_bounds(self, validator):
        """Testa orientação rx fora dos limites."""
        pose = [0.3, 0.2, 0.5, 4.0, 0, 0]  # rx = 4.0, limite é 3.15

        result = validator.validate_orientation(pose)

        assert result.is_valid is False
        assert any("rx" in err.lower() or "rotação" in err.lower() for err in result.errors)

    def test_orientation_at_limit(self, validator):
        """Testa orientação exatamente no limite."""
        pose = [0.3, 0.2, 0.5, 3.14, 3.14, 3.14]

        result = validator.validate_orientation(pose)

        assert result.is_valid is True

    def test_orientation_warnings_for_extreme_angles(self, validator):
        """Testa warnings para ângulos extremos mas válidos."""
        pose = [0.3, 0.2, 0.5, 3.0, 3.0, 3.0]

        result = validator.validate_orientation(pose)

        # Pode ser válido mas com warnings
        assert result.is_valid is True
        # Pode ter warnings sobre ângulos extremos


class TestCompleteValidation:
    """Testes de validação completa (todas as camadas)."""

    @pytest.fixture
    def validator(self, workspace_limits, safe_ur_limits):
        return PoseValidationService(workspace_limits, safe_ur_limits)

    def test_completely_valid_pose(self, validator, valid_pose):
        """Testa pose completamente válida em todas as camadas."""
        result = validator.validate_complete(valid_pose)

        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.pose == valid_pose

    def test_invalid_format_fails_early(self, validator):
        """Testa que formato inválido falha antes de validar workspace."""
        invalid_pose = [0.3, 0.2]  # Formato inválido

        result = validator.validate_complete(invalid_pose)

        assert result.is_valid is False
        # Deve ter erro de formato
        assert any("formato" in err.lower() or "elementos" in err.lower() for err in result.errors)

    def test_valid_format_but_out_of_workspace(self, validator):
        """Testa formato válido mas fora do workspace."""
        pose = [1.5, 0.2, 0.5, 0, 0, 0]  # Formato OK, mas x fora

        result = validator.validate_complete(pose)

        assert result.is_valid is False
        assert any("x" in err.lower() or "workspace" in err.lower() for err in result.errors)

    def test_accumulates_multiple_errors(self, validator):
        """Testa que múltiplos erros são acumulados."""
        pose = [1.5, 1.5, 1.5, 5.0, 5.0, 5.0]  # Múltiplos erros

        result = validator.validate_complete(pose)

        assert result.is_valid is False
        assert len(result.errors) >= 2  # Pelo menos workspace + orientação


class TestValidationResult:
    """Testes da classe ValidationResult."""

    def test_validation_result_creation(self):
        """Testa criação de ValidationResult."""
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=["Ângulo extremo"],
            pose=[0.3, 0.2, 0.5, 0, 0, 0]
        )

        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 1
        assert result.pose is not None

    def test_validation_result_with_errors(self):
        """Testa ValidationResult com erros."""
        result = ValidationResult(
            is_valid=False,
            errors=["X fora do workspace", "Z muito alto"],
            warnings=[],
            pose=None
        )

        assert result.is_valid is False
        assert len(result.errors) == 2
        assert result.pose is None


class TestPoseValidationHelperMethods:
    """Testes de métodos auxiliares."""

    @pytest.fixture
    def validator(self, workspace_limits):
        return PoseValidationService(workspace_limits)

    def test_validate_pose_wrapper(self, validator, valid_pose):
        """Testa método validate_pose (wrapper para validate_complete)."""
        result = validator.validate_pose(valid_pose)

        assert result.is_valid is True

    def test_validate_coordinates_only(self, validator):
        """Testa validação apenas de coordenadas XYZ."""
        result = validator.validate_coordinates([0.3, 0.2, 0.5])

        assert result.is_valid is True

    def test_validate_coordinates_out_of_bounds(self, validator):
        """Testa validação de coordenadas fora dos limites."""
        result = validator.validate_coordinates([1.5, 0.2, 0.5])

        assert result.is_valid is False


class TestEdgeCases:
    """Testes de casos extremos."""

    @pytest.fixture
    def validator(self, workspace_limits):
        return PoseValidationService(workspace_limits)

    def test_pose_with_infinities(self, validator):
        """Testa pose com valores infinitos."""
        pose = [float('inf'), 0.2, 0.5, 0, 0, 0]

        result = validator.validate_complete(pose)

        assert result.is_valid is False

    def test_pose_with_nan(self, validator):
        """Testa pose com NaN."""
        pose = [0.3, float('nan'), 0.5, 0, 0, 0]

        result = validator.validate_complete(pose)

        assert result.is_valid is False

    def test_very_small_workspace(self):
        """Testa comportamento com workspace muito pequeno."""
        tiny_limits = {
            'x': (0.0, 0.01),
            'y': (0.0, 0.01),
            'z': (0.0, 0.01),
        }
        validator = PoseValidationService(tiny_limits)

        valid_pose = [0.005, 0.005, 0.005, 0, 0, 0]
        result = validator.validate_workspace(valid_pose)

        assert result.is_valid is True

    def test_negative_workspace(self):
        """Testa workspace com coordenadas negativas."""
        negative_limits = {
            'x': (-1.0, -0.5),
            'y': (-1.0, -0.5),
            'z': (-1.0, -0.5),
        }
        validator = PoseValidationService(negative_limits)

        valid_pose = [-0.7, -0.7, -0.7, 0, 0, 0]
        result = validator.validate_workspace(valid_pose)

        assert result.is_valid is True


class TestSafetyChecks:
    """Testes de verificações de segurança."""

    @pytest.fixture
    def validator(self, workspace_limits, safe_ur_limits):
        return PoseValidationService(workspace_limits, safe_ur_limits)

    def test_check_safety_limits(self, validator, valid_pose):
        """Testa verificação de limites de segurança."""
        result = validator.check_safety_limits(valid_pose)

        assert result.is_valid is True

    def test_safety_limits_violation(self, validator):
        """Testa violação de limites de segurança."""
        unsafe_pose = [0.3, 0.2, 0.5, 5.0, 5.0, 5.0]  # Orientações extremas

        result = validator.check_safety_limits(unsafe_pose)

        assert result.is_valid is False

    def test_check_reachability(self, validator, valid_pose):
        """Testa verificação de alcançabilidade."""
        result = validator.check_reachability(valid_pose)

        # Deve retornar resultado de validação
        assert isinstance(result, ValidationResult)
