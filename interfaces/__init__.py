"""
Interfaces Package - Contratos e Abstrações
Componentes de interfaces e protocolos para o sistema robótico
"""

from .robot_interfaces import (
    IRobotController,
    IRobotValidator,
    IGameService,
    IBoardCoordinateSystem,
    IDiagnostics,
    IVisionSystem
)

__all__ = [
    'IRobotController',
    'IRobotValidator',
    'IGameService',
    'IBoardCoordinateSystem',
    'IDiagnostics',
    'IVisionSystem'
]
