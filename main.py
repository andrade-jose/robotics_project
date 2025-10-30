"""
Main - Tapatan Robótico com Sistema de Visão ArUco Integrado
===========================================================
Interface principal do jogo Tapatan com robô e visão ArUco
Sistema completo para detecção de marcadores, controle do robô e lógica do jogo

ARQUITETURA REFATORADA:
- TapatanInterface: Coordenador principal (orquestra componentes)
- GameDisplay (ui/): Apresentação e visualização
- MenuManager (ui/): Gerenciamento de menus e ações
- VisionIntegration (integration/): Sistema de visão ArUco
"""

# --- CORREÇÃO UNICODE: Deve ser a primeira coisa no script ---
import sys
import codecs
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except (TypeError, AttributeError):
        # Em alguns ambientes (como IDEs), stdout/stderr podem não ter um .buffer
        # ou o atributo pode ser somente leitura. A codificação nesses
        # ambientes geralmente já é correta.
        pass
# --- Fim da correção ---

import time
import traceback
from typing import Optional

# Imports do sistema robótico
try:
    from services.game_orchestrator import TapatanOrchestrator
    from config.config_completa import ConfigRobo, ConfigJogo
except ImportError:
    print("AVISO: Módulos 'services' ou 'config' não encontrados. O programa não funcionará corretamente.")
    # Classes placeholder para permitir que o script seja analisado sem erros
    class TapatanOrchestrator: pass
    class ConfigRobo: pass
    class ConfigJogo: pass

# Imports dos novos componentes refatorados
from ui.game_display import GameDisplay
from ui.menu_manager import MenuManager
from integration.vision_integration import VisionIntegration, VISION_AVAILABLE


class TapatanInterface:
    """
    Interface principal do jogo Tapatan com sistema de visão ArUco integrado.

    RESPONSABILIDADE: Coordenar os componentes do sistema (não implementar toda a lógica).
    Delega para:
    - GameDisplay: Toda a apresentação visual
    - MenuManager: Gerenciamento de menus e ações
    - VisionIntegration: Sistema de visão
    - TapatanOrchestrator: Lógica do jogo e controle do robô
    """

    def __init__(self):
        """Inicializa a interface principal (modo produção)."""
        # Configurações
        self.config_robo = ConfigRobo()
        self.config_jogo = ConfigJogo()

        # Orquestrador do jogo
        try:
            self.orquestrador = TapatanOrchestrator(self.config_robo, self.config_jogo)
            print("✅ Orquestrador do jogo inicializado.")
        except Exception as e:
            print(f"❌ Falha ao inicializar o Orquestrador: {e}")
            self.orquestrador = None

        # Componentes da UI e integração
        self.game_display = GameDisplay(vision_available=VISION_AVAILABLE)
        self.vision_integration = VisionIntegration() if VISION_AVAILABLE else None
        self.menu_manager = MenuManager(self.orquestrador, self.vision_integration)

        print("\n🎮 TapatanInterface inicializada")
        if VISION_AVAILABLE:
            print("📹 Sistema de visão disponível")
        else:
            print("⚠️ Sistema de visão não disponível - continuará sem visão")

    # ========== INICIALIZAÇÃO E FINALIZAÇÃO ==========

    def inicializar_sistema(self) -> bool:
        """Inicializa os componentes principais do sistema."""
        print("🚀 Inicializando sistema Tapatan...")

        if not self.orquestrador:
            print("❌ Orquestrador não foi criado. Não é possível inicializar.")
            return False

        try:
            if self.orquestrador.inicializar():
                print("✅ Sistema robótico inicializado com sucesso!")
                return True
            else:
                print("❌ Falha na inicialização do sistema robótico!")
                return False
        except Exception as e:
            print(f"❌ Erro na inicialização: {e}")
            return False

    def finalizar_sistema(self):
        """Finaliza todos os sistemas de forma segura."""
        print("\n🔚 Finalizando sistema...")

        if self.vision_integration and self.vision_integration.vision_active:
            self.vision_integration.parar_sistema_visao()

        if self.orquestrador:
            self.orquestrador.finalizar()

        print("✅ Sistema finalizado!")

    # ========== EXECUÇÃO DA PARTIDA ==========

    def executar_partida(self):
        """
        Executa uma partida completa com sistema de visão integrado.

        Coordena:
        1. Preparação do tabuleiro (se visão disponível)
        2. Inicialização da partida
        3. Loop principal do jogo
        4. Finalização
        """
        if not self.orquestrador:
            print("❌ Orquestrador não inicializado! Impossível iniciar.")
            return

        print("\n🎮 Iniciando nova partida...")

        # Prepara sistema de visão se disponível
        usar_visao = False
        if VISION_AVAILABLE and self.vision_integration:
            usar_visao = self.menu_manager.preparar_tabuleiro_com_visao()
            if not usar_visao and self.vision_integration.vision_active:
                # Se a preparação foi cancelada, para a visão
                self.vision_integration.parar_sistema_visao()
                self.vision_integration.show_vision_window = False
                return

        # Inicia partida no orquestrador
        if not self.orquestrador.iniciar_partida():
            print("❌ Erro ao iniciar a partida no orquestrador!")
            if usar_visao:
                self.vision_integration.parar_sistema_visao()
            return

        # Loop principal da partida
        try:
            while True:
                estado_jogo = self.orquestrador.game_service.obter_estado_jogo()

                # Mostra tabuleiro (com ou sem visão)
                if usar_visao:
                    estado_visao = self.vision_integration.obter_estado_visao()
                    self.game_display.mostrar_tabuleiro_com_visao(estado_jogo, estado_visao)
                else:
                    self.game_display.mostrar_tabuleiro(estado_jogo)

                self.game_display.mostrar_info_jogo(estado_jogo)

                # Verifica fim de jogo
                if estado_jogo['jogo_terminado']:
                    print("🎉 Jogo terminado!")
                    input("   Pressione ENTER para voltar ao menu...")
                    break

                # Turno do humano (jogador 2)
                if estado_jogo['jogador_atual'] == 2:
                    if usar_visao:
                        estado_visao = self.vision_integration.obter_estado_visao()
                        jogada = self.game_display.obter_jogada_humano_com_visao(estado_jogo, estado_visao)
                    else:
                        jogada = self.game_display.obter_jogada_humano(estado_jogo)

                    if jogada is None:
                        break

                    resultado = self.orquestrador.processar_jogada_humano(**jogada)

                    if not resultado['sucesso']:
                        print(f"   ❌ Erro: {resultado.get('mensagem', 'Jogada inválida')}")
                        time.sleep(1)
                        continue

                    print("   ✅ Sua jogada foi processada!")

                    # Se o robô respondeu imediatamente
                    if 'jogada_robo' in resultado:
                        jr = resultado['jogada_robo']['jogada']
                        if 'posicao' in jr:
                            print(f"   🤖 Robô respondeu colocando na pos {jr['posicao']}")
                        else:
                            print(f"   🤖 Robô respondeu movendo de {jr['origem']} para {jr['destino']}")
                        self.game_display.aguardar_confirmacao_robo()

                # Turno do robô (jogador 1)
                elif estado_jogo['jogador_atual'] == 1:
                    input("   🤖 Vez do robô. Pressione ENTER para ele jogar...")
                    resultado = self.orquestrador.executar_jogada_robo()

                    if resultado['sucesso']:
                        j = resultado['jogada']
                        if 'posicao' in j:
                            print(f"   🤖 Robô colocou na posição {j['posicao']}")
                        else:
                            print(f"   🤖 Robô moveu de {j['origem']} para {j['destino']}")
                        self.game_display.aguardar_confirmacao_robo()
                    else:
                        print(f"❌ Erro na jogada do robô: {resultado['mensagem']}")
                        break

        except KeyboardInterrupt:
            print("\n\n🛑 Partida interrompida!")
        except Exception as e:
            print(f"\n❌ Erro fatal durante a partida: {e}")
            traceback.print_exc()
        finally:
            if usar_visao and self.vision_integration:
                # A visão continua rodando durante o jogo, então paramos aqui
                self.vision_integration.parar_sistema_visao()
                self.vision_integration.show_vision_window = False

    # ========== PONTO DE ENTRADA ==========

    def executar(self):
        """Ponto de entrada principal da interface."""
        self.game_display.mostrar_banner()

        if self.inicializar_sistema():
            try:
                while True:
                    # Menu principal retorna True para iniciar partida, False para sair
                    deve_executar_partida = self.menu_manager.menu_principal()
                    if not deve_executar_partida:
                        break
                    self.executar_partida()

                print("\n👋 Até logo!")

            except Exception as e:
                print(f"❌ Erro inesperado na execução: {e}")
                traceback.print_exc()
        else:
            print("❌ Não foi possível inicializar o sistema!")

        self.finalizar_sistema()


class TapatanTestInterface(TapatanInterface):
    """
    Interface de teste que herda da principal para reutilizar código
    e sobrepõe apenas o necessário para o modo de teste.
    """

    def __init__(self):
        """Inicializa a interface em modo de teste."""
        # Configurações específicas de teste
        self.config_robo = ConfigRobo()
        self.config_robo.pausa_entre_jogadas = 1.0
        self.config_robo.velocidade_padrao = 0.05
        self.config_robo.auto_calibrar = False

        self.config_jogo = ConfigJogo(profundidade_ia=3, debug_mode=True)

        # Orquestrador com configs de teste
        try:
            self.orquestrador = TapatanOrchestrator(self.config_robo, self.config_jogo)
            print("✅ Orquestrador do jogo inicializado em MODO TESTE.")
        except Exception as e:
            print(f"❌ Falha ao inicializar o Orquestrador em MODO TESTE: {e}")
            self.orquestrador = None

        # Componentes da UI (sem visão no modo teste)
        self.game_display = GameDisplay(vision_available=False)
        self.vision_integration = None
        self.menu_manager = MenuManager(self.orquestrador, None)

        print("🧪 TapatanTestInterface inicializada.")

    def mostrar_banner_teste(self):
        """Mostra o banner específico para o modo de teste."""
        print("=" * 70)
        print("       🧪 TAPATAN ROBÓTICO - MODO TESTE 🤖")
        print("=" * 70)
        print("  Testando movimentação e lógica do jogo (SEM visão)")
        print("=" * 70)

    def executar_partida(self):
        """Executa uma partida simplificada para testes, sem visão."""
        if not self.orquestrador or not self.orquestrador.iniciar_partida():
            print("❌ Erro ao iniciar a partida de teste!")
            return

        print("\n🧪 Iniciando partida de teste (sem visão)...")

        try:
            while True:
                estado_jogo = self.orquestrador.game_service.obter_estado_jogo()
                self.game_display.mostrar_tabuleiro(estado_jogo)
                self.game_display.mostrar_info_jogo(estado_jogo)

                if estado_jogo['jogo_terminado']:
                    print("🎉 Jogo de teste terminado!")
                    input("   Pressione ENTER para voltar ao menu...")
                    break

                if estado_jogo['jogador_atual'] == 2:
                    jogada = self.game_display.obter_jogada_humano(estado_jogo)
                    if jogada is None:
                        break

                    resultado = self.orquestrador.processar_jogada_humano(**jogada)
                    if not resultado['sucesso']:
                        print(f"   ❌ Erro: {resultado.get('mensagem', 'Jogada inválida')}")
                        continue

                    print("   ✅ Sua jogada foi processada!")
                    if 'jogada_robo' in resultado:
                        self.game_display.aguardar_confirmacao_robo()

                elif estado_jogo['jogador_atual'] == 1:
                    input("   🤖 Vez do robô. Pressione ENTER para ele jogar...")
                    resultado = self.orquestrador.executar_jogada_robo()
                    if resultado['sucesso']:
                        self.game_display.aguardar_confirmacao_robo()
                    else:
                        print(f"❌ Erro na jogada do robô: {resultado['mensagem']}")
                        break

        except KeyboardInterrupt:
            print("\n\n🛑 Partida de teste interrompida!")
        except Exception as e:
            print(f"\n❌ Erro fatal na partida de teste: {e}")

    def executar(self):
        """Ponto de entrada para o modo de teste."""
        self.mostrar_banner_teste()

        if self.inicializar_sistema():
            try:
                while True:
                    deve_executar_partida = self.menu_manager.menu_principal()
                    if not deve_executar_partida:
                        break
                    self.executar_partida()

                print("\n👋 Até logo!")

            except Exception as e:
                print(f"❌ Erro inesperado na execução: {e}")
                traceback.print_exc()
        else:
            print("❌ Não foi possível inicializar o sistema!")

        self.finalizar_sistema()


def main():
    """Função principal que decide qual interface instanciar."""
    if "--test" in sys.argv:
        print("🧪 Modo TESTE ativado")
        interface = TapatanTestInterface()
    else:
        print("🎮 Modo PRODUÇÃO ativado")
        interface = TapatanInterface()

    try:
        interface.executar()
    except KeyboardInterrupt:
        print("\n\n👋 Programa interrompido pelo usuário!")
    except Exception as e:
        print(f"❌ Erro fatal e não tratado na execução: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()