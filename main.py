"""
Main - Tapatan Robótico com Sistema de Visão ArUco Integrado
===========================================================
Interface principal do jogo Tapatan com robô e visão ArUco
Sistema completo para detecção de marcadores, controle do robô e lógica do jogo
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
import threading
import traceback
from typing import Optional, Dict, Any

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

# Imports do sistema de visão integrado
try:
    # noinspection PyUnresolvedReferences
    import cv2
    from vision import ArUcoVisionSystem, CameraManager, VisualMonitor, create_vision_system
    VISION_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Sistema de visão não disponível: {e}")
    VISION_AVAILABLE = False


class TapatanInterface:
    """
    Interface principal do jogo Tapatan com sistema de visão ArUco integrado.
    """
    def __init__(self):
        """Inicializa a interface principal (modo produção)."""
        self.config_robo = ConfigRobo()
        self.config_jogo = ConfigJogo()
        try:
            self.orquestrador = TapatanOrchestrator(self.config_robo, self.config_jogo)
            print("✅ Orquestrador do jogo inicializado.")
        except Exception as e:
            print(f"❌ Falha ao inicializar o Orquestrador: {e}")
            self.orquestrador = None

        # Sistema de visão
        self.vision_system: Optional[ArUcoVisionSystem] = None
        self.camera_manager: Optional[CameraManager] = None
        self.visual_monitor: Optional[VisualMonitor] = None
        self.vision_thread: Optional[threading.Thread] = None
        self.vision_active = False
        self.vision_calibrated = False

        # Estado da visão
        self.current_detections: Dict[str, Any] = {}
        self.board_positions_detected: Dict[int, Any] = {}
        self.show_vision_window = False

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
        if self.vision_active:
            self.parar_sistema_visao()
        if self.orquestrador:
            self.orquestrador.finalizar()
        print("✅ Sistema finalizado!")

    # ========== SISTEMA DE VISÃO ==========

    def inicializar_sistema_visao(self) -> bool:
        """Inicializa o sistema de visão integrado."""
        if not VISION_AVAILABLE:
            print("❌ Sistema de visão não está disponível (bibliotecas ausentes).")
            return False
        try:
            print("📹 Inicializando sistema de visão...")
            self.vision_system, self.camera_manager, self.visual_monitor = create_vision_system()
            if not self.camera_manager.initialize_camera():
                print("⚠️ Câmera não disponível - jogo continuará sem visão")
                return False
            print("✅ Sistema de visão inicializado!")
            return True
        except Exception as e:
            print(f"❌ Erro ao inicializar visão: {e}")
            return False

    def iniciar_visao_em_thread(self):
        """Inicia o sistema de visão em uma thread separada."""
        if not self.vision_system or not self.camera_manager:
            return
        self.vision_active = True
        self.vision_thread = threading.Thread(target=self._loop_visao, daemon=True)
        self.vision_thread.start()
        print("🎥 Sistema de visão ativo em background")

    def _loop_visao(self):
        """Loop principal da visão executado na thread."""
        while self.vision_active:
            try:
                frame = self.camera_manager.capture_frame()
                if frame is None:
                    time.sleep(0.1)
                    continue

                detections = self.vision_system.detect_markers(frame)
                self.current_detections = detections
                self._atualizar_posicoes_jogo(detections)

                if not self.vision_calibrated and len(detections.get('reference_markers', {})) >= 2:
                    if self.vision_system.calibrate_system(detections):
                        self.vision_calibrated = True
                        print("\n🎯 Sistema de visão calibrado automaticamente!")

                if self.show_vision_window:
                    display_frame = self.visual_monitor.draw_detection_overlay(frame, detections)
                    cv2.imshow("Tapatan Vision System", display_frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        self.vision_active = False
                        break
                    elif key == ord('c'):
                        self._calibrar_visao_manual(detections)
                    elif key == ord('s'):
                        filename = f"tapatan_vision_{int(time.time())}.jpg"
                        cv2.imwrite(filename, display_frame)
                        print(f"📸 Screenshot salvo como {filename}")
                time.sleep(0.03)
            except Exception as e:
                print(f"❌ Erro no loop de visão: {e}")
                time.sleep(1)
        if self.show_vision_window:
            cv2.destroyAllWindows()

    def _atualizar_posicoes_jogo(self, detections: dict):
        """Atualiza o estado das peças detectadas no tabuleiro."""
        self.board_positions_detected.clear()
        for group_name in ['group1_markers', 'group2_markers']:
            for marker_id, marker_info in detections.get(group_name, {}).items():
                board_coords = self.vision_system.get_board_coordinates(marker_info)
                if board_coords is not None:
                    board_position = self._coords_to_board_position(board_coords)
                    if board_position is not None:
                        player_group = 1 if group_name == 'group1_markers' else 2
                        self.board_positions_detected[board_position] = {
                            'player': player_group, 'marker_id': marker_id, 'coordinates': board_coords}

    @staticmethod
    def _coords_to_board_position(coords: tuple) -> Optional[int]:
        """Converte coordenadas normalizadas para uma posição (0-8) no tabuleiro."""
        try:
            x, y = coords
            col = int((x + 1.0) / 2.0 * 3)
            row = int((y + 1.0) / 2.0 * 3)
            col, row = max(0, min(2, col)), max(0, min(2, row))
            return row * 3 + col
        except (TypeError, ValueError) as e:
            print(f"❌ Erro na conversão de coordenadas: {e}")
            return None

    def _calibrar_visao_manual(self, detections: dict):
        """Realiza a calibração manual da visão."""
        if self.vision_system.calibrate_system(detections):
            self.vision_calibrated = True
            print("\n✅ Sistema de visão calibrado manualmente!")
            summary = self.visual_monitor.show_detection_summary(detections)
            print(f"📊 Status: {summary}")
        else:
            print("\n❌ Calibração manual falhou - verifique marcadores de referência")

    def parar_sistema_visao(self):
        """Para a thread de visão e libera a câmera."""
        self.vision_active = False
        if self.vision_thread and self.vision_thread.is_alive():
            self.vision_thread.join(timeout=2)
        if self.camera_manager:
            self.camera_manager.release()
        cv2.destroyAllWindows()
        print("📹 Sistema de visão finalizado")

    def obter_estado_visao(self) -> dict:
        """Retorna um dicionário com o estado atual do sistema de visão."""
        if not self.vision_system:
            return {'available': False}
        return {'available': True, 'calibrated': self.vision_calibrated, 'active': self.vision_active,
                'detections_count': self.current_detections.get('detection_count', 0),
                'board_positions': self.board_positions_detected.copy(),
                'last_detection_time': self.current_detections.get('timestamp', 0)}

    # ========== INTERFACE DE JOGO ==========

    def mostrar_banner(self):
        """Mostra o banner inicial da aplicação."""
        print("=" * 70)
        print("       🎮 TAPATAN ROBÓTICO COM SISTEMA DE VISÃO ArUco 🤖📹")
        print("=" * 70)
        print("  Sistema completo: Robô UR + Lógica do jogo + Visão em tempo real")
        print(f"  📹 Sistema de visão ArUco: {'DISPONÍVEL' if VISION_AVAILABLE else 'INDISPONÍVEL'}")
        print("=" * 70)

    def mostrar_tabuleiro(self, estado_jogo: dict):
        """Mostra o tabuleiro atual de forma visual."""
        tabuleiro = estado_jogo['tabuleiro']
        simbolos = {0: ' ', 1: '🤖', 2: '👤'}
        print("\n" + "=" * 30)
        print("        TABULEIRO TAPATAN")
        print("=" * 30)
        print(f"      {simbolos[tabuleiro[0]]} | {simbolos[tabuleiro[1]]} | {simbolos[tabuleiro[2]]}       Pos: 0 | 1 | 2")
        print("     ---+---+---           ---+---+---")
        print(f"      {simbolos[tabuleiro[3]]} | {simbolos[tabuleiro[4]]} | {simbolos[tabuleiro[5]]}       Pos: 3 | 4 | 5")
        print("     ---+---+---           ---+---+---")
        print(f"      {simbolos[tabuleiro[6]]} | {simbolos[tabuleiro[7]]} | {simbolos[tabuleiro[8]]}       Pos: 6 | 7 | 8")
        print("=" * 30)

    def mostrar_tabuleiro_com_visao(self, estado_jogo: dict):
        """Mostra o tabuleiro com informações da visão integradas."""
        self.mostrar_tabuleiro(estado_jogo)
        estado_visao = self.obter_estado_visao()
        if estado_visao.get('available'):
            status_calibracao = '🟢 Calibrada' if estado_visao['calibrated'] else '🟡 Não calibrada'
            print(f"📹 Visão: {status_calibracao} | "
                  f"Detecções: {estado_visao['detections_count']} | "
                  f"Peças Visíveis: {len(estado_visao['board_positions'])}")
            if estado_visao['board_positions']:
                self._mostrar_comparacao_jogo_visao(estado_jogo, estado_visao)

    def _mostrar_comparacao_jogo_visao(self, estado_jogo: dict, estado_visao: dict):
        """Compara o estado lógico do jogo com as detecções da visão."""
        tabuleiro_jogo = estado_jogo['tabuleiro']
        posicoes_visao = estado_visao['board_positions']
        discrepancias = []
        for pos in range(9):
            jogo_valor, visao_info = tabuleiro_jogo[pos], posicoes_visao.get(pos)
            if jogo_valor != 0 and visao_info is None:
                discrepancias.append(f"Pos {pos}: Jogo tem peça, visão não detectou")
            elif jogo_valor == 0 and visao_info is not None:
                discrepancias.append(f"Pos {pos}: Visão detectou peça, jogo está vazio")
            elif jogo_valor != 0 and visao_info is not None and jogo_valor != visao_info['player']:
                discrepancias.append(
                    f"Pos {pos}: Jogador diferente (Jogo: {jogo_valor}, Visão: {visao_info['player']})")
        if discrepancias:
            print("⚠️ Discrepâncias detectadas entre jogo e visão:")
            for disc in discrepancias[:3]: print(f"   {disc}")

    def mostrar_info_jogo(self, estado_jogo: dict):
        """Mostra informações sobre o estado atual da partida."""
        jogador_atual = "🤖 Robô" if estado_jogo['jogador_atual'] == 1 else "👤 Humano"
        fase = "Colocação" if estado_jogo['fase'] == "colocacao" else "Movimento"
        print(f"\n👾 Jogador atual: {jogador_atual}  |  ⚡ Fase: {fase}")
        print(f"   🤖 Peças robô: {estado_jogo['pecas_colocadas'][1]}/3  |  "
              f"👤 Peças humano: {estado_jogo['pecas_colocadas'][2]}/3")
        if estado_jogo['jogo_terminado']:
            vencedor = "🤖 Robô" if estado_jogo['vencedor'] == 1 else "👤 Humano"
            print(f"🏆 VENCEDOR: {vencedor}!")
        print()

    def obter_jogada_humano(self, estado_jogo: dict) -> Optional[Dict[str, int]]:
        """Obtém a jogada do humano pelo terminal."""
        try:
            if estado_jogo['fase'] == "colocacao":
                print("🎯 Sua vez! Escolha uma posição para colocar sua peça (0-8):")
                while True:
                    try:
                        posicao = int(input("   Posição: "))
                        if 0 <= posicao <= 8: return {'posicao': posicao}
                        else: print("   ❌ Posição inválida! Use números de 0 a 8.")
                    except ValueError: print("   ❌ Digite apenas números!")
            else:
                print("🎯 Sua vez! Mova uma de suas peças:")
                print("   Digite 'origem destino' (ex: '3 4')")
                while True:
                    try:
                        entrada = input("   Movimento: ").strip().split()
                        if len(entrada) == 2:
                            origem, destino = int(entrada[0]), int(entrada[1])
                            if 0 <= origem <= 8 and 0 <= destino <= 8:
                                return {'origem': origem, 'destino': destino}
                            else: print("   ❌ Posições inválidas! Use números de 0 a 8.")
                        else: print("   ❌ Formato inválido! Digite 'origem destino'.")
                    except ValueError: print("   ❌ Digite apenas números!")
        except KeyboardInterrupt:
            print("\n\n👋 Saindo do jogo...")
            return None

    def obter_jogada_humano_com_visao(self, estado_jogo: dict):
        """Obtém a jogada do humano com sugestões da visão."""
        estado_visao = self.obter_estado_visao()
        if estado_visao.get('available') and estado_visao.get('calibrated'):
            self._mostrar_sugestoes_visao(estado_jogo, estado_visao)
        return self.obter_jogada_humano(estado_jogo)

    def _mostrar_sugestoes_visao(self, estado_jogo: dict, estado_visao: dict):
        """Mostra sugestões de jogadas baseadas na visão."""
        print("\n💡 Sugestões baseadas na visão:")
        posicoes_detectadas = estado_visao['board_positions']
        if not posicoes_detectadas:
            print("   Nenhuma peça detectada pela visão")
            return
        minhas_pecas = [pos for pos, info in posicoes_detectadas.items() if info['player'] == 2]
        if not minhas_pecas:
            print("   Nenhuma de suas peças foi detectada.")
            return
        print(f"   Suas peças detectadas nas posições: {sorted(minhas_pecas)}")
        if estado_jogo['fase'] == 'movimento':
            sugestoes = [f"   Da pos {pos} pode mover para: {[p for p in self._get_adjacent_positions(pos) if p not in posicoes_detectadas]}"
                         for pos in minhas_pecas if any(p not in posicoes_detectadas for p in self._get_adjacent_positions(pos))]
            if sugestoes:
                for s in sugestoes: print(s)
            else: print("   Nenhum movimento válido detectado para suas peças.")

    @staticmethod
    def _get_adjacent_positions(position: int) -> list:
        """Retorna uma lista de posições adjacentes no tabuleiro."""
        adj = {0: [1, 3, 4], 1: [0, 2, 3, 4, 5], 2: [1, 4, 5], 3: [0, 1, 4, 6, 7],
               4: [0, 1, 2, 3, 5, 6, 7, 8], 5: [1, 2, 4, 7, 8], 6: [3, 4, 7], 7: [3, 4, 5, 6, 8],
               8: [4, 5, 7]}
        return adj.get(position, [])

    @staticmethod
    def aguardar_confirmacao_robo():
        """Pausa a execução até o usuário confirmar que o robô terminou."""
        print("\n🤖 Robô está executando movimento...")
        input("   ⏳ Pressione ENTER após o robô completar o movimento...")

    # ========== ROTINAS DO MENU ==========

    def calibrar_sistema(self):
        """Executa a rotina de calibração do sistema robótico."""
        print("\n🔧 Iniciando calibração do sistema robótico...")
        if not (self.orquestrador and hasattr(self.orquestrador, 'calibrar_sistema')):
            print("⚠️ Função de calibração não implementada no orquestrador.")
            input("Pressione ENTER para voltar...")
            return
        print("⚠️ O robô visitará algumas posições do tabuleiro.")
        if input("   Continuar? (s/N): ").lower().strip().startswith('s'):
            if self.orquestrador.calibrar_sistema():
                print("✅ Calibração concluída com sucesso!")
            else:
                print("❌ Falha na calibração!")
        else:
            print("Calibração cancelada.")

    def testar_sistema_visao(self):
        """Testa o sistema de visão de forma isolada."""
        print("\n📹 Iniciando teste do sistema de visão...")
        if not self.inicializar_sistema_visao():
            input("Pressione ENTER para voltar...")
            return
        print("\n" + "+" + "-" * 58 + "+")
        print("| 🎥 Janela de visão aberta. Pressione 'q' na janela para fechar. |")
        print("|    - Pressione 'c' para tentar calibrar.                    |")
        print("|    - Pressione 's' para salvar um screenshot.                |")
        print("+" + "-" * 58 + "+")
        self.show_vision_window = True
        self.iniciar_visao_em_thread()
        while self.vision_active and self.vision_thread.is_alive():
            try:
                # Espera a janela ser fechada pelo usuário ou 'q' ser pressionado no loop de visão
                if cv2.getWindowProperty("Tapatan Vision System", cv2.WND_PROP_VISIBLE) < 1:
                    self.vision_active = False
            except cv2.error:
                self.vision_active = False # Janela foi fechada
            time.sleep(0.5)
        self.parar_sistema_visao()
        self.show_vision_window = False
        print("\n✅ Teste de visão finalizado.")

    def mostrar_status_completo(self):
        """Mostra o status completo do robô e da visão."""
        print("\n" + "="*35 + "\n      📊 STATUS GERAL DO SISTEMA\n" + "="*35)
        if self.orquestrador and hasattr(self.orquestrador, 'obter_status_completo'):
            status = self.orquestrador.obter_status_completo()
            print(f"🎮 Orquestrador: {status.get('orquestrador', {}).get('status', 'N/A')}")
            # Adicione mais detalhes do status do orquestrador se necessário
        else:
            print("  - Serviço do robô não disponível ou status não implementado.")
        
        print("\n📹 Status da Visão:")
        estado_visao = self.obter_estado_visao()
        if estado_visao.get('available'):
            print(f"  - Disponível: Sim | Ativa: {'Sim' if estado_visao['active'] else 'Não'}")
            print(f"  - Calibrada: {'Sim' if estado_visao['calibrated'] else 'Não'}")
            print(f"  - Detecções Atuais: {estado_visao['detections_count']}")
        else:
            print("  - Sistema de visão não disponível.")
        print("="*35)
        input("\nPressione ENTER para voltar ao menu...")

    def parada_emergencia(self):
        """Para todos os sistemas imediatamente após confirmação."""
        print("\n" + "🚨" * 15 + "\n      PARADA DE EMERGÊNCIA\n" + "🚨" * 15)
        if input("⚠️ Confirma parada de emergência? (s/N): ").lower().strip().startswith('s'):
            if self.orquestrador and hasattr(self.orquestrador, 'parada_emergencia'):
                self.orquestrador.parada_emergencia()
            self.parar_sistema_visao()
            print("🛑 Todos os sistemas foram parados. Encerrando por segurança.")
            sys.exit(1)
        else:
            print("Parada de emergência cancelada.")

    # ========== EXECUÇÃO E PARTIDA ==========

    def menu_principal(self):
        """Exibe o menu principal e processa a escolha do usuário."""
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
                if opcao == "1": self.executar_partida()
                elif opcao == "2": self.calibrar_sistema()
                elif opcao == "3": self.testar_sistema_visao()
                elif opcao == "4": self.mostrar_status_completo()
                elif opcao == "5": self.parada_emergencia()
                elif opcao == "6": break
                else: print("   ❌ Opção inválida!")
            except KeyboardInterrupt:
                break
        print("\n👋 Até logo!")

    def preparar_tabuleiro_com_visao(self) -> bool:
        """
        Inicia a visão e aguarda o usuário preparar o tabuleiro físico.
        Retorna True se o usuário confirmar, False se cancelar ou falhar.
        """
        print("\n" + "="*50)
        print("    🔧 PREPARAÇÃO DO TABULEIRO COM VISÃO 🔧")
        print("="*50)
        
        if not self.inicializar_sistema_visao():
            print("❌ Não foi possível iniciar a visão. O jogo continuará sem ela.")
            # Se a visão for crucial, pode retornar False aqui.
            # Por enquanto, permite o jogo continuar.
            return False 

        self.show_vision_window = True
        self.iniciar_visao_em_thread()

        print("\n1. Posicione o tabuleiro e os marcadores de referência.")
        print("2. Pressione 'c' na janela de visão para calibrar o sistema.")
        print("3. Remova TODAS as peças do tabuleiro (deixe-o vazio).")
        print("4. Quando estiver pronto, volte para este terminal e pressione ENTER.")

        try:
            input("\n   Pressione ENTER para iniciar a partida ou CTRL+C para cancelar...")
            estado_visao = self.obter_estado_visao()
            if len(estado_visao['board_positions']) > 0:
                print("⚠️  Atenção: A visão detectou peças no tabuleiro. O jogo espera um tabuleiro vazio.")
                if input("   Deseja continuar mesmo assim? (s/N): ").lower().strip() != 's':
                    print("   Partida cancelada pelo usuário.")
                    return False
            
            print("✅ Tabuleiro pronto! Iniciando partida...")
            return True

        except KeyboardInterrupt:
            print("\n   Preparação cancelada.")
            return False

    def executar_partida(self):
        """Executa uma partida completa com sistema de visão integrado."""
        if not self.orquestrador:
            print("❌ Orquestrador não inicializado! Impossível iniciar.")
            return

        print("\n🎮 Iniciando nova partida...")
        usar_visao = False
        if VISION_AVAILABLE:
            usar_visao = self.preparar_tabuleiro_com_visao()
            if not usar_visao and self.vision_active:
                # Se a preparação foi cancelada, para a visão
                self.parar_sistema_visao()
                self.show_vision_window = False
                return

        if not self.orquestrador.iniciar_partida():
            print("❌ Erro ao iniciar a partida no orquestrador!")
            if usar_visao: self.parar_sistema_visao()
            return

        try:
            while True:
                estado_jogo = self.orquestrador.game_service.obter_estado_jogo()
                self.mostrar_tabuleiro_com_visao(estado_jogo) if usar_visao else self.mostrar_tabuleiro(estado_jogo)
                self.mostrar_info_jogo(estado_jogo)

                if estado_jogo['jogo_terminado']:
                    print("🎉 Jogo terminado!")
                    input("   Pressione ENTER para voltar ao menu...")
                    break

                if estado_jogo['jogador_atual'] == 2:
                    jogada = self.obter_jogada_humano_com_visao(estado_jogo) if usar_visao else self.obter_jogada_humano(estado_jogo)
                    if jogada is None: break
                    resultado = self.orquestrador.processar_jogada_humano(**jogada)
                    
                    if not resultado['sucesso']:
                        print(f"   ❌ Erro: {resultado.get('mensagem', 'Jogada inválida')}")
                        time.sleep(1)
                        continue
                    print("   ✅ Sua jogada foi processada!")
                    if 'jogada_robo' in resultado:
                        jr = resultado['jogada_robo']['jogada']
                        print(f"   🤖 Robô respondeu colocando na pos {jr['posicao']}" if 'posicao' in jr else f"   🤖 Robô respondeu movendo de {jr['origem']} para {jr['destino']}")
                        self.aguardar_confirmacao_robo()

                elif estado_jogo['jogador_atual'] == 1:
                    input("   🤖 Vez do robô. Pressione ENTER para ele jogar...")
                    resultado = self.orquestrador.executar_jogada_robo()
                    if resultado['sucesso']:
                        j = resultado['jogada']
                        print(f"   🤖 Robô colocou na posição {j['posicao']}" if 'posicao' in j else f"   🤖 Robô moveu de {j['origem']} para {j['destino']}")
                        self.aguardar_confirmacao_robo()
                    else:
                        print(f"❌ Erro na jogada do robô: {resultado['mensagem']}")
                        break
        except KeyboardInterrupt:
            print("\n\n🛑 Partida interrompida!")
        except Exception as e:
            print(f"\n❌ Erro fatal durante a partida: {e}")
            traceback.print_exc()
        finally:
            if usar_visao:
                # A visão continua rodando durante o jogo, então paramos aqui
                self.parar_sistema_visao()
            self.show_vision_window = False

    def executar(self):
        """Ponto de entrada principal da interface."""
        self.mostrar_banner()
        if self.inicializar_sistema():
            try:
                self.menu_principal()
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
        super().__init__()
        self.config_robo = ConfigRobo(pausa_entre_jogadas=1.0, velocidade_padrao=0.05, auto_calibrar=False)
        self.config_jogo = ConfigJogo(profundidade_ia=3, debug_mode=True)
        try:
            self.orquestrador = TapatanOrchestrator(self.config_robo, self.config_jogo)
            print("✅ Orquestrador do jogo inicializado em MODO TESTE.")
        except Exception as e:
            print(f"❌ Falha ao inicializar o Orquestrador em MODO TESTE: {e}")
            self.orquestrador = None
        print("🧪 TapatanTestInterface inicializada.")

    def mostrar_banner(self):
        """Mostra o banner específico para o modo de teste."""
        print("=" * 70)
        print("       🧪 TAPATAN ROBÓTICO - MODO TESTE COM VISÃO 🤖📹")
        print("=" * 70)
        print("  Testando movimentação, lógica do jogo e sistema de visão")
        print(f"  📹 Sistema de visão ArUco: {'DISPONÍVEL' if VISION_AVAILABLE else 'INDISPONÍVEL'}")
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
                self.mostrar_tabuleiro(estado_jogo)
                self.mostrar_info_jogo(estado_jogo)
                if estado_jogo['jogo_terminado']:
                    print("🎉 Jogo de teste terminado!")
                    input("   Pressione ENTER para voltar ao menu...")
                    break
                if estado_jogo['jogador_atual'] == 2:
                    jogada = self.obter_jogada_humano(estado_jogo)
                    if jogada is None: break
                    resultado = self.orquestrador.processar_jogada_humano(**jogada)
                    if not resultado['sucesso']:
                        print(f"   ❌ Erro: {resultado.get('mensagem', 'Jogada inválida')}")
                        continue
                    print("   ✅ Sua jogada foi processada!")
                    if 'jogada_robo' in resultado:
                        self.aguardar_confirmacao_robo()
                elif estado_jogo['jogador_atual'] == 1:
                    input("   🤖 Vez do robô. Pressione ENTER para ele jogar...")
                    resultado = self.orquestrador.executar_jogada_robo()
                    if resultado['sucesso']:
                        self.aguardar_confirmacao_robo()
                    else:
                        print(f"❌ Erro na jogada do robô: {resultado['mensagem']}")
                        break
        except KeyboardInterrupt:
            print("\n\n🛑 Partida de teste interrompida!")
        except Exception as e:
            print(f"\n❌ Erro fatal na partida de teste: {e}")


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

