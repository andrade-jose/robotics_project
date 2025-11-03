"""
Pytest Configuration and Shared Fixtures
Configuração global do pytest e fixtures compartilhadas entre todos os testes.
"""

import pytest
import sys
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import Mock, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# ============================================================================
# FIXTURES: Workspace e Configurações
# ============================================================================

@pytest.fixture
def workspace_limits() -> Dict[str, tuple]:
    """Limites padrão do workspace do robô UR."""
    return {
        'x': (-0.5, 0.5),
        'y': (-0.5, 0.5),
        'z': (0.0, 0.8),
    }


@pytest.fixture
def safe_ur_limits() -> Dict[str, tuple]:
    """Limites de segurança para robô UR."""
    return {
        'x': (-0.6, 0.6),
        'y': (-0.6, 0.6),
        'z': (-0.1, 0.9),
        'rx': (-3.15, 3.15),
        'ry': (-3.15, 3.15),
        'rz': (-3.15, 3.15),
    }


@pytest.fixture
def board_config() -> Dict:
    """Configuração padrão do tabuleiro Tapatan."""
    return {
        'size': 3,  # 3x3 grid
        'positions': 9,
        'center_x': 0.3,
        'center_y': -0.2,
        'spacing': 0.05,  # 5cm between positions
        'z_height': 0.15,  # Height above table
    }


@pytest.fixture
def config_robo():
    """Configuração real do robô UR3e."""
    from config.config_completa import ConfigRobo
    return ConfigRobo()


# ============================================================================
# FIXTURES: Poses e Coordenadas
# ============================================================================

@pytest.fixture
def valid_pose() -> List[float]:
    """Pose válida dentro do workspace."""
    return [0.3, 0.2, 0.5, 0, 0, 0]


@pytest.fixture
def invalid_pose_out_of_bounds() -> List[float]:
    """Pose fora dos limites do workspace."""
    return [1.5, 0.2, 0.5, 0, 0, 0]  # x muito grande


@pytest.fixture
def invalid_pose_format() -> List[float]:
    """Pose com formato inválido."""
    return [0.3, 0.2]  # Faltam elementos


@pytest.fixture
def home_pose() -> List[float]:
    """Pose de home padrão."""
    return [0.0, -0.4, 0.4, 0, 0, 0]


@pytest.fixture
def sample_board_positions() -> Dict[int, List[float]]:
    """Posições do tabuleiro (0-8) mapeadas para poses 3D."""
    base_z = 0.15
    spacing = 0.05
    center_x = 0.3
    center_y = -0.2

    positions = {}
    for row in range(3):
        for col in range(3):
            pos_num = row * 3 + col
            x = center_x + (col - 1) * spacing
            y = center_y + (row - 1) * spacing
            positions[pos_num] = [x, y, base_z, 0, 0, 0]

    return positions


# ============================================================================
# FIXTURES: Mocks de Hardware
# ============================================================================

@pytest.fixture
def mock_rtde_control():
    """Mock do RTDE Control Interface."""
    mock = MagicMock()
    mock.moveL.return_value = True
    mock.moveJ.return_value = True
    mock.getActualTCPPose.return_value = [0.3, 0.2, 0.5, 0, 0, 0]
    mock.getActualQ.return_value = [0, -1.57, 1.57, 0, 0, 0]
    mock.stopScript.return_value = True
    mock.disconnect.return_value = None
    mock.isConnected.return_value = True
    return mock


@pytest.fixture
def mock_rtde_receive():
    """Mock do RTDE Receive Interface."""
    mock = MagicMock()
    mock.getActualTCPPose.return_value = [0.3, 0.2, 0.5, 0, 0, 0]
    mock.getActualQ.return_value = [0, -1.57, 1.57, 0, 0, 0]
    mock.getActualTCPSpeed.return_value = [0, 0, 0, 0, 0, 0]
    mock.getRobotMode.return_value = 7  # RUNNING mode
    mock.getSafetyMode.return_value = 1  # NORMAL mode
    mock.isConnected.return_value = True
    mock.disconnect.return_value = None
    return mock


@pytest.fixture
def mock_camera():
    """Mock de câmera OpenCV."""
    mock = MagicMock()
    mock.isOpened.return_value = True
    mock.read.return_value = (True, None)  # Success, frame
    mock.release.return_value = None
    mock.get.return_value = 640  # Width/Height
    return mock


@pytest.fixture
def mock_aruco_detector():
    """Mock do detector ArUco."""
    mock = MagicMock()
    # Simula detecção de 4 marcadores (cantos do tabuleiro)
    mock.detectMarkers.return_value = (
        [[[100, 100], [200, 100], [200, 200], [100, 200]]] * 4,  # corners
        [0, 1, 2, 3],  # IDs
        None  # rejected
    )
    return mock


# ============================================================================
# FIXTURES: Mocks de Serviços
# ============================================================================

@pytest.fixture
def mock_robot_controller():
    """Mock do IRobotController."""
    mock = Mock()
    mock.connect.return_value = True
    mock.disconnect.return_value = True
    mock.is_connected.return_value = True
    mock.move_to_pose.return_value = True
    mock.get_current_pose.return_value = [0.3, 0.2, 0.5, 0, 0, 0]
    mock.stop_movement.return_value = True
    mock.emergency_stop.return_value = True
    mock.get_joint_positions.return_value = [0, -1.57, 1.57, 0, 0, 0]
    return mock


@pytest.fixture
def mock_validator():
    """Mock do IRobotValidator (PoseValidationService)."""
    from services.pose_validation_service import ValidationResult

    mock = Mock()
    mock.validate_complete.return_value = ValidationResult(
        is_valid=True,
        errors=[],
        warnings=[],
        pose=[0.3, 0.2, 0.5, 0, 0, 0]
    )
    mock.validate_pose.return_value = ValidationResult(
        is_valid=True,
        errors=[],
        warnings=[],
        pose=[0.3, 0.2, 0.5, 0, 0, 0]
    )
    return mock


@pytest.fixture
def mock_board_coords():
    """Mock do IBoardCoordinateSystem."""
    mock = Mock()
    mock.get_position.return_value = [0.3, 0.2, 0.15, 0, 0, 0]
    mock.is_position_valid.return_value = True
    mock.get_all_positions.return_value = {i: [0.3, 0.2, 0.15, 0, 0, 0] for i in range(9)}
    mock.save_positions.return_value = True
    mock.load_positions.return_value = True
    return mock


@pytest.fixture
def mock_vision_system():
    """Mock do IVisionSystem."""
    mock = Mock()
    mock.calibrate.return_value = True
    mock.is_calibrated.return_value = True
    mock.detect_markers.return_value = [
        {'id': 0, 'corners': [[100, 100], [200, 100], [200, 200], [100, 200]]},
        {'id': 1, 'corners': [[300, 100], [400, 100], [400, 200], [300, 200]]},
    ]
    mock.calculate_positions.return_value = {i: [0.3, 0.2, 0.15] for i in range(9)}
    mock.start.return_value = True
    mock.stop.return_value = True
    return mock


# ============================================================================
# FIXTURES: Dados de Teste
# ============================================================================

@pytest.fixture
def sample_game_state() -> List[int]:
    """Estado de jogo de exemplo."""
    # 0 = vazio, 1 = jogador 1, 2 = jogador 2
    return [
        1, 0, 2,
        0, 1, 0,
        2, 0, 1
    ]


@pytest.fixture
def empty_board() -> List[int]:
    """Tabuleiro vazio."""
    return [0] * 9


@pytest.fixture
def winning_state_player1() -> List[int]:
    """Estado de vitória para jogador 1 (linha horizontal)."""
    return [
        1, 1, 1,
        0, 2, 0,
        2, 0, 0
    ]


# ============================================================================
# HOOKS: Setup e Teardown
# ============================================================================

def pytest_configure(config):
    """Configuração executada antes de todos os testes."""
    print("\n[SETUP] Configurando ambiente de testes...")


def pytest_unconfigure(config):
    """Cleanup executado após todos os testes."""
    print("\n[TEARDOWN] Limpando ambiente de testes...")


# ============================================================================
# MARKERS: Configurações de Markers
# ============================================================================

def pytest_collection_modifyitems(config, items):
    """Modifica items coletados para adicionar markers automaticamente."""
    for item in items:
        # Adiciona marker 'unit' para testes em tests/unit/
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Adiciona marker 'integration' para testes em tests/integration/
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
