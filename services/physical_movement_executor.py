"""
PhysicalMovementExecutor - Executor de Movimentos Físicos do Robô
==================================================================
Responsável pela execução de todos os movimentos físicos do robô:
- Colocação de peças
- Movimento de peças no tabuleiro
- Conversão de jogadas lógicas para comandos físicos
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

from services.robot_service import RobotService, RobotPose, PickPlaceCommand, ValidationLevel
from services.board_coordinate_system import BoardCoordinateSystem
from config.config_completa import ConfigRobo


class PhysicalMovementExecutor:
    """
    Executa movimentos físicos do robô baseados em jogadas lógicas.

    Responsabilidades:
    - Converter posições do tabuleiro em comandos de robô
    - Executar colocação de peças
    - Executar movimentos de peças
    - Validar poses antes da execução
    - Gerenciar sequências pick-and-place
    """

    def __init__(self,
                 robot_service: RobotService,
                 board_coords: BoardCoordinateSystem,
                 config_robo: ConfigRobo,
                 logger: Optional[logging.Logger] = None):
        """
        Inicializa o executor de movimentos físicos.

        Args:
            robot_service: Serviço de comunicação com o robô
            board_coords: Sistema de coordenadas do tabuleiro
            config_robo: Configuração do robô
            logger: Logger opcional
        """
        self.robot_service = robot_service
        self.board_coords = board_coords
        self.config_robo = config_robo
        self.logger = logger or logging.getLogger('PhysicalMovementExecutor')

        # Depósito de peças (posições de onde pegar peças novas)
        self.posicao_deposito_pecas: Dict[str, RobotPose] = {}

    # ========== CONFIGURAÇÃO ==========

    def set_piece_depot_position(self, player: str, pose: RobotPose):
        """
        Define a posição do depósito de peças para um jogador.

        Args:
            player: Identificador do jogador (ex: "jogador1", "jogador2")
            pose: Posição do depósito
        """
        self.posicao_deposito_pecas[player] = pose
        self.logger.info(f"Posição do depósito definida para {player}")

    # ========== EXECUÇÃO DE MOVIMENTOS ==========

    def executar_movimento_jogada(self, jogada: Dict[str, Any], fase: str) -> bool:
        """
        Executa o movimento físico baseado na jogada e fase do jogo.

        Args:
            jogada: Dicionário com informações da jogada
            fase: Fase do jogo ("colocacao" ou "movimento")

        Returns:
            True se o movimento foi executado com sucesso
        """
        try:
            if fase == "colocacao":
                posicao = jogada["posicao"]
                return self.executar_colocacao(posicao)

            elif fase == "movimento":
                return self.executar_movimento_peca(
                    jogada["origem"],
                    jogada["destino"]
                )

            self.logger.error(f"Fase desconhecida: {fase}")
            return False

        except Exception as e:
            self.logger.error(f"Erro ao executar movimento da jogada: {e}")
            return False

    def executar_colocacao(self, posicao: int, player: str = "jogador1") -> bool:
        """
        Executa colocação física de peça em uma posição do tabuleiro.

        Args:
            posicao: Posição no tabuleiro (0-8)
            player: Identificador do jogador

        Returns:
            True se a colocação foi bem-sucedida
        """
        try:
            # Obter coordenadas da posição de destino
            coord_destino = self.board_coords.get_position(posicao)
            if not coord_destino:
                self.logger.error(f"Posição {posicao} não encontrada nas coordenadas")
                return False

            # Obter posição do depósito de peças
            if player not in self.posicao_deposito_pecas:
                self.logger.error(f"Posição do depósito não definida para {player}")
                return False

            origem = self.posicao_deposito_pecas[player]
            destino = RobotPose(
                coord_destino[0],
                coord_destino[1],
                coord_destino[2],
                0.0,  # rx
                3.14,  # ry (180 graus)
                0.0   # rz
            )

            # Validar pose de destino se configurado
            if self.config_robo.validar_antes_executar:
                resultado = self.robot_service.validate_pose(
                    destino,
                    validation_level=ValidationLevel.COMPLETE
                )
                if not resultado.is_valid:
                    self.logger.error(f"Pose de destino inválida: {resultado.error_message}")
                    return False

            # Criar e executar comando pick-and-place
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
                self.logger.info(f"[OK] Peça colocada na posição {posicao}")
            else:
                self.logger.error(f"[ERRO] Falha ao colocar peça na posição {posicao}")

            return sucesso

        except Exception as e:
            self.logger.error(f"Erro na colocação física: {e}")
            return False

    def executar_movimento_peca(self, origem: int, destino: int) -> bool:
        """
        Executa movimento físico de peça de uma posição para outra no tabuleiro.

        Args:
            origem: Posição de origem (0-8)
            destino: Posição de destino (0-8)

        Returns:
            True se o movimento foi bem-sucedido
        """
        try:
            # Obter coordenadas de origem e destino
            coord_origem = self.board_coords.get_position(origem)
            coord_destino = self.board_coords.get_position(destino)

            if not coord_origem or not coord_destino:
                self.logger.error(
                    f"Coordenadas não encontradas: origem={origem}, destino={destino}"
                )
                return False

            # Criar poses
            pose_origem = RobotPose(
                coord_origem[0],
                coord_origem[1],
                coord_origem[2],
                0.0,
                3.14,
                0.0
            )
            pose_destino = RobotPose(
                coord_destino[0],
                coord_destino[1],
                coord_destino[2],
                0.0,
                3.14,
                0.0
            )

            # Validar poses se configurado
            if self.config_robo.validar_antes_executar:
                for pose, nome in [(pose_origem, "origem"), (pose_destino, "destino")]:
                    resultado = self.robot_service.validate_pose(
                        pose,
                        validation_level=ValidationLevel.COMPLETE
                    )
                    if not resultado.is_valid:
                        self.logger.error(f"Pose de {nome} inválida: {resultado.error_message}")
                        return False

            # Criar e executar comando pick-and-place
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
                self.logger.info(f"[OK] Peça movida de {origem} para {destino}")
            else:
                self.logger.error(f"[ERRO] Falha ao mover peça de {origem} para {destino}")

            return sucesso

        except Exception as e:
            self.logger.error(f"Erro no movimento físico da peça: {e}")
            return False

    def executar_movimento_simples(self, posicao: int) -> bool:
        """
        Executa movimento simples para uma posição (usado em calibração).

        Args:
            posicao: Posição no tabuleiro (0-8)

        Returns:
            True se o movimento foi bem-sucedido
        """
        try:
            coord = self.board_coords.get_position(posicao)
            if not coord:
                self.logger.error(f"Posição {posicao} não encontrada")
                return False

            # Criar pose com altura um pouco acima da posição
            pose_teste = RobotPose(
                coord[0],
                coord[1],
                coord[2] + 0.1,  # 10cm acima
                0.0,
                3.14,
                0.0
            )

            # Validar se configurado
            if self.config_robo.validar_antes_executar:
                resultado = self.robot_service.validate_pose(
                    pose_teste,
                    validation_level=ValidationLevel.COMPLETE
                )
                if not resultado.is_valid:
                    self.logger.error(f"Pose inválida para posição {posicao}")
                    return False

            return self.robot_service.move_to_pose(
                pose=pose_teste,
                speed=self.config_robo.velocidade_normal
            )

        except Exception as e:
            self.logger.error(f"Erro no movimento simples: {e}")
            return False