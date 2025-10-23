"""
TapatanOrchestrator - Orquestrador Principal do Jogo Tapatan Robótico
Integra o controle do robô com a lógica do jogo de forma simples e eficiente
"""

import json
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging

from services.robot_service import RobotService, RobotPose, PickPlaceCommand,ValidationLevel,MovementStrategy
from services.game_service import GameService
from config.config_completa import ConfigRobo
from config.config_completa import ConfigJogo



class OrquestradorStatus(Enum):
    INICIALIZANDO = "inicializando"
    PRONTO = "pronto"
    JOGANDO = "jogando"
    PAUSADO = "pausado"
    ERRO = "erro"
    FINALIZANDO = "finalizando"


class TipoJogada(Enum):
    COLOCACAO = "colocacao"
    MOVIMENTO = "movimento"
    FINALIZACAO = "finalizacao"



class TapatanOrchestrator:
    """Orquestrador principal que coordena jogo e robô"""
    
    def __init__(self, config_robo: Optional[ConfigRobo] = None, 
                 config_jogo: Optional[ConfigJogo] = None):
        self.config_robo = config_robo or ConfigRobo()
        self.config_jogo = config_jogo or ConfigJogo()

        # NOVO: Configurações de distância e posicionamento do robô
        self.offset_robo_x = 0.0  # Distância X do robô em relação ao centro do tabuleiro
        self.offset_robo_y = 0.0  # Distância Y do robô em relação ao centro do tabuleiro
        self.vision_system = None  # Sistema de visão integrado

        self.status = OrquestradorStatus.INICIALIZANDO

        self.robot_service: Optional[RobotService] = None  # Inicializa depois
        self.game_service = GameService()

        # Estados
        self.jogo_ativo = False
        self.ultimo_erro: Optional[str] = None
        self.historico_partida: List[Dict] = []

        # Coordenadas
        self.coordenadas_tabuleiro: Dict[int, Tuple[float, float, float]] = {}
        self.posicao_deposito_pecas: Dict[str, RobotPose] = {}

        self.setup_logging()
        
    def setup_logging(self):
        """Configura sistema de logging"""
        level = logging.DEBUG if self.config_jogo.debug_mode else logging.INFO
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('tapatan_orchestrator.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('TapatanOrchestrator')

    # ====================== INICIALIZAÇÃO E CONFIGURAÇÃO ======================
    
    def inicializar(self) -> bool:
        """Inicializa todos os componentes do sistema"""
        try:
            self.logger.info("Iniciando orquestrador Tapatan...")
            
            # Inicializar robô
            if not self._inicializar_robot():
                return False
                
            # Carregar coordenadas do tabuleiro
            if not self._carregar_coordenadas_tabuleiro():
                return False
                2
            # Calibração automática se habilitada
            if self.config_robo.auto_calibrar:
                if not self.calibrar_sistema():
                    self.logger.warning("⚠️ Calibração automática falhou, continuando...")
            
            self.status = OrquestradorStatus.PRONTO
            self.logger.info("Orquestrador inicializado com sucesso!")
            return True
            
        except Exception as e:
            self.status = OrquestradorStatus.ERRO
            self.ultimo_erro = str(e)
            self.logger.error(f"Erro na inicialização: {e}")
            return False

    def _inicializar_robot(self) -> bool:
        """Inicializa conexão com o robô"""
        try:
            self.robot_service = RobotService()
            self.robot_service.config_robo = self.config_robo
            
            if not self.robot_service.connect():
                self.logger.error("Falha ao conectar com o robô")
                return False
                
            # Mover para posição home
            if not self.robot_service.move_home():
                self.logger.error("Falha ao mover robô para home")
                return False
                
            self.logger.info("Robô inicializado e em posição home")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao inicializar robô: {e}")
            return False

    def _carregar_coordenadas_tabuleiro(self) -> bool:
        """
        Carrega coordenadas físicas do tabuleiro - VERSÃO SIMPLIFICADA FINAL
        
        RESPONSABILIDADE ÚNICA:
        - Apenas gerar coordenadas das 9 posições do tabuleiro
        - Sistema 100% dinâmico baseado em ArUco
        """
        try:
            # ============ VERIFICAR SISTEMA DE VISÃO ============
            if not hasattr(self, 'vision_system') or self.vision_system is None:
                self.logger.error("❌ Sistema de visão ArUco não disponível")
                return False
            
            if not self.vision_system.is_calibrated:
                self.logger.warning("⚠️ Sistema de visão não calibrado")
                self._criar_coordenadas_temporarias()
                return True
            
            # ============ GERAR COORDENADAS DINÂMICAS ============
            self.logger.info("🎯 Carregando coordenadas dinâmicas...")
            
            grid_positions = self.vision_system.calculate_grid_3x3_positions()
            
            if not grid_positions or len(grid_positions) != 9:
                self.logger.error(f"❌ Grid incompleto: {len(grid_positions) if grid_positions else 0}/9")
                self._criar_coordenadas_temporarias()
                return False
            
            # ============ APLICAR COORDENADAS ============
            self.coordenadas_tabuleiro = {}
            
            for pos in grid_positions:
                # Converter mm → metros + aplicar offset do robô
                x_final = (pos['x_mm'] / 1000.0) + getattr(self, 'offset_robo_x', 0.0)
                y_final = (pos['y_mm'] / 1000.0) + getattr(self, 'offset_robo_y', 0.0)
                z_final = (pos['z_mm'] / 1000.0) + 0.05  # Altura do tabuleiro
                
                self.coordenadas_tabuleiro[pos['index']] = (x_final, y_final, z_final)
            
            self.logger.info(f"✅ Tabuleiro pronto: {len(self.coordenadas_tabuleiro)}/9 posições")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao carregar coordenadas: {e}")
            self._criar_coordenadas_temporarias()
            return False

    def _criar_coordenadas_temporarias(self):
        """Coordenadas básicas temporárias (grid 3x3)"""
        self.coordenadas_tabuleiro = {}
        for i in range(9):
            row, col = divmod(i, 3)
            x = (col - 1) * 0.06  # 6cm entre posições
            y = (row - 1) * 0.06
            z = 0.05
            self.coordenadas_tabuleiro[i] = (x, y, z)
        
        self.logger.info("⚠️ Coordenadas temporárias criadas (aguardando calibração)")

    def set_vision_system(self, vision_system):
        """Integra sistema de visão ArUco"""
        self.vision_system = vision_system
        if vision_system.is_calibrated:
            self._carregar_coordenadas_tabuleiro()

    def set_robot_offset(self, offset_x: float, offset_y: float):
        """Define posicionamento do robô em relação ao tabuleiro"""
        self.offset_robo_x = offset_x
        self.offset_robo_y = offset_y
        self.logger.info(f"🤖 Offset robô: X={offset_x:.3f}m, Y={offset_y:.3f}m")
        if hasattr(self, 'vision_system') and self.vision_system and self.vision_system.is_calibrated:
            self._carregar_coordenadas_tabuleiro()

    # ====================== CONTROLE DO JOGO ======================
    
    def iniciar_partida(self) -> bool:
        """Inicia uma nova partida"""
        try:
            if self.status != OrquestradorStatus.PRONTO:
                self.logger.error("Sistema não está pronto para iniciar partida")
                return False
                
            self.logger.info("Iniciando nova partida de Tapatan...")
            
            # Reiniciar jogo
            self.game_service.reiniciar_jogo()
            self.jogo_ativo = True
            self.historico_partida.clear()
            self.status = OrquestradorStatus.JOGANDO
            
            # Mover robô para posição inicial
            self.robot_service.move_home()
            
            self.logger.info("Partida iniciada! Aguardando primeiro movimento...")
            return True
            
        except Exception as e:
            self.ultimo_erro = str(e)
            self.logger.error(f"Erro ao iniciar partida: {e}")
            return False

    def processar_jogada_humano(self, posicao: int = None, origem: int = None, destino: int = None) -> Dict[str, Any]:
        """Processa jogada do jogador humano"""
        try:
            if not self.jogo_ativo:
                return {"sucesso": False, "mensagem": "Jogo não está ativo"}
                
            self.logger.info(f"Processando jogada humano: pos={posicao}, orig={origem}, dest={destino}")
            
            # Executar jogada no game service
            resultado = self.game_service.fazer_jogada_humano(posicao, origem, destino)
            
            if resultado["sucesso"]:
                # Registrar no histórico
                self._registrar_jogada("HUMANO", posicao, origem, destino)
                
                # Verificar se jogo terminou
                if self._verificar_fim_jogo():
                    return resultado
                    
                # Executar jogada do robô automaticamente
                time.sleep(self.config_robo.pausa_entre_jogadas)
                resultado_robo = self.executar_jogada_robo()
                
                resultado["jogada_robo"] = resultado_robo
                
            return resultado
            
        except Exception as e:
            self.logger.error(f"Erro ao processar jogada humano: {e}")
            return {"sucesso": False, "mensagem": f"Erro: {str(e)}"}

    def executar_jogada_robo(self) -> Dict[str, Any]:
        """Executa jogada do robô (IA + movimento físico)"""
        try:
            if not self.jogo_ativo:
                return {"sucesso": False, "mensagem": "Jogo não está ativo"}
                
            self.logger.info("Executando jogada do robô...")
            
            # Obter jogada da IA
            resultado_ia = self.game_service.fazer_jogada_robo(self.config_jogo.profundidade_ia)
            
            if not resultado_ia["sucesso"]:
                resultado_ia["mensagem"] = str(resultado_ia.get("mensagem", "")) + " (falha no movimento físico)"

                
            # Executar movimento físico do robô
            sucesso_movimento = self._executar_movimento_fisico(resultado_ia["jogada"])
            
            if sucesso_movimento:
                # Registrar no histórico
                jogada = resultado_ia["jogada"]
                self._registrar_jogada("ROBO", 
                                     jogada.get("posicao"),
                                     jogada.get("origem"),
                                     jogada.get("destino"))
                
                # Verificar fim do jogo
                self._verificar_fim_jogo()
                
                resultado_ia["movimento_fisico"] = "executado"
            else:
                resultado_ia["movimento_fisico"] = "falha"
                resultado_ia["sucesso"] = False
                resultado_ia["mensagem"] += " (falha no movimento físico)"
                
            return resultado_ia
            
        except Exception as e:
            self.logger.error(f"Erro ao executar jogada do robô: {e}")
            return {"sucesso": False, "mensagem": f"Erro: {str(e)}"}

    def _executar_movimento_fisico(self, jogada: Dict[str, Any]) -> bool:
        """Executa o movimento físico do robô baseado na jogada"""
        try:
            estado_jogo = self.game_service.obter_estado_jogo()

            if estado_jogo["fase"] == "colocacao":
                posicao = jogada["posicao"]
                destino = self.coordenadas_tabuleiro.get(posicao)

                if not destino:
                    self.logger.error(f"Posição física não encontrada para {posicao}")
                    return False

                pose_destino = RobotPose.from_list([*destino, 0.0, 3.14, 0.0])

                if self.config_robo.validar_antes_executar:
                    resultado = self.robot_service.validate_pose(pose_destino, validation_level=ValidationLevel.COMPLETE)
                    if not resultado.is_valid:
                        self.logger.error(f" Pose inválida para colocação: {resultado.error_message}")
                        return False

                return self.robot_service.move_to_pose(
                    pose=pose_destino,
                    speed=self.config_robo.velocidade_normal
                )

            elif estado_jogo["fase"] == "movimento":
                return self._executar_movimento_fisico_peca(jogada["origem"], jogada["destino"])

            return False

        except Exception as e:
            self.logger.error(f"Erro no movimento físico: {e}")
            return False
    def _executar_colocacao_fisica(self, posicao: int) -> bool:
        """Executa colocação física de peça"""
        try:
            # Obter coordenadas da posição
            if posicao not in self.coordenadas_tabuleiro:
                self.logger.error(f"Posição {posicao} não encontrada nas coordenadas")
                return False
                
            coord_destino = self.coordenadas_tabuleiro[posicao]
            
            # Criar poses para pick and place
            origem = self.posicao_deposito_pecas["jogador1"]
            destino = RobotPose(coord_destino[0], coord_destino[1], coord_destino[2], 0.0, 3.14, 0.0)
            
            # Executar pick and place
            comando = PickPlaceCommand(
                origin=origem,
                destination=destino,
                safe_height=self.config_robo.altura_segura,
                pick_height=self.config_robo.altura_pegar,
                speed_normal=self.config_robo.velocidade_normal,
                speed_precise=self.config_robo.velocidade_precisa
            )
            
            sucesso = self.robot_service.pick_and_place(comando)
            
            if sucesso:
                self.logger.info(f"Peça colocada na posição {posicao}")
            else:
                self.logger.error(f"Falha ao colocar peça na posição {posicao}")
                
            return sucesso
            
        except Exception as e:
            self.logger.error(f"Erro na colocação física: {e}")
            return False

    def _executar_movimento_fisico_peca(self, origem: int, destino: int) -> bool:
        """Executa movimento físico de peça no tabuleiro"""
        try:
            # Obter coordenadas
            if origem not in self.coordenadas_tabuleiro or destino not in self.coordenadas_tabuleiro:
                self.logger.error(f"Coordenadas não encontradas: origem={origem}, destino={destino}")
                return False
                
            coord_origem = self.coordenadas_tabuleiro[origem]
            coord_destino = self.coordenadas_tabuleiro[destino]
            
            # Criar poses
            pose_origem = RobotPose(coord_origem[0], coord_origem[1], coord_origem[2], 0.0, 3.14, 0.0)
            pose_destino = RobotPose(coord_destino[0], coord_destino[1], coord_destino[2], 0.0, 3.14, 0.0)
            
            # Executar movimento
            comando = PickPlaceCommand(
                origin=pose_origem,
                destination=pose_destino,
                safe_height=self.config_robo.altura_segura,
                pick_height=self.config_robo.altura_pegar,
                speed_normal=self.config_robo.velocidade_normal,
                speed_precise=self.config_robo.velocidade_precisa
            )
            
            sucesso = self.robot_service.pick_and_place(comando)
            
            if sucesso:
                self.logger.info(f"Peça movida de {origem} para {destino}")
            else:
                self.logger.error(f"Falha ao mover peça de {origem} para {destino}")
                
            return sucesso
            
        except Exception as e:
            self.logger.error(f"Erro no movimento físico da peça: {e}")
            return False

    # ====================== CONTROLE E MONITORAMENTO ======================
    
    def obter_status_completo(self) -> Dict[str, Any]:
        """Retorna status completo do sistema"""
        status = {
            "orquestrador": {
                "status": self.status.value,
                "jogo_ativo": self.jogo_ativo,
                "ultimo_erro": self.ultimo_erro
            },
            "jogo": self.game_service.obter_estado_jogo() if self.jogo_ativo else None,
            "robot": self.robot_service.get_status() if self.robot_service else None,
            "historico": self.historico_partida
        }
        
        return status

    def pausar_jogo(self):
        """Pausa o jogo atual"""
        if self.jogo_ativo:
            self.status = OrquestradorStatus.PAUSADO
            self.logger.info("⏸️ Jogo pausado")

    def retomar_jogo(self):
        """Retoma o jogo pausado"""
        if self.status == OrquestradorStatus.PAUSADO:
            self.status = OrquestradorStatus.JOGANDO
            self.logger.info("▶️ Jogo retomado")

    def parar_jogo(self):
        """Para o jogo atual"""
        self.jogo_ativo = False
        self.status = OrquestradorStatus.PRONTO
        self.logger.info("Jogo parado")

    def parada_emergencia(self) -> bool:
        """Executa parada de emergência"""
        try:
            if self.robot_service:
                sucesso = self.robot_service.emergency_stop()
                if sucesso:
                    self.status = OrquestradorStatus.ERRO
                    self.jogo_ativo = False
                    self.logger.warning("PARADA DE EMERGÊNCIA EXECUTADA")
                return sucesso
            return False
        except Exception as e:
            self.logger.error(f"Erro na parada de emergência: {e}")
            return False

    def calibrar_sistema(self) -> bool:
        """Executa calibração do sistema"""
        try:
            self.logger.info("Iniciando calibração do sistema...")
            
            # Verificar conexão do robô
            if not self.robot_service or not self.robot_service.get_status()["connected"]:
                self.logger.error("Robô não conectado para calibração")
                return False
                
            # Mover para home
            if not self.robot_service.move_home():
                self.logger.error("Falha ao mover para home na calibração")
                return False
                
            # Testar algumas posições do tabuleiro
            posicoes_teste = [0, 4, 8]  # Cantos e centro
            for pos in posicoes_teste:
                if pos in self.coordenadas_tabuleiro:
                    coord = self.coordenadas_tabuleiro[pos]
                    pose_teste = RobotPose(coord[0], coord[1], coord[2] + 0.1, 0.0, 3.14, 0.0)
                    
                    if not self.robot_service.move_to_pose(pose_teste, 0.05):
                        self.logger.error(f"Falha ao testar posição {pos}")
                        return False
                        
            # Retornar para home
            self.robot_service.move_home()
            
            self.logger.info("Calibração concluída com sucesso")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro na calibração: {e}")
            return False

    # ====================== MÉTODOS AUXILIARES ======================
    
    def _verificar_fim_jogo(self) -> bool:
        """Verifica se o jogo terminou"""
        estado = self.game_service.obter_estado_jogo()
        
        if estado["jogo_terminado"]:
            self.jogo_ativo = False
            self.status = OrquestradorStatus.PRONTO
            
            vencedor = "Empate" if estado["vencedor"] is None else f"Jogador {estado['vencedor']}"
            self.logger.info(f"Jogo terminado! Vencedor: {vencedor}")
            
            # Mover robô para home
            if self.robot_service:
                self.robot_service.move_home()
                
            return True
            
        return False

    def _registrar_jogada(self, tipo: str, posicao: int = None, origem: int = None, destino: int = None):
        """Registra jogada no histórico do orquestrador"""
        jogada = {
            "timestamp": time.time(),
            "tipo": tipo,
            "posicao": posicao,
            "origem": origem,
            "destino": destino
        }
        self.historico_partida.append(jogada)

    def finalizar(self):
        """Finaliza o orquestrador e limpa recursos"""
        try:
            self.status = OrquestradorStatus.FINALIZANDO
            self.logger.info("Finalizando orquestrador...")
            
            # Parar jogo se ativo
            if self.jogo_ativo:
                self.parar_jogo()
                
            # Desconectar robô
            if self.robot_service:
                self.robot_service.move_home()
                self.robot_service.disconnect()
                
            self.logger.info("Orquestrador finalizado")
            
        except Exception as e:
            self.logger.error(f"Erro ao finalizar: {e}")

    # ====================== CONTEXT MANAGER ======================
    
    def __enter__(self):
        """Context manager entry"""
        self.inicializar()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.finalizar()
