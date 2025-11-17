"""
Lógica do Jogo Tapatan para Implementação em Braço Robótico
Jogo tradicional filipino de estratégia 3x3

FORMATO DO TABULEIRO TAPATAN:
O tabuleiro é um quadrado com linhas bissetrizes formando 9 pontos de intersecção:

    0-----1-----2
    | \   |   / |
    |   \ | /   |
    3-----4-----5
    |   / | \   |
    | /   |   \ |
    6-----7-----8

Regras do Jogo:
- Tabuleiro com grade 3x3 e 9 posições numeradas de 0 a 8
- Cada jogador tem exatamente 3 peças
- Duas fases: Colocação, depois Movimento  

- Vitória ao conseguir 3 peças em linha (horizontal, vertical ou diagonal)
- Movimento apenas para posições adjacentes vazias seguindo as linhas do tabuleiro
"""

 
from config.config_completa import Jogador, FaseJogo
class TabuleiraTapatan:
    def __init__(self):
        self.tabuleiro = [Jogador.VAZIO] * 9
        self.pecas_colocadas = {
            Jogador.JOGADOR1: 0,
            Jogador.JOGADOR2: 0
        }
        self.fase = FaseJogo.COLOCACAO
        self.jogador_atual = Jogador.JOGADOR1
        self.padroes_vitoria = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],
            [0, 3, 6], [1, 4, 7], [2, 5, 8],
            [0, 4, 8], [2, 4, 6]
        ]
        self.mapa_adjacencia = {
            0: [1, 3, 4],
            1: [0, 2, 4],
            2: [1, 4, 5],
            3: [0, 4, 6],
            4: [0, 1, 2, 3, 5, 6, 7, 8],
            5: [2, 4, 8],
            6: [3, 4, 7],
            7: [4, 6, 8],
            8: [4, 5, 7]
        }
        self.coordenadas_tabuleiro = {}

    @staticmethod
    def verificar_vencedor_tabuleiro(tabuleiro: list) -> Jogador | None:
        padroes_vitoria = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],
            [0, 3, 6], [1, 4, 7], [2, 5, 8],
            [0, 4, 8], [2, 4, 6]
        ]
        for padrao in padroes_vitoria:
            p0, p1, p2 = padrao
            if tabuleiro[p0] == tabuleiro[p1] == tabuleiro[p2] and tabuleiro[p0] != Jogador.VAZIO:
                return tabuleiro[p0]
        return None

    def obter_estado_tabuleiro(self) -> list:
        return [jogador.value for jogador in self.tabuleiro]

    def obter_posicoes_vazias(self) -> list:
        return [i for i, peca in enumerate(self.tabuleiro) if peca == Jogador.VAZIO]

    def eh_movimento_valido(self, pos_origem: int, pos_destino: int) -> bool:
        if self.fase != FaseJogo.MOVIMENTO:
            return False
        if self.tabuleiro[pos_origem] != self.jogador_atual:
            return False
        if self.tabuleiro[pos_destino] != Jogador.VAZIO:
            return False
        return pos_destino in self.mapa_adjacencia[pos_origem]

    def verificar_coordenadas(self) -> bool:
        if len(self.coordenadas_tabuleiro) != 9:
            print(f"❌ Coordenadas incompletas: {len(self.coordenadas_tabuleiro)} definidas")
            return False
        for i in range(9):
            if i not in self.coordenadas_tabuleiro or self.coordenadas_tabuleiro[i] is None:
                print(f"❌ Coordenada ausente ou inválida para a posição {i}")
                return False
        print("✅ Todas as coordenadas do tabuleiro estão corretamente definidas")
        return True

    def verificar_vencedor(self) -> Jogador | None:
        for padrao in self.padroes_vitoria:
            if (self.tabuleiro[padrao[0]] == self.tabuleiro[padrao[1]] ==
                self.tabuleiro[padrao[2]] != Jogador.VAZIO):
                return self.tabuleiro[padrao[0]]
        return None


    def obter_pecas_jogador(self, jogador: Jogador) -> list:
        return [i for i, peca in enumerate(self.tabuleiro) if peca == jogador]

    def obter_movimentos_validos(self, jogador: Jogador = None, tabuleiro: list = None) -> list:
        """
        Retorna lista de movimentos válidos (origem, destino) para o jogador,
        considerando o tabuleiro passado ou o estado interno.
        """
        tab = tabuleiro if tabuleiro is not None else self.tabuleiro
        if self.fase != FaseJogo.MOVIMENTO:
            return []
        if jogador is None:
            jogador = self.jogador_atual

        movimentos_validos = []
        pecas_jogador = [i for i, peca in enumerate(tab) if peca == jogador]

        for pos_origem in pecas_jogador:
            for pos_destino in self.mapa_adjacencia[pos_origem]:
                if tab[pos_destino] == Jogador.VAZIO:
                    movimentos_validos.append((pos_origem, pos_destino))
        return movimentos_validos

    def alternar_jogador(self):
        self.jogador_atual = Jogador.JOGADOR1 if self.jogador_atual == Jogador.JOGADOR2 else Jogador.JOGADOR2

    def jogo_terminado(self, tabuleiro: list = None, fase: FaseJogo = None, jogador: Jogador = None) -> bool:
        tab = tabuleiro if tabuleiro is not None else self.tabuleiro
        fase_atual = fase if fase is not None else self.fase
        jogador_atual = jogador if jogador is not None else self.jogador_atual

        # Verifica vencedor
        for padrao in self.padroes_vitoria:
            if (tab[padrao[0]] == tab[padrao[1]] == tab[padrao[2]] != Jogador.VAZIO):
                return True

        # Se estiver na fase de movimento, verifica se há movimentos válidos
        if fase_atual == FaseJogo.MOVIMENTO:
            movimentos = self.obter_movimentos_validos(jogador=jogador_atual, tabuleiro=tab)
            if not movimentos:
                return True

        return False

    def reiniciar_jogo(self, estado_inicial: list = None):
        self.tabuleiro = [Jogador.VAZIO] * 9
        self.jogador_atual = Jogador.JOGADOR1
        self.fase = FaseJogo.COLOCACAO
        self.pecas_colocadas = {Jogador.JOGADOR1: 0, Jogador.JOGADOR2: 0}

        if estado_inicial:
            if len(estado_inicial) != 9:
                raise ValueError("Estado inválido: deve conter exatamente 9 posições")
            
            try:
                for i, val in enumerate(estado_inicial):
                    self.tabuleiro[i] = Jogador(val)
            except ValueError:
                raise ValueError("Estado inválido: valores devem ser 0 (vazio), 1 (J1) ou 2 (J2)")

            j1 = sum(1 for p in self.tabuleiro if p == Jogador.JOGADOR1)
            j2 = sum(1 for p in self.tabuleiro if p == Jogador.JOGADOR2)

            if j1 > 3 or j2 > 3 or (j1 + j2) > 6:
                raise ValueError("Estado inválido: número de peças inválido")

            self.pecas_colocadas[Jogador.JOGADOR1] = j1
            self.pecas_colocadas[Jogador.JOGADOR2] = j2

            if j1 == 3 and j2 == 3:
                self.fase = FaseJogo.MOVIMENTO


    def posicao_para_coordenadas(self, posicao: int) -> tuple:
        return (posicao // 3, posicao % 3)

    def coordenadas_para_posicao(self, linha: int, coluna: int) -> int:
        return linha * 3 + coluna

    def imprimir_tabuleiro(self):
        simbolos = {Jogador.VAZIO: '.', Jogador.JOGADOR1: 'X', Jogador.JOGADOR2: 'O'}
        print(f"Fase: {self.fase.value}, Jogador Atual: {self.jogador_atual.name}")
        print("Tabuleiro:")
        for i in range(3):
            linha = [simbolos[self.tabuleiro[i*3 + j]] for j in range(3)]
            print(' | '.join(linha))
            if i < 2:
                print('---------')
        print()


