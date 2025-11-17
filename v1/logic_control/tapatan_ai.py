from config.config_completa import Jogador
from logic_control.tapatan_logic import TabuleiraTapatan

class TapatanAI:

    def __init__(self, jogo: TabuleiraTapatan):
        self.jogo = jogo
        self._cache = {}  # Cache para posições já avaliadas
        self._historico_movimentos = {}  # Histórico para heurística de movimentos

    def avaliar_tabuleiro(self, tabuleiro: list) -> int:
        """Função de avaliação: +10 vitória do robô, -10 vitória do humano, 0 se neutro"""
        vencedor = self._verificar_vencedor_tabuleiro(tabuleiro)
        if vencedor == Jogador.JOGADOR1:
            return 10
        elif vencedor == Jogador.JOGADOR2:
            return -10
        return 0

    def _verificar_vencedor_tabuleiro(self, tabuleiro: list) -> int | None:
        """Usar método existente da lógica do jogo"""
        # Salvar estado atual
        tabuleiro_original = self.jogo.tabuleiro.copy()
        
        # Temporariamente usar o tabuleiro passado
        self.jogo.tabuleiro = tabuleiro
        vencedor = self.jogo.verificar_vencedor()  # Usar método existente
        
        # Restaurar estado original
        self.jogo.tabuleiro = tabuleiro_original
        
        return vencedor
        
    def _obter_movimentos_possiveis(self, tabuleiro: list, jogador: int) -> list:
        """Obter todos os movimentos possíveis para um jogador"""
        movimentos = []
        pecas = [i for i, peca in enumerate(tabuleiro) if peca == jogador]
        
        for origem in pecas:
            for destino in self.jogo.mapa_adjacencia[origem]:
                if tabuleiro[destino] == Jogador.VAZIO:
                    movimentos.append((origem, destino))
        
        return movimentos

    def minimax(self, tabuleiro: list, profundidade: int, maximizando: bool, alpha: float = -float('inf'), beta: float = float('inf')) -> int:
        tabuleiro_str = str(tabuleiro)
        cache_key = (tabuleiro_str, profundidade, maximizando)
        if cache_key in self._cache:
            return self._cache[cache_key]

        score = self.avaliar_tabuleiro(tabuleiro)

        # Parada: vitória, derrota ou profundidade zero ou fim de jogo no estado
        if abs(score) == 10 or profundidade == 0 or self.jogo.jogo_terminado(tabuleiro):
            return score

        jogador = Jogador.JOGADOR1 if maximizando else Jogador.JOGADOR2
        movimentos = self._ordenar_movimentos(tabuleiro, jogador)

        if not movimentos:
            return self._avaliar_posicao_avancada(tabuleiro)

        if maximizando:
            melhor_valor = -float('inf')
            for origem, destino in movimentos:
                novo_tabuleiro = self._fazer_movimento(tabuleiro, origem, destino, Jogador.JOGADOR1)
                valor = self.minimax(novo_tabuleiro, profundidade - 1, False, alpha, beta)
                melhor_valor = max(melhor_valor, valor)
                alpha = max(alpha, melhor_valor)
                if beta <= alpha:
                    break
            self._cache[cache_key] = melhor_valor
            return melhor_valor
        else:
            pior_valor = float('inf')
            for origem, destino in movimentos:
                novo_tabuleiro = self._fazer_movimento(tabuleiro, origem, destino, Jogador.JOGADOR2)
                valor = self.minimax(novo_tabuleiro, profundidade - 1, True, alpha, beta)
                pior_valor = min(pior_valor, valor)
                beta = min(beta, pior_valor)
                if beta <= alpha:
                    break
            self._cache[cache_key] = pior_valor
            return pior_valor

    def _fazer_movimento(self, tabuleiro: list, origem: int, destino: int, jogador: int) -> list:
        """Criar novo tabuleiro com movimento aplicado"""
        novo_tabuleiro = tabuleiro.copy()
        novo_tabuleiro[origem] = Jogador.VAZIO
        novo_tabuleiro[destino] = jogador
        return novo_tabuleiro

    def _avaliar_posicao_avancada(self, tabuleiro: list) -> int:
        """Avaliação mais sofisticada da posição"""
        score = 0
        
        # Avaliar cada linha vencedora
        for linha in self.jogo.padroes_vitoria:
            valores = [tabuleiro[i] for i in linha]
            score += self._avaliar_linha(valores)
        
        # Bonus por controle do centro (posição 4 no tabuleiro 3x3)
        if len(tabuleiro) > 4 and tabuleiro[4] == Jogador.JOGADOR1:
            score += 3
        elif len(tabuleiro) > 4 and tabuleiro[4] == Jogador.JOGADOR2:
            score -= 3
        
        # Avaliar mobilidade (número de movimentos possíveis)
        mobilidade_ia = len(self._obter_movimentos_possiveis(tabuleiro, Jogador.JOGADOR1))
        mobilidade_humano = len(self._obter_movimentos_possiveis(tabuleiro, Jogador.JOGADOR2))
        score += (mobilidade_ia - mobilidade_humano) * 0.1
        
        return score

    def _avaliar_linha(self, valores: list) -> int:
        """Avaliar uma linha específica do tabuleiro"""
        score = 0
        
        # Contar peças de cada jogador na linha
        jogador1_count = valores.count(Jogador.JOGADOR1)
        jogador2_count = valores.count(Jogador.JOGADOR2)
        vazio_count = valores.count(Jogador.VAZIO)
        
        # Se a linha tem peças de ambos os jogadores, não há vantagem
        if jogador1_count > 0 and jogador2_count > 0:
            return 0
            
        # Avaliar vantagem do jogador 1 (robô)
        if jogador1_count == 3:
            score += 100  # Vitória
        elif jogador1_count == 2 and vazio_count == 1:
            score += 10   # Ameaça de vitória
        elif jogador1_count == 1 and vazio_count == 2:
            score += 1    # Posição favorável
            
        # Avaliar vantagem do jogador 2 (humano) - valores negativos
        if jogador2_count == 3:
            score -= 100  # Derrota
        elif jogador2_count == 2 and vazio_count == 1:
            score -= 10   # Ameaça de derrota
        elif jogador2_count == 1 and vazio_count == 2:
            score -= 1    # Posição desfavorável
            
        return score

    def _ordenar_movimentos(self, tabuleiro: list, jogador: int) -> list:
        """Ordena movimentos para melhorar a eficiência do alpha-beta pruning"""
        movimentos = self._obter_movimentos_possiveis(tabuleiro, jogador)
        if not movimentos:
            return movimentos

        # Lista para armazenar tuplas (movimento, score)
        movimentos_scores = []
        
        for origem, destino in movimentos:
            score = 0
            # Priorizar movimentos do histórico
            if (origem, destino) in self._historico_movimentos:
                score += self._historico_movimentos[(origem, destino)] * 10
            
            # Priorizar movimentos que criam ameaças
            novo_tabuleiro = self._fazer_movimento(tabuleiro.copy(), origem, destino, jogador)
            score += self._avaliar_posicao_avancada(novo_tabuleiro)
            
            # Priorizar movimentos próximos ao centro
            if destino == 4:  # Centro
                score += 5
            elif destino in [1, 3, 5, 7]:  # Adjacentes ao centro
                score += 3
                
            movimentos_scores.append(((origem, destino), score))
        
        # Ordenar movimentos por score (maior para menor)
        movimentos_scores.sort(key=lambda x: x[1], reverse=True)
        return [mov for mov, _ in movimentos_scores]

    def fazer_jogada_robo_minimax(self, profundidade_maxima: int = 5) -> tuple | None:
        """
        Método principal para fazer a jogada do robô usando minimax com iterative deepening
        Retorna uma tupla (origem, destino) ou None se não houver jogadas válidas
        """
        tabuleiro_atual = self.jogo.tabuleiro.copy()
        movimentos = self._ordenar_movimentos(tabuleiro_atual, Jogador.JOGADOR1)
        
        if not movimentos:
            return None
            
        melhor_movimento = movimentos[0]  # Movimento padrão caso tempo acabe
        self._cache.clear()  # Limpar cache para nova busca
        
        # Iterative deepening
        for profundidade in range(2, profundidade_maxima + 1):
            melhor_valor = -float('inf')
            melhor_mov_atual = None
            
            for origem, destino in movimentos:
                novo_tabuleiro = self._fazer_movimento(tabuleiro_atual, origem, destino, Jogador.JOGADOR1)
                valor = self.minimax(novo_tabuleiro, profundidade - 1, False, -float('inf'), float('inf'))
                
                if valor > melhor_valor:
                    melhor_valor = valor
                    melhor_mov_atual = (origem, destino)
            
            if melhor_mov_atual:
                melhor_movimento = melhor_mov_atual
                # Atualizar histórico de movimentos
                if melhor_mov_atual not in self._historico_movimentos:
                    self._historico_movimentos[melhor_mov_atual] = 0
                self._historico_movimentos[melhor_mov_atual] += 1
                
        return melhor_movimento