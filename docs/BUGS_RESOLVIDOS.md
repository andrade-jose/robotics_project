# Bugs Resolvidos - Sistema Tapatan Robótico

## Data: 2025-10-28

---

## 1. Erro de Import Circular - `gerar_tabuleiro_tapatan`

**Tipo:** ImportError
**Severidade:** Crítica
**Arquivo Afetado:** `services/robot_service.py`

### Descrição do Problema
```python
ImportError: cannot import name 'gerar_tabuleiro_tapatan' from 'services.game_service'
```

O módulo `robot_service.py` estava tentando importar a função `gerar_tabuleiro_tapatan` de `services.game_service`, mas essa função estava localizada em `utils.tapatan_board`.

### Solução
**Arquivo:** `services/robot_service.py` (linha 12)

**Antes:**
```python
from services.game_service import gerar_tabuleiro_tapatan
```

**Depois:**
```python
from utils.tapatan_board import gerar_tabuleiro_tapatan
```

**Commit:** Correção de import para função `gerar_tabuleiro_tapatan`

---

## 2. Erro de Encoding Unicode no Windows

**Tipo:** UnicodeEncodeError
**Severidade:** Crítica
**Arquivo Afetado:** `config/config_completa.py`

### Descrição do Problema
```python
UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f527' in position 0: character maps to <undefined>
```

O Windows estava tendo problemas para renderizar emojis Unicode nos prints da configuração, causando falha na importação do módulo.

### Solução
**Arquivo:** `config/config_completa.py` (linhas 94-115)

**Antes:**
```python
print("🔧 Detectado ambiente de SIMULAÇÃO.")
print("🔧 Detectado ROBÔ REAL - aplicando configurações de segurança.")
print("⚠️ AVISO: z_min muito baixo, ajustando para 0.01m.")
```

**Depois:**
```python
print("[CONFIG] Detectado ambiente de SIMULACAO.")
print("[CONFIG] ROBO REAL - aplicando configuracoes de seguranca.")
print("[CONFIG] AVISO: z_min muito baixo, ajustando para 0.01m.")
```

**Commit:** Remoção de emojis para compatibilidade com Windows

---

## 3. Atributos Faltando na Classe ConfigRobo

**Tipo:** AttributeError
**Severidade:** Crítica
**Arquivo Afetado:** `config/config_completa.py`

### Descrição do Problema
```python
AttributeError: 'ConfigRobo' object has no attribute 'velocidade_padrao'
AttributeError: 'ConfigRobo' object has no attribute 'pausa_entre_jogadas'
AttributeError: 'ConfigRobo' object has no attribute 'aceleracao_padrao'
AttributeError: 'ConfigRobo' object has no attribute 'habilitar_correcao_automatica'
```

Vários módulos estavam tentando acessar atributos que não existiam na classe `ConfigRobo`.

### Solução
**Arquivo:** `config/config_completa.py`

Adicionados os seguintes atributos ao dataclass `ConfigRobo`:

#### Velocidades e Acelerações (linhas 32, 36)
```python
velocidade_padrao: float = 0.1
aceleracao_padrao: float = 0.1
```

#### Pausas e Timeouts (linhas 39-40)
```python
pausa_entre_movimentos: float = 1.0
pausa_entre_jogadas: float = 2.0
```

#### Configurações de Movimento e Segurança (linhas 58-70)
```python
auto_calibrar: bool = False
habilitar_correcao_automatica: bool = True
habilitar_correcao_inteligente: bool = True
habilitar_pontos_intermediarios: bool = True
usar_pontos_intermediarios: bool = True
passo_pontos_intermediarios: float = 0.1
distancia_threshold_pontos_intermediarios: float = 0.3
distancia_maxima_movimento: float = 0.8
max_tentativas_movimento: int = 3
max_tentativas_correcao: int = 3
tentativas_validacao: int = 3
modo_ultra_seguro: bool = False
fator_velocidade_ultra_seguro: float = 0.5
```

**Commit:** Adição de atributos faltantes em ConfigRobo

---

## 4. Inicialização Incorreta do URController

**Tipo:** TypeError
**Severidade:** Crítica
**Arquivo Afetado:** `services/robot_service.py`

### Descrição do Problema
```python
TypeError: URController.__init__() got an unexpected keyword argument 'robot_ip'
```

O `URController` esperava receber um objeto `ConfigRobo` completo, mas estava recebendo parâmetros individuais (`robot_ip`, `speed`, `acceleration`).

### Solução
**Arquivo:** `services/robot_service.py` (linha 188)

**Antes:**
```python
self.controller = URController(
    robot_ip=self.robot_ip,
    speed=self.config["speed"],
    acceleration=self.config["acceleration"]
)
```

**Depois:**
```python
self.controller = URController(config=self.config_robo)
```

**Commit:** Correção na inicialização do URController

---

## 5. Modo Teste Tentando Conectar ao Robô Real

**Tipo:** Configuração
**Severidade:** Média
**Arquivo Afetado:** `main.py`

### Descrição do Problema
O modo de teste estava tentando conectar ao robô físico no IP `10.1.7.30`, causando timeout e falha na inicialização.

```
Timeout connecting to UR dashboard server.
```

### Solução
**Arquivo:** `main.py` (linha 266)

**Antes:**
```python
def __init__(self):
    self.config_robo = ConfigRobo()
    self.config_robo.pausa_entre_jogadas = 1.0
```

**Depois:**
```python
def __init__(self):
    self.config_robo = ConfigRobo()
    self.config_robo.ip = "127.0.0.1"  # Modo simulação
    self.config_robo.pausa_entre_jogadas = 1.0
```

**Commit:** Configuração de IP de simulação para modo teste

---

## 6. Argumentos Incorretos no Construtor de ConfigRobo

**Tipo:** TypeError
**Severidade:** Média
**Arquivo Afetado:** `main.py`

### Descrição do Problema
```python
TypeError: ConfigRobo() takes no arguments
```

O código estava tentando passar argumentos diretamente no construtor do dataclass, mas deveria criar a instância primeiro e depois modificar os atributos.

### Solução
**Arquivo:** `main.py` (linhas 265-273)

**Antes:**
```python
self.config_robo = ConfigRobo(
    pausa_entre_jogadas=1.0,
    velocidade_padrao=0.05,
    auto_calibrar=False
)
```

**Depois:**
```python
self.config_robo = ConfigRobo()
self.config_robo.ip = "127.0.0.1"
self.config_robo.pausa_entre_jogadas = 1.0
self.config_robo.velocidade_padrao = 0.05
self.config_robo.auto_calibrar = False
```

**Commit:** Correção na inicialização de ConfigRobo no modo teste

---

## 7. Método Inexistente no URController - move_to_pose_safe

**Tipo:** AttributeError
**Severidade:** Crítica
**Arquivo Afetado:** `services/robot_service.py`

### Descrição do Problema
```python
AttributeError: 'URController' object has no attribute 'move_to_pose_safe'
```

O `robot_service.py` estava chamando o método `move_to_pose_safe()` que não existe no URController. O método correto é `move_to_pose()`.

### Contexto
Quando o sistema tenta mover o robô para a posição home durante a inicialização, ocorre erro porque o método chamado não existe.

### Log do Erro
```
2025-10-28 09:23:24,279 - RobotService - INFO -  Movendo para posição home
2025-10-28 09:23:24,279 - TapatanOrchestrator - ERROR - Falha ao mover robô para home
❌ Falha na inicialização do sistema robótico!
```

### Solução
**Arquivo:** `services/robot_service.py` (linha 233)

**Antes:**
```python
success = self.controller.move_to_pose_safe(
    pose.to_list(),
    speed or self.config["speed"],
    acceleration or self.config["acceleration"],
    strategy
)
```

**Depois:**
```python
success = self.controller.move_to_pose(
    pose.to_list(),
    speed or self.config["speed"],
    acceleration or self.config["acceleration"]
)
```

**Nota:** O parâmetro `strategy` foi removido pois não é suportado pelo método `move_to_pose()` do URController.

**Commit:** Correção do nome do método para mover robô para pose

---

## 8. RobotService Não Recebia ConfigRobo no Construtor

**Tipo:** Design/Configuração
**Severidade:** Média
**Arquivo Afetado:** `services/robot_service.py`, `services/game_orchestrator.py`

### Descrição do Problema
O `RobotService` criava sempre um novo `ConfigRobo()` com valores padrão, ignorando as configurações personalizadas passadas pelo orquestrador. Isso causava comportamento inconsistente entre modo teste e produção.

### Contexto
O orquestrador passava um `config_robo` personalizado, mas o RobotService criava sua própria instância com IP padrão (`10.1.7.30`), ignorando configurações de teste ou personalizadas.

### Solução
**Arquivo 1:** `services/robot_service.py` (linha 101)

**Antes:**
```python
def __init__(self, config_file: Optional[str] = None):
    self.config_robo = ConfigRobo()
```

**Depois:**
```python
def __init__(self, config_robo: Optional[ConfigRobo] = None, config_file: Optional[str] = None):
    self.config_robo = config_robo or ConfigRobo()
```

**Arquivo 2:** `services/game_orchestrator.py` (linha 109)

**Antes:**
```python
self.robot_service = RobotService()
self.robot_service.config_robo = self.config_robo
```

**Depois:**
```python
self.robot_service = RobotService(config_robo=self.config_robo)
```

**Commit:** Correção para RobotService aceitar ConfigRobo no construtor

---

## Resumo de Impacto

| Bug | Severidade | Status | Impacto |
|-----|-----------|--------|---------|
| Import `gerar_tabuleiro_tapatan` | Crítica | ✅ Resolvido | Bloqueava inicialização completa |
| Encoding Unicode | Crítica | ✅ Resolvido | Falha de import no Windows |
| Atributos faltando | Crítica | ✅ Resolvido | AttributeError em runtime |
| Inicialização URController | Crítica | ✅ Resolvido | Conexão com robô falhava |
| IP no modo teste | Média | ✅ Resolvido | Timeout na conexão |
| Construtor ConfigRobo | Média | ✅ Resolvido | Falha na criação de objeto |
| Método inexistente | Crítica | ✅ Resolvido | Falha ao mover para home |
| ConfigRobo não passado | Média | ✅ Resolvido | Configurações ignoradas |

---

## Como Testar

### Modo Teste (Simulação)
```bash
python main.py --test
```

### Modo Produção (Robô Real)
```bash
python main.py
```

---

## Notas Técnicas

### Dependências Afetadas
- `services/robot_service.py`
- `config/config_completa.py`
- `main.py`
- `logic_control/ur_controller.py`

### Compatibilidade
- ✅ Windows 10/11
- ✅ Python 3.12+
- ✅ Sistema UR3e

### Próximas Melhorias Sugeridas
1. Implementar mock completo do robô para testes sem hardware
2. Adicionar validação de tipos em tempo de execução
3. Criar testes unitários para ConfigRobo
4. Documentar todos os atributos de configuração

---

**Documentação criada por:** Claude Code
**Última atualização:** 2025-10-28
