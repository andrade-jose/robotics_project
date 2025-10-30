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
from services.board_coordinate_system import BoardCoordinateSystem
from services.physical_movement_executor import PhysicalMovementExecutor
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

        self.status = OrquestradorStatus.INICIALIZANDO

        self.robot_service: Optional[RobotService] = None  # Inicializa depois
        self.game_service = GameService()

        # Sistema de coordenadas centralizado
        self.setup_logging()
        self.board_coords = BoardCoordinateSystem(logger=self.logger)

        # Executor de movimentos físicos (criado após inicialização do robô)
        self.movement_executor: Optional[PhysicalMovementExecutor] = None

        # Estados
        self.jogo_ativo = False
        self.ultimo_erro: Optional[str] = None
        self.historico_partida: List[Dict] = []
        
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
                    self.logger.warning("[AVISO] Calibração automática falhou, continuando...")
            
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
            self.robot_service = RobotService(config_robo=self.config_robo)

            if not self.robot_service.connect():
                self.logger.error("Falha ao conectar com o robô")
                return False

            # Mover para posição home
            if not self.robot_service.move_home():
                self.logger.error("Falha ao mover robô para home")
                return False

            # Criar executor de movimentos físicos
            self.movement_executor = PhysicalMovementExecutor(
                robot_service=self.robot_service,
                board_coords=self.board_coords,
                config_robo=self.config_robo,
                logger=self.logger
            )

            # Configurar posições de depósito (exemplo - ajustar conforme necessário)
            deposito_pose = RobotPose(0.3, -0.3, 0.1, 0.0, 3.14, 0.0)
            self.movement_executor.set_piece_depot_position("jogador1", deposito_pose)

            self.logger.info("Robô inicializado e em posição home")
            return True

        except Exception as e:
            self.logger.error(f"Erro ao inicializar robô: {e}")
            return False

    def _carregar_coordenadas_tabuleiro(self) -> bool:
        """
        Carrega coordenadas físicas do tabuleiro usando BoardCoordinateSystem.

        Returns:
            True se coordenadas foram carregadas com sucesso
        """
        try:
            # Verificar se sistema de visão está disponível
            if not hasattr(self, 'board_coords') or self.board_coords is None:
                self.logger.error("[ERRO] Sistema de coordenadas não inicializado")
                return False

            # Tentar gerar coordenadas dinâmicas via visão
            if self.board_coords.vision_system and self.board_coords.vision_system.is_calibrated:
                self.logger.info("[EXECUTANDO] Carregando coordenadas dinâmicas...")
                if self.board_coords.generate_from_vision(self.board_coords.vision_system):
                    self.logger.info("[OK] Coordenadas dinâmicas carregadas")
                    return True

            # Fallback: coordenadas temporárias
            self.logger.warning("[AVISO] Usando coordenadas temporárias")
            self.board_coords.generate_temporary_grid()
            return True

        except Exception as e:
            self.logger.error(f"[ERRO] Erro ao carregar coordenadas: {e}")
            self.board_coords.generate_temporary_grid()
            return False

    def set_vision_system(self, vision_system):
        """Integra sistema de visão ArUco"""
        self.board_coords.set_vision_system(vision_system)

    def set_robot_offset(self, offset_x: float, offset_y: float):
        """Define posicionamento do robô em relação ao tabuleiro"""
        self.board_coords.set_robot_offset(offset_x, offset_y)

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
        """
        Executa o movimento físico do robô baseado na jogada.
        DELEGA para PhysicalMovementExecutor.
        """
        try:
            if not self.movement_executor:
                self.logger.error("Executor de movimentos não inicializado")
                return False

            estado_jogo = self.game_service.obter_estado_jogo()
            return self.movement_executor.executar_movimento_jogada(
                jogada=jogada,
                fase=estado_jogo["fase"]
            )

        except Exception as e:
            self.logger.error(f"Erro no movimento físico: {e}")
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
            self.logger.info("[PARADA] Jogo pausado")

    def retomar_jogo(self):
        """Retoma o jogo pausado"""
        if self.status == OrquestradorStatus.PAUSADO:
            self.status = OrquestradorStatus.JOGANDO
            self.logger.info("[INICIO] Jogo retomado")

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
        """
        Executa calibração do sistema.
        Usa PhysicalMovementExecutor para testar posições.
        """
        try:
            self.logger.info("Iniciando calibração do sistema...")

            # Verificar conexão do robô
            if not self.robot_service or not self.robot_service.get_status()["connected"]:
                self.logger.error("Robô não conectado para calibração")
                return False

            if not self.movement_executor:
                self.logger.error("Executor de movimentos não inicializado")
                return False

            # Mover para home
            if not self.robot_service.move_home():
                self.logger.error("Falha ao mover para home na calibração")
                return False

            # Testar algumas posições do tabuleiro
            posicoes_teste = [0, 4, 8]  # Cantos e centro
            for pos in posicoes_teste:
                if not self.movement_executor.executar_movimento_simples(pos):
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
