"""
Service Provider
================
Provider centralizado que configura e fornece acesso a todos os serviços do sistema.

Responsabilidades:
- Configurar o container DI com todos os serviços
- Fornecer métodos convenientes para acessar serviços
- Gerenciar ciclo de vida dos serviços
"""

from typing import Optional
import logging

from .dependency_injection import Container
from interfaces.robot_interfaces import (
    IRobotController,
    IRobotValidator,
    IGameService,
    IBoardCoordinateSystem,
    IDiagnostics,
    IVisionSystem
)


class ServiceProvider:
    """
    Provider centralizado de serviços do sistema.

    Configura o container DI e fornece acesso fácil a todos os serviços.

    Exemplo de uso:
    ```python
    provider = ServiceProvider()
    robot = provider.get_robot_controller()
    validator = provider.get_validator()
    ```
    """

    def __init__(self, config_file: Optional[str] = None):
        """
        Inicializa o service provider.

        Args:
            config_file: Caminho para arquivo de configuração (opcional)
        """
        self.container = Container()
        self.config_file = config_file
        self.logger = logging.getLogger('ServiceProvider')

        # Registra todos os serviços
        self._register_services()

        self.logger.info("ServiceProvider inicializado")

    def _register_services(self):
        """
        Registra todos os serviços do sistema no container.

        Esta é a configuração central de DI do sistema.
        """
        # Importações locais para evitar ciclos de dependência
        from logic_control.ur_controller import URController
        from services.pose_validation_service import PoseValidationService
        from services.robot_service import RobotService
        from services.board_coordinate_system import BoardCoordinateSystem
        from diagnostics.robot_diagnostics import RobotDiagnostics
        from config.config_completa import ConfigRobo

        self.logger.debug("Registrando serviços...")

        # ===== CONFIGURAÇÃO =====
        # Registra configuração como singleton
        config = ConfigRobo()
        self.container.register_instance(ConfigRobo, config)

        # ===== INFRAESTRUTURA - Robot Controller =====
        # Singleton: apenas uma conexão com o robô
        def create_ur_controller(container: Container) -> URController:
            config = container.resolve(ConfigRobo)
            return URController(config)

        self.container.register(
            IRobotController,
            factory=create_ur_controller,
            singleton=True
        )

        # ===== DOMAIN - Validators =====
        # Singleton: validador pode ser compartilhado
        def create_pose_validator(container: Container) -> PoseValidationService:
            config = container.resolve(ConfigRobo)
            return PoseValidationService(
                workspace_limits=config.limites_workspace,
                max_movement_distance=config.distancia_maxima_movimento
            )

        self.container.register(
            IRobotValidator,
            factory=create_pose_validator,
            singleton=True
        )

        # ===== DOMAIN - Board Coordinate System =====
        # Singleton: sistema de coordenadas único
        def create_board_coords(container: Container) -> BoardCoordinateSystem:
            return BoardCoordinateSystem()

        self.container.register(
            IBoardCoordinateSystem,
            factory=create_board_coords,
            singleton=True
        )

        # ===== DIAGNOSTICS =====
        # Singleton: estatísticas centralizadas
        def create_diagnostics(container: Container) -> RobotDiagnostics:
            return RobotDiagnostics()

        self.container.register(
            IDiagnostics,
            factory=create_diagnostics,
            singleton=True
        )

        # ===== APPLICATION - Robot Service =====
        # Singleton: serviço principal do robô
        def create_robot_service(container: Container) -> RobotService:
            config_file = self.config_file
            return RobotService(config_file=config_file)

        self.container.register(
            IGameService,
            factory=create_robot_service,
            singleton=True
        )

        # ===== VISION SYSTEM =====
        # Registra apenas se visão estiver disponível
        try:
            from vision.aruco_vision import ArucoVision

            def create_vision_system(container: Container) -> ArucoVision:
                return ArucoVision()

            self.container.register(
                IVisionSystem,
                factory=create_vision_system,
                singleton=True
            )
            self.logger.debug("Sistema de visão registrado")
        except ImportError:
            self.logger.warning("Sistema de visão não disponível")

        self.logger.info(
            f"Serviços registrados: {len(self.container.get_registered_services())}"
        )

    # ===== MÉTODOS CONVENIENTES =====

    def get_robot_controller(self) -> IRobotController:
        """
        Retorna o controlador do robô.

        Returns:
            Implementação de IRobotController
        """
        return self.container.resolve(IRobotController)

    def get_validator(self) -> IRobotValidator:
        """
        Retorna o validador de poses.

        Returns:
            Implementação de IRobotValidator
        """
        return self.container.resolve(IRobotValidator)

    def get_robot_service(self) -> IGameService:
        """
        Retorna o serviço principal do robô.

        Returns:
            Implementação de IGameService
        """
        return self.container.resolve(IGameService)

    def get_board_coordinates(self) -> IBoardCoordinateSystem:
        """
        Retorna o sistema de coordenadas do tabuleiro.

        Returns:
            Implementação de IBoardCoordinateSystem
        """
        return self.container.resolve(IBoardCoordinateSystem)

    def get_diagnostics(self) -> IDiagnostics:
        """
        Retorna o sistema de diagnósticos.

        Returns:
            Implementação de IDiagnostics
        """
        return self.container.resolve(IDiagnostics)

    def get_vision_system(self) -> Optional[IVisionSystem]:
        """
        Retorna o sistema de visão (se disponível).

        Returns:
            Implementação de IVisionSystem ou None se não disponível
        """
        try:
            return self.container.resolve(IVisionSystem)
        except ValueError:
            return None

    def get_config(self) -> 'ConfigRobo':
        """
        Retorna a configuração do sistema.

        Returns:
            Instância de ConfigRobo
        """
        from config.config_completa import ConfigRobo
        return self.container.resolve(ConfigRobo)

    def shutdown(self):
        """Finaliza todos os serviços e limpa o container."""
        self.logger.info("Finalizando ServiceProvider...")

        # Tenta finalizar RobotService se existir
        try:
            robot_service = self.get_robot_service()
            if hasattr(robot_service, 'shutdown'):
                robot_service.shutdown()
        except:
            pass

        # Limpa container
        self.container.clear()
        self.logger.info("ServiceProvider finalizado")

    def __repr__(self) -> str:
        """Representação em string do service provider."""
        return f"ServiceProvider({self.container})"
