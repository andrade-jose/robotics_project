"""
MenuManager - Gerenciador de Menus e Ações do Sistema
======================================================
Responsável por toda a interface de menu e ações do sistema:
- Menu principal
- Calibração do robô
- Testes do sistema de visão
- Status do sistema
- Parada de emergência
"""

import sys
import time
from typing import Optional, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from services.game_orchestrator import TapatanOrchestrator
    from integration.vision_integration import VisionIntegration

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


class MenuManager:
    """
    Gerencia o menu principal e todas as ações do sistema.

    Responsabilidades:
    - Exibir menu principal e processar opções
    - Executar calibração do sistema robótico
    - Testar sistema de visão
    - Mostrar status completo
    - Parada de emergência
    - Preparação do tabuleiro para partida
    """

    def __init__(self,
                 orquestrador: 'TapatanOrchestrator',
                 vision_integration: Optional['VisionIntegration'] = None):
        """
        Inicializa o gerenciador de menus.

        Args:
            orquestrador: Instância do orquestrador do jogo
            vision_integration: Instância do sistema de visão (opcional)
        """
        self.orquestrador = orquestrador
        self.vision_integration = vision_integration

    # ========== MENU PRINCIPAL ==========

    def menu_principal(self) -> bool:
        """
        Exibe o menu principal e processa a escolha do usuário.

        Returns:
            False quando o usuário escolhe sair, True caso contrário
        """
        while True:
            print("\n" + "=" * 50)
            print("           MENU PRINCIPAL - TAPATAN COM VISÃO")
            print("=" * 50)
            print("  1. 🚀 Iniciar nova partida")
            print("  2. 🔧 Calibrar sistema robótico")
            print("  3. 📹 Testar sistema de visão")
            print("  4. 📊 Ver status do sistema")
            print("  5. 🚨 Parada de emergência")
            print("  6. 👋 Sair")
            print("=" * 50)

            try:
                opcao = input("   Escolha uma opção: ").strip()

                if opcao == "1":
                    return True  # Sinaliza que deve executar partida
                elif opcao == "2":
                    self.calibrar_sistema()
                elif opcao == "3":
                    self.testar_sistema_visao()
                elif opcao == "4":
                    self.mostrar_status_completo()
                elif opcao == "5":
                    self.parada_emergencia()
                elif opcao == "6":
                    return False  # Sinaliza que deve sair
                else:
                    print("   ❌ Opção inválida!")

            except KeyboardInterrupt:
                return False

    # ========== CALIBRAÇÃO DO SISTEMA ==========

    def calibrar_sistema(self):
        """Executa a rotina de calibração do sistema robótico."""
        print("\n🔧 Iniciando calibração do sistema robótico...")

        if not (self.orquestrador and hasattr(self.orquestrador, 'calibrar_sistema')):
            print("⚠️ Função de calibração não implementada no orquestrador.")
            input("Pressione ENTER para voltar...")
            return

        print("⚠️ O robô visitará algumas posições do tabuleiro.")
        confirmacao = input("   Continuar? (s/N): ").lower().strip()

        if confirmacao.startswith('s'):
            if self.orquestrador.calibrar_sistema():
                print("✅ Calibração concluída com sucesso!")
            else:
                print("❌ Falha na calibração!")
        else:
            print("Calibração cancelada.")

    # ========== TESTE DO SISTEMA DE VISÃO ==========

    def testar_sistema_visao(self):
        """Testa o sistema de visão de forma isolada."""
        print("\n📹 Iniciando teste do sistema de visão...")

        if not self.vision_integration:
            print("❌ Sistema de visão não disponível.")
            input("Pressione ENTER para voltar...")
            return

        if not self.vision_integration.inicializar_sistema_visao():
            input("Pressione ENTER para voltar...")
            return

        print("\n" + "+" + "-" * 58 + "+")
        print("| 🎥 Janela de visão aberta. Pressione 'q' na janela para fechar. |")
        print("|    - Pressione 'c' para tentar calibrar.                    |")
        print("|    - Pressione 's' para salvar um screenshot.                |")
        print("+" + "-" * 58 + "+")

        self.vision_integration.show_vision_window = True
        self.vision_integration.iniciar_visao_em_thread()

        # Aguarda a janela ser fechada
        while (self.vision_integration.vision_active and
               self.vision_integration.vision_thread.is_alive()):
            try:
                if CV2_AVAILABLE:
                    # Verifica se a janela ainda está aberta
                    if cv2.getWindowProperty("Tapatan Vision System", cv2.WND_PROP_VISIBLE) < 1:
                        self.vision_integration.vision_active = False
            except (cv2.error, AttributeError):
                self.vision_integration.vision_active = False
            time.sleep(0.5)

        self.vision_integration.parar_sistema_visao()
        self.vision_integration.show_vision_window = False
        print("\n✅ Teste de visão finalizado.")

    # ========== STATUS DO SISTEMA ==========

    def mostrar_status_completo(self):
        """Mostra o status completo do robô e da visão."""
        print("\n" + "=" * 35 + "\n      📊 STATUS GERAL DO SISTEMA\n" + "=" * 35)

        # Status do orquestrador
        if self.orquestrador and hasattr(self.orquestrador, 'obter_status_completo'):
            status = self.orquestrador.obter_status_completo()
            print(f"🎮 Orquestrador: {status.get('orquestrador', {}).get('status', 'N/A')}")
        else:
            print("  - Serviço do robô não disponível ou status não implementado.")

        # Status da visão
        print("\n📹 Status da Visão:")
        if self.vision_integration:
            estado_visao = self.vision_integration.obter_estado_visao()
            if estado_visao.get('available'):
                print(f"  - Disponível: Sim | Ativa: {'Sim' if estado_visao['active'] else 'Não'}")
                print(f"  - Calibrada: {'Sim' if estado_visao['calibrated'] else 'Não'}")
                print(f"  - Detecções Atuais: {estado_visao['detections_count']}")
            else:
                print("  - Sistema de visão não disponível.")
        else:
            print("  - Sistema de visão não inicializado.")

        print("=" * 35)
        input("\nPressione ENTER para voltar ao menu...")

    # ========== PARADA DE EMERGÊNCIA ==========

    def parada_emergencia(self):
        """Para todos os sistemas imediatamente após confirmação."""
        print("\n" + "🚨" * 15 + "\n      PARADA DE EMERGÊNCIA\n" + "🚨" * 15)

        confirmacao = input("⚠️ Confirma parada de emergência? (s/N): ").lower().strip()

        if confirmacao.startswith('s'):
            # Para o orquestrador
            if self.orquestrador and hasattr(self.orquestrador, 'parada_emergencia'):
                self.orquestrador.parada_emergencia()

            # Para a visão
            if self.vision_integration:
                self.vision_integration.parar_sistema_visao()

            print("🛑 Todos os sistemas foram parados. Encerrando por segurança.")
            sys.exit(1)
        else:
            print("Parada de emergência cancelada.")

    # ========== PREPARAÇÃO DO TABULEIRO ==========

    def preparar_tabuleiro_com_visao(self) -> bool:
        """
        Inicia a visão e aguarda o usuário preparar o tabuleiro físico.

        Returns:
            True se o usuário confirmar, False se cancelar ou falhar
        """
        print("\n" + "=" * 50)
        print("    🔧 PREPARAÇÃO DO TABULEIRO COM VISÃO 🔧")
        print("=" * 50)

        if not self.vision_integration:
            print("❌ Sistema de visão não disponível.")
            return False

        if not self.vision_integration.inicializar_sistema_visao():
            print("❌ Não foi possível iniciar a visão. O jogo continuará sem ela.")
            return False

        self.vision_integration.show_vision_window = True
        self.vision_integration.iniciar_visao_em_thread()

        print("\n1. Posicione o tabuleiro e os marcadores de referência.")
        print("2. Pressione 'c' na janela de visão para calibrar o sistema.")
        print("3. Remova TODAS as peças do tabuleiro (deixe-o vazio).")
        print("4. Quando estiver pronto, volte para este terminal e pressione ENTER.")

        try:
            input("\n   Pressione ENTER para iniciar a partida ou CTRL+C para cancelar...")

            # Verifica se há peças no tabuleiro
            estado_visao = self.vision_integration.obter_estado_visao()
            if len(estado_visao['board_positions']) > 0:
                print("⚠️  Atenção: A visão detectou peças no tabuleiro. O jogo espera um tabuleiro vazio.")
                confirmacao = input("   Deseja continuar mesmo assim? (s/N): ").lower().strip()
                if confirmacao != 's':
                    print("   Partida cancelada pelo usuário.")
                    return False

            print("✅ Tabuleiro pronto! Iniciando partida...")
            return True

        except KeyboardInterrupt:
            print("\n   Preparação cancelada.")
            return False