"""
Robot Interfaces - Contratos de Interfaces para o Sistema Robótico
==================================================================
Define interfaces abstratas para todos os componentes principais:
- IRobotController: Controlador do robô UR
- IRobotValidator: Validação de poses e segurança
- IGameService: Serviço principal de gerenciamento do robô
- IBoardCoordinateSystem: Sistema de coordenadas do tabuleiro
- IDiagnostics: Sistema de diagnósticos e estatísticas
- IVisionSystem: Sistema de visão ArUco
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum


# ========== TIPOS E ENUMS ==========

class RobotStatus(Enum):
    """Estados possíveis do robô."""
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    READY = "ready"
    MOVING = "moving"
    ERROR = "error"
    EMERGENCY_STOP = "emergency_stop"


# ========== INTERFACE: ROBOT CONTROLLER ==========

class IRobotController(ABC):
    """
    Interface para controladores de robô.
    Define operações de baixo nível para comunicação e controle do robô.
    """

    @abstractmethod
    def connect(self) -> bool:
        """
        Conecta ao robô.

        Returns:
            True se conectado com sucesso, False caso contrário
        """
        pass

    @abstractmethod
    def disconnect(self):
        """Desconecta do robô e libera recursos."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """
        Verifica se está conectado ao robô.

        Returns:
            True se conectado, False caso contrário
        """
        pass

    @abstractmethod
    def move_to_pose(self, pose: List[float], velocity: float = 0.5,
                     acceleration: float = 0.3, asynchronous: bool = False) -> bool:
        """
        Move o robô para uma pose específica.

        Args:
            pose: Lista de 6 valores [x, y, z, rx, ry, rz]
            velocity: Velocidade do movimento (0.0-1.0)
            acceleration: Aceleração do movimento (0.0-1.0)
            asynchronous: Se True, retorna imediatamente sem esperar

        Returns:
            True se movimento executado com sucesso, False caso contrário
        """
        pass

    @abstractmethod
    def get_current_pose(self) -> Optional[List[float]]:
        """
        Obtém a pose atual do robô.

        Returns:
            Lista de 6 valores [x, y, z, rx, ry, rz] ou None se erro
        """
        pass

    @abstractmethod
    def get_current_joints(self) -> Optional[List[float]]:
        """
        Obtém os ângulos atuais das juntas do robô.

        Returns:
            Lista de 6 valores de ângulos ou None se erro
        """
        pass

    @abstractmethod
    def stop_movement(self):
        """Para qualquer movimento do robô imediatamente."""
        pass

    @abstractmethod
    def emergency_stop(self):
        """Executa parada de emergência do robô."""
        pass


# ========== INTERFACE: ROBOT VALIDATOR ==========

class IRobotValidator(ABC):
    """
    Interface para validadores de poses e segurança do robô.
    Define operações de validação antes de executar movimentos.
    """

    @abstractmethod
    def validate_pose(self, pose: List[float]) -> Tuple[bool, str]:
        """
        Valida uma pose completa do robô.

        Args:
            pose: Lista de 6 valores [x, y, z, rx, ry, rz]

        Returns:
            Tupla (válido, mensagem_erro)
        """
        pass

    @abstractmethod
    def validate_coordinates(self, x: float, y: float, z: float) -> Tuple[bool, str]:
        """
        Valida apenas coordenadas XYZ.

        Args:
            x, y, z: Coordenadas cartesianas

        Returns:
            Tupla (válido, mensagem_erro)
        """
        pass

    @abstractmethod
    def validate_orientation(self, rx: float, ry: float, rz: float) -> Tuple[bool, str]:
        """
        Valida apenas orientação (rotação).

        Args:
            rx, ry, rz: Ângulos de rotação

        Returns:
            Tupla (válido, mensagem_erro)
        """
        pass

    @abstractmethod
    def check_reachability(self, pose: List[float]) -> bool:
        """
        Verifica se o robô pode alcançar a pose.

        Args:
            pose: Lista de 6 valores [x, y, z, rx, ry, rz]

        Returns:
            True se alcançável, False caso contrário
        """
        pass

    @abstractmethod
    def check_safety_limits(self, pose: List[float]) -> Tuple[bool, str]:
        """
        Verifica se a pose está dentro dos limites de segurança.

        Args:
            pose: Lista de 6 valores [x, y, z, rx, ry, rz]

        Returns:
            Tupla (seguro, mensagem_alerta)
        """
        pass


# ========== INTERFACE: GAME SERVICE ==========

class IGameService(ABC):
    """
    Interface para serviços de gerenciamento do robô no jogo.
    Define operações de alto nível para controle do robô.
    """

    @abstractmethod
    def initialize(self) -> bool:
        """
        Inicializa o serviço do robô.

        Returns:
            True se inicializado com sucesso, False caso contrário
        """
        pass

    @abstractmethod
    def shutdown(self):
        """Finaliza o serviço e libera recursos."""
        pass

    @abstractmethod
    def get_status(self) -> RobotStatus:
        """
        Obtém o status atual do serviço.

        Returns:
            Estado do robô (RobotStatus)
        """
        pass

    @abstractmethod
    def move_to_board_position(self, position: int) -> bool:
        """
        Move o robô para uma posição do tabuleiro (0-8).

        Args:
            position: Posição no tabuleiro (0-8)

        Returns:
            True se movimento executado com sucesso, False caso contrário
        """
        pass

    @abstractmethod
    def place_piece(self, position: int, player: str) -> bool:
        """
        Coloca uma peça em uma posição do tabuleiro.

        Args:
            position: Posição no tabuleiro (0-8)
            player: Identificador do jogador

        Returns:
            True se peça colocada com sucesso, False caso contrário
        """
        pass

    @abstractmethod
    def move_piece(self, from_position: int, to_position: int) -> bool:
        """
        Move uma peça de uma posição para outra.

        Args:
            from_position: Posição de origem (0-8)
            to_position: Posição de destino (0-8)

        Returns:
            True se peça movida com sucesso, False caso contrário
        """
        pass

    @abstractmethod
    def return_to_home(self) -> bool:
        """
        Retorna o robô para a posição home.

        Returns:
            True se retornado com sucesso, False caso contrário
        """
        pass


# ========== INTERFACE: BOARD COORDINATE SYSTEM ==========

class IBoardCoordinateSystem(ABC):
    """
    Interface para sistemas de coordenadas do tabuleiro.
    Define operações de mapeamento entre posições lógicas e físicas.
    """

    @abstractmethod
    def get_pose_for_position(self, position: int) -> Optional[List[float]]:
        """
        Obtém a pose do robô para uma posição do tabuleiro.

        Args:
            position: Posição no tabuleiro (0-8)

        Returns:
            Lista de 6 valores [x, y, z, rx, ry, rz] ou None se inválido
        """
        pass

    @abstractmethod
    def set_pose_for_position(self, position: int, pose: List[float]) -> bool:
        """
        Define a pose do robô para uma posição do tabuleiro.

        Args:
            position: Posição no tabuleiro (0-8)
            pose: Lista de 6 valores [x, y, z, rx, ry, rz]

        Returns:
            True se definido com sucesso, False caso contrário
        """
        pass

    @abstractmethod
    def is_position_valid(self, position: int) -> bool:
        """
        Verifica se uma posição do tabuleiro é válida.

        Args:
            position: Posição a verificar

        Returns:
            True se válida (0-8), False caso contrário
        """
        pass

    @abstractmethod
    def get_all_positions(self) -> Dict[int, List[float]]:
        """
        Obtém todas as poses mapeadas do tabuleiro.

        Returns:
            Dicionário {posição: pose}
        """
        pass

    @abstractmethod
    def calibrate_board(self, reference_poses: Dict[int, List[float]]) -> bool:
        """
        Calibra o sistema de coordenadas com poses de referência.

        Args:
            reference_poses: Dicionário com poses de referência

        Returns:
            True se calibrado com sucesso, False caso contrário
        """
        pass

    @abstractmethod
    def save_calibration(self, filename: str) -> bool:
        """
        Salva calibração em arquivo.

        Args:
            filename: Nome do arquivo para salvar

        Returns:
            True se salvo com sucesso, False caso contrário
        """
        pass

    @abstractmethod
    def load_calibration(self, filename: str) -> bool:
        """
        Carrega calibração de arquivo.

        Args:
            filename: Nome do arquivo para carregar

        Returns:
            True se carregado com sucesso, False caso contrário
        """
        pass


# ========== INTERFACE: DIAGNOSTICS ==========

class IDiagnostics(ABC):
    """
    Interface para sistemas de diagnósticos e estatísticas.
    Define operações de monitoramento e análise do sistema.
    """

    @abstractmethod
    def register_movement(self, movement_data: Dict[str, Any]):
        """
        Registra um movimento executado.

        Args:
            movement_data: Dicionário com dados do movimento
        """
        pass

    @abstractmethod
    def register_validation(self, validation_data: Dict[str, Any]):
        """
        Registra uma validação executada.

        Args:
            validation_data: Dicionário com dados da validação
        """
        pass

    @abstractmethod
    def get_movement_statistics(self) -> Dict[str, Any]:
        """
        Obtém estatísticas de movimentos.

        Returns:
            Dicionário com estatísticas
        """
        pass

    @abstractmethod
    def generate_safety_report(self) -> Dict[str, Any]:
        """
        Gera relatório de segurança do sistema.

        Returns:
            Dicionário com relatório de segurança
        """
        pass

    @abstractmethod
    def reset_statistics(self):
        """Reseta todas as estatísticas coletadas."""
        pass

    @abstractmethod
    def export_history(self, filename: str) -> bool:
        """
        Exporta histórico de operações para arquivo.

        Args:
            filename: Nome do arquivo para exportar

        Returns:
            True se exportado com sucesso, False caso contrário
        """
        pass


# ========== INTERFACE: VISION SYSTEM ==========

class IVisionSystem(ABC):
    """
    Interface para sistemas de visão computacional.
    Define operações de captura, detecção e calibração de visão.
    """

    @abstractmethod
    def initialize(self) -> bool:
        """
        Inicializa o sistema de visão.

        Returns:
            True se inicializado com sucesso, False caso contrário
        """
        pass

    @abstractmethod
    def shutdown(self):
        """Finaliza o sistema de visão e libera recursos."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Verifica se o sistema de visão está disponível.

        Returns:
            True se disponível, False caso contrário
        """
        pass

    @abstractmethod
    def is_calibrated(self) -> bool:
        """
        Verifica se o sistema está calibrado.

        Returns:
            True se calibrado, False caso contrário
        """
        pass

    @abstractmethod
    def capture_frame(self) -> Optional[Any]:
        """
        Captura um frame da câmera.

        Returns:
            Frame capturado ou None se erro
        """
        pass

    @abstractmethod
    def detect_markers(self, frame: Any) -> Dict[str, Any]:
        """
        Detecta marcadores no frame.

        Args:
            frame: Frame a processar

        Returns:
            Dicionário com detecções
        """
        pass

    @abstractmethod
    def get_board_positions(self) -> Dict[int, Any]:
        """
        Obtém posições detectadas no tabuleiro.

        Returns:
            Dicionário {posição: informação}
        """
        pass

    @abstractmethod
    def calibrate(self, reference_data: Dict[str, Any]) -> bool:
        """
        Calibra o sistema de visão.

        Args:
            reference_data: Dados de referência para calibração

        Returns:
            True se calibrado com sucesso, False caso contrário
        """
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Obtém status completo do sistema de visão.

        Returns:
            Dicionário com informações de status
        """
        pass
