import json
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from pathlib import Path
import math

from logic_control.ur_controller import URController
from config.config_completa import CONFIG, ConfigRobo
from services.game_service import gerar_tabuleiro_tapatan

class RobotStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    MOVING = "moving"
    IDLE = "idle"
    ERROR = "error"
    EMERGENCY_STOP = "emergency_stop"
    VALIDATING = "validating"

class MovementType(Enum):
    LINEAR = "linear"
    JOINT = "joint"
    PICK_PLACE = "pick_place"
    HOME = "home"
    SEQUENCE = "sequence"
    SMART_CORRECTION = "smart_correction"  #  NOVO: Movimento com correção automática
    INTERMEDIATE_POINTS = "intermediate_points"  #  NOVO: Movimento com pontos intermediários

class ValidationLevel(Enum):
    BASIC = "basic"           # Apenas workspace
    STANDARD = "standard"     # Workspace + alcançabilidade  
    ADVANCED = "advanced"     # Workspace + alcançabilidade + UR safety limits
    COMPLETE = "complete"     #  NOVO: Validação completa com todas as verificações

class MovementStrategy(Enum):
    DIRECT = "direct"                    # Movimento direto
    SMART_CORRECTION = "smart_correction"  #  NOVO: Com correção automática
    INTERMEDIATE = "intermediate"        #  NOVO: Com pontos intermediários
    ULTRA_SAFE = "ultra_safe"           #  NOVO: Todas as estratégias de segurança

@dataclass
class RobotPose:
    x: float
    y: float
    z: float
    rx: float
    ry: float
    rz: float
    
    def to_list(self) -> List[float]:
        return [self.x, self.y, self.z, self.rx, self.ry, self.rz]
    
    @classmethod
    def from_list(cls, pose_list: List[float]):
        if len(pose_list) != 6:
            raise ValueError("Pose deve ter exatamente 6 elementos")
        return cls(*pose_list)
    
    def __str__(self):
        return f"Pose(x={self.x:.3f}, y={self.y:.3f}, z={self.z:.3f}, rx={self.rx:.3f}, ry={self.ry:.3f}, rz={self.rz:.3f})"

@dataclass
class MovementCommand:
    type: MovementType
    target_pose: Optional[RobotPose] = None
    speed: Optional[float] = None
    acceleration: Optional[float] = None
    validation_level: ValidationLevel = ValidationLevel.ADVANCED  #  NOVO
    movement_strategy: MovementStrategy = MovementStrategy.SMART_CORRECTION  #  NOVO
    parameters: Optional[Dict[str, Any]] = None

@dataclass
class PickPlaceCommand:
    origin: RobotPose
    destination: RobotPose
    safe_height: float
    pick_height: float
    speed_normal: float = 0.1
    speed_precise: float = 0.05
    validation_level: ValidationLevel = ValidationLevel.COMPLETE  #  NOVO: Validação completa para pick&place

@dataclass
class ValidationResult:
    """ NOVO: Resultado detalhado de validação"""
    is_valid: bool
    workspace_ok: bool = False
    reachability_ok: bool = False
    safety_limits_ok: bool = False
    corrections_applied: List[str] = None
    final_pose: Optional[List[float]] = None
    error_message: Optional[str] = None

class RobotService:
    def __init__(self, config_file: Optional[str] = None):
        # Usar config fornecida ou criar padrão
        self.config_robo = ConfigRobo()
        self.robot_ip = self.config_robo.ip
        self.controller: Optional[URController] = None
        self.status = RobotStatus.DISCONNECTED
        self.last_error: Optional[str] = None
        self.poses = gerar_tabuleiro_tapatan
        
        # Converter ConfigRobo para formato dict compatível (temporário)
        self.config = self._convert_config_to_dict()
        
        # Carregar configuração adicional se fornecida
        if config_file:
            additional_config = self.load_config(config_file)
            self.config.update(additional_config)
        
        # Setup logging
        self.setup_logging()
        
        # Histórico de movimentos para análise
        self.movement_history: List[Dict] = []
        self.validation_stats = {
            "total_validations": 0,
            "successful_validations": 0,
            "corrections_applied": 0,
            "movements_with_intermediate_points": 0
        }
        self.verbose_logging = False
        self.log_summary_only = True
        
    def setup_logging(self):
        """Configura sistema de logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('robot_service.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('RobotService')

    def _convert_config_to_dict(self) -> Dict:
        """Converte ConfigRobo para dict mantendo compatibilidade"""
        return {
            "speed": self.config_robo.velocidade_padrao,
            "acceleration": self.config_robo.aceleracao_padrao,
            "safe_height": self.config_robo.altura_segura,
            "pick_height": self.config_robo.altura_pegar,
            "pause_between_moves": self.config_robo.pausa_entre_movimentos,
            "home_pose": self.config_robo.pose_home,
            
            "default_validation_level": self.config_robo.nivel_validacao_padrao,
            "default_movement_strategy": self.config_robo.estrategia_movimento_padrao,
            "enable_auto_correction": self.config_robo.habilitar_correcao_automatica,
            "max_correction_attempts": self.config_robo.max_tentativas_correcao,
            "intermediate_points_distance_threshold": self.config_robo.distancia_threshold_pontos_intermediarios,
            "ultra_safe_mode": self.config_robo.modo_ultra_seguro,
            
            "smart_movement": {
                "enable_smart_correction": self.config_robo.habilitar_correcao_inteligente,
                "enable_intermediate_points": self.config_robo.habilitar_pontos_intermediarios,
                "max_movement_distance": self.config_robo.distancia_maxima_movimento,
                "intermediate_points_step": self.config_robo.passo_pontos_intermediarios,
                "ultra_safe_speed_factor": self.config_robo.fator_velocidade_ultra_seguro,
                "validation_retries": self.config_robo.tentativas_validacao
            },
            
        }

    def load_config(self, config_file: str) -> Dict:
        """Carrega configuração de arquivo JSON"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            self.logger.info(f" Configuração carregada de {config_file}")
            return config
        except Exception as e:
            self.logger.error(f" Erro ao carregar configuração: {e}")
            return {}

    def save_config(self, config_file: str):
        """Salva configuração atual em arquivo JSON"""
        try:
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
            self.logger.info(f" Configuração salva em {config_file}")
        except Exception as e:
            self.logger.error(f" Erro ao salvar configuração: {e}")

    def connect(self) -> bool:
        """Conecta ao robô"""
        try:
            self.logger.info(f" Conectando ao robô em {self.robot_ip}...")
            self.controller = URController(
                robot_ip=self.robot_ip,
                speed=self.config["speed"],
                acceleration=self.config["acceleration"]
            )
            
            if self.controller.is_connected():
                self.status = RobotStatus.CONNECTED
                
                #  NOVO: Configurar parâmetros de segurança no controlador
                if self.config.get("enable_auto_correction", True):
                    self.controller.enable_safety_mode(True)
                
                self.logger.info(" Robô conectado com sucesso")
                self.logger.info(f" Modo de segurança: {'HABILITADO' if self.config.get('enable_auto_correction', True) else 'DESABILITADO'}")
                return True
            else:
                self.status = RobotStatus.ERROR
                self.last_error = "Falha na conexão"
                self.logger.error(" Falha ao conectar com o robô")
                return False
                
        except Exception as e:
            self.status = RobotStatus.ERROR
            self.last_error = str(e)
            self.logger.error(f" Erro ao conectar: {e}")
            return False

    def disconnect(self):
        """Desconecta do robô"""
        try:
            if self.controller:
                self.controller.disconnect()
                self.controller = None
            self.status = RobotStatus.DISCONNECTED
            self.logger.info(" Robô desconectado")
        except Exception as e:
            self.logger.error(f" Erro ao desconectar: {e}")

        
    # ===================  FUNÇÕES DE MOVIMENTO ATUALIZADAS ===================

    def move_to_pose(self, pose, speed=None, acceleration=None, strategy="auto"):
        """Movimento simplificado - URController faz toda validação"""
        if not self._check_connection():
            return False
        
        try:
            self.status = RobotStatus.MOVING
            success = self.controller.move_to_pose_safe(
                pose.to_list(), 
                speed or self.config["speed"],
                acceleration or self.config["acceleration"],
                strategy
            )
            
            self.status = RobotStatus.IDLE if success else RobotStatus.ERROR
            return success

        except Exception as e:
            self.status = RobotStatus.ERROR
            self.last_error = str(e)
            return False

    def move_home(self) -> bool:
        """Move robô para posição home com segurança máxima"""
        home_pose = RobotPose.from_list(self.config["home_pose"])
        self.logger.info(" Movendo para posição home")
        
        # Home sempre usa estratégia ultra-segura
        return self.move_to_pose(home_pose)

    def pick_and_place(self, pick_place_cmd: PickPlaceCommand) -> bool:
        """
         FUNÇÃO ATUALIZADA: Pick and place com validação completa em cada etapa
        """
        if not self._check_connection():
            return False
            
        try:
            self.status = RobotStatus.MOVING
            self.logger.info(f"     Origem: {pick_place_cmd.origin}")
            self.logger.info(f"     Destino: {pick_place_cmd.destination}")
            
            #  USAR FUNÇÃO ATUALIZADA DO URCONTROLLER
            success = self.controller.executar_movimento_peca(
                pick_place_cmd.origin.to_list(),
                pick_place_cmd.destination.to_list(),
                pick_place_cmd.safe_height,
                pick_place_cmd.pick_height
            )
            
            if success:
                self.status = RobotStatus.IDLE
                self.logger.info(" Pick and place concluído")
                return True
            else:
                self.status = RobotStatus.ERROR
                self.last_error = "Falha no pick and place"
                self.logger.error(" Falha no pick and place")
                return False
                
        except Exception as e:
            self.status = RobotStatus.ERROR
            self.last_error = str(e)
            self.logger.error(f" Erro durante pick and place: {e}")
            return False


    # ===================  NOVAS FUNÇÕES DE SEQUÊNCIA ===================

    def execute_sequence_advanced(self, commands: List[MovementCommand], 
                                 stop_on_failure: bool = True,
                                 validation_summary: bool = True) -> Dict[str, Any]:
        """
         NOVA FUNÇÃO: Execução avançada de sequência com relatório detalhado
        """
        if not self._check_connection():
            return {"success": False, "error": "Robô não conectado"}
        
        
        sequence_result = {
            "success": False,
            "total_commands": len(commands),
            "executed_commands": 0,
            "failed_commands": 0,
            "validations_performed": 0,
            "corrections_applied": 0,
            "intermediate_movements": 0,
            "execution_time": 0,
            "command_results": [],
            "error_summary": []
        }
        
        start_time = time.time()
        
        for i, cmd in enumerate(commands):
            command_start = time.time()
            command_result = {
                "index": i,
                "type": cmd.type.value,
                "success": False,
                "execution_time": 0,
                "validation_level": cmd.validation_level.value if hasattr(cmd, 'validation_level') else "standard",
                "movement_strategy": cmd.movement_strategy.value if hasattr(cmd, 'movement_strategy') else "direct"
            }
            
            try:
                if cmd.type == MovementType.LINEAR:
                    if cmd.target_pose:
                        # Validar antes de executar se solicitado      
                        success = self.move_to_pose(
                            cmd.target_pose, 
                            cmd.speed, 
                            cmd.acceleration,
                            cmd.movement_strategy,
                            cmd.validation_level
                        )
                        command_result["success"] = success
                        
                elif cmd.type == MovementType.HOME:
                    success = self.move_home()
                    command_result["success"] = success
                    
                elif cmd.type == MovementType.PICK_PLACE:
                    if cmd.parameters:
                        pick_place_cmd = PickPlaceCommand(
                            origin=RobotPose.from_list(cmd.parameters["origin"]),
                            destination=RobotPose.from_list(cmd.parameters["destination"]),
                            safe_height=cmd.parameters.get("safe_height", self.config["safe_height"]),
                            pick_height=cmd.parameters.get("pick_height", self.config["pick_height"]),
                            validation_level=cmd.validation_level
                        )
                        success = self.pick_and_place(pick_place_cmd)
                        command_result["success"] = success
                
                command_result["execution_time"] = time.time() - command_start
                
                if command_result["success"]:
                    sequence_result["executed_commands"] += 1
                else:
                    sequence_result["failed_commands"] += 1
                    if stop_on_failure:
                        self.logger.error(f" Falha no comando {i+1} - sequência interrompida")
                        sequence_result["error_summary"].append(f"Comando {i+1}: Execução falhou")
                        break
                
            except Exception as e:
                command_result["error"] = str(e)
                sequence_result["failed_commands"] += 1
                sequence_result["error_summary"].append(f"Comando {i+1}: {str(e)}")
                
                if stop_on_failure:
                    break
            
            sequence_result["command_results"].append(command_result)
            
            # Pausa entre comandos
            time.sleep(self.config["pause_between_moves"])
        
        sequence_result["execution_time"] = time.time() - start_time
        sequence_result["success"] = sequence_result["failed_commands"] == 0
        
        # Estatísticas do histórico atual
        sequence_result["corrections_applied"] = self.validation_stats["corrections_applied"]
        sequence_result["intermediate_movements"] = self.validation_stats["movements_with_intermediate_points"]
        
        self.logger.info(f" Sequência concluída")
        
        return sequence_result

    def execute_sequence(self, commands: List[MovementCommand]) -> bool:
        """Executa sequência de comandos (interface compatível)"""
        result = self.execute_sequence_advanced(commands, stop_on_failure=True, validation_summary=False)
        return result["success"]
    
    def debug_movement_sequence(self, poses_list, test_only=False):
        """
        🔥 NOVA FUNÇÃO: Debugga uma sequência de movimentos
        """
        print(f"🐛 DEBUG: Testando sequência de {len(poses_list)} poses...")
        
        resultados = []
        for i, pose in enumerate(poses_list):
            print(f"\n--- POSE {i+1}/{len(poses_list)} ---")
            
            if test_only:
                resultado = self.test_pose_validation(pose)
            else:
                resultado = self.move_to_pose_safe(pose)
                
            resultados.append(resultado)
            
            if not resultado:
                print(f"❌ Sequência INTERROMPIDA na pose {i+1}")
                break
                
        aprovadas = sum(resultados)
        print(f"\n📊 RESULTADO DA SEQUÊNCIA:")
        print(f"   Poses aprovadas: {aprovadas}/{len(poses_list)}")
        print(f"   Taxa de sucesso: {(aprovadas/len(poses_list)*100):.1f}%")
        
        return resultados

    def move_with_intermediate_points(self, target_pose, speed=None, acceleration=None, num_points=3):
        """
        🔥 ESTRATÉGIA AVANÇADA: Movimento com pontos intermediários
        Para poses muito distantes, divide o movimento em etapas
        """
        if speed is None:
            speed = self.speed
        if acceleration is None:
            acceleration = self.acceleration
            
        print(f"🚀 Movimento com {num_points} pontos intermediários")
        
        current_pose = self.get_current_pose()
        if not current_pose:
            print("❌ Não foi possível obter pose atual")
            return False
            
        # Gerar pontos intermediários
        intermediate_poses = []
        for i in range(1, num_points + 1):
            factor = i / (num_points + 1)
            
            intermediate_pose = [
                current_pose[j] + (target_pose[j] - current_pose[j]) * factor
                for j in range(6)
            ]
            intermediate_poses.append(intermediate_pose)
            
        # Adicionar pose final
        intermediate_poses.append(target_pose)
        
        print(f"📍 Planejamento de {len(intermediate_poses)} pontos:")
        for i, pose in enumerate(intermediate_poses):
            print(f"   Ponto {i+1}: {[f'{p:.3f}' for p in pose]}")
            
        # Executar sequência
        for i, pose in enumerate(intermediate_poses):
            print(f"\n🎯 Executando ponto {i+1}/{len(intermediate_poses)}")
            
            sucesso, pose_final = self.move_to_pose_with_smart_correction(pose, speed, acceleration)
            
            if not sucesso:
                print(f"❌ Falha no ponto {i+1} - movimento interrompido")
                return False
                
        print("✅ Movimento com pontos intermediários concluído!")
        return True
    
    def executar_movimento_peca(self, origem, destino, altura_segura, altura_pegar):
        """
        🔥 MOVIMENTO DE PEÇA ATUALIZADO com validação em cada etapa
        """
        print(f"🤖 Executando movimento de peça com VALIDAÇÃO COMPLETA:")
        print(f"   📍 Origem: {[f'{p:.3f}' for p in origem]}")
        print(f"   📍 Destino: {[f'{p:.3f}' for p in destino]}")
        print(f"   ⬆️ Altura segura: {altura_segura:.3f}")
        print(f"   ⬇️ Altura pegar: {altura_pegar:.3f}")
        
        try:
            # 1. Mover para posição segura acima da origem
            pose_segura_origem = origem.copy()
            pose_segura_origem[2] = altura_segura
            
            print("🔍 Etapa 1: Validando posição segura origem...")
            if not self.move_to_pose_safe(pose_segura_origem):
                print("❌ Falha ao mover para posição segura origem")
                return False
                
            # 2. Descer para pegar a peça
            pose_pegar = origem.copy()
            pose_pegar[2] = altura_pegar
            
            print("🔍 Etapa 2: Validando descida para pegar...")
            if not self.move_to_pose_safe(pose_pegar, speed=self.config.velocidade_precisa):
                print("❌ Falha ao descer para pegar peça")
                return False
                
            # 3. Subir com a peça
            print("🔍 Etapa 3: Validando subida com peça...")
            if not self.move_to_pose_safe(pose_segura_origem):
                print("❌ Falha ao subir com peça")
                return False
                
            # 4. Mover para posição segura acima do destino
            pose_segura_destino = destino.copy()
            pose_segura_destino[2] = altura_segura
            
            print("🔍 Etapa 4: Validando posição segura destino...")
            if not self.move_to_pose_safe(pose_segura_destino):
                print("❌ Falha ao mover para posição segura destino")
                return False
                
            # 5. Descer para colocar a peça
            pose_colocar = destino.copy()
            pose_colocar[2] = altura_pegar
            
            print("🔍 Etapa 5: Validando descida para colocar...")
            if not self.move_to_pose_safe(pose_colocar, speed=self.config.velocidade_precisa):
                print("❌ Falha ao descer para colocar peça")
                return False
                
            # 6. Subir após colocar
            print("🔍 Etapa 6: Validando subida final...")
            if not self.move_to_pose_safe(pose_segura_destino):
                print("❌ Falha ao subir após colocar peça")
                return False
                
            print("✅ Movimento de peça concluído com SUCESSO TOTAL!")
            return True
            
        except Exception as e:
            print(f"❌ Erro durante movimento de peça: {e}")
            return False
    # ===================  NOVAS FUNÇÕES DE DEBUG E ANÁLISE ===================

    def debug_pose_sequence(self, poses: List[RobotPose], test_only: bool = True) -> Dict[str, Any]:
        """
         NOVA FUNÇÃO: Debug de sequência de poses
        """
        if not self._check_connection():
            return {"error": "Robô não conectado"}
            
        self.logger.info(f" DEBUG: Analisando sequência de {len(poses)} poses")
        
        # Usar função de debug do URController
        poses_list = [pose.to_list() for pose in poses]
        results = self.controller.debug_movement_sequence(poses_list, test_only=test_only)
        
        debug_summary = {
            "total_poses": len(poses),
            "valid_poses": sum(results),
            "invalid_poses": len(results) - sum(results),
            "success_rate": (sum(results) / len(results)) * 100 if results else 0,
            "pose_results": []
        }
        
        for i, (pose, result) in enumerate(zip(poses, results)):
            debug_summary["pose_results"].append({
                "index": i,
                "pose": asdict(pose),
                "valid": result
            })
        
        return debug_summary

    def get_movement_statistics(self) -> Dict[str, Any]:
        """
         NOVA FUNÇÃO: Estatísticas de movimento e validação
        """
        total_movements = len(self.movement_history)
        successful_movements = sum(1 for m in self.movement_history if m.get("success", False))
        
        stats = {
            "total_movements": total_movements,
            "successful_movements": successful_movements,
            "failed_movements": total_movements - successful_movements,
            "success_rate": (successful_movements / total_movements * 100) if total_movements > 0 else 0,
            "validation_stats": self.validation_stats.copy(),
            "strategy_usage": {},
            "average_execution_time": 0
        }
        
        if self.movement_history:
            # Análise de estratégias usadas
            for movement in self.movement_history:
                strategy = movement.get("strategy", "unknown")
                stats["strategy_usage"][strategy] = stats["strategy_usage"].get(strategy, 0) + 1
            
            # Tempo médio de execução
            total_time = sum(m.get("duration", 0) for m in self.movement_history)
            stats["average_execution_time"] = total_time / len(self.movement_history)
        
        return stats

    def get_current_pose(self) -> Optional[RobotPose]:
        """Obtém pose atual do robô"""
        if not self._check_connection():
            return None
            
        try:
            pose_list = self.controller.get_current_pose()
            if pose_list:
                return RobotPose.from_list(pose_list)
            return None
        except Exception as e:
            self.logger.error(f" Erro ao obter pose atual: {e}")
            return None

    def fix_calibration_pose(self, position_index, target_pose):
        """
        🎯 CORREÇÃO ESPECÍFICA: Para usar na calibração
        Retorna a melhor pose corrigida para uma posição específica
        """
        print(f"🎯 Corrigindo pose para posição {position_index}")
        
        # 1. Diagnóstico
        diagnostics = self.diagnostic_pose_rejection(target_pose)
        
        # 2. Se pose é válida, retornar original
        if self.rtde_c.isPoseWithinSafetyLimits(target_pose):
            print("✅ Pose original já é válida")
            return target_pose, True
            
        # 3. Tentar correção automática
        corrected = self.correct_pose_automatically(target_pose)
        if self.rtde_c.isPoseWithinSafetyLimits(corrected):
            print("✅ Correção automática funcionou")
            return corrected, True
            
        # 4. Estratégias específicas para calibração
        calibration_strategies = [
            ("Elevação +3cm", lambda p: self._elevate_pose(p, 0.03)),
            ("Elevação +5cm", lambda p: self._elevate_pose(p, 0.05)),
            ("Elevação +8cm", lambda p: self._elevate_pose(p, 0.08)),
            ("Posição mais central", self._move_to_center),
        ]
        
        for strategy_name, strategy_func in calibration_strategies:
            try:
                test_pose = strategy_func(target_pose)
                if self.rtde_c.isPoseWithinSafetyLimits(test_pose):
                    print(f"✅ {strategy_name} funcionou")
                    return test_pose, True
            except Exception as e:
                continue
                
        print("❌ Nenhuma estratégia funcionou para esta pose")
        return target_pose, False

    def get_status(self) -> Dict[str, Any]:
        """
         FUNÇÃO ATUALIZADA: Status completo com novas informações
        """
        status_dict = {
            "status": self.status.value,
            "connected": self.status not in [RobotStatus.DISCONNECTED, RobotStatus.ERROR],
            "last_error": self.last_error,
            "current_pose": None,
            "robot_details": None,
            "movement_statistics": self.get_movement_statistics(),  #  NOVO
            "safety_configuration": {  #  NOVO
                "validation_level": self.config.get("default_validation_level", "advanced"),
                "movement_strategy": self.config.get("default_movement_strategy", "smart_correction"),
                "auto_correction_enabled": self.config.get("enable_auto_correction", True),
                "ultra_safe_mode": self.config.get("ultra_safe_mode", False),
                "max_correction_attempts": self.config.get("max_correction_attempts", 3)
            }
        }
        
        if self.controller and self.controller.is_connected():
            try:
                current_pose = self.get_current_pose()
                if current_pose:
                    status_dict["current_pose"] = {
                        "x": current_pose.x,
                        "y": current_pose.y,
                        "z": current_pose.z,
                        "rx": current_pose.rx,
                        "ry": current_pose.ry,
                        "rz": current_pose.rz
                    }
                
                robot_status = self.controller.get_robot_status()
                status_dict["robot_details"] = robot_status
                
            except Exception as e:
                self.logger.error(f" Erro ao obter status detalhado: {e}")
        
        return status_dict
    
    def validate_pose(self, pose):
        """
        Valida pose usando PoseValidationService (via URController).

        Args:
            pose: RobotPose ou lista [x, y, z, rx, ry, rz]

        Returns:
            bool: True se pose é válida
        """
        if not self._check_connection():
            return False

        # Converter RobotPose para lista se necessário
        pose_list = pose.to_list() if hasattr(pose, 'to_list') else pose

        # Usar validação completa do URController (que usa PoseValidationService)
        return self.controller.validate_pose_complete(pose_list)

    # ===================  NOVAS FUNÇÕES DE CONTROLE DE SEGURANÇA ===================

    def enable_ultra_safe_mode(self, enable: bool = True):
        """
         NOVA FUNÇÃO: Liga/desliga modo ultra-seguro
        """
        self.config["ultra_safe_mode"] = enable
        if self.controller:
            self.controller.enable_safety_mode(enable)
        
        mode_status = "HABILITADO" if enable else "DESABILITADO"
        self.logger.info(f" Modo ultra-seguro {mode_status}")

    def set_validation_level(self, level: ValidationLevel):
        """
         NOVA FUNÇÃO: Define nível de validação padrão
        """
        self.config["default_validation_level"] = level.value

    def set_movement_strategy(self, strategy: MovementStrategy):
        """
         NOVA FUNÇÃO: Define estratégia de movimento padrão
        """
        self.config["default_movement_strategy"] = strategy.value

    def move_to_pose_safe(self, pose, speed=None, acceleration=None, strategy="auto"):
        """
        Movimento seguro com estratégias configuráveis
        strategy: "simple", "smart_correction", "intermediate_points", "auto"
        """
        if speed is None:
            speed = self.speed
        if acceleration is None:
            acceleration = self.acceleration
            
        if strategy == "simple":
            return self._move_simple(pose, speed, acceleration)
        elif strategy == "smart_correction":
            return self._move_with_correction(pose, speed, acceleration)
        elif strategy == "intermediate_points":
            return self._move_with_intermediate_points(pose, speed, acceleration)
        else:  # auto
            # Tenta simple primeiro, depois smart_correction se falhar
            if self.validate_pose_complete(pose):
                return self._move_simple(pose, speed, acceleration)
            else:
                return self._move_with_correction(pose, speed, acceleration)
            
    def benchmark_correction_system(self):
        """
        📊 BENCHMARK: Testa o sistema de correção com várias poses
        """
        print("📊 BENCHMARK - Sistema de Correção")
        print("=" * 50)
        
        # Poses de teste variadas
        test_poses = [
            # Poses normais
            [0.3, 0.0, 0.3, 0.0, 3.14, 0.0],
            [0.4, 0.1, 0.2, 0.0, 3.14, 0.0], 
            
            # Poses problemáticas (muito baixas)
            [0.4, 0.2, 0.13, 0.0, 3.14, 0.0],
            [0.5, 0.3, 0.10, 0.0, 3.14, 0.0],
            
            # Poses extremas
            [0.7, 0.3, 0.15, 0.5, 3.14, 0.5],
            [0.2, -0.3, 0.12, -0.5, 2.5, -0.3],
            
            # Poses impossíveis
            [1.0, 0.8, 0.05, 1.0, 4.0, 2.0],
        ]
        
        results = {
            'total': len(test_poses),
            'original_valid': 0,
            'corrected_valid': 0,
            'impossible': 0,
            'details': []
        }
        
        for i, pose in enumerate(test_poses):
            print(f"\n📊 Teste {i+1}/{len(test_poses)}: {[f'{p:.3f}' for p in pose]}")
            
            # Teste original
            original_valid = self.rtde_c.isPoseWithinSafetyLimits(pose)
            if original_valid:
                results['original_valid'] += 1
                
            # Teste com correção
            corrected = self.correct_pose_automatically(pose)
            corrected_valid = self.rtde_c.isPoseWithinSafetyLimits(corrected)
            
            if corrected_valid:
                results['corrected_valid'] += 1
                status = "✅ CORRIGIDA"
            elif original_valid:
                status = "⚠️ PIOROU"
            else:
                results['impossible'] += 1
                status = "❌ IMPOSSÍVEL"
                
            results['details'].append({
                'pose': pose,
                'original_valid': original_valid,
                'corrected_valid': corrected_valid,
                'status': status
            })
            
            print(f"   Original: {'✅' if original_valid else '❌'} | Corrigida: {'✅' if corrected_valid else '❌'} | {status}")
        
        # Relatório final
        print(f"\n📊 RELATÓRIO FINAL DO BENCHMARK:")
        print(f"   Total de poses testadas: {results['total']}")
        print(f"   Originalmente válidas: {results['original_valid']} ({results['original_valid']/results['total']*100:.1f}%)")
        print(f"   Válidas após correção: {results['corrected_valid']} ({results['corrected_valid']/results['total']*100:.1f}%)")
        print(f"   Impossíveis: {results['impossible']} ({results['impossible']/results['total']*100:.1f}%)")
        print(f"   Taxa de melhoria: {((results['corrected_valid'] - results['original_valid'])/results['total']*100):.1f}%")
        
        return results

    # =================== FUNÇÕES DE CONTROLE EXISTENTES ATUALIZADAS ===================

    def emergency_stop(self) -> bool:
        """Parada de emergência"""
        try:
            if self.controller:
                success = self.controller.emergency_stop()
                if success:
                    self.status = RobotStatus.EMERGENCY_STOP
                    self.logger.warning(" PARADA DE EMERGÊNCIA ATIVADA")
                    return True
            return False
        except Exception as e:
            self.logger.error(f" Erro na parada de emergência: {e}")
            return False

    def stop_movement(self) -> bool:
        """Para movimento atual"""
        try:
            if self.controller:
                success = self.controller.stop()
                if success:
                    self.status = RobotStatus.IDLE
                    self.logger.info(" Movimento parado")
                    return True
            return False
        except Exception as e:
            self.logger.error(f" Erro ao parar movimento: {e}")
            return False

    def get_predefined_pose(self, pose_name: str) -> Optional[RobotPose]:
        """Obtém pose predefinida por nome"""
        if pose_name == "home":
            return RobotPose.from_list(self.config["home_pose"])
        elif pose_name in self.poses:
            return RobotPose.from_list(self.poses)
        else:
            self.logger.error(f" Pose '{pose_name}' não encontrada")
            return None

    def update_config(self, new_config: Dict[str, Any]):
        """
         FUNÇÃO ATUALIZADA: Atualiza configuração com validação
        """
        old_config = self.config.copy()
        self.config.update(new_config)
        
        # Validar configurações críticas
        if "default_validation_level" in new_config:
            try:
                ValidationLevel(new_config["default_validation_level"])
            except ValueError:
                self.logger.error(f" Nível de validação inválido: {new_config['default_validation_level']}")
                self.config["default_validation_level"] = old_config["default_validation_level"]
        
        if "default_movement_strategy" in new_config:
            try:
                MovementStrategy(new_config["default_movement_strategy"])
            except ValueError:
                self.logger.error(f" Estratégia de movimento inválida: {new_config['default_movement_strategy']}")
                self.config["default_movement_strategy"] = old_config["default_movement_strategy"]
        
        
        # Atualizar parâmetros do controlador se conectado
        if self.controller:
            if "speed" in new_config or "acceleration" in new_config:
                self.controller.set_speed_parameters(
                    self.config["speed"],
                    self.config["acceleration"]
                )
            
            if "enable_auto_correction" in new_config:
                self.controller.enable_safety_mode(new_config["enable_auto_correction"])

    def _check_connection(self) -> bool:
        """Verifica se está conectado ao robô"""
        if not self.controller or not self.controller.is_connected():
            self.status = RobotStatus.DISCONNECTED
            self.last_error = "Robô não conectado"
            self.logger.error(" Robô não está conectado")
            return False
        return True

    # ===================  NOVAS FUNÇÕES DE RELATÓRIO ===================

    def generate_safety_report(self) -> Dict[str, Any]:
        """
         NOVA FUNÇÃO: Gera relatório de segurança detalhado
        """
        stats = self.get_movement_statistics()
        
        report = {
            "timestamp": time.time(),
            "robot_status": self.status.value,
            "safety_configuration": {
                "validation_level": self.config.get("default_validation_level"),
                "movement_strategy": self.config.get("default_movement_strategy"),
                "auto_correction_enabled": self.config.get("enable_auto_correction"),
                "ultra_safe_mode": self.config.get("ultra_safe_mode")
            },
            "performance_metrics": {
                "total_movements": stats["total_movements"],
                "success_rate": stats["success_rate"],
                "correction_rate": (stats["validation_stats"]["corrections_applied"] / 
                                  max(stats["total_movements"], 1)) * 100,
                "intermediate_movement_rate": (stats["validation_stats"]["movements_with_intermediate_points"] / 
                                             max(stats["total_movements"], 1)) * 100,
                "average_execution_time": stats["average_execution_time"]
            },
            "validation_statistics": stats["validation_stats"],
            "strategy_distribution": stats["strategy_usage"],
            "recommendations": []
        }
        
        # Gerar recomendações baseadas nos dados
        if report["performance_metrics"]["success_rate"] < 90:
            report["recommendations"].append("Considere usar ValidationLevel.COMPLETE para maior segurança")
        
        if report["performance_metrics"]["correction_rate"] > 20:
            report["recommendations"].append("Alta taxa de correções - verifique configuração do workspace")
        
        if report["performance_metrics"]["average_execution_time"] > 10:
            report["recommendations"].append("Tempo de execução alto - considere otimizar trajetórias")
        
        return report

    def export_movement_history(self, filename: str = None) -> str:
        """
         NOVA FUNÇÃO: Exporta histórico de movimentos para JSON
        """
        if filename is None:
            filename = f"movement_history_{int(time.time())}.json"
        
        export_data = {
            "export_timestamp": time.time(),
            "robot_ip": self.robot_ip,
            "config": self.config,
            "movement_history": self.movement_history,
            "validation_stats": self.validation_stats,
            "safety_report": self.generate_safety_report()
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            return filename
        except Exception as e:
            self.logger.error(f" Erro ao exportar histórico: {e}")
            return ""

    def reset_statistics(self):
        """
         NOVA FUNÇÃO: Reseta estatísticas de movimento
        """
        self.movement_history.clear()
        self.validation_stats = {
            "total_validations": 0,
            "successful_validations": 0,
            "corrections_applied": 0,
            "movements_with_intermediate_points": 0
        }

    def set_logging_mode(self, verbose: bool = False, summary_only: bool = True):
        """
         NOVA: Controla modo de logging
        """
        self.verbose_logging = verbose
        self.log_summary_only = summary_only
        
        # Configurar também no URController
        if self.controller:
            # Desabilitar prints excessivos do URController se possível
            pass
        
        mode = "VERBOSE" if verbose else "RESUMO" if summary_only else "NORMAL"
    

    def _generate_safe_fallback_pose(self, problematic_pose: RobotPose) -> RobotPose:
        """
         FUNÇÃO AUXILIAR: Gera pose segura como fallback
        """
        safe_z = 0.3
        
        # Criar pose segura mantendo X,Y mas elevando Z
        safe_pose = RobotPose(
            x=max(-0.5, min(0.5, problematic_pose.x)),  # Limitar X
            y=max(-0.3, min(0.3, problematic_pose.y)),  # Limitar Y  
            z=max(safe_z, 0.3),  # Z seguro
            rx=0.0,  # Orientação conservadora
            ry=3.14,  # TCP para baixo
            rz=0.0
        )
        
        return safe_pose

    def benchmark_correction_system(self) -> Dict[str, Any]:
        """
        📊 NOVA FUNÇÃO: Benchmark do sistema de correção
        Testa o sistema com poses conhecidas
        """
        if not self._check_connection():
            return {"error": "Robô não conectado"}
        
        
        # Usar função do URController
        benchmark_results = self.controller.benchmark_correction_system()
        
        # Adicionar análise do RobotService
        service_analysis = {
            "controller_results": benchmark_results,
            "service_config": {
                "validation_level": self.config.get("default_validation_level"),
                "correction_enabled": self.config.get("enable_auto_correction"),
            },
            "performance_rating": "unknown",
            "recommendations": []
        }
        
        # Calcular rating de performance
        if benchmark_results.get("total", 0) > 0:
            correction_rate = (benchmark_results.get("corrected_valid", 0) - 
                            benchmark_results.get("original_valid", 0)) / benchmark_results.get("total", 1) * 100
            
            if correction_rate > 50:
                service_analysis["performance_rating"] = " EXCELENTE"
            elif correction_rate > 20:
                service_analysis["performance_rating"] = " BOM"
            elif correction_rate > 0:
                service_analysis["performance_rating"] = " REGULAR"
            else:
                service_analysis["performance_rating"] = " RUIM"
            
            # Recomendações baseadas no desempenho
            if correction_rate < 10:
                service_analysis["recommendations"].append("Sistema de correção pouco efetivo - verificar configurações")
            
            impossible_rate = benchmark_results.get("impossible", 0) / benchmark_results.get("total", 1) * 100
            if impossible_rate > 30:
                service_analysis["recommendations"].append("Muitas poses impossíveis - revisar workspace limits")
        
        self.logger.info(f" Benchmark concluído - Rating: {service_analysis['performance_rating']}")
        
        return service_analysis
    
    def debug_pose(self, pose):
        """Wrapper simples para debug"""
        if not self._check_connection():
            return {"error": "Robô não conectado"}
        return self.controller.diagnostic_pose_rejection(pose.to_list())

    # =================== CONTEXT MANAGER ===================

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()

# ===================  CLASSE DE UTILIDADE PARA CRIAÇÃO DE COMANDOS ===================

class MovementCommandBuilder:
    """
     NOVA CLASSE: Builder pattern para criar comandos de movimento facilmente
    """
    @staticmethod
    def create_linear_movement(pose: RobotPose, 
                             speed: float = None,
                             acceleration: float = None,
                             validation_level: ValidationLevel = ValidationLevel.ADVANCED,
                             movement_strategy: MovementStrategy = MovementStrategy.SMART_CORRECTION) -> MovementCommand:
        """Cria comando de movimento linear"""
        return MovementCommand(
            type=MovementType.LINEAR,
            target_pose=pose,
            speed=speed,
            acceleration=acceleration,
            validation_level=validation_level,
            movement_strategy=movement_strategy
        )
    
    @staticmethod
    def create_home_movement(validation_level: ValidationLevel = ValidationLevel.COMPLETE) -> MovementCommand:
        """Cria comando de movimento para home"""
        return MovementCommand(
            type=MovementType.HOME,
            validation_level=validation_level,
            movement_strategy=MovementStrategy.ULTRA_SAFE
        )
    
    @staticmethod
    def create_pick_place_movement(origin: RobotPose,
                                destination: RobotPose,
                                safe_height: float = CONFIG['robo'].altura_segura,
                                pick_height: float = CONFIG['robo'].altura_pegar) -> MovementCommand:
        """Cria comando de pick and place"""
        return MovementCommand(
            type=MovementType.PICK_PLACE,
            validation_level=ValidationLevel.COMPLETE,
            movement_strategy=MovementStrategy.ULTRA_SAFE,
            parameters={
                "origin": origin.to_list(),
                "destination": destination.to_list(),
                "safe_height": safe_height,
                "pick_height": pick_height
            }
        )
    
    @staticmethod
    def create_sequence_from_poses(poses: List[RobotPose],
                                 speed: float = None,
                                 validation_level: ValidationLevel = ValidationLevel.ADVANCED,
                                 movement_strategy: MovementStrategy = MovementStrategy.SMART_CORRECTION) -> List[MovementCommand]:
        """Cria sequência de comandos a partir de lista de poses"""
        return [
            MovementCommandBuilder.create_linear_movement(
                pose, speed, None, validation_level, movement_strategy
            ) for pose in poses
        ]