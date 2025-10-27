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
- **Interface de Usuário**: Menu interativo para controle do sistema

### Como Funciona

1. **Setup**: Posicione o tabuleiro físico na área de trabalho do robô
2. **Calibração**: Calibre as 9 posições do tabuleiro ou use visão ArUco
3. **Jogo**: Jogue contra o robô - ele detecta suas jogadas e responde automaticamente
4. **Segurança**: Múltiplas camadas de validação garantem movimentos seguros

---

## ✨ Características

### Jogabilidade
- ✅ Jogo humano vs robô
- ✅ Dois modos: com ou sem visão computacional
- ✅ IA usando algoritmo Minimax com poda alpha-beta
- ✅ Detecção automática de vitória/empate

### Sistema de Visão
- ✅ Detecção de marcadores ArUco em tempo real
- ✅ Calibração automática do tabuleiro
- ✅ Detecção de peças posicionadas
- ✅ Thread separada para processamento contínuo

### Controle do Robô
- ✅ Comunicação RTDE com robô UR
- ✅ Validação multi-camadas de poses:
  - Formato (6 valores)
  - Workspace (limites cartesianos)
  - Rotação (limites angulares)
  - Alcançabilidade (distância máxima)
  - Segurança UR (limites do fabricante)
- ✅ Correção automática de poses inválidas
- ✅ Movimentos com pontos intermediários para segurança
- ✅ Sistema de diagnósticos e estatísticas

### Arquitetura
- ✅ Design modular baseado em princípios SOLID
- ✅ Separação clara de responsabilidades (SRP)
- ✅ Interfaces bem definidas para todos os componentes
- ✅ 4 camadas arquiteturais (Presentation, Application, Domain, Infrastructure)
- ✅ Padrões de design (Facade, Command, Strategy, Observer)

---

## 🏗️ Arquitetura

O sistema é organizado em 4 camadas:

```
┌─────────────────────────────────────┐
│    Presentation Layer               │  UI, menus, visualização
│    • main.py                        │
│    • ui/ (GameDisplay, MenuManager) │
├─────────────────────────────────────┤
│    Application Layer                │  Orquestração, facades
│    • services/ (Orchestrator)       │
│    • integration/ (Vision)          │
├─────────────────────────────────────┤
│    Domain Layer                     │  Regras de negócio, interfaces
│    • interfaces/                    │
│    • services/ (Validation, Coords) │
├─────────────────────────────────────┤
│    Infrastructure Layer             │  Hardware, drivers
│    • logic_control/ (URController)  │
│    • vision/ (ArUco, Camera)        │
│    • diagnostics/                   │
└─────────────────────────────────────┘
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

### Iniciar o Sistema

```bash
python main.py
```

### Menu Principal

Ao iniciar, você verá:

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
  - Estrutura de camadas
  - Componentes principais
  - Fluxos de dados
  - Decisões arquiteturais (ADRs)

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

### Executar Testes de Interface

```bash
python test_interfaces.py
```

### Testes Manuais

1. **Teste de Conexão**:
```bash
python -c "from services.robot_service import RobotService; r = RobotService(); print('Conectado' if r.connect() else 'Falhou')"
```

2. **Teste de Visão**:
```bash
python -c "from vision.camera_manager import CameraManager; c = CameraManager(); print('OK' if c.list_cameras() else 'Sem câmera')"
```

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

- Desenvolvido com auxílio de Claude (Anthropic)
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

**Versão**: 2.0 (Pós-Refatoração)
**Última Atualização**: 2025-10-27
