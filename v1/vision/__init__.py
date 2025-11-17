#!/usr/bin/env python3
"""
VISION MODULE - INICIALIZAÇÃO
============================
Módulo de visão ArUco integrado ao robotics_project

Este módulo fornece:
- Sistema completo de detecção ArUco
- Gerenciamento de câmera
- Interface visual para monitoramento
- Integração com as configurações do projeto

Uso básico:
    from vision import ArUcoVisionSystem, CameraManager
    
    # Usa automaticamente CONFIG['visao'] da config_completa.py
    vision_system = ArUcoVisionSystem()
    camera_manager = CameraManager()
"""

# Importações principais do módulo
from .aruco_vision import ArUcoVisionSystem, MarkerInfo
from config.config_completa import ConfigVisao
from .camera_manager import CameraManager, CameraInfo  
from .visual_monitor import VisualMonitor
from .vision_logger import VisionLogger

# Versão do módulo
__version__ = "1.0.0"

# Metadados
__author__ = "Robotics Project Team"
__description__ = "Sistema de visão ArUco integrado"

# Exports públicos
__all__ = [
    'ArUcoVisionSystem',
    'MarkerInfo', 
    'CameraManager',
    'CameraInfo',
    'VisualMonitor', 
    'VisionLogger',
    'ConfigVisao'
]

# Função de conveniência para inicialização rápida
def create_vision_system():
    """
    Cria e retorna uma instância completa do sistema de visão
    
    Returns:
        tuple: (vision_system, camera_manager, visual_monitor)
    """
    # Importar configurações do projeto
    from config.config_completa import CONFIG
    
    # Criar componentes usando configurações integradas
    config_visao = ConfigVisao()
    vision_system = ArUcoVisionSystem()
    camera_manager = CameraManager()
    visual_monitor = VisualMonitor(vision_system)
    
    return vision_system, camera_manager, visual_monitor

# Função para verificar se o sistema está pronto
def check_system_health():
    """
    Verifica se todos os componentes do sistema de visão estão funcionais
    
    Returns:
        dict: Status de cada componente
    """
    try:
        # Importar configurações
        from config.config_completa import CONFIG
        config_visao = CONFIG['visao']
        
        # Verificar configurações básicas
        health_status = {
            'config_loaded': True,
            'camera_index_valid': isinstance(config_visao.camera_index, int),
            'marker_groups_configured': (
                len(config_visao.reference_ids) >= 2 and
                len(config_visao.group1_ids) >= 1 and
                len(config_visao.group2_ids) >= 1
            ),
            'opencv_available': True,  # Será verificado na importação
            'system_ready': False
        }
        
        # Verificar se pode inicializar sistema básico
        try:
            vision_system = ArUcoVisionSystem()
            health_status['aruco_system'] = True
        except Exception as e:
            health_status['aruco_system'] = False
            health_status['aruco_error'] = str(e)
        
        # Determinar status geral
        health_status['system_ready'] = all([
            health_status['config_loaded'],
            health_status['camera_index_valid'], 
            health_status['marker_groups_configured'],
            health_status.get('aruco_system', False)
        ])
        
        return health_status
        
    except Exception as e:
        return {
            'config_loaded': False,
            'error': str(e),
            'system_ready': False
        }

# Verificação na importação
try:
    import cv2
    import numpy as np
    _OPENCV_AVAILABLE = True
except ImportError as e:
    _OPENCV_AVAILABLE = False
    print(f"⚠️ Aviso: OpenCV não disponível - {e}")
    print("💡 Instale com: pip install opencv-python")

# Informações de debug se necessário
if __name__ == "__main__":
    print("🔍 === DIAGNÓSTICO DO MÓDULO VISION ===")
    print(f"Versão: {__version__}")
    print(f"OpenCV disponível: {_OPENCV_AVAILABLE}")
    
    health = check_system_health()
    print("\n📊 Status do sistema:")
    for key, value in health.items():
        status = "✅" if value else "❌"
        print(f"  {status} {key}: {value}")
    
    if health['system_ready']:
        print("\n🚀 Sistema pronto para uso!")
    else:
        print("\n⚠️ Sistema precisa de configuração adicional")