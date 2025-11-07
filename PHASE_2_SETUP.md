# Phase 2: V2 Setup - Parallel Development Structure

**Data**: 2025-11-06 (Dia após Phase 1 cleanup)

**Status**: ✅ CONCLUÍDO

## 🎯 Objetivo

Criar estrutura limpa de v2 (parallel development) enquanto v1 permanece frozen e funcional.

```
v1 (Frozen)
├── Fallback seguro
├── Pronto para produção
└── Não será modificado

v2 (Novo)
├── Arquitetura limpa
├── Visão será reescrita do zero
└── Testes isolados para cada módulo
```

---

## ✅ O Que Foi Feito

### 1. Estrutura de Diretórios Criada

```
c:\Venv\robotics_project\v2\
├── __init__.py
├── main_v2.py                (nova entrada de v2)
├── README_V2.md              (documentação estrutura)
│
├── config/                   ✅ Copiado
│   ├── __init__.py
│   └── config_completa.py
│
├── interfaces/               ✅ Copiado
│   ├── __init__.py
│   └── robot_interfaces.py
│
├── logic_control/            ✅ Copiado
│   ├── __init__.py
│   ├── tapatan_logic.py
│   ├── tapatan_ai.py
│   └── ur_controller.py
│
├── services/                 ✅ Copiado
│   ├── __init__.py
│   ├── robot_service.py
│   ├── game_service.py
│   ├── game_orchestrator.py
│   ├── board_coordinate_system.py
│   ├── physical_movement_executor.py
│   └── pose_validation_service.py
│
├── ui/                       ✅ Copiado
│   ├── __init__.py
│   ├── game_display.py
│   └── menu_manager.py
│
├── diagnostics/              ✅ Copiado (opcional)
│   ├── __init__.py
│   ├── robot_diagnostics.py
│   └── ur_diagnostics.py
│
├── integration/              🚧 Vazio (pronto para Phase 3)
│   └── __init__.py
│
├── vision/                   🚧 Vazio (pronto para Phase 3)
│   ├── __init__.py
│   └── README_VISION_V2.md   (plano detalhado)
│
└── tests/                    🚧 Vazio (pronto para Phase 3)
    └── __init__.py
```

### 2. Componentes Copiados de V1

#### Estáveis (sem mudanças esperadas)
- ✅ `config/config_completa.py` - Configuração
- ✅ `interfaces/robot_interfaces.py` - Contratos (RobotStatus com IDLE adicionado em Phase 1)
- ✅ `logic_control/` - Lógica do jogo (Tapatan, IA Minimax, UR control)
- ✅ `ui/` - Interface do usuário (GameDisplay, MenuManager)
- ✅ `diagnostics/` - Ferramentas (RobotDiagnostics, URDiagnostics)

#### Com Potencial para Ajustes
- ✅ `services/robot_service.py` - Serviço do robô
- ✅ `services/game_service.py` - Serviço do jogo
- ✅ `services/game_orchestrator.py` - Orquestração principal
- ✅ `services/board_coordinate_system.py` - Será ajustado para sync com nova visão
- ✅ `services/physical_movement_executor.py` - Executor de movimentos
- ✅ `services/pose_validation_service.py` - Validação de poses

### 3. Novo Entry Point

**Arquivo**: `v2/main_v2.py`

**Classe**: `TapatanInterfaceV2`

**Características**:
- Estrutura idêntica a v1 para agora
- Preparada para integração de nova visão
- Suporte a test_mode como v1
- Comentários TODOs para Phase 3

### 4. Suporte de Flags em main.py

**Uso**:
```bash
# Versão 1 (padrão, produção)
python main.py

# Versão 1 (modo teste)
python main.py --test

# Versão 2 (quando pronto - Phase 3 completo)
python main.py --v2

# Versão 2 (modo teste)
python main.py --v2 --test
```

### 5. Documentação Criada

| Arquivo | Conteúdo |
|---------|----------|
| `v2/README_V2.md` | Visão geral da estrutura v2 |
| `v2/vision/README_VISION_V2.md` | Plano detalhado da visão (4 módulos) |
| `PHASE_2_SETUP.md` | Este arquivo (o que foi feito) |

---

## 📊 Comparação V1 vs V2

| Aspecto | V1 | V2 |
|---------|----|----|
| Status | Frozen (Phase 1 cleanup) | Setup (Phase 2) |
| Modificações | Não será alterado | Em desenvolvimento |
| Visão | Existente (com bugs) | A ser reescrita |
| Testes | Não isolados | Isolados por módulo |
| Fallback | N/A | v1 é fallback |
| Pronto para | Produção | Phase 3 (visão) |

---

## 🚀 Como Usar V2 Agora

### Verificar estrutura
```bash
ls -la v2/
# Mostrar todos os componentes copiados
```

### Testar compilação
```bash
cd v2
python -m py_compile main_v2.py
# Sem erros = estrutura OK
```

### Entrar em v2 (quando Phase 3 completo)
```bash
python main.py --v2
# Entrará em v2 em vez de v1
```

---

## 🔧 Próximas Etapas (Phase 3)

### Semana 1: Visão Básica
- [ ] Implementar `vision/camera_simple.py` (só captura)
- [ ] Implementar `vision/aruco_detector.py` (detecção)
- [ ] Implementar `vision/grid_calculator.py` (mapear grid)
- [ ] Criar testes isolados para cada

### Semana 2: Integração
- [ ] Implementar `vision/vision_manager.py`
- [ ] Adaptar `integration/vision_integration_v2.py`
- [ ] Integrar com game loop
- [ ] Testar lado-a-lado com v1

### Semana 3: Refinement
- [ ] Bug fixes
- [ ] Documentar arquitetura v2
- [ ] Preparar decisão final (v1 vs v2)

---

## 🎯 Checklist Phase 2

- [x] Criar estrutura `/v2/` com 9 diretórios
- [x] Copiar componentes estáveis de v1
- [x] Criar `__init__.py` em todos os diretórios
- [x] Criar `v2/main_v2.py` entry point
- [x] Atualizar `main.py` com suporte a --v2
- [x] Criar `v2/README_V2.md` (estrutura)
- [x] Criar `v2/vision/README_VISION_V2.md` (plano visão)
- [x] Criar `PHASE_2_SETUP.md` (este arquivo)

---

## 💾 Git Status Phase 2

**Commit esperado**:
```bash
git add v2/ PHASE_2_SETUP.md
git commit -m "Phase 2: v2 parallel development setup complete

- Create /v2/ directory structure with 9 subdirectories
- Copy stable components from v1 (config, logic, services, ui)
- Create v2/main_v2.py entry point
- Add --v2 flag support to main.py
- Document v2 structure and Phase 3 vision plan
- v1 frozen and ready as fallback

This enables:
- Parallel development of v2
- Experimental new vision system
- Isolated testing per module
- Zero risk (v1 is fallback)

Total files: ~30 copied from v1 + new v2 specific files
Status: Ready for Phase 3 (Vision rebuild from zero)
"
```

---

## 📈 Progresso Global

```
Phase 1 (Cleanup): ✅ COMPLETO (3 dias)
├── Remove legado (5-8%)
├── Consolidate enums
├── Refactor test interface
└── v1 baseline tag

Phase 2 (Setup): ✅ COMPLETO (1 dia)
├── Create v2 structure
├── Copy stable components
├── Create entry point
└── Document vision plan

Phase 3 (Vision): 🚧 PRÓXIMO (2-3 semanas)
├── camera_simple.py
├── aruco_detector.py
├── grid_calculator.py
├── vision_manager.py
└── integration

Phase 4 (Coords): 🚧 PENDING (1 semana)
└── board_coordinate_system_v2.py

Phase 5 (Decision): 🚧 PENDING (1-2 dias)
└── Decidir v1 vs v2
```

---

## 🎓 Lições Aprendidas

1. **Estrutura Modular**: Cada componente v2 pode ser testado isoladamente
2. **Zero Risco**: v1 é fallback em qualquer momento
3. **Separação Clara**: v1 = produção, v2 = experimentação
4. **Documentação**: Cada fase bem documentada

---

## 📞 Próxima Ação

**Quando**: Após aprovação desta Phase 2

**O que**: Iniciar Phase 3 (Visão)

**Primeiro passo**: Implementar `v2/vision/camera_simple.py` com testes

**Resultado esperado**: Câmera funcionando isoladamente, testável sem o resto do sistema

---

**Conclusão**: V2 está pronta para receber a nova implementação de visão.

Pode começar Phase 3? 🚀
