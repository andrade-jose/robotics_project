"""
Dependency Injection Container
==============================
Sistema simples de injeção de dependência para o projeto.

Funcionalidades:
- Registro de serviços (transient ou singleton)
- Resolução automática de dependências
- Suporte a interfaces/abstrações
- Factory functions para criação customizada
"""

from typing import Dict, Type, Any, Callable, Optional
import inspect
import logging


class Container:
    """
    Container de Injeção de Dependência.

    Gerencia o ciclo de vida de serviços e suas dependências,
    permitindo desacoplamento entre componentes.

    Exemplo de uso:
    ```python
    container = Container()

    # Registrar serviços
    container.register(IRobotController, URController, singleton=True)
    container.register(IVisionSystem, ArucoVision, singleton=False)

    # Resolver dependências
    robot = container.resolve(IRobotController)
    ```
    """

    def __init__(self):
        """Inicializa o container vazio."""
        self._services: Dict[Type, Callable] = {}
        self._singletons: Dict[Type, Any] = {}
        self._singleton_flags: Dict[Type, bool] = {}
        self._factories: Dict[Type, Callable] = {}
        self.logger = logging.getLogger('DI.Container')

    def register(
        self,
        interface: Type,
        implementation: Optional[Callable] = None,
        singleton: bool = True,
        factory: Optional[Callable] = None
    ):
        """
        Registra um serviço no container.

        Args:
            interface: Interface ou tipo abstrato
            implementation: Implementação concreta (opcional se factory fornecido)
            singleton: Se True, cria apenas uma instância (default: True)
            factory: Função factory customizada para criar a instância

        Raises:
            ValueError: Se nem implementation nem factory forem fornecidos
        """
        if implementation is None and factory is None:
            raise ValueError("Deve fornecer implementation ou factory")

        if factory:
            self._factories[interface] = factory
        else:
            self._services[interface] = implementation

        self._singleton_flags[interface] = singleton

        if singleton:
            self._singletons[interface] = None  # Será criado sob demanda

        self.logger.debug(
            f"Registrado: {interface.__name__} -> "
            f"{'Factory' if factory else implementation.__name__} "
            f"(singleton={singleton})"
        )

    def register_instance(self, interface: Type, instance: Any):
        """
        Registra uma instância já criada como singleton.

        Args:
            interface: Interface ou tipo
            instance: Instância já criada
        """
        self._singletons[interface] = instance
        self._singleton_flags[interface] = True
        self.logger.debug(f"Registrada instância: {interface.__name__}")

    def resolve(self, interface: Type) -> Any:
        """
        Resolve uma dependência, criando instância se necessário.

        Args:
            interface: Interface ou tipo a resolver

        Returns:
            Instância do serviço

        Raises:
            ValueError: Se o serviço não estiver registrado
        """
        # Verifica se é singleton e já foi criado
        if self._singleton_flags.get(interface) and self._singletons.get(interface):
            self.logger.debug(f"Retornando singleton existente: {interface.__name__}")
            return self._singletons[interface]

        # Cria nova instância
        instance = self._create_instance(interface)

        # Armazena se for singleton
        if self._singleton_flags.get(interface):
            self._singletons[interface] = instance
            self.logger.debug(f"Singleton criado e armazenado: {interface.__name__}")

        return instance

    def _create_instance(self, interface: Type) -> Any:
        """
        Cria uma nova instância do serviço.

        Args:
            interface: Interface ou tipo

        Returns:
            Nova instância

        Raises:
            ValueError: Se o serviço não estiver registrado
        """
        # Verifica se tem factory
        if interface in self._factories:
            self.logger.debug(f"Criando via factory: {interface.__name__}")
            return self._factories[interface](self)

        # Verifica se tem implementação registrada
        if interface not in self._services:
            raise ValueError(f"Serviço não registrado: {interface.__name__}")

        implementation = self._services[interface]

        self.logger.debug(f"Criando instância: {implementation.__name__}")

        # Tenta resolver dependências do construtor automaticamente
        try:
            sig = inspect.signature(implementation.__init__)
            dependencies = {}

            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue

                # Se tem type annotation, tenta resolver
                if param.annotation != inspect.Parameter.empty:
                    try:
                        dependencies[param_name] = self.resolve(param.annotation)
                        self.logger.debug(
                            f"  Dependência resolvida: {param_name} -> "
                            f"{param.annotation.__name__}"
                        )
                    except ValueError:
                        # Se não conseguir resolver, usa valor default se houver
                        if param.default != inspect.Parameter.empty:
                            dependencies[param_name] = param.default
                        # Se não tem default e não é obrigatório, pula
                        elif param.default != inspect.Parameter.empty:
                            pass

            # Cria instância com dependências resolvidas
            instance = implementation(**dependencies)
            return instance

        except Exception as e:
            self.logger.error(
                f"Erro ao criar instância de {implementation.__name__}: {e}"
            )
            # Fallback: tenta criar sem argumentos
            try:
                return implementation()
            except:
                raise ValueError(
                    f"Não foi possível criar instância de {implementation.__name__}: {e}"
                )

    def is_registered(self, interface: Type) -> bool:
        """
        Verifica se um serviço está registrado.

        Args:
            interface: Interface ou tipo

        Returns:
            True se registrado, False caso contrário
        """
        return (
            interface in self._services or
            interface in self._factories or
            interface in self._singletons
        )

    def clear(self):
        """Limpa todos os serviços registrados e instâncias."""
        self._services.clear()
        self._singletons.clear()
        self._singleton_flags.clear()
        self._factories.clear()
        self.logger.debug("Container limpo")

    def get_registered_services(self) -> list:
        """
        Retorna lista de todos os serviços registrados.

        Returns:
            Lista de interfaces/tipos registrados
        """
        return list(set(
            list(self._services.keys()) +
            list(self._factories.keys()) +
            list(self._singletons.keys())
        ))

    def __repr__(self) -> str:
        """Representação em string do container."""
        services_count = len(self.get_registered_services())
        singletons_count = sum(1 for v in self._singletons.values() if v is not None)
        return (
            f"Container(services={services_count}, "
            f"singletons_created={singletons_count})"
        )
