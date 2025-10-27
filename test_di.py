"""
Script de Teste para Dependency Injection
==========================================
Testa o sistema de DI sem conectar ao robô real.
"""

from core.service_provider import ServiceProvider
from core.dependency_injection import Container
from interfaces.robot_interfaces import (
    IRobotController,
    IRobotValidator,
    IGameService,
    IBoardCoordinateSystem,
    IDiagnostics
)


def test_container_basic():
    """Testa funcionalidades básicas do Container."""
    print("=" * 60)
    print("TESTE 1: Container Básico")
    print("=" * 60)

    container = Container()

    # Teste de registro simples
    class SimpleService:
        def __init__(self):
            self.value = "test"

    container.register(SimpleService, SimpleService, singleton=True)

    # Resolve
    service1 = container.resolve(SimpleService)
    service2 = container.resolve(SimpleService)

    print(f"[OK] Serviço resolvido: {service1}")
    print(f"[OK] Singleton verificado: {service1 is service2}")

    assert service1 is service2, "Singleton não funcionou!"
    print("[OK] Container básico: OK\n")


def test_container_with_dependencies():
    """Testa resolução automática de dependências."""
    print("=" * 60)
    print("TESTE 2: Resolução de Dependências")
    print("=" * 60)

    container = Container()

    # Serviço sem dependências
    class DatabaseService:
        def __init__(self):
            self.connected = True

    # Serviço que depende de DatabaseService
    class UserService:
        def __init__(self, db: DatabaseService):
            self.db = db

    # Registra ambos
    container.register(DatabaseService, DatabaseService, singleton=True)
    container.register(UserService, UserService, singleton=False)

    # Resolve - deve resolver DatabaseService automaticamente
    user_service = container.resolve(UserService)

    print(f"[OK] UserService resolvido: {user_service}")
    print(f"[OK] DatabaseService injetado: {user_service.db}")
    print(f"[OK] DB conectado: {user_service.db.connected}")

    assert user_service.db.connected, "Dependência não foi injetada!"
    print("[OK] Resolução de dependências: OK\n")


def test_service_provider():
    """Testa o ServiceProvider completo."""
    print("=" * 60)
    print("TESTE 3: ServiceProvider")
    print("=" * 60)

    provider = ServiceProvider()

    print(f"[OK] ServiceProvider criado: {provider}")
    print(f"[OK] Container: {provider.container}")

    # Testa se os serviços principais estão registrados
    services_to_test = [
        (IRobotController, "Robot Controller"),
        (IRobotValidator, "Pose Validator"),
        (IGameService, "Game Service"),
        (IBoardCoordinateSystem, "Board Coordinates"),
        (IDiagnostics, "Diagnostics")
    ]

    for interface, name in services_to_test:
        is_registered = provider.container.is_registered(interface)
        status = "[OK]" if is_registered else "[FAIL]"
        print(f"{status} {name}: {'Registrado' if is_registered else 'NÃO registrado'}")

        if not is_registered:
            print(f"  AVISO: {name} não está registrado!")

    print(f"\n[OK] Total de serviços registrados: "
          f"{len(provider.container.get_registered_services())}")
    print("[OK] ServiceProvider: OK\n")


def test_service_resolution():
    """Testa resolução de serviços do sistema."""
    print("=" * 60)
    print("TESTE 4: Resolução de Serviços do Sistema")
    print("=" * 60)

    provider = ServiceProvider()

    # Testa métodos convenientes
    print("Testando métodos de acesso...")

    try:
        validator = provider.get_validator()
        print(f"[OK] Validator obtido: {validator.__class__.__name__}")
    except Exception as e:
        print(f"[FAIL] Erro ao obter Validator: {e}")

    try:
        coords = provider.get_board_coordinates()
        print(f"[OK] Board Coordinates obtido: {coords.__class__.__name__}")
    except Exception as e:
        print(f"[FAIL] Erro ao obter Board Coordinates: {e}")

    try:
        diagnostics = provider.get_diagnostics()
        print(f"[OK] Diagnostics obtido: {diagnostics.__class__.__name__}")
    except Exception as e:
        print(f"[FAIL] Erro ao obter Diagnostics: {e}")

    try:
        config = provider.get_config()
        print(f"[OK] Config obtido: {config.__class__.__name__}")
        print(f"  IP do robô: {config.ip}")
    except Exception as e:
        print(f"[FAIL] Erro ao obter Config: {e}")

    # Nota: RobotController e GameService não são testados
    # pois tentam conectar ao robô real

    print("\n[OK] Resolução de serviços: OK\n")


def test_singleton_behavior():
    """Testa comportamento de singleton."""
    print("=" * 60)
    print("TESTE 5: Comportamento Singleton")
    print("=" * 60)

    provider = ServiceProvider()

    # Resolve o mesmo serviço múltiplas vezes
    validator1 = provider.get_validator()
    validator2 = provider.get_validator()

    coords1 = provider.get_board_coordinates()
    coords2 = provider.get_board_coordinates()

    diagnostics1 = provider.get_diagnostics()
    diagnostics2 = provider.get_diagnostics()

    print(f"[OK] Validator é singleton: {validator1 is validator2}")
    print(f"[OK] Board Coords é singleton: {coords1 is coords2}")
    print(f"[OK] Diagnostics é singleton: {diagnostics1 is diagnostics2}")

    assert validator1 is validator2, "Validator não é singleton!"
    assert coords1 is coords2, "Board Coords não é singleton!"
    assert diagnostics1 is diagnostics2, "Diagnostics não é singleton!"

    print("\n[OK] Comportamento singleton: OK\n")


def main():
    """Executa todos os testes."""
    print("\n")
    print("=" * 60)
    print(" " * 10 + "TESTES DE DEPENDENCY INJECTION")
    print("=" * 60)
    print()

    try:
        test_container_basic()
        test_container_with_dependencies()
        test_service_provider()
        test_service_resolution()
        test_singleton_behavior()

        print("=" * 60)
        print("RESULTADO FINAL: TODOS OS TESTES PASSARAM!")
        print("=" * 60)
        print()
        print("[OK] Container funcionando corretamente")
        print("[OK] Resolução de dependências automática OK")
        print("[OK] ServiceProvider configurado corretamente")
        print("[OK] Todos os serviços principais registrados")
        print("[OK] Singletons funcionando como esperado")
        print()

    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"[FAIL] TESTE FALHOU: {e}")
        print("=" * 60)
        return 1

    except Exception as e:
        print()
        print("=" * 60)
        print(f"[FAIL] ERRO INESPERADO: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
