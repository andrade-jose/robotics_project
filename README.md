# 🤖 Sistema Tapatan Robótico

Sistema completo para jogar Tapatan (variante filipina de Tic-Tac-Toe) usando robô UR (Universal Robots) e visão computacional com marcadores ArUco.

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![UR Robot](https://img.shields.io/badge/UR-Robot-orange.svg)](https://www.universal-robots.com/)
[![OpenCV](https://img.shields.io/badge/OpenCV-ArUco-green.svg)](https://opencv.org/)

---

## 📋 Índice

- [Visão Geral](#visao-geral)
- [Características](#caracteristicas)
- [Arquitetura](#arquitetura)
- [Requisitos](#requisitos)
- [Instalação](#instalacao)
- [Configuração](#configuracao)
- [Uso](#uso)
- [Calibração](#calibracao)
- [Troubleshooting](#troubleshooting)
- [Documentação](#documentacao)
- [Contribuindo](#contribuindo)

---

## 🎯 Visão Geral

Este projeto implementa um sistema robótico completo para jogar o jogo **Tapatan**, uma variante filipina do jogo da velha (Tic-Tac-Toe), usando:

- **Robô UR**: Manipulação física das peças do jogo
- **Visão Computacional**: Detecção dinâmica do tabuleiro usando marcadores ArUco
- **IA Minimax**: Jogadas inteligentes do robô
- **Sistema de Calibração V2**: Pipeline automático de 2-marcador para calibração precisa
- **Arquitetura Modular**: Desenvolvimento paralelo de v1 (produção) e v2 (nova geração)

### Status do Projeto

| Fase | Status | Descrição |
|------|--------|-----------|
| **Phase 1** | ✅ Completo | Limpeza v1 e consolidação |
| **Phase 2** | ✅ Completo | Setup v2 em paralelo |
| **Phase 3** | ✅ Completo | Sistema de visão v2 modular |
| **Phase 4** | ✅ Completo | Calibração com 2-marcadores ArUco |
| **Phase 5** | ✅ **COMPLETO** | **GameOrchestrator V2 + Integração** |
| **Phase 6** | 🔄 Próximo | Testes com robô real |

**Métricas de Conclusão (Phase 5)**:
- ✅ 56 testes automatizados (100% passando)
- ✅ ~1,500 linhas de código novo
- ✅ 85% do projeto completo
- ✅ 4,500+ LOC total

### Como Funciona (V2)

1. **Setup**: Posicione 2 marcadores ArUco no tabuleiro para auto-calibração
2. **Calibração Automática**: Sistema detecta e mapeia os 9 pontos da grade 3x3
3. **Jogo**: Execute `python v2/main_v2.py --test` para modo simulado
4. **Validação**: Múltiplas camadas garantem precisão sub-milimétrica
5. **Robô**: Envia coordenadas calibradas (mm) ao controlador UR

---

## ✨ Características

### Jogabilidade
- ✅ Jogo humano vs robô (v1 completo)
- ✅ Dois modos: com ou sem visão computacional
- ✅ IA usando algoritmo Minimax com poda alpha-beta
- ✅ Detecção automática de vitória/empate
- ✅ Interface em modo teste para v2 (sem hardware)

### Sistema de Visão V2 (Phase 4-5)
- ✅ **Calibração automática com 2-marcadores ArUco** (Pipeline Phase 4)
- ✅ Detecção e mapeamento preciso da grade 3x3
- ✅ Transformação homográfica para geometria exata
- ✅ Validação de workspace para segurança
- ✅ Conversão automática pixel → grid → mm

### Controle do Robô (V1 + V2)
- ✅ Comunicação RTDE com robô UR
- ✅ Validação multi-camadas de poses:
  - Formato (6 valores)
  - Workspace (limites cartesianos)
  - Rotação (limites angulares)
  - Alcançabilidade (distância máxima)
  - Segurança UR (limites do fabricante)
- ✅ Correção automática de poses inválidas
- ✅ Movimentos com pontos intermediários para segurança
- ✅ **V2 Integration**: Pipeline completo calibração → validação → execução

### Arquitetura
- ✅ Design modular baseado em princípios SOLID
- ✅ Separação clara de responsabilidades (SRP)
- ✅ Interfaces bem definidas para todos os componentes
- ✅ 4 camadas arquiteturais (Presentation, Application, Domain, Infrastructure)
- ✅ Padrões de design (Facade, Command, Strategy, Observer)
- ✅ **Desenvolvimento Paralelo**: v1 congelado + v2 em desenvolvimento
- ✅ **Orquestração Completa**: GameOrchestratorV2 pipeline (Phase 5)

---

## 🏗️ Arquitetura

### V1 (Produção) - Congelado
```
┌─────────────────────────────────────┐
│    Presentation Layer (V1)          │  main.py, UI menus
├─────────────────────────────────────┤
│    Application Layer (V1)           │  RobotService, Orchestrator
├─────────────────────────────────────┤
│    Domain Layer (V1)                │  Interfaces, Validação
├─────────────────────────────────────┤
│    Infrastructure Layer (V1)        │  URController, RobotService
└─────────────────────────────────────┘
```

### V2 (Nova Geração) - Em Desenvolvimento (Phase 5 ✅)

```
┌──────────────────────────────────────────┐
│    Presentation Layer (V2)               │  v2/main_v2.py (teste + real)
├──────────────────────────────────────────┤
│    Application Layer (V2)                │  GameOrchestratorV2 (Phase 5)
│    • Integration Layer: Orquestração     │
│    • BoardCoordinateSystemV2: Coords     │
├──────────────────────────────────────────┤
│    Domain Layer (V2)                     │  TabuleiraTapatan (lógica)
│    • interfaces/ (specs)                 │
├──────────────────────────────────────────┤
│    Infrastructure Layer (V2)             │  CalibrationOrchestrator (Phase 4)
│    • vision/ (ArUco, Camera)             │
│    • logic_control/ (Game Logic)         │
│    • services/ (Calibration)             │
└──────────────────────────────────────────┘
```

**Pipeline V2 (Phase 5)**:
```
Frame de Câmera
       ↓
CalibrationOrchestrator (Phase 4)
  • Detecta 2-marcadores ArUco
  • Calcula transform homográfica
  • Mapeia grade 3x3 (9 pontos)
       ↓
BoardCoordinateSystemV2
  • Converte: pixel → grid (0-8) → mm
  • Valida movimentos com workspace
       ↓
GameOrchestratorV2 (Phase 5)
  • Valida com lógica Tapatan
  • Executa movimento no jogo
  • Envia ao robô com coordenadas calibradas
```

Para detalhes completos, veja [ARCHITECTURE.md](ARCHITECTURE.md).

---

## 📦 Requisitos

### Hardware
- Robô UR (Universal Robots) - testado com UR3/UR5
- Câmera USB para visão computacional (opcional)
- Tabuleiro físico 3x3
- Peças do jogo (ex: moedas diferentes para cada jogador)
- Marcadores ArUco impressos (opcional, para modo visão)

### Software
- **Python 3.8+**
- **Sistema Operacional**: Windows, Linux ou macOS
- **Bibliotecas Python**:
  - `ur-rtde` - Comunicação com robô UR
  - `opencv-python` - Visão computacional
  - `opencv-contrib-python` - Módulo ArUco
  - `numpy` - Operações numéricas

---

## 🚀 Instalação

### 1. Clone o Repositório

```bash
git clone https://github.com/seu-usuario/robotics_project.git
cd robotics_project
```

### 2. Crie um Ambiente Virtual

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Instale as Dependências

```bash
pip install ur-rtde opencv-python opencv-contrib-python numpy
```

### 4. Verifique a Instalação

```bash
python -c "import cv2; import ur_rtde; print('OK')"
```

---

## ⚙️ Configuração

### 1. Configure o Robô UR

Edite `config/config_completa.py`:

```python
@dataclass
class ConfigRobo:
    ip: str = "192.168.1.100"  # IP do seu robô UR
    velocidade_normal: float = 0.5
    aceleracao_normal: float = 0.3
    # ... outros parâmetros
```

### 2. Configure Limites de Segurança

Ajuste os limites do workspace no mesmo arquivo:

```python
limites_workspace = {
    'x_min': -0.5, 'x_max': 0.5,
    'y_min': -0.5, 'y_max': 0.5,
    'z_min': 0.0, 'z_max': 0.8,
}
```

### 3. Configure a Câmera (Opcional)

Se usar visão computacional, configure em `vision/camera_manager.py`:

```python
CAMERA_INDEX = 0  # Índice da câmera USB
RESOLUTION = (1280, 720)
FPS = 30
```

---

## 🎮 Uso

### V1 (Sistema Completo com Hardware)

```bash
python main.py
```

### V2 (Sistema em Desenvolvimento - Modo Teste Disponível)

```bash
# Modo teste (simulado, sem hardware necessário)
python v2/main_v2.py --test

# Modo com debug detalhado
python v2/main_v2.py --test --debug

# Modo produção (com câmera e robô real - Phase 6)
python v2/main_v2.py
```

### Menu Principal V1

Ao iniciar V1, você verá:

```
========================================
   🤖 SISTEMA TAPATAN ROBÓTICO 🎮
========================================

1. Iniciar novo jogo
2. Calibrar sistema
3. Testar sistema de visão
4. Ver status do sistema
5. Parada de emergência
0. Sair

Escolha uma opção:
```

### V2 Modo Teste (Phase 5)

Saída esperada:

```
[MainV2] Inicializando sistema Tapatan V2...
[MainV2] Configurando componentes...
[MainV2] ✅ Componentes configurados com sucesso
[MainV2] Modo teste: simulando calibração
[MainV2] ✅ Calibração bem-sucedida
[MainV2] ✅ Sistema pronto para jogo!
[MainV2] Testando movimento: 0 → 4
[MainV2] ✅ Movimento bem-sucedido
```

### Opções do Menu

#### 1. Iniciar Novo Jogo
- Escolha entre modo com ou sem visão
- **Sem visão**: Você informa manualmente onde jogou
- **Com visão**: Sistema detecta automaticamente suas jogadas
- O robô responde automaticamente a cada jogada

#### 2. Calibrar Sistema
- Calibra as 9 posições do tabuleiro
- O robô move para cada posição sequencialmente
- Ajuste fino usando comandos de movimento

#### 3. Testar Sistema de Visão
- Testa detecção de marcadores ArUco
- Mostra feed de vídeo com marcadores detectados
- Pressione 'q' para sair

#### 4. Ver Status do Sistema
- Mostra status de conexão do robô
- Estatísticas de movimentos
- Estado da calibração
- Informações do sistema de visão

#### 5. Parada de Emergência
- Para imediatamente qualquer movimento
- Use em caso de situação perigosa

---

## 🎯 Calibração

### Calibração Manual

1. No menu, escolha "Calibrar sistema"
2. O robô move para cada posição do tabuleiro (0-8)
3. Para cada posição:
   - Verifique se está correta
   - Ajuste usando comandos:
     - `w/s` - move em Y
     - `a/d` - move em X
     - `q/e` - move em Z
     - `c` - confirma posição
4. Calibração salva automaticamente em `board_calibration.json`

### Calibração com Visão

1. Posicione marcadores ArUco nas 4 quinas do tabuleiro
2. Execute "Testar sistema de visão"
3. Sistema detecta automaticamente as posições
4. Calibração é feita dinamicamente durante o jogo

### IDs de Marcadores ArUco

- **ID 0**: Canto superior esquerdo
- **ID 1**: Canto superior direito
- **ID 2**: Canto inferior esquerdo
- **ID 3**: Canto inferior direito
- **IDs 10-18**: Marcadores de peças (opcional)

---

## 🔧 Troubleshooting

### Robô não conecta

**Problema**: `❌ Erro ao conectar ao robô`

**Soluções**:
1. Verifique o IP na configuração
2. Confirme que o robô está ligado e em modo remoto
3. Teste conectividade: `ping 192.168.1.100`
4. Verifique firewall e permissões de rede
5. Certifique-se que nenhum outro programa está usando RTDE

### Câmera não detectada

**Problema**: `❌ Nenhuma câmera disponível`

**Soluções**:
1. Conecte a câmera USB
2. Tente diferentes índices de câmera (0, 1, 2...)
3. Verifique drivers da câmera
4. Em Linux, adicione permissões: `sudo usermod -a -G video $USER`

### Poses rejeitadas

**Problema**: `❌ Pose rejeitada pelos limites de segurança`

**Soluções**:
1. Verifique limites do workspace em `config_completa.py`
2. Ajuste limites de rotação se necessário
3. Execute diagnóstico: Menu → "Ver status do sistema"
4. Use `diagnostic_pose_rejection()` para análise detalhada

### Marcadores ArUco não detectados

**Problema**: `⚠️ Nenhum marcador detectado`

**Soluções**:
1. Melhore iluminação da área
2. Certifique-se que marcadores estão planos e visíveis
3. Ajuste distância da câmera (30-50cm ideal)
4. Verifique tamanho dos marcadores (mínimo 5x5cm)
5. Reimprima marcadores em alta qualidade

### Movimentos imprecisos

**Problema**: Robô não atinge posições exatas

**Soluções**:
1. Recalibre o sistema
2. Verifique se há vibração na mesa
3. Aguarde robô completar movimento antes da próxima ação
4. Reduza velocidade e aceleração na configuração
5. Execute benchmark: `robot_service.benchmark_correction_system()`

---

## 📚 Documentação

### Documentos Principais

- **[ARCHITECTURE.md](ARCHITECTURE.md)**: Arquitetura completa do sistema
  - Estrutura de camadas (V1 + V2)
  - Componentes principais
  - Fluxos de dados
  - Decisões arquiteturais (ADRs)

- **[ESTRATEGIA_PARALELA_V2.md](ESTRATEGIA_PARALELA_V2.md)**: Estratégia de desenvolvimento paralelo
  - Phase-by-phase breakdown
  - v1 congelado + v2 desenvolvimento
  - Status de implementação

- **[PHASE_5_INTEGRATION_PLAN.md](PHASE_5_INTEGRATION_PLAN.md)**: Plano de Phase 5
  - GameOrchestratorV2 integração
  - BoardCoordinateSystemV2
  - 56 testes implementados

- **[REFACTORING_PLAN.md](REFACTORING_PLAN.md)**: Plano de refatoração
  - Progresso das tarefas
  - Métricas de qualidade
  - Log de mudanças

### APIs e Interfaces

#### IRobotController
```python
from interfaces.robot_interfaces import IRobotController

controller: IRobotController = URController(config)
controller.connect()
controller.move_to_pose([x, y, z, rx, ry, rz])
controller.get_current_pose()
```

#### IGameService
```python
from interfaces.robot_interfaces import IGameService

service: IGameService = RobotService()
service.initialize()
service.move_to_board_position(5)  # Centro do tabuleiro
service.place_piece(5, "jogador1")
```

#### IVisionSystem
```python
from interfaces.robot_interfaces import IVisionSystem

vision: IVisionSystem = ArucoVision()
vision.initialize()
detections = vision.detect_markers(frame)
positions = vision.get_board_positions()
```

---

## 🧪 Testes

### V1 - Testes de Interface

```bash
python test_interfaces.py
```

### V2 - Testes de Integração (Phase 5 - 56 testes ✅)

```bash
# Testes BoardCoordinateSystemV2 (34 testes)
pytest v2/services/tests/test_board_coordinate_system_v2.py -v

# Testes GameOrchestratorV2 (22 testes)
pytest v2/integration/tests/test_game_orchestrator_v2.py -v

# Executar todos os testes V2
pytest v2/ -v

# Com coverage report
pytest v2/ --cov=v2 --cov-report=html
```

### Testes Manuais V1

1. **Teste de Conexão**:
```bash
python -c "from services.robot_service import RobotService; r = RobotService(); print('Conectado' if r.connect() else 'Falhou')"
```

2. **Teste de Visão**:
```bash
python -c "from vision.camera_manager import CameraManager; c = CameraManager(); print('OK' if c.list_cameras() else 'Sem câmera')"
```

### Teste V2 Rápido

```bash
# Executar main_v2 em modo teste
python v2/main_v2.py --test

# Esperado: Sistema completo funcional sem hardware
```

**Cobertura de Testes V2**:
- ✅ Inicialização de componentes
- ✅ Calibração (sucesso/falha)
- ✅ Conversão de coordenadas (pixel → grid → mm)
- ✅ Validação de movimentos
- ✅ Execução de movimentos completos
- ✅ Integração com robô (mock)
- ✅ Gerenciamento de estado
- ✅ 100% passing rate (56/56 testes)

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

### Guidelines

- Siga os princípios SOLID já implementados
- Adicione testes para novas funcionalidades
- Atualize documentação conforme necessário
- Use type hints em Python
- Mantenha código limpo e bem documentado

---

## 📄 Licença

Este projeto é parte de um trabalho acadêmico/pesquisa.

---

## 👥 Autores

- Baseado em pesquisa em robótica e visão computacional

---

## 🙏 Agradecimentos

- Universal Robots pela plataforma robótica
- OpenCV pela biblioteca de visão computacional
- Comunidade Python pela excelente documentação

---

## 📞 Suporte

Para dúvidas e problemas:
1. Consulte a seção [Troubleshooting](#troubleshooting)
2. Leia a [documentação completa](ARCHITECTURE.md)
3. Abra uma issue no GitHub

---

**Versão**: 2.5 (Phase 5 - GameOrchestrator Integration Complete)
**Última Atualização**: 2025-11-17
**Status**: Phase 5 ✅ | Phase 6 🔄 (Testes com robô real)

### Quick Links
- 🧪 Testes: `pytest v2/ -v` (56/56 passing)
- 🎮 Demo V2: `python v2/main_v2.py --test`
- 📊 Status: [STATUS_ATUAL.md](STATUS_ATUAL.md)
- 🗺️ Roadmap: [ESTRATEGIA_PARALELA_V2.md](ESTRATEGIA_PARALELA_V2.md)
