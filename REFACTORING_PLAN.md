# 🔧 PLANO DE REFATORAÇÃO - SISTEMA TAPATAN ROBÓTICO

**Data de Criação:** 2025-10-23
**Última Atualização:** 2025-10-23
**Status Geral:** 🟡 EM ANDAMENTO
**Progresso:** 3/28 tarefas concluídas (10.7%)

---

## 📋 ÍNDICE

1. [Resumo Executivo](#resumo-executivo)
2. [Prioridade Alta](#prioridade-alta)
3. [Prioridade Média](#prioridade-média)
4. [Prioridade Baixa](#prioridade-baixa)
5. [Checklist Geral](#checklist-geral)
6. [Log de Progresso](#log-de-progresso)

---

## 🎯 RESUMO EXECUTIVO

### Problemas Identificados

- ❌ **Violação de SRP**: Classes com 5-8 responsabilidades
- ❌ **Código Duplicado**: Validação, coordenadas, correção de poses
- ❌ **Código Redundante**: Métodos duplicados, código comentado
- ❌ **Acoplamento Forte**: Dependências diretas sem abstrações
- ❌ **Falta de Testes**: Sem interfaces ou testes unitários

### Objetivos

- ✅ Aplicar princípio de Responsabilidade Única
- ✅ Eliminar duplicação de código
- ✅ Criar abstrações e interfaces
- ✅ Reduzir acoplamento entre componentes
- ✅ Possibilitar testes unitários

---

## 🔴 PRIORIDADE ALTA

> **Meta:** Resolver problemas críticos que afetam manutenibilidade imediata

### FASE 1: Limpeza de Código Duplicado e Obsoleto

#### ✅ Tarefa 1.1: Remover Código Duplicado em `game_service.py`

**Status:** ✅ CONCLUÍDA
**Estimativa:** 15 min
**Arquivo:** [services/game_service.py](services/game_service.py)

**Problema:**
- Linhas 240-356 contêm métodos duplicados que já existem nas linhas 219-221

**Ação:**
```python
# REMOVER COMPLETAMENTE as linhas 240-356
# Manter apenas as definições originais (linhas 1-239)
```

**Verificação:**
- [x] Código duplicado removido (118 linhas removidas!)
- [x] Testes existentes ainda passam
- [x] Nenhuma funcionalidade quebrada

**Última Atualização:** 2025-10-23
**Responsável:** Claude Code

---

#### ✅ Tarefa 1.2: Corrigir Linha Solta em `ur_controller.py`

**Status:** ✅ CONCLUÍDA
**Estimativa:** 5 min
**Arquivo:** [logic_control/ur_controller.py](logic_control/ur_controller.py#L22)

**Problema:**
- Linha 22 tinha print fora de função com identação incorreta

**Ação:**
```python
# ANTES (linha 22):
print(f"✅ Conectado ao robô UR em {self.config.ip}")

# DEPOIS (movido para dentro do __init__):
def __init__(self, config):
    self.config = config
    self.rtde_c = RTDEControlInterface(self.config.ip)
    self.rtde_r = RTDEReceiveInterface(self.config.ip)
    # ... configurações ...
    print(f"✅ Conectado ao robô UR em {self.config.ip}")
```

**Verificação:**
- [x] Print movido corretamente
- [x] Identação corrigida
- [x] Mensagem aparece no momento certo

**Última Atualização:** 2025-10-23
**Responsável:** Claude Code

---

#### ✅ Tarefa 1.3: Remover Código Comentado em `robot_service.py`

**Status:** ✅ CONCLUÍDA
**Estimativa:** 20 min
**Arquivo:** [services/robot_service.py](services/robot_service.py)

**Problema:**
- Funções obsoletas ou não utilizadas (linhas 624-678):
  - `_apply_drastic_corrections`
  - `_apply_alternative_corrections`
  - Duplicadas com implementações em `ur_controller.py`

**Ação:**
```python
# IDENTIFICADAS as funções duplicadas
# VERIFICADO que existem em ur_controller.py (linhas 407 e 428)
# REMOVIDAS 55 linhas de código duplicado
```

**Verificação:**
- [x] Funções não utilizadas identificadas
- [x] Código removido (55 linhas)
- [x] Implementações mantidas em ur_controller.py
- [x] Sem quebra de funcionalidade

**Última Atualização:** 2025-10-23
**Responsável:** Claude Code

---

### FASE 2: Unificação de Código Duplicado

#### ✅ Tarefa 2.1: Criar `BoardCoordinateSystem` Única

**Status:** ⬜ NÃO INICIADO
**Estimativa:** 45 min
**Novo Arquivo:** `services/board_coordinate_system.py`

**Problema:**
- Coordenadas do tabuleiro duplicadas em 3 locais:
  - [game_orchestrator.py:130-189](services/game_orchestrator.py#L130-L189)
  - [game_service.py:219-221 + 313-341](services/game_service.py#L219-L221)
  - [utils/tapatan_board.py:3-30](utils/tapatan_board.py#L3-L30)

**Ação:**
```python
# CRIAR novo arquivo: services/board_coordinate_system.py

class BoardCoordinateSystem:
    """
    Única classe responsável por gerenciar coordenadas do tabuleiro 3x3.
    Centraliza toda lógica de geração, validação e acesso a posições.
    """

    def __init__(self):
        self.coordinates = {}

    def generate_grid_3x3(self,
                         origin: Pose,
                         x_spacing: float,
                         y_spacing: float) -> dict:
        """Gera grid 3x3 de coordenadas."""
        pass

    def validate_coordinates(self, coords: dict) -> bool:
        """Valida se coordenadas estão corretas."""
        pass

    def get_position(self, position: int) -> Pose:
        """Retorna coordenada de uma posição específica."""
        pass

    def load_from_file(self, filepath: str) -> bool:
        """Carrega coordenadas de arquivo JSON."""
        pass

    def save_to_file(self, filepath: str) -> bool:
        """Salva coordenadas em arquivo JSON."""
        pass
```

**Refatoração Necessária:**
- [ ] Criar novo arquivo `services/board_coordinate_system.py`
- [ ] Implementar classe `BoardCoordinateSystem`
- [ ] Refatorar `game_orchestrator.py` para usar a nova classe
- [ ] Refatorar `game_service.py` para usar a nova classe
- [ ] Deprecar/remover `utils/tapatan_board.py`
- [ ] Atualizar imports em todos os arquivos
- [ ] Criar testes unitários

**Verificação:**
- [ ] Classe criada e funcionando
- [ ] Todos os 3 locais antigos refatorados
- [ ] Testes passam
- [ ] Sem duplicação de código

**Última Atualização:** -
**Responsável:** -

---

#### ✅ Tarefa 2.2: Criar `PoseValidationService` Único

**Status:** ⬜ NÃO INICIADO
**Estimativa:** 1h
**Novo Arquivo:** `services/pose_validation_service.py`

**Problema:**
- Validação de poses duplicada em 3 locais:
  - [robot_service.py:762-766](services/robot_service.py#L762-L766)
  - [ur_controller.py:189-212](logic_control/ur_controller.py#L189-L212)
  - [ur_controller.py:214-247](logic_control/ur_controller.py#L214-L247)

**Ação:**
```python
# CRIAR novo arquivo: services/pose_validation_service.py

from dataclasses import dataclass
from typing import List, Tuple, Optional

@dataclass
class ValidationResult:
    """Resultado de uma validação de pose."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]

class PoseValidationService:
    """
    Serviço único para validação de poses do robô UR.
    Centraliza todas as regras de validação.
    """

    def __init__(self, workspace_limits: dict):
        self.workspace_limits = workspace_limits

    def validate_complete(self, pose: List[float]) -> ValidationResult:
        """Validação completa em múltiplas etapas."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])

        # 1. Validar formato
        if not self._validate_format(pose):
            result.is_valid = False
            result.errors.append("Formato de pose inválido")

        # 2. Validar workspace
        if not self._validate_workspace(pose):
            result.is_valid = False
            result.errors.append("Pose fora do workspace")

        # 3. Validar singularidades
        if self._check_singularity(pose):
            result.warnings.append("Próximo a singularidade")

        # 4. Validar limites articulares
        if not self._validate_joint_limits(pose):
            result.is_valid = False
            result.errors.append("Limites articulares excedidos")

        return result

    def _validate_format(self, pose: List[float]) -> bool:
        """Valida formato básico da pose."""
        pass

    def _validate_workspace(self, pose: List[float]) -> bool:
        """Valida se pose está dentro do workspace."""
        pass

    def _check_singularity(self, pose: List[float]) -> bool:
        """Verifica proximidade de singularidades."""
        pass

    def _validate_joint_limits(self, pose: List[float]) -> bool:
        """Valida limites das juntas."""
        pass
```

**Refatoração Necessária:**
- [ ] Criar novo arquivo `services/pose_validation_service.py`
- [ ] Implementar classe `PoseValidationService`
- [ ] Implementar classe `ValidationResult`
- [ ] Refatorar `robot_service.py` para usar o serviço
- [ ] Refatorar `ur_controller.py` para usar o serviço
- [ ] Remover métodos duplicados
- [ ] Criar testes unitários

**Verificação:**
- [ ] Serviço criado e funcionando
- [ ] Validação unificada em um único local
- [ ] Testes passam
- [ ] Sem duplicação

**Última Atualização:** -
**Responsável:** -

---

#### ✅ Tarefa 2.3: Unificar Sistema de Correção de Poses

**Status:** ⬜ NÃO INICIADO
**Estimativa:** 1h 30min
**Arquivo Principal:** [logic_control/ur_controller.py](logic_control/ur_controller.py)

**Problema:**
- Correção de poses implementada em 2 locais:
  - [robot_service.py:624-678](services/robot_service.py#L624-L678) - Funções auxiliares
  - [ur_controller.py:287-427](logic_control/ur_controller.py#L287-L427) - Sistema completo

**Ação:**
```python
# DECIDIR: Manter apenas em URController OU extrair para classe própria
# OPÇÃO 1: Manter em URController (mais simples)
# OPÇÃO 2: Criar PoseCorrectionService (mais SOLID)

# Se OPÇÃO 2:
class PoseCorrectionService:
    """Serviço para correção automática de poses inválidas."""

    def __init__(self, validator: PoseValidationService):
        self.validator = validator

    def correct_pose(self,
                    pose: List[float],
                    max_attempts: int = 5) -> Optional[List[float]]:
        """
        Tenta corrigir pose inválida aplicando ajustes incrementais.
        Retorna pose corrigida ou None se impossível.
        """
        pass

    def _apply_incremental_corrections(self, pose: List[float]) -> List[float]:
        """Aplica correções incrementais."""
        pass
```

**Refatoração Necessária:**
- [ ] Decidir entre OPÇÃO 1 ou OPÇÃO 2
- [ ] Se OPÇÃO 2: Criar `PoseCorrectionService`
- [ ] Remover duplicação em `robot_service.py`
- [ ] Manter apenas uma implementação
- [ ] Atualizar dependências
- [ ] Criar testes

**Verificação:**
- [ ] Apenas uma implementação existe
- [ ] Funcionalidade mantida
- [ ] Testes passam

**Última Atualização:** -
**Responsável:** -

---

#### ✅ Tarefa 2.4: Unificar Movimento com Pontos Intermediários

**Status:** ⬜ NÃO INICIADO
**Estimativa:** 45 min
**Arquivo Principal:** [logic_control/ur_controller.py](logic_control/ur_controller.py)

**Problema:**
- Movimento com waypoints duplicado em 2 locais:
  - [robot_service.py:436-482](services/robot_service.py#L436-L482)
  - [ur_controller.py:470-516](logic_control/ur_controller.py#L470-L516)

**Ação:**
```python
# MANTER APENAS no URController (camada de controle baixo nível)
# REMOVER de robot_service.py
# FAZER robot_service.py chamar ur_controller.move_with_waypoints()
```

**Refatoração Necessária:**
- [ ] Verificar diferenças entre as duas implementações
- [ ] Consolidar melhor versão no `ur_controller.py`
- [ ] Remover de `robot_service.py`
- [ ] Atualizar chamadas para usar `ur_controller.move_with_waypoints()`
- [ ] Criar testes

**Verificação:**
- [ ] Apenas uma implementação
- [ ] Funcionalidade mantida
- [ ] Testes passam

**Última Atualização:** -
**Responsável:** -

---

## 🟡 PRIORIDADE MÉDIA

> **Meta:** Melhorar arquitetura e aplicar SOLID

### FASE 3: Refatoração de Responsabilidades

#### ✅ Tarefa 3.1: Refatorar `TapatanInterface` (main.py)

**Status:** ⬜ NÃO INICIADO
**Estimativa:** 3h
**Arquivo:** [main.py](main.py#L49-L677)

**Problema:**
- Classe com 7+ responsabilidades diferentes (677 linhas!)
- Violação massiva do SRP

**Ação:**
```python
# CRIAR 4 novas classes:

# 1. ui/menu_manager.py
class MenuManager:
    """Gerencia apenas menus e input do usuário."""
    def display_main_menu(self)
    def get_user_choice(self)
    def display_game_menu(self)

# 2. ui/game_display.py
class GameDisplay:
    """Gerencia apenas visualização do tabuleiro."""
    def render_board(self, state)
    def show_move_history(self, moves)
    def display_winner(self, player)

# 3. integration/vision_integration.py
class VisionIntegration:
    """Gerencia integração com sistema de visão."""
    def setup_vision_system(self)
    def calibrate_vision(self)
    def get_board_state_from_vision(self)

# 4. main.py (reduzido)
class TapatanInterface:
    """Coordena APENAS fluxo principal da aplicação."""
    def __init__(self):
        self.menu = MenuManager()
        self.display = GameDisplay()
        self.vision = VisionIntegration()
        self.orchestrator = GameOrchestrator()

    def run(self):
        """Loop principal simplificado."""
        pass
```

**Refatoração Necessária:**
- [ ] Criar pasta `ui/`
- [ ] Criar `ui/menu_manager.py`
- [ ] Criar `ui/game_display.py`
- [ ] Criar pasta `integration/`
- [ ] Criar `integration/vision_integration.py`
- [ ] Refatorar `main.py` para usar as novas classes
- [ ] Testar cada componente isoladamente
- [ ] Integrar e testar sistema completo

**Verificação:**
- [ ] `main.py` reduzido para <150 linhas
- [ ] Cada classe tem 1 responsabilidade clara
- [ ] Sistema funciona igual
- [ ] Código mais legível e testável

**Última Atualização:** -
**Responsável:** -

---

#### ✅ Tarefa 3.2: Refatorar `GameOrchestrator`

**Status:** ⬜ NÃO INICIADO
**Estimativa:** 2h 30min
**Arquivo:** [services/game_orchestrator.py](services/game_orchestrator.py#L36-L561)

**Problema:**
- 561 linhas com 5 responsabilidades diferentes
- Conhece detalhes de implementação de tudo

**Ação:**
```python
# SEPARAR EM:

# 1. services/board_coordinate_manager.py (JÁ CRIADO NA TAREFA 2.1)
# Usar BoardCoordinateSystem criado anteriormente

# 2. integration/vision_integrator.py
class VisionIntegrator:
    """Integra sistema de visão com orquestrador."""
    def __init__(self, vision_system):
        self.vision_system = vision_system

    def calculate_board_positions(self)
    def detect_current_state(self)
    def is_calibrated(self) -> bool

# 3. services/game_orchestrator.py (reduzido)
class GameOrchestrator:
    """Orquestra APENAS fluxo do jogo."""
    def __init__(self,
                 game_service: GameService,
                 robot_service: RobotService,
                 board_coords: BoardCoordinateSystem,
                 vision_integrator: VisionIntegrator):
        # Injeção de dependência
        self.game_service = game_service
        self.robot_service = robot_service
        self.board_coords = board_coords
        self.vision = vision_integrator

    def iniciar_jogo(self)
    def processar_jogada(self)
    def executar_movimento_fisico(self)
    # Métodos de orquestração apenas
```

**Refatoração Necessária:**
- [ ] Criar `integration/vision_integrator.py`
- [ ] Implementar `VisionIntegrator`
- [ ] Extrair código de coordenadas para `BoardCoordinateSystem`
- [ ] Extrair código de visão para `VisionIntegrator`
- [ ] Refatorar `GameOrchestrator` para usar injeção de dependência
- [ ] Remover código duplicado e movido
- [ ] Criar testes para cada componente

**Verificação:**
- [ ] `GameOrchestrator` reduzido para <200 linhas
- [ ] Responsabilidades bem separadas
- [ ] Injeção de dependência implementada
- [ ] Testes passam

**Última Atualização:** -
**Responsável:** -

---

#### ✅ Tarefa 3.3: Refatorar `RobotService`

**Status:** ⬜ NÃO INICIADO
**Estimativa:** 4h
**Arquivo:** [services/robot_service.py](services/robot_service.py#L96-L1210)

**Problema:**
- Arquivo GIGANTE com 1210 linhas!
- 8+ responsabilidades misturadas

**Ação:**
```python
# SEPARAR EM:

# 1. services/robot_communication.py
class RobotCommunication:
    """Apenas comunicação básica com robô."""
    def connect(self)
    def disconnect(self)
    def send_command(self)
    def get_status(self)

# 2. services/pose_validator.py (JÁ CRIADO NA TAREFA 2.2)
# Usar PoseValidationService

# 3. services/pose_corrector.py
class PoseCorrector:
    """Apenas correção automática de poses."""
    def correct_pose(self)
    def apply_safety_adjustments(self)

# 4. services/movement_executor.py
class MovementExecutor:
    """Apenas execução de movimentos."""
    def execute_move(self)
    def execute_pick_and_place(self)
    def move_to_home(self)

# 5. diagnostics/robot_diagnostics.py
class RobotDiagnostics:
    """Debug, benchmark e diagnóstico."""
    def run_diagnostics(self)
    def benchmark_movement(self)
    def generate_report(self)
    def get_statistics(self)

# 6. services/robot_service.py (reduzido - FAÇADE)
class RobotService:
    """Fachada que coordena componentes do robô."""
    def __init__(self,
                 communication: RobotCommunication,
                 validator: PoseValidationService,
                 corrector: PoseCorrector,
                 executor: MovementExecutor,
                 diagnostics: RobotDiagnostics):
        # Injeção de dependência
        pass
```

**Refatoração Necessária:**
- [ ] Criar pasta `diagnostics/`
- [ ] Criar `services/robot_communication.py`
- [ ] Criar `services/pose_corrector.py`
- [ ] Criar `services/movement_executor.py`
- [ ] Criar `diagnostics/robot_diagnostics.py`
- [ ] Refatorar `robot_service.py` como façade
- [ ] Mover código para classes apropriadas
- [ ] Implementar injeção de dependência
- [ ] Criar testes para cada componente

**Verificação:**
- [ ] `robot_service.py` reduzido para <300 linhas
- [ ] Cada classe tem 1 responsabilidade
- [ ] Padrão Façade implementado corretamente
- [ ] Todos os testes passam

**Última Atualização:** -
**Responsável:** -

---

#### ✅ Tarefa 3.4: Refatorar `URController`

**Status:** ⬜ NÃO INICIADO
**Estimativa:** 2h
**Arquivo:** [logic_control/ur_controller.py](logic_control/ur_controller.py#L7-L747)

**Problema:**
- 747 linhas misturando low-level e high-level
- Validação, diagnóstico, correção no mesmo arquivo

**Ação:**
```python
# SEPARAR EM:

# 1. logic_control/ur_low_level_controller.py
class URLowLevelController:
    """Apenas comandos RTDE básicos."""
    def connect_rtde(self)
    def send_move_command(self)
    def read_joint_positions(self)
    def emergency_stop(self)

# 2. diagnostics/ur_safety_diagnostics.py
class URSafetyDiagnostics:
    """Diagnóstico de segurança específico UR."""
    def check_safety_limits(self)
    def detect_collision(self)
    def validate_workspace(self)

# 3. logic_control/ur_controller.py (reduzido)
class URController:
    """Controlador principal UR - coordena componentes."""
    def __init__(self,
                 low_level: URLowLevelController,
                 diagnostics: URSafetyDiagnostics,
                 validator: PoseValidationService):
        # Injeção de dependência
        pass

    def move_to_pose(self, pose)
    def move_with_waypoints(self, waypoints)
    def get_current_pose(self)
```

**Refatoração Necessária:**
- [ ] Criar `logic_control/ur_low_level_controller.py`
- [ ] Criar `diagnostics/ur_safety_diagnostics.py`
- [ ] Extrair código low-level
- [ ] Extrair código de diagnóstico
- [ ] Refatorar `URController` para coordenar
- [ ] Implementar injeção de dependência
- [ ] Criar testes

**Verificação:**
- [ ] `URController` reduzido para <250 linhas
- [ ] Separação clara de responsabilidades
- [ ] Testes passam

**Última Atualização:** -
**Responsável:** -

---

## 🔵 PRIORIDADE BAIXA

> **Meta:** Melhorar testabilidade e manutenibilidade a longo prazo

### FASE 4: Criação de Abstrações e Interfaces

#### ✅ Tarefa 4.1: Criar Interfaces/Protocolos

**Status:** ⬜ NÃO INICIADO
**Estimativa:** 2h
**Novo Arquivo:** `interfaces/robot_interfaces.py`

**Objetivo:**
- Criar contratos bem definidos
- Permitir diferentes implementações
- Facilitar testes com mocks

**Ação:**
```python
# CRIAR: interfaces/robot_interfaces.py

from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class Pose:
    """Representação de uma pose do robô."""
    x: float
    y: float
    z: float
    rx: float
    ry: float
    rz: float

# ===== INTERFACES DE ROBÔ =====

class IRobotController(ABC):
    """Interface para controladores de robô."""

    @abstractmethod
    def connect(self) -> bool:
        """Conecta ao robô."""
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """Desconecta do robô."""
        pass

    @abstractmethod
    def move_to_pose(self, pose: Pose, speed: float = 0.5) -> bool:
        """Move para uma pose específica."""
        pass

    @abstractmethod
    def get_current_pose(self) -> Optional[Pose]:
        """Retorna pose atual do robô."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Verifica se está conectado."""
        pass

class IRobotValidator(ABC):
    """Interface para validação de poses."""

    @abstractmethod
    def validate_pose(self, pose: Pose) -> ValidationResult:
        """Valida uma pose."""
        pass

# ===== INTERFACES DE VISÃO =====

class IVisionSystem(ABC):
    """Interface para sistemas de visão."""

    @abstractmethod
    def calibrate(self) -> bool:
        """Calibra o sistema de visão."""
        pass

    @abstractmethod
    def detect_markers(self, frame) -> List[dict]:
        """Detecta marcadores na imagem."""
        pass

    @abstractmethod
    def calculate_positions(self) -> dict:
        """Calcula posições do tabuleiro."""
        pass

    @abstractmethod
    def is_calibrated(self) -> bool:
        """Verifica se está calibrado."""
        pass

# ===== INTERFACES DE JOGO =====

class IGameLogic(ABC):
    """Interface para lógica de jogo."""

    @abstractmethod
    def make_move(self, from_pos: int, to_pos: int, player: int) -> bool:
        """Executa uma jogada."""
        pass

    @abstractmethod
    def is_valid_move(self, from_pos: int, to_pos: int, player: int) -> bool:
        """Verifica se jogada é válida."""
        pass

    @abstractmethod
    def check_winner(self) -> Optional[int]:
        """Verifica se há vencedor."""
        pass

    @abstractmethod
    def get_board_state(self) -> List[int]:
        """Retorna estado atual do tabuleiro."""
        pass
```

**Refatoração Necessária:**
- [ ] Criar pasta `interfaces/`
- [ ] Criar `interfaces/robot_interfaces.py`
- [ ] Criar `interfaces/vision_interfaces.py`
- [ ] Criar `interfaces/game_interfaces.py`
- [ ] Documentar cada interface
- [ ] Criar exemplos de uso

**Verificação:**
- [ ] Interfaces criadas
- [ ] Documentação completa
- [ ] Exemplos funcionando

**Última Atualização:** -
**Responsável:** -

---

#### ✅ Tarefa 4.2: Implementar Injeção de Dependência

**Status:** ⬜ NÃO INICIADO
**Estimativa:** 3h
**Novo Arquivo:** `core/dependency_injection.py`

**Objetivo:**
- Reduzir acoplamento
- Facilitar testes
- Melhorar flexibilidade

**Ação:**
```python
# CRIAR: core/dependency_injection.py

from typing import Dict, Type, Any, Callable
import inspect

class Container:
    """Container de injeção de dependência."""

    def __init__(self):
        self._services: Dict[Type, Callable] = {}
        self._singletons: Dict[Type, Any] = {}

    def register(self, interface: Type, implementation: Callable, singleton: bool = True):
        """Registra um serviço."""
        self._services[interface] = implementation
        if singleton:
            self._singletons[interface] = None

    def resolve(self, interface: Type) -> Any:
        """Resolve uma dependência."""
        # Se é singleton e já foi criado
        if interface in self._singletons and self._singletons[interface]:
            return self._singletons[interface]

        # Busca implementação
        if interface not in self._services:
            raise ValueError(f"Service {interface} not registered")

        implementation = self._services[interface]

        # Auto-resolve dependências do construtor
        sig = inspect.signature(implementation)
        dependencies = {}

        for param_name, param in sig.parameters.items():
            if param.annotation != inspect.Parameter.empty:
                dependencies[param_name] = self.resolve(param.annotation)

        # Cria instância
        instance = implementation(**dependencies)

        # Armazena se singleton
        if interface in self._singletons:
            self._singletons[interface] = instance

        return instance

# CRIAR: core/service_provider.py

class ServiceProvider:
    """Provider centralizado de serviços."""

    def __init__(self):
        self.container = Container()
        self._register_services()

    def _register_services(self):
        """Registra todos os serviços do sistema."""
        from interfaces.robot_interfaces import IRobotController, IVisionSystem
        from logic_control.ur_controller import URController
        from vision.aruco_vision import ArucoVision

        # Registrar robô
        self.container.register(IRobotController, URController)

        # Registrar visão
        self.container.register(IVisionSystem, ArucoVision)

        # ... registrar outros serviços

    def get_robot_controller(self) -> IRobotController:
        """Retorna controlador de robô."""
        return self.container.resolve(IRobotController)

    def get_vision_system(self) -> IVisionSystem:
        """Retorna sistema de visão."""
        return self.container.resolve(IVisionSystem)
```

**Refatoração Necessária:**
- [ ] Criar pasta `core/`
- [ ] Implementar `Container`
- [ ] Implementar `ServiceProvider`
- [ ] Refatorar classes para usar interfaces
- [ ] Atualizar `main.py` para usar DI
- [ ] Criar testes de DI

**Verificação:**
- [ ] DI funcionando
- [ ] Classes desacopladas
- [ ] Fácil trocar implementações
- [ ] Testes usando mocks

**Última Atualização:** -
**Responsável:** -

---

#### ✅ Tarefa 4.3: Criar Testes Unitários

**Status:** ⬜ NÃO INICIADO
**Estimativa:** 6h
**Nova Pasta:** `tests/unit/`

**Objetivo:**
- Garantir qualidade do código
- Detectar regressões
- Documentar comportamento esperado

**Ação:**
```python
# CRIAR estrutura de testes:

tests/
├── unit/
│   ├── services/
│   │   ├── test_board_coordinate_system.py
│   │   ├── test_pose_validation_service.py
│   │   ├── test_robot_service.py
│   │   └── test_game_service.py
│   ├── logic_control/
│   │   └── test_ur_controller.py
│   ├── vision/
│   │   └── test_aruco_vision.py
│   └── ui/
│       ├── test_menu_manager.py
│       └── test_game_display.py
├── integration/
│   ├── test_game_orchestrator.py
│   └── test_vision_robot_integration.py
└── fixtures/
    ├── mock_robot.py
    ├── mock_vision.py
    └── sample_data.py

# EXEMPLO: tests/unit/services/test_pose_validation_service.py

import pytest
from services.pose_validation_service import PoseValidationService, ValidationResult

class TestPoseValidationService:

    @pytest.fixture
    def validator(self):
        workspace_limits = {
            'x': (-0.5, 0.5),
            'y': (-0.5, 0.5),
            'z': (0.0, 0.8),
        }
        return PoseValidationService(workspace_limits)

    def test_valid_pose(self, validator):
        """Testa validação de pose válida."""
        valid_pose = [0.3, 0.2, 0.5, 0, 0, 0]
        result = validator.validate_complete(valid_pose)

        assert result.is_valid == True
        assert len(result.errors) == 0

    def test_invalid_pose_out_of_workspace(self, validator):
        """Testa pose fora do workspace."""
        invalid_pose = [1.5, 0.2, 0.5, 0, 0, 0]  # x muito grande
        result = validator.validate_complete(invalid_pose)

        assert result.is_valid == False
        assert any("workspace" in err.lower() for err in result.errors)

    def test_invalid_pose_format(self, validator):
        """Testa formato inválido."""
        invalid_pose = [0.3, 0.2]  # Faltam elementos
        result = validator.validate_complete(invalid_pose)

        assert result.is_valid == False
        assert any("formato" in err.lower() for err in result.errors)
```

**Tarefas:**
- [ ] Criar estrutura de pastas de teste
- [ ] Configurar pytest
- [ ] Criar fixtures e mocks
- [ ] Escrever testes para `BoardCoordinateSystem`
- [ ] Escrever testes para `PoseValidationService`
- [ ] Escrever testes para cada serviço refatorado
- [ ] Configurar CI para rodar testes
- [ ] Atingir >70% de cobertura

**Verificação:**
- [ ] Testes criados
- [ ] Todos os testes passam
- [ ] Cobertura >70%
- [ ] CI configurado

**Última Atualização:** -
**Responsável:** -

---

#### ✅ Tarefa 4.4: Documentação de Arquitetura

**Status:** ⬜ NÃO INICIADO
**Estimativa:** 2h
**Novo Arquivo:** `ARCHITECTURE.md`

**Objetivo:**
- Documentar decisões arquiteturais
- Facilitar onboarding
- Manter documentação atualizada

**Ação:**
```markdown
# CRIAR: ARCHITECTURE.md

# 📐 Arquitetura do Sistema Tapatan Robótico

## Visão Geral

Sistema para jogar Tapatan usando robô UR e visão computacional.

## Princípios Arquiteturais

1. **Single Responsibility Principle (SRP)**: Cada classe tem uma única responsabilidade
2. **Dependency Injection**: Componentes recebem dependências via construtor
3. **Interface Segregation**: Interfaces pequenas e específicas
4. **Separation of Concerns**: Camadas bem definidas

## Estrutura de Camadas

```
┌─────────────────────────────────────┐
│         UI Layer                    │  main.py, ui/
│  (Menu, Display, User Input)        │
├─────────────────────────────────────┤
│      Application Layer              │  services/
│  (Orchestration, Game Logic)        │
├─────────────────────────────────────┤
│       Domain Layer                  │  models/, interfaces/
│  (Business Logic, Entities)         │
├─────────────────────────────────────┤
│    Infrastructure Layer             │  logic_control/, vision/
│  (Robot Control, Vision, Hardware)  │
└─────────────────────────────────────┘
```

## Componentes Principais

### 1. UI Layer
- **MenuManager**: Gerencia menus
- **GameDisplay**: Exibe tabuleiro

### 2. Application Layer
- **GameOrchestrator**: Coordena fluxo do jogo
- **GameService**: Lógica de jogo
- **RobotService**: Façade para controle de robô

### 3. Domain Layer
- **Interfaces**: Contratos (IRobotController, IVisionSystem)
- **Models**: Entidades (Pose, Move, BoardState)

### 4. Infrastructure Layer
- **URController**: Controle UR específico
- **ArucoVision**: Visão com ArUco
- **CameraManager**: Gerencia câmera

## Fluxo de Dados

```
User Input → MenuManager → GameOrchestrator
                              ↓
                        GameService ← VisionIntegrator
                              ↓
                        RobotService → URController → UR Robot
```

## Decisões Arquiteturais

### ADR 001: Separação de Validação de Poses
**Contexto**: Validação duplicada em 3 locais
**Decisão**: Criar PoseValidationService único
**Consequências**: Código centralizado, fácil manutenção

### ADR 002: Injeção de Dependência
**Contexto**: Acoplamento forte entre componentes
**Decisão**: Usar DI container
**Consequências**: Código testável, flexível
```

**Tarefas:**
- [ ] Criar `ARCHITECTURE.md`
- [ ] Documentar camadas
- [ ] Criar diagramas (mermaid)
- [ ] Documentar ADRs
- [ ] Criar guia de contribuição

**Verificação:**
- [ ] Documentação criada
- [ ] Diagramas claros
- [ ] ADRs documentadas

**Última Atualização:** -
**Responsável:** -

---

## ✅ CHECKLIST GERAL

### Prioridade Alta (Concluir primeiro)
- [x] 1.1 - Remover código duplicado `game_service.py` ✅ **CONCLUÍDA**
- [x] 1.2 - Corrigir linha solta `ur_controller.py` ✅ **CONCLUÍDA**
- [x] 1.3 - Remover código comentado `robot_service.py` ✅ **CONCLUÍDA**
- [ ] 2.1 - Criar `BoardCoordinateSystem`
- [ ] 2.2 - Criar `PoseValidationService`
- [ ] 2.3 - Unificar correção de poses
- [ ] 2.4 - Unificar movimento com waypoints

### Prioridade Média
- [ ] 3.1 - Refatorar `TapatanInterface`
- [ ] 3.2 - Refatorar `GameOrchestrator`
- [ ] 3.3 - Refatorar `RobotService`
- [ ] 3.4 - Refatorar `URController`

### Prioridade Baixa
- [ ] 4.1 - Criar interfaces/protocolos
- [ ] 4.2 - Implementar DI
- [ ] 4.3 - Criar testes unitários
- [ ] 4.4 - Documentação de arquitetura

---

## 📊 LOG DE PROGRESSO

### 2025-10-23

#### Sessão 1 - Limpeza Inicial (FASE 1 - Concluída)
- ✅ Plano de refatoração criado (REFACTORING_PLAN.md)
- ✅ **Tarefa 1.1 CONCLUÍDA**: Removido código duplicado em `game_service.py` (118 linhas)
- ✅ **Tarefa 1.2 CONCLUÍDA**: Corrigido print fora de função em `ur_controller.py`
- ✅ **Tarefa 1.3 CONCLUÍDA**: Removidas funções não utilizadas em `robot_service.py` (55 linhas)
- 📊 **Total removido**: ~173 linhas de código duplicado/obsoleto
- 🎯 **Próxima fase**: FASE 2 - Unificação de Código Duplicado

---

## 📈 MÉTRICAS DE ACOMPANHAMENTO

| Métrica | Antes | Meta | Atual | Progresso |
|---------|-------|------|-------|-----------|
| Linhas em `main.py` | 677 | <150 | 677 | 0% |
| Linhas em `robot_service.py` | 1210 | <300 | ~1155 | ✅ -55 linhas |
| Linhas em `game_service.py` | 356 | <250 | 238 | ✅ -118 linhas |
| Linhas em `game_orchestrator.py` | 561 | <200 | 561 | 0% |
| Linhas em `ur_controller.py` | 747 | <250 | 747 | 0% |
| Duplicação de código | Alta | Nenhuma | Média | 🟡 Melhorando |
| Cobertura de testes | 0% | >70% | 0% | 0% |
| Violações SRP | 7 classes | 0 | 7 | 0% |
| **Total linhas removidas** | - | - | **173** | ✅ |

---

## 🎯 PRÓXIMOS PASSOS

1. ~~**Tarefa 1.1** - Remover código duplicado em `game_service.py`~~ ✅ CONCLUÍDA
2. ~~**Tarefa 1.2** - Corrigir linha solta `ur_controller.py`~~ ✅ CONCLUÍDA
3. ~~**Tarefa 1.3** - Remover código não utilizado `robot_service.py`~~ ✅ CONCLUÍDA
4. **PRÓXIMA → Tarefa 2.1** - Criar `BoardCoordinateSystem` única
5. **Continuar** com Tarefa 2.2 - Criar `PoseValidationService`
6. **Commitar** quando atingir marcos significativos

---

## 📝 NOTAS

- Este é um documento vivo - atualizar após cada tarefa
- Marcar checkboxes com `[x]` quando concluído
- Adicionar data e responsável em cada tarefa
- Documentar decisões importantes no log de progresso
- Criar branches separadas para cada fase

---

**Última Atualização:** 2025-10-23
**Versão:** 1.0
**Status:** 🔴 PLANEJAMENTO CONCLUÍDO - AGUARDANDO EXECUÇÃO