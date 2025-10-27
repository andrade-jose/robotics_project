# Estrutura de Testes - Sistema Tapatan Robótico

## Visão Geral

Este diretório contém a suite de testes completa para o sistema Tapatan Robótico, incluindo testes unitários, testes de integração, e fixtures compartilhadas.

## Estrutura de Diretórios

```
tests/
├── unit/                      # Testes unitários (isolados, rápidos)
│   ├── services/              # Testes de serviços
│   │   ├── test_board_coordinate_system.py
│   │   ├── test_pose_validation_service.py
│   │   ├── test_robot_service.py
│   │   └── test_physical_movement_executor.py
│   ├── logic_control/         # Testes de controladores
│   ├── vision/                # Testes de visão
│   └── ui/                    # Testes de interface
├── integration/               # Testes de integração
├── fixtures/                  # Dados de teste compartilhados
├── conftest.py                # Fixtures globais do pytest
└── README.md                  # Este arquivo
```

## Configuração

### Arquivos de Configuração

- **pytest.ini**: Configuração global do pytest (markers, paths, output)
- **conftest.py**: Fixtures compartilhadas e hooks do pytest

### Requisitos

```bash
pip install pytest pytest-cov
```

### Fixtures Disponíveis (conftest.py)

#### Configuração e Limites
- `workspace_limits`: Limites do workspace do robô
- `safe_ur_limits`: Limites de segurança UR
- `board_config`: Configuração do tabuleiro Tapatan

#### Poses e Coordenadas
- `valid_pose`: Pose válida de teste
- `invalid_pose_out_of_bounds`: Pose fora do workspace
- `invalid_pose_format`: Pose com formato inválido
- `home_pose`: Pose de home padrão
- `sample_board_positions`: 9 posições do tabuleiro

#### Mocks de Hardware
- `mock_rtde_control`: Mock do controlador RTDE
- `mock_rtde_receive`: Mock do receptor RTDE
- `mock_camera`: Mock de câmera OpenCV
- `mock_aruco_detector`: Mock do detector ArUco

#### Mocks de Serviços
- `mock_robot_controller`: Mock de IRobotController
- `mock_validator`: Mock de PoseValidationService
- `mock_board_coords`: Mock de BoardCoordinateSystem
- `mock_vision_system`: Mock de IVisionSystem

#### Dados de Teste
- `sample_game_state`: Estado de jogo de exemplo
- `empty_board`: Tabuleiro vazio
- `winning_state_player1`: Estado de vitória

## Executando os Testes

### Todos os Testes
```bash
pytest
```

### Apenas Testes Unitários
```bash
pytest -m unit
```

### Apenas Testes de Integração
```bash
pytest -m integration
```

### Com Cobertura
```bash
pytest --cov=services --cov=logic_control --cov-report=html
```

### Testes Específicos
```bash
# Teste de um arquivo específico
pytest tests/unit/services/test_pose_validation_service.py

# Teste de uma classe específica
pytest tests/unit/services/test_pose_validation_service.py::TestPoseFormatValidation

# Teste de um método específico
pytest tests/unit/services/test_pose_validation_service.py::TestPoseFormatValidation::test_valid_pose_format
```

### Modo Verbose
```bash
pytest -v                  # Verbose
pytest -vv                 # Very verbose
pytest -vv -s              # Com prints
```

## Markers Disponíveis

Configure com `@pytest.mark.MARKER`:

- `@pytest.mark.unit`: Testes unitários (rápidos, isolados)
- `@pytest.mark.integration`: Testes de integração
- `@pytest.mark.slow`: Testes lentos
- `@pytest.mark.requires_robot`: Requer conexão com robô real
- `@pytest.mark.requires_camera`: Requer hardware de câmera

### Exemplos de Uso

```python
@pytest.mark.unit
def test_pose_validation():
    ...

@pytest.mark.requires_robot
@pytest.mark.slow
def test_real_robot_movement():
    ...
```

### Executar apenas testes que NÃO precisam de hardware
```bash
pytest -m "not requires_robot and not requires_camera"
```

## Testes Criados

### ✅ BoardCoordinateSystem (25 testes)
- Inicialização e configuração
- Cálculo e recuperação de posições
- Validação de posições
- Persistência (save/load)
- Atualização de posições
- Cálculos matemáticos
- Casos extremos

### ✅ PoseValidationService (30+ testes)
- Validação de formato (Layer 1)
- Validação de workspace (Layer 2)
- Validação de orientação (Layer 3)
- Validação completa (todas as camadas)
- ValidationResult
- Métodos auxiliares
- Casos extremos
- Verificações de segurança

### ✅ RobotService (25+ testes)
- Inicialização e injeção de dependências
- Conexão/desconexão
- Movimentos básicos
- Operações de jogo (place_piece, move_piece)
- Calibração
- Validação delegada
- Tratamento de erros
- Gerenciamento de estado
- Integração entre componentes

### ✅ PhysicalMovementExecutor (20+ testes)
- Inicialização
- Movimentos simples
- Colocação de peças
- Movimento de peças
- Execução de jogadas completas
- Gerenciamento de posições de depósito
- Movimentos com segurança (waypoints)
- Tratamento de erros

## Padrões de Teste

### Estrutura de Classes de Teste
```python
class TestComponentName:
    """Descrição do que está sendo testado."""

    @pytest.fixture
    def component(self):
        """Fixture do componente sendo testado."""
        return ComponentName()

    def test_specific_behavior(self, component):
        """Testa comportamento específico."""
        # Arrange
        input_data = ...

        # Act
        result = component.method(input_data)

        # Assert
        assert result == expected
```

### Uso de Mocks
```python
from unittest.mock import Mock, patch

def test_with_mock(self, mock_robot_controller):
    """Usa mock injetado do conftest.py."""
    mock_robot_controller.move_to_pose.return_value = True
    ...

@patch('module.ClassName')
def test_with_patch(self, mock_class):
    """Usa patch para mockar importação."""
    ...
```

### Testes Parametrizados
```python
@pytest.mark.parametrize("input,expected", [
    ([0.3, 0.2, 0.5, 0, 0, 0], True),
    ([1.5, 0.2, 0.5, 0, 0, 0], False),
])
def test_multiple_cases(self, validator, input, expected):
    result = validator.validate_workspace(input)
    assert result.is_valid == expected
```

## Cobertura de Código

### Meta de Cobertura
- **Objetivo**: >70% de cobertura
- **Atual**: Em desenvolvimento

### Gerar Relatório de Cobertura
```bash
pytest --cov=services --cov=logic_control --cov-report=html
# Abre htmlcov/index.html no navegador
```

## Integração Contínua (CI)

**TODO**: Configurar pipeline CI para executar testes automaticamente:
- GitHub Actions / GitLab CI
- Executar em cada push/pull request
- Verificar cobertura mínima
- Reportar falhas

## Próximos Passos

### Testes Pendentes
- [ ] `logic_control/test_ur_controller.py`
- [ ] `vision/test_aruco_vision.py`
- [ ] `ui/test_menu_manager.py`
- [ ] `ui/test_game_display.py`
- [ ] `diagnostics/test_robot_diagnostics.py`
- [ ] `integration/test_game_orchestrator.py`
- [ ] `integration/test_vision_robot_integration.py`

### Melhorias
- [ ] Adicionar testes de performance
- [ ] Adicionar testes de stress
- [ ] Configurar CI/CD pipeline
- [ ] Melhorar cobertura para >80%
- [ ] Adicionar testes de regressão

## Troubleshooting

### Testes falhando?
1. Verifique que todas as dependências estão instaladas: `pip install -r requirements.txt`
2. Verifique que pytest está instalado: `pip install pytest pytest-cov`
3. Execute com `-vv` para mais detalhes: `pytest -vv`
4. Verifique logs: `tests/test_run.log`

### Imports falhando?
- Certifique-se que está no diretório raiz do projeto
- `pytest.ini` configura `pythonpath = .` automaticamente

### Fixtures não encontradas?
- Fixtures globais estão em `tests/conftest.py`
- Fixtures específicas devem estar na classe de teste ou em conftest.py local

## Contribuindo

### Adicionar Novos Testes
1. Crie arquivo `test_*.py` no diretório apropriado
2. Use fixtures do `conftest.py` quando possível
3. Siga padrão Arrange-Act-Assert
4. Adicione docstrings descritivas
5. Use markers apropriados (`@pytest.mark.unit`, etc.)

### Boas Práticas
- Testes devem ser independentes
- Um assert por teste (quando possível)
- Nomes descritivos: `test_should_reject_invalid_pose`
- Mocks para dependências externas
- Testes rápidos (<100ms)

## Referências

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest Best Practices](https://docs.pytest.org/en/stable/goodpractices.html)
- [Python Testing with pytest (Book)](https://pragprog.com/titles/bopytest/python-testing-with-pytest/)
