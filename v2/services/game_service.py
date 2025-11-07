"""
GameService - Serviço Central do Jogo Tapatan
Combina a lógica do jogo e IA em uma interface única e simples
"""
from typing import Dict,Tuple
from config.config_completa import Jogador, FaseJogo
from logic_control.tapatan_logic import TabuleiraTapatan
from logic_control.tapatan_ai import TapatanAI
# NOTA: gerar_tabuleiro_tapatan foi substituído por BoardCoordinateSystem
# from utils.tapatan_board import gerar_tabuleiro_tapatan

class GameService:
    """Serviço principal que gerencia toda a lógica do jogo Tapatan"""
    
    def __init__(self):
        self.tabuleiro = TabuleiraTapatan()
        self.ai = TapatanAI(self.tabuleiro)
        self._historico_jogadas = []
        
    # ==================== CONTROLE BÁSICO DO JOGO ====================
    
    def reiniciar_jogo(self, estado_inicial: list = None):
        """Reinicia o jogo com estado opcional"""
        if estado_inicial is None:
            estado_inicial = [
                1, 2, 1,  
                0, 0, 0,
                2, 1, 2   
            ]
        self.tabuleiro.reiniciar_jogo(estado_inicial)
        self.ai = TapatanAI(self.tabuleiro)  # Reinicializar IA
        self._historico_jogadas.clear()
        
    def obter_estado_jogo(self) -> dict:
        """Retorna o estado completo do jogo"""
        return {
            'tabuleiro': self.tabuleiro.obter_estado_tabuleiro(),
            'jogador_atual': self.tabuleiro.jogador_atual.value,
            'fase': self.tabuleiro.fase.value,
            'pecas_colocadas': {j.value: v for j, v in self.tabuleiro.pecas_colocadas.items()},
            'vencedor': self.obter_vencedor(),
            'jogo_terminado': self.tabuleiro.jogo_terminado(),
            'movimentos_validos': self.obter_movimentos_validos()
        }
        
    def obter_vencedor(self) -> int | None:
        """Retorna o vencedor do jogo ou None"""
        vencedor = self.tabuleiro.verificar_vencedor()
        return vencedor.value if vencedor else None
        
    def obter_movimentos_validos(self) -> list:
        """Retorna lista de movimentos válidos para o jogador atual"""
        if self.tabuleiro.fase == FaseJogo.COLOCACAO:
            return self.tabuleiro.obter_posicoes_vazias()
        else:
            return self.tabuleiro.obter_movimentos_validos()
    
    # ==================== JOGADAS DO JOGADOR HUMANO ====================
    
    def fazer_jogada_humano(self, posicao: int = None, origem: int = None, destino: int = None) -> dict:
        """
        Executa jogada do jogador humano
        Para colocação: usar 'posicao'
        Para movimento: usar 'origem' e 'destino'
        """
        resultado = {'sucesso': False, 'mensagem': '', 'estado': None}
        
        try:
            if self.tabuleiro.jogador_atual != Jogador.JOGADOR2:
                resultado['mensagem'] = "Não é a vez do jogador humano"
                return resultado
                
            if self.tabuleiro.jogo_terminado():
                resultado['mensagem'] = "Jogo já terminou"
                return resultado
            
            # Fase de colocação
            if self.tabuleiro.fase == FaseJogo.COLOCACAO:
                if posicao is None:
                    resultado['mensagem'] = "Posição não informada para colocação"
                    return resultado
                    
                if not self._executar_colocacao(posicao, Jogador.JOGADOR2):
                    resultado['mensagem'] = f"Movimento inválido: posição {posicao} já ocupada"
                    return resultado
                    
            # Fase de movimento
            elif self.tabuleiro.fase == FaseJogo.MOVIMENTO:
                if origem is None or destino is None:
                    resultado['mensagem'] = "Origem e destino não informados para movimento"
                    return resultado
                    
                if not self.tabuleiro.eh_movimento_valido(origem, destino):
                    resultado['mensagem'] = f"Movimento inválido: {origem} → {destino}"
                    return resultado
                    
                self._executar_movimento(origem, destino)
            
            # Registrar jogada e alternar jogador
            self._registrar_jogada('HUMANO', posicao, origem, destino)
            self.tabuleiro.alternar_jogador()
            
            resultado['sucesso'] = True
            resultado['mensagem'] = "Jogada executada com sucesso"
            resultado['estado'] = self.obter_estado_jogo()
            
        except Exception as e:
            resultado['mensagem'] = f"Erro ao executar jogada: {str(e)}"
            
        return resultado
    
    # ==================== JOGADAS DO ROBÔ (IA) ====================
    
    def fazer_jogada_robo(self, profundidade: int = 5) -> dict:
        """Executa jogada do robô usando IA"""
        resultado = {'sucesso': False, 'mensagem': '', 'estado': None, 'jogada': None}
        
        try:
            if self.tabuleiro.jogador_atual != Jogador.JOGADOR1:
                resultado['mensagem'] = "Não é a vez do robô"
                return resultado
                
            if self.tabuleiro.jogo_terminado():
                resultado['mensagem'] = "Jogo já terminou"
                return resultado
            
            # Fase de colocação - usar estratégia simples
            if self.tabuleiro.fase == FaseJogo.COLOCACAO:
                jogada = self._fazer_colocacao_robo()
                if jogada is None:
                    resultado['mensagem'] = "Nenhuma posição disponível para colocação"
                    return resultado
                    
                self._executar_colocacao(jogada, Jogador.JOGADOR1)
                resultado['jogada'] = {'posicao': jogada}
                
            # Fase de movimento - usar minimax
            elif self.tabuleiro.fase == FaseJogo.MOVIMENTO:
                jogada = self.ai.fazer_jogada_robo_minimax(profundidade)
                if jogada is None:
                    resultado['mensagem'] = "Nenhum movimento válido disponível"
                    return resultado
                    
                origem, destino = jogada
                self._executar_movimento(origem, destino)
                resultado['jogada'] = {'origem': origem, 'destino': destino}
            
            # Registrar jogada e alternar jogador
            self._registrar_jogada('ROBO', 
                                 resultado['jogada'].get('posicao'),
                                 resultado['jogada'].get('origem'),
                                 resultado['jogada'].get('destino'))
            self.tabuleiro.alternar_jogador()
            
            resultado['sucesso'] = True
            resultado['mensagem'] = "Jogada do robô executada com sucesso"
            resultado['estado'] = self.obter_estado_jogo()
            
        except Exception as e:
            resultado['mensagem'] = f"Erro na jogada do robô: {str(e)}"
            
        return resultado
    
    # ==================== MÉTODOS AUXILIARES PRIVADOS ====================
    
    def _executar_colocacao(self, posicao: int, jogador: Jogador) -> bool:
        """Executa colocação de peça no tabuleiro"""
        if self.tabuleiro.tabuleiro[posicao] != Jogador.VAZIO:
            return False
            
        self.tabuleiro.tabuleiro[posicao] = jogador
        self.tabuleiro.pecas_colocadas[jogador] += 1
        
        # Verificar se deve mudar para fase de movimento
        if (self.tabuleiro.pecas_colocadas[Jogador.JOGADOR1] == 3 and 
            self.tabuleiro.pecas_colocadas[Jogador.JOGADOR2] == 3):
            self.tabuleiro.fase = FaseJogo.MOVIMENTO
            
        return True
    
    def _executar_movimento(self, origem: int, destino: int):
        """Executa movimento de peça no tabuleiro"""
        jogador = self.tabuleiro.tabuleiro[origem]
        self.tabuleiro.tabuleiro[origem] = Jogador.VAZIO
        self.tabuleiro.tabuleiro[destino] = jogador
    
    def _fazer_colocacao_robo(self) -> int | None:
        """Estratégia simples para colocação do robô"""
        posicoes_vazias = self.tabuleiro.obter_posicoes_vazias()
        if not posicoes_vazias:
            return None
            
        # Prioridades: centro -> cantos -> laterais
        prioridades = [4, 0, 2, 6, 8, 1, 3, 5, 7]
        
        for pos in prioridades:
            if pos in posicoes_vazias:
                return pos
                
        return posicoes_vazias[0]  # Fallback
    
    def _registrar_jogada(self, tipo: str, posicao: int = None, origem: int = None, destino: int = None):
        """Registra jogada no histórico"""
        jogada = {
            'tipo': tipo,
            'jogador': self.tabuleiro.jogador_atual.value,
            'fase': self.tabuleiro.fase.value
        }
        
        if posicao is not None:
            jogada['posicao'] = posicao
        if origem is not None and destino is not None:
            jogada['origem'] = origem
            jogada['destino'] = destino
            
        self._historico_jogadas.append(jogada)
    
    # ==================== MÉTODOS DE UTILIDADE ====================
    
    def definir_coordenadas_tabuleiro(self, coordenadas: dict):
        """
        Define coordenadas físicas do tabuleiro para o robô.

        NOTA: Este método mantém compatibilidade retroativa.
        O orquestrador agora usa BoardCoordinateSystem diretamente.

        Args:
            coordenadas: Dict {posição: (x, y, z)} das 9 posições
        """
        self.tabuleiro.coordenadas_tabuleiro = coordenadas
        
    def verificar_coordenadas(self) -> bool:
        """Verifica se as coordenadas do tabuleiro estão definidas"""
        return self.tabuleiro.verificar_coordenadas()
    
    def obter_historico_jogadas(self) -> list:
        """Retorna histórico completo de jogadas"""
        return self._historico_jogadas.copy()
    
    def imprimir_tabuleiro(self):
        """Imprime estado atual do tabuleiro"""
        self.tabuleiro.imprimir_tabuleiro()
        
    def obter_coordenadas_posicao(self, posicao: int) -> tuple | None:
        """Retorna coordenadas físicas de uma posição do tabuleiro"""
        return self.tabuleiro.coordenadas_tabuleiro.get(posicao)

