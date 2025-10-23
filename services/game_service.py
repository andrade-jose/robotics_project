"""
GameService - Serviço Central do Jogo Tapatan
Combina a lógica do jogo e IA em uma interface única e simples
"""
from typing import Dict,Tuple
from config.config_completa import Jogador, FaseJogo
from logic_control.tapatan_logic import TabuleiraTapatan
from logic_control.tapatan_ai import TapatanAI
from utils.tapatan_board import gerar_tabuleiro_tapatan

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
        """Define coordenadas físicas do tabuleiro para o robô"""
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
    # NO GAME_SERVICE.PY - MÉTODOS SIMPLIFICADOS (SEM DEPÓSITO):

def validar_coordenadas_tabuleiro(self, coordenadas_tabuleiro: dict) -> dict:
    """
    Valida se as coordenadas do tabuleiro estão corretas
    
    Returns:
        Dict com resultado da validação e detalhes
    """
    resultado = {
        'valido': False,
        'posicoes_ok': 0,
        'posicoes_faltando': [],
        'distancias_ok': True,
        'detalhes': []
    }
    
    try:
        # Verificar se temos as 9 posições
        posicoes_esperadas = set(range(9))
        posicoes_encontradas = set(coordenadas_tabuleiro.keys())
        
        resultado['posicoes_ok'] = len(posicoes_encontradas)
        resultado['posicoes_faltando'] = list(posicoes_esperadas - posicoes_encontradas)
        
        if resultado['posicoes_faltando']:
            resultado['detalhes'].append(f"Posições faltando: {resultado['posicoes_faltando']}")
            return resultado
        
        # Verificar consistência das distâncias
        distancias = []
        for i in [0, 3, 6]:  # Primeira coluna de cada linha
            if i in coordenadas_tabuleiro and (i+1) in coordenadas_tabuleiro:
                coord1 = coordenadas_tabuleiro[i]
                coord2 = coordenadas_tabuleiro[i+1]
                dist = ((coord2[0]-coord1[0])**2 + (coord2[1]-coord1[1])**2)**0.5
                distancias.append(dist)
        
        if distancias:
            dist_media = sum(distancias) / len(distancias)
            variacao = max(distancias) - min(distancias)
            
            if variacao > dist_media * 0.1:  # Variação > 10%
                resultado['distancias_ok'] = False
                resultado['detalhes'].append(f"Distâncias inconsistentes: {variacao*100:.1f}cm")
            else:
                resultado['detalhes'].append(f"Espaçamento OK: {dist_media*100:.1f}cm")
        
        resultado['valido'] = (resultado['posicoes_ok'] == 9 and resultado['distancias_ok'])
        
        if resultado['valido']:
            resultado['detalhes'].append("✅ Tabuleiro válido")
        
        return resultado
        
    except Exception as e:
        resultado['detalhes'].append(f"Erro na validação: {e}")
        return resultado

def get_coordenadas_status(self, coordenadas_tabuleiro: dict, vision_system=None) -> dict:
    """
    Status das coordenadas para debug
    """
    return {
        'total_posicoes': len(coordenadas_tabuleiro),
        'sistema_dinamico': vision_system is not None,
        'visao_calibrada': vision_system.is_calibrated if vision_system else False,
        'validacao': self.validar_coordenadas_tabuleiro(coordenadas_tabuleiro),
        'exemplo_coordenadas': {
            'pos_0': coordenadas_tabuleiro.get(0),
            'pos_4_centro': coordenadas_tabuleiro.get(4),
            'pos_8': coordenadas_tabuleiro.get(8)
        }
    }

def definir_coordenadas_tabuleiro(self, coordenadas: dict):
    """
    Define coordenadas físicas do tabuleiro - MÉTODO SIMPLIFICADO
    
    Args:
        coordenadas: Dict {posicao: (x, y, z)} das 9 posições
    """
    self.tabuleiro.coordenadas_tabuleiro = coordenadas
    print(f"📍 Coordenadas definidas: {len(coordenadas)} posições")

def verificar_coordenadas(self) -> bool:
    """
    Verifica se coordenadas estão definidas - MÉTODO SIMPLIFICADO
    """
    if not hasattr(self.tabuleiro, 'coordenadas_tabuleiro'):
        return False
    
    coordenadas = self.tabuleiro.coordenadas_tabuleiro
    if len(coordenadas) != 9:
        print(f"❌ Coordenadas incompletas: {len(coordenadas)}/9")
        return False
    
    for i in range(9):
        if i not in coordenadas:
            print(f"❌ Posição {i} não definida")
            return False
    
    print("✅ Todas as 9 posições definidas")
    return True

def obter_coordenadas_posicao(self, posicao: int) -> tuple:
    """
    Retorna coordenadas de uma posição específica
    
    Args:
        posicao: Índice da posição (0-8)
        
    Returns:
        Tupla (x, y, z) ou None se não existir
    """
    if hasattr(self.tabuleiro, 'coordenadas_tabuleiro'):
        return self.tabuleiro.coordenadas_tabuleiro.get(posicao)
    return None

