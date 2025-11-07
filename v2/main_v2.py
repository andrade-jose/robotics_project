"""
V2 Entry Point - Parallel Development Version

This is the entry point for v2 (new clean implementation).
v1 is frozen and serves as a fallback.

Usage:
    python main.py --v2          # Start v2 (when ready)

Current status: Phase 2 (Setup) - Vision not yet implemented
Next phase: Phase 3 (Vision rebuild from zero)
"""

import sys
import os
import traceback
import time

# Add v2 to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from config.config_completa import ConfigRobo, ConfigJogo
from services.game_orchestrator import TapatanOrchestrator
from ui.game_display import GameDisplay
from ui.menu_manager import MenuManager

# TODO: Vision will be imported here in Phase 3
# from integration.vision_integration_v2 import VisionIntegration


class TapatanInterfaceV2:
    """
    V2 Interface - New parallel development.

    Currently identical to v1 but prepared for:
    - New vision system integration
    - Potential improvements to BoardCoordinateSystem
    - Better testing structure
    """

    def __init__(self, test_mode: bool = False):
        """Initialize v2 interface."""
        self.config_robo = ConfigRobo()
        if test_mode:
            self.config_robo.pausa_entre_jogadas = 1.0
            self.config_robo.velocidade_padrao = 0.05
            self.config_robo.auto_calibrar = False

        self.config_jogo = ConfigJogo(profundidade_ia=3 if test_mode else 5, debug_mode=test_mode)
        self.test_mode = test_mode

        try:
            self.orquestrador = TapatanOrchestrator(self.config_robo, self.config_jogo)
            modo_str = "TESTE" if test_mode else "PRODUÇÃO"
            print(f"[OK] Orquestrador v2 inicializado em MODO {modo_str}.")
        except Exception as e:
            print(f"[ERRO] Falha ao inicializar Orquestrador v2: {e}")
            self.orquestrador = None

        # TODO: Vision integration v2 when ready
        vision_available = False  # Será True quando fase 3 completar
        self.game_display = GameDisplay(vision_available=vision_available)
        self.vision_integration = None  # TODO: Será VisionIntegrationV2()
        self.menu_manager = MenuManager(self.orquestrador, self.vision_integration)

        print("\n[SISTEMA] TapatanInterface V2 inicializada")
        print("[V2] Sistema em fase de desenvolvimento paralelo")
        if test_mode:
            print("[TESTE] Modo teste - visão desativada")

    def inicializar_sistema(self) -> bool:
        """Initialize system components."""
        print("[SISTEMA] Inicializando sistema Tapatan V2...")

        if not self.orquestrador:
            print("[ERRO] Orquestrador não foi criado.")
            return False

        try:
            if self.orquestrador.inicializar():
                print("[OK] Sistema robótico V2 inicializado!")
                return True
            else:
                print("[ERRO] Falha na inicialização!")
                return False
        except Exception as e:
            print(f"[ERRO] Erro na inicialização: {e}")
            return False

    def finalizar_sistema(self):
        """Finalize system safely."""
        print("\n[SISTEMA] Finalizando sistema V2...")

        if self.vision_integration:
            pass  # TODO: Para visão quando implementada

        if self.orquestrador:
            self.orquestrador.finalizar()

        print("[OK] Sistema V2 finalizado!")

    def executar_partida(self):
        """Execute game match."""
        if not self.orquestrador or not self.orquestrador.iniciar_partida():
            print("[ERRO] Erro ao iniciar partida!")
            return

        print("\n[V2] Iniciando partida V2...")

        try:
            while True:
                estado_jogo = self.orquestrador.game_service.obter_estado_jogo()
                self.game_display.mostrar_tabuleiro(estado_jogo)
                self.game_display.mostrar_info_jogo(estado_jogo)

                if estado_jogo['jogo_terminado']:
                    print("[OK] Jogo terminado!")
                    input("   Pressione ENTER para voltar ao menu...")
                    break

                if estado_jogo['jogador_atual'] == 2:
                    jogada = self.game_display.obter_jogada_humano(estado_jogo)
                    if jogada is None:
                        break

                    resultado = self.orquestrador.processar_jogada_humano(**jogada)
                    if not resultado['sucesso']:
                        print(f"   [ERRO] {resultado.get('mensagem', 'Inválida')}")
                        continue

                    print("   [OK] Jogada processada!")
                    if 'jogada_robo' in resultado:
                        self.game_display.aguardar_confirmacao_robo()

                elif estado_jogo['jogador_atual'] == 1:
                    input("   [ROBO] Pressione ENTER para o robô jogar...")
                    resultado = self.orquestrador.executar_jogada_robo()
                    if resultado['sucesso']:
                        self.game_display.aguardar_confirmacao_robo()
                    else:
                        print(f"[ERRO] {resultado['mensagem']}")
                        break

        except KeyboardInterrupt:
            print("\n\n[PARADA] Partida interrompida!")
        except Exception as e:
            print(f"\n[ERRO] Erro na partida: {e}")

    def executar(self):
        """Main entry point."""
        self.game_display.mostrar_banner()

        if self.inicializar_sistema():
            try:
                while True:
                    deve_executar_partida = self.menu_manager.menu_principal()
                    if not deve_executar_partida:
                        break
                    self.executar_partida()

                print("\n[OK] Até logo!")

            except Exception as e:
                print(f"[ERRO] Erro inesperado: {e}")
                traceback.print_exc()
        else:
            print("[ERRO] Não foi possível inicializar!")

        self.finalizar_sistema()


def main_v2():
    """Main function for v2."""
    test_mode = "--test" in sys.argv
    modo_str = "TESTE" if test_mode else "PRODUÇÃO"
    print(f"[V2] Iniciando em MODO {modo_str}")
    print("[V2] Status: Phase 2 (Setup) - Visão a implementar em Phase 3")
    print("")

    interface = TapatanInterfaceV2(test_mode=test_mode)

    try:
        interface.executar()
    except KeyboardInterrupt:
        print("\n\n[OK] Programa interrompido!")
    except Exception as e:
        print(f"[ERRO] Erro não tratado: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main_v2()
