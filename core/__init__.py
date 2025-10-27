"""
Core Package - Componentes fundamentais do sistema
Inclui Dependency Injection Container e Service Provider
"""

from .dependency_injection import Container
from .service_provider import ServiceProvider

__all__ = ['Container', 'ServiceProvider']
