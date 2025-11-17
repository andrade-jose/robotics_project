"""
Diagnostics Package - Diagnósticos e Estatísticas do Sistema
Componentes para monitoramento, análise e relatórios do sistema robótico
"""

from .robot_diagnostics import RobotDiagnostics
from .ur_diagnostics import URDiagnostics

__all__ = ['RobotDiagnostics', 'URDiagnostics']
