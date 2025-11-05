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

    def __init__(self, test_mode: bool = False):
        """
        Inicializa a interface principal.

        Args:
            test_mode: Se True, usa configurações de teste. Se False, usa produção.
        """
        # Configurações (ajustadas para modo teste se necessário)
        self.config_robo = ConfigRobo()
        if test_mode:
            self.config_robo.pausa_entre_jogadas = 1.0
            self.config_robo.velocidade_padrao = 0.05
            self.config_robo.auto_calibrar = False

        self.config_jogo = ConfigJogo(profundidade_ia=3 if test_mode else 5, debug_mode=test_mode)
        self.test_mode = test_mode

        # Orquestrador do jogo
        try:
            self.orquestrador = TapatanOrchestrator(self.config_robo, self.config_jogo)
            modo_str = "TESTE" if test_mode else "PRODUÇÃO"
            print(f"[OK] Orquestrador do jogo inicializado em MODO {modo_str}.")
        except Exception as e:
            print(f"[ERRO] Falha ao inicializar o Orquestrador: {e}")
            self.orquestrador = None

        # Componentes da UI e integração
        # Em modo teste, sempre desativa visão
        vision_mode = VISION_AVAILABLE and not test_mode
        self.game_display = GameDisplay(vision_available=vision_mode)
        self.vision_integration = VisionIntegration() if vision_mode else None
        self.menu_manager = MenuManager(self.orquestrador, self.vision_integration)

        print("\n[SISTEMA] TapatanInterface inicializada")
        if test_mode:
            print("[TESTE] Modo de teste ativado - visão desativada")
        elif vision_mode:
            print("[VISAO] Sistema de visão disponível")
        else:
            print("[AVISO] Sistema de visão não disponível - continuará sem visão")

    # ========== INICIALIZAÇÃO E FINALIZAÇÃO ==========

    def inicializar_sistema(self) -> bool:
        """Inicializa os componentes principais do sistema."""
        print("[SISTEMA] Inicializando sistema Tapatan...")

        if not self.orquestrador:
            print("[ERRO] Orquestrador não foi criado. Não é possível inicializar.")
            return False

        try:
            if self.orquestrador.inicializar():
                print("[OK] Sistema robótico inicializado com sucesso!")
                return True
            else:
                print("[ERRO] Falha na inicialização do sistema robótico!")
                return False
        except Exception as e:
            print(f"[ERRO] Erro na inicialização: {e}")
            return False

    def finalizar_sistema(self):
        """Finaliza todos os sistemas de forma segura."""
        print("\n[SISTEMA] Finalizando sistema...")

        if self.vision_integration and self.vision_integration.vision_active:
            self.vision_integration.parar_sistema_visao()

        if self.orquestrador:
            self.orquestrador.finalizar()

        print("[OK] Sistema finalizado!")

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
            print("[ERRO] Orquestrador não inicializado! Impossível iniciar.")
            return

        print("\n[INICIO] Iniciando nova partida...")

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

                if usar_visao and self.vision_integration:
                    if not self.vision_integration.vision_active:
                        print("[AVISO] Sistema de visão parou - continuando sem visão")
                        usar_visao = False

                # Mostra tabuleiro (com ou sem visão)
                if usar_visao:
                    estado_visao = self.vision_integration.obter_estado_visao()
                    self.game_display.mostrar_tabuleiro_com_visao(estado_jogo, estado_visao)
                else:
                    self.game_display.mostrar_tabuleiro(estado_jogo)

                self.game_display.mostrar_info_jogo(estado_jogo)

                # Verifica fim de jogo
                if estado_jogo['jogo_terminado']:
                    print("[OK] Jogo terminado!")
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
                        print(f"   [ERRO] Erro: {resultado.get('mensagem', 'Jogada inválida')}")
                        time.sleep(1)
                        continue

                    print("   [OK] Sua jogada foi processada!")

                    # Se o robô respondeu imediatamente
                    if 'jogada_robo' in resultado:
                        jr = resultado['jogada_robo']['jogada']
                        if 'posicao' in jr:
                            print(f"   [ROBO] Robô respondeu colocando na pos {jr['posicao']}")
                        else:
                            print(f"   [ROBO] Robô respondeu movendo de {jr['origem']} para {jr['destino']}")
                        self.game_display.aguardar_confirmacao_robo()

                # Turno do robô (jogador 1)
                elif estado_jogo['jogador_atual'] == 1:
                    input("   [ROBO] Vez do robô. Pressione ENTER para ele jogar...")
                    resultado = self.orquestrador.executar_jogada_robo()

                    if resultado['sucesso']:
                        j = resultado['jogada']
                        if 'posicao' in j:
                            print(f"   [ROBO] Robô colocou na posição {j['posicao']}")
                        else:
                            print(f"   [ROBO] Robô moveu de {j['origem']} para {j['destino']}")
                        self.game_display.aguardar_confirmacao_robo()
                    else:
                        print(f"[ERRO] Erro na jogada do robô: {resultado['mensagem']}")
                        break

        except KeyboardInterrupt:
            print("\n\n[PARADA] Partida interrompida!")
        except Exception as e:
            print(f"\n[ERRO] Erro fatal durante a partida: {e}")
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

                print("\n[OK] Até logo!")

            except Exception as e:
                print(f"[ERRO] Erro inesperado na execução: {e}")
                traceback.print_exc()
        else:
            print("[ERRO] Não foi possível inicializar o sistema!")

        self.finalizar_sistema()


def main():
    """
    Função principal que cria a interface apropriada baseado em argumentos da linha de comando.

    Argumentos:
        --test: Ativa modo de teste (sem visão, velocidades reduzidas)
    """
    test_mode = "--test" in sys.argv
    modo_str = "TESTE" if test_mode else "PRODUÇÃO"
    print(f"[SISTEMA] Modo {modo_str} ativado")

    # Factory pattern: criar instância com configuração apropriada
    interface = TapatanInterface(test_mode=test_mode)

    try:
        interface.executar()
    except KeyboardInterrupt:
        print("\n\n[OK] Programa interrompido pelo usuário!")
    except Exception as e:
        print(f"[ERRO] Erro fatal e não tratado na execução: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()