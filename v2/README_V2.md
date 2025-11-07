# V2 - Parallel Development Structure

**Status**: Phase 2 - Setup complete, ready for Phase 3 (Vision rebuild)

**Created**: 2025-11-06 (Post Phase 1 cleanup)

## 🎯 Objetivo

V2 é uma reconstrução paralela do sistema, mantendo v1 como fallback seguro.

```
V1 (Frozen): produção com fallbacks
    ↓
V2 (Nova): arquitetura limpa, visão do zero, testes isolados
```

## 📁 Estrutura

```
v2/
├── config/                  ✅ Copiado (stable)
│   ├── __init__.py
│   └── config_completa.py
│
├── interfaces/              ✅ Copiado (stable)
│   ├── __init__.py
│   └── robot_interfaces.py
│
├── logic_control/           ✅ Copiado (stable)
│   ├── __init__.py
│   ├── tapatan_logic.py
│   ├── tapatan_ai.py
│   └── ur_controller.py
│
├── services/                ✅ Copiado (com ajustes planejados)
│   ├── robot_service.py
│   ├── game_service.py
│   ├── game_orchestrator.py
│   ├── board_coordinate_system.py
│   ├── physical_movement_executor.py
│   └── pose_validation_service.py
│
├── ui/                      ✅ Copiado (stable)
│   ├── game_display.py
│   └── menu_manager.py
│
├── diagnostics/             ✅ Copiado (opcional)
│   ├── robot_diagnostics.py
│   └── ur_diagnostics.py
│
├── integration/             🚧 TODO
│   └── vision_integration_v2.py  (nova implementação)
│
├── vision/                  🚧 TODO (CRITICAL)
│   ├── camera_simple.py         (nova)
│   ├── aruco_detector.py        (nova)
│   ├── grid_calculator.py       (nova)
│   ├── vision_manager.py        (nova)
│   └── tests/
│       ├── test_camera.py       (nova)
│       ├── test_aruco.py        (nova)
│       └── test_grid.py         (nova)
│
└── tests/                   🚧 TODO
    ├── test_board_coordinate_system.py
    ├── test_physical_movement.py
    └── test_game_flow.py
```

## ✅ Componentes Copiados de V1

### Estáveis (sem mudanças esperadas)
- `config/config_completa.py` - Configuração
- `interfaces/robot_interfaces.py` - Contratos (com IDLE state adicionado)
- `logic_control/` - Lógica do jogo (Tapatan, IA, UR control)
- `ui/` - Interface do usuário
- `diagnostics/` - Ferramentas de diagnóstico

### Com Potencial para Ajustes
- `services/board_coordinate_system.py` - Será ajustado para sync com nova visão
- `services/robot_service.py` - Será ajustado se necessário
- `services/game_orchestrator.py` - Orquestração
- `services/physical_movement_executor.py` - Executor de movimentos

## 🚧 TODO - Phase 3

### Semana 1: Visão Básica
- [ ] Implementar `vision/camera_simple.py` (captura apenas)
- [ ] Implementar `vision/aruco_detector.py` (detecção pura)
- [ ] Implementar `vision/grid_calculator.py` (mapear grid 3x3)
- [ ] Criar testes isolados para cada módulo

### Semana 2: Integração e Testes
- [ ] Implementar `vision/vision_manager.py` (orquestra tudo)
- [ ] Integrar com `services/` existentes
- [ ] Testar lado-a-lado com v1
- [ ] Ajustar `board_coordinate_system.py` se necessário

### Semana 3: Refinements
- [ ] Bug fixes e ajustes
- [ ] Documentar arquitetura v2
- [ ] Preparar para decisão final (v1 vs v2)

## 🔄 Como Rodar

### Modo Teste V1 (fallback seguro)
```bash
python main.py --test
```

### Modo Produção V1 (original)
```bash
python main.py
```

### Modo V2 (quando pronto)
```bash
python main.py --v2
# (será implementado após Phase 3)
```

## 🎯 Checklist Phase 2

- [x] Criar estrutura de diretórios `/v2/`
- [x] Copiar componentes estáveis de v1
- [ ] Criar __init__.py em todos os diretórios
- [ ] Criar v2/main.py wrapper
- [ ] Primeiro commit de Phase 2

## 📝 Notas

- **v1 é READ-ONLY**: Não modificar após Phase 1 cleanup
- **v2 é DEVELOPMENT**: Área para experimentação limpa
- **Sem pressão**: v1 é fallback em qualquer momento
- **Testes isolados**: Cada módulo v2 pode ser testado separadamente

## 🔗 Referências

- `ESTRATEGIA_PARALELA_V2.md` - Plano completo (5-6 semanas)
- `../v1-baseline` - Git tag para reverter se necessário
- INDICE_DOCUMENTACAO.md - Índice de toda documentação
