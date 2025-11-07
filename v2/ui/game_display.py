"""
GameDisplay - Componente de Exibição do Jogo
==============================================
Responsável por toda a visualização e apresentação do jogo Tapatan:
- Exibição do tabuleiro
- Informações da partida
- Integração com sistema de visão
- Obtenção de jogadas do usuário
"""

from typing import Optional, Dict, Any


class GameDisplay:
    """
    Gerencia toda a apresentação visual do jogo Tapatan.

    Responsabilidades:
    - Exibir banner e informações do sistema
    - Renderizar o tabuleiro e estado do jogo
    - Coletar input do jogador humano
    - Mostrar informações da visão integrada
    """

    def __init__(self, vision_available: bool = False):
        """
        Inicializa o componente de exibição.

        Args:
            vision_available: Se o sistema de visão está disponível
        """
        self.vision_available = vision_available

    # ========== BANNERS E INFORMAÇÕES GERAIS ==========

    def mostrar_banner(self):
        """Mostra o banner inicial da aplicação."""
        print("=" * 70)
        print("       [JOGO] TAPATAN ROBÓTICO COM SISTEMA DE VISÃO ArUco [ROBO][VISAO]")
        print("=" * 70)
        print("  Sistema completo: Robô UR + Lógica do jogo + Visão em tempo real")
        print(f"  [VISAO] Sistema de visão ArUco: {'DISPONÍVEL' if self.vision_available else 'INDISPONÍVEL'}")
        print("=" * 70)

    # ========== EXIBIÇÃO DO TABULEIRO ==========

    def mostrar_tabuleiro(self, estado_jogo: dict):
        """
        Mostra o tabuleiro atual de forma visual.

        Args:
            estado_jogo: Dicionário com o estado completo do jogo
        """
        tabuleiro = estado_jogo['tabuleiro']
        simbolos = {0: ' ', 1: '[ROBO]', 2: '[HUMANO]'}

        print("\n" + "=" * 30)
        print("        TABULEIRO TAPATAN")
        print("=" * 30)
        print(f"      {simbolos[tabuleiro[0]]} | {simbolos[tabuleiro[1]]} | {simbolos[tabuleiro[2]]}       Pos: 0 | 1 | 2")
        print("     ---+---+---           ---+---+---")
        print(f"      {simbolos[tabuleiro[3]]} | {simbolos[tabuleiro[4]]} | {simbolos[tabuleiro[5]]}       Pos: 3 | 4 | 5")
        print("     ---+---+---           ---+---+---")
        print(f"      {simbolos[tabuleiro[6]]} | {simbolos[tabuleiro[7]]} | {simbolos[tabuleiro[8]]}       Pos: 6 | 7 | 8")
        print("=" * 30)

    def mostrar_tabuleiro_com_visao(self, estado_jogo: dict, estado_visao: dict):
        """
        Mostra o tabuleiro com informações da visão integradas.

        Args:
            estado_jogo: Dicionário com o estado completo do jogo
            estado_visao: Dicionário com o estado da visão
        """
        self.mostrar_tabuleiro(estado_jogo)

        if estado_visao.get('available'):
            status_calibracao = '[OK] Calibrada' if estado_visao['calibrated'] else '[AVISO] Não calibrada'
            print(f"[VISAO] Visão: {status_calibracao} | "
                  f"Detecções: {estado_visao['detections_count']} | "
                  f"Peças Visíveis: {len(estado_visao['board_positions'])}")

            if estado_visao['board_positions']:
                self._mostrar_comparacao_jogo_visao(estado_jogo, estado_visao)

    def _mostrar_comparacao_jogo_visao(self, estado_jogo: dict, estado_visao: dict):
        """
        Compara o estado lógico do jogo com as detecções da visão.

        Args:
            estado_jogo: Estado do jogo
            estado_visao: Estado da visão
        """
        tabuleiro_jogo = estado_jogo['tabuleiro']
        posicoes_visao = estado_visao['board_positions']
        discrepancias = []

        for pos in range(9):
            jogo_valor = tabuleiro_jogo[pos]
            visao_info = posicoes_visao.get(pos)

            if jogo_valor != 0 and visao_info is None:
                discrepancias.append(f"Pos {pos}: Jogo tem peça, visão não detectou")
            elif jogo_valor == 0 and visao_info is not None:
                discrepancias.append(f"Pos {pos}: Visão detectou peça, jogo está vazio")
            elif jogo_valor != 0 and visao_info is not None and jogo_valor != visao_info['player']:
                discrepancias.append(
                    f"Pos {pos}: Jogador diferente (Jogo: {jogo_valor}, Visão: {visao_info['player']})")

        if discrepancias:
            print("[AVISO] Discrepâncias detectadas entre jogo e visão:")
            for disc in discrepancias[:3]:
                print(f"   {disc}")

    # ========== INFORMAÇÕES DO JOGO ==========

    def mostrar_info_jogo(self, estado_jogo: dict):
        """
        Mostra informações sobre o estado atual da partida.

        Args:
            estado_jogo: Dicionário com o estado do jogo
        """
        jogador_atual = "[ROBO] Robô" if estado_jogo['jogador_atual'] == 1 else "[HUMANO] Humano"
        fase = "Colocação" if estado_jogo['fase'] == "colocacao" else "Movimento"

        print(f"\n👾 Jogador atual: {jogador_atual}  |  ⚡ Fase: {fase}")
        print(f"   [ROBO] Peças robô: {estado_jogo['pecas_colocadas'][1]}/3  |  "
              f"[HUMANO] Peças humano: {estado_jogo['pecas_colocadas'][2]}/3")

        if estado_jogo['jogo_terminado']:
            vencedor = "[ROBO] Robô" if estado_jogo['vencedor'] == 1 else "[HUMANO] Humano"
            print(f"[VENCEDOR] VENCEDOR: {vencedor}!")
        print()

    # ========== INPUT DO JOGADOR ==========

    def obter_jogada_humano(self, estado_jogo: dict) -> Optional[Dict[str, int]]:
        """
        Obtém a jogada do humano pelo terminal.

        Args:
            estado_jogo: Estado atual do jogo

        Returns:
            Dicionário com a jogada {'posicao': int} ou {'origem': int, 'destino': int}
            None se o usuário cancelar
        """
        try:
            if estado_jogo['fase'] == "colocacao":
                print("[EXECUTANDO] Sua vez! Escolha uma posição para colocar sua peça (0-8):")
                while True:
                    try:
                        posicao = int(input("   Posição: "))
                        if 0 <= posicao <= 8:
                            return {'posicao': posicao}
                        else:
                            print("   [ERRO] Posição inválida! Use números de 0 a 8.")
                    except ValueError:
                        print("   [ERRO] Digite apenas números!")
            else:
                print("[EXECUTANDO] Sua vez! Mova uma de suas peças:")
                print("   Digite 'origem destino' (ex: '3 4')")
                while True:
                    try:
                        entrada = input("   Movimento: ").strip().split()
                        if len(entrada) == 2:
                            origem, destino = int(entrada[0]), int(entrada[1])
                            if 0 <= origem <= 8 and 0 <= destino <= 8:
                                return {'origem': origem, 'destino': destino}
                            else:
                                print("   [ERRO] Posições inválidas! Use números de 0 a 8.")
                        else:
                            print("   [ERRO] Formato inválido! Digite 'origem destino'.")
                    except ValueError:
                        print("   [ERRO] Digite apenas números!")
        except KeyboardInterrupt:
            print("\n\n[INFO] Saindo do jogo...")
            return None

    def obter_jogada_humano_com_visao(self, estado_jogo: dict, estado_visao: dict) -> Optional[Dict[str, int]]:
        """
        Obtém a jogada do humano com sugestões da visão.

        Args:
            estado_jogo: Estado atual do jogo
            estado_visao: Estado da visão

        Returns:
            Dicionário com a jogada ou None se cancelar
        """
        if estado_visao.get('available') and estado_visao.get('calibrated'):
            self._mostrar_sugestoes_visao(estado_jogo, estado_visao)

        return self.obter_jogada_humano(estado_jogo)

    def _mostrar_sugestoes_visao(self, estado_jogo: dict, estado_visao: dict):
        """
        Mostra sugestões de jogadas baseadas na visão.

        Args:
            estado_jogo: Estado do jogo
            estado_visao: Estado da visão
        """
        print("\n[INFO] Sugestões baseadas na visão:")
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
            sugestoes = []
            for pos in minhas_pecas:
                adjacentes_livres = [p for p in self._get_adjacent_positions(pos)
                                   if p not in posicoes_detectadas]
                if adjacentes_livres:
                    sugestoes.append(f"   Da pos {pos} pode mover para: {adjacentes_livres}")

            if sugestoes:
                for s in sugestoes:
                    print(s)
            else:
                print("   Nenhum movimento válido detectado para suas peças.")

    @staticmethod
    def _get_adjacent_positions(position: int) -> list:
        """
        Retorna uma lista de posições adjacentes no tabuleiro.

        Args:
            position: Posição no tabuleiro (0-8)

        Returns:
            Lista de posições adjacentes válidas
        """
        adjacencias = {
            0: [1, 3, 4],
            1: [0, 2, 3, 4, 5],
            2: [1, 4, 5],
            3: [0, 1, 4, 6, 7],
            4: [0, 1, 2, 3, 5, 6, 7, 8],
            5: [1, 2, 4, 7, 8],
            6: [3, 4, 7],
            7: [3, 4, 5, 6, 8],
            8: [4, 5, 7]
        }
        return adjacencias.get(position, [])

    # ========== MENSAGENS E CONFIRMAÇÕES ==========

    @staticmethod
    def aguardar_confirmacao_robo():
        """Pausa a execução até o usuário confirmar que o robô terminou."""
        print("\n[ROBO] Robô está executando movimento...")
        input("   ⏳ Pressione ENTER após o robô completar o movimento...")