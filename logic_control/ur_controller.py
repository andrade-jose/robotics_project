from rtde_control import RTDEControlInterface
from rtde_receive import RTDEReceiveInterface
from config.config_completa import ConfigRobo
from services.pose_validation_service import PoseValidationService
from diagnostics.ur_diagnostics import URDiagnostics
import time
import math
import logging

class URController:
    def __init__(self, config: ConfigRobo):
        self.config = config
        self.rtde_c = RTDEControlInterface(self.config.ip)
        self.rtde_r = RTDEReceiveInterface(self.config.ip)

        self.enable_safety_validation = True
        self.max_movement_distance = self.config.distancia_maxima_movimento
        self.workspace_limits = self.config.limites_workspace
        self.speed = self.config.velocidade_normal
        self.acceleration = self.config.aceleracao_normal
        self.pause_between_moves = self.config.pausa_entre_movimentos
        self.validation_retries = self.config.max_tentativas_correcao
        self.em_movimento = False

        # Sistema de validação centralizado
        self.logger = logging.getLogger('URController')
        self.pose_validator = PoseValidationService(
            workspace_limits=self.workspace_limits,
            max_movement_distance=self.max_movement_distance,
            logger=self.logger
        )
        self.pose_validator.set_ur_controller(self)

        # Sistema de diagnósticos
        self.diagnostics = URDiagnostics(config=self.config, logger=self.logger)

        print(f"✅ Conectado ao robô UR em {self.config.ip}")

    def is_connected(self):
        """Verifica se está conectado ao robô"""
        return (self.rtde_c and self.rtde_r and self.rtde_c.isConnected())

    def validate_pose_safety_limits(self, pose):
        """
        🔥 NOVA FUNÇÃO: Usa isPoseWithinSafetyLimits() da biblioteca ur_rtde
        Valida se a pose está dentro dos limites de segurança definidos no robô
        """
        if not self.enable_safety_validation:
            return True
            
        if not self.is_connected():
            print("❌ Robô não conectado para validação")
            return False
            
        try:
            # Usar a função oficial da biblioteca ur_rtde
            is_safe = self.rtde_c.isPoseWithinSafetyLimits(pose)
            
            if is_safe:
                print(f"✅ Pose APROVADA nos limites de segurança: {[f'{p:.3f}' for p in pose]}")
            else:
                print(f"❌ Pose REJEITADA pelos limites de segurança: {[f'{p:.3f}' for p in pose]}")
                
            return is_safe
            
        except Exception as e:
            print(f"❌ Erro na validação de limites de segurança: {e}")
            return False
        

    def diagnostic_pose_rejection(self, pose):
        """
        Diagnóstico avançado: identifica exatamente por que a pose foi rejeitada.
        DELEGA para URDiagnostics.
        """
        return self.diagnostics.diagnostic_pose_rejection(
            pose=pose,
            rtde_c=self.rtde_c,
            get_current_joints_func=self.get_current_joints
        )

    def validate_pose_reachability(self, pose):
        """
        ⚠️ DEPRECATED: Use pose_validator.validate_reachability() diretamente.

        Validação de alcançabilidade.
        Mantido para compatibilidade retroativa.
        """
        try:
            # Verificar se a pose tem formato correto
            if len(pose) != 6:
                print(f"❌ Formato de pose inválido: deve ter 6 elementos, recebeu {len(pose)}")
                return False
                
            # Obter pose atual para calcular distância
            current_pose = self.get_current_pose()
            if not current_pose:
                print("❌ Não foi possível obter pose atual")
                return False
                
            # Calcular distância euclidiana do movimento
            distance = math.sqrt(
                (pose[0] - current_pose[0])**2 +
                (pose[1] - current_pose[1])**2 +
                (pose[2] - current_pose[2])**2
            )
            
            # Verificar se a distância não é muito grande
            if distance > self.max_movement_distance:
                print(f"❌ Movimento muito grande: {distance:.3f}m > {self.max_movement_distance}m")
                return False
                
            # Verificar se as orientações não são extremas
            rotation_magnitude = math.sqrt(pose[3]**2 + pose[4]**2 + pose[5]**2)
            if rotation_magnitude > math.pi:
                print(f"❌ Magnitude de rotação extrema: {rotation_magnitude:.3f} > π")
                return False
                
            print(f"✅ Pose alcançável - Distância: {distance:.3f}m, Rotação: {rotation_magnitude:.3f}rad")
            return True
            
        except Exception as e:
            print(f"❌ Erro na validação de alcançabilidade: {e}")
            return False

    def validate_pose_complete(self, pose):
        """
        Executa validação completa usando PoseValidationService.

        Args:
            pose: Lista [x, y, z, rx, ry, rz]

        Returns:
            bool: True se pose é válida
        """
        if not self.enable_safety_validation:
            return True

        # Obter pose atual para validação de alcançabilidade
        current_pose = self.get_current_pose()

        # Executar validação completa
        result = self.pose_validator.validate_complete(pose, current_pose)

        # Retornar resultado simples
        return result.is_valid

    def validate_pose(self, pose):
        """
        ⚠️ DEPRECATED: Use pose_validator.validate_workspace() diretamente.

        Valida se a pose está dentro dos limites do workspace.
        Mantido para compatibilidade retroativa.

        Pose format: [x, y, z, rx, ry, rz] onde:
        - x, y, z em metros
        - rx, ry, rz em radianos (angle-axis representation)
        """
        if len(pose) != 6:
            print(f"❌ Pose inválida: deve ter 6 elementos, recebeu {len(pose)}")
            return False
            
        x, y, z, rx, ry, rz = pose
        
        # Validar posição cartesiana
        if not (self.workspace_limits['x_min'] <= x <= self.workspace_limits['x_max']):
            print(f"❌ X fora dos limites: {x} (min: {self.workspace_limits['x_min']}, max: {self.workspace_limits['x_max']})")
            return False
            
        if not (self.workspace_limits['y_min'] <= y <= self.workspace_limits['y_max']):
            print(f"❌ Y fora dos limites: {y} (min: {self.workspace_limits['y_min']}, max: {self.workspace_limits['y_max']})")
            return False
            
        if not (self.workspace_limits['z_min'] <= z <= self.workspace_limits['z_max']):
            print(f"❌ Z fora dos limites: {z} (min: {self.workspace_limits['z_min']}, max: {self.workspace_limits['z_max']})")
            return False
        
        # Validar orientação (angle-axis)
        rotation_magnitude = math.sqrt(rx**2 + ry**2 + rz**2)
        if rotation_magnitude > math.pi:
            print(f"❌ Magnitude de rotação muito grande: {rotation_magnitude} > π")
            return False
            
        print(f"✅ Pose válida no workspace: x={x:.3f}, y={y:.3f}, z={z:.3f}, rx={rx:.3f}, ry={ry:.3f}, rz={rz:.3f}")
        return True

    def get_current_pose(self):
        """Retorna a pose atual do TCP"""
        if self.is_connected():
            try:
                pose = self.rtde_r.getActualTCPPose()
                if pose:
                    print(f"📍 Pose atual: x={pose[0]:.3f}, y={pose[1]:.3f}, z={pose[2]:.3f}, "
                          f"rx={pose[3]:.3f}, ry={pose[4]:.3f}, rz={pose[5]:.3f}")
                return pose
            except Exception as e:
                print(f"❌ Erro ao obter pose atual: {e}")
                return None
        return None

    def getActualTCPPose(self):
        """Alias para compatibilidade"""
        return self.get_current_pose()

    def get_current_joints(self): 
        if self.is_connected():
            try:
                joints = self.rtde_r.getActualQ()
                if joints:
                    print(f"🔧 Juntas atuais: {[f'{j:.3f}' for j in joints]}")
                return joints
            except Exception as e:
                print(f"❌ Erro ao obter juntas: {e}")
                return None
        return None

    def is_pose_reachable(self, target_pose):
        """
        🔄 FUNÇÃO ATUALIZADA: Agora usa validate_pose_complete
        """
        return self.validate_pose_complete(target_pose)

    # SUBSTITUIR a função correct_pose_automatically no URController

    def correct_pose_automatically(self, pose):
        """
        Correção inteligente de poses usando diagnóstico avançado.

        RESPONSABILIDADE: Este método centraliza TODA a lógica de correção de poses.
        É usado por robot_service.fix_calibration_pose() e outros componentes.

        Estratégias de correção:
        1. Diagnóstico completo da pose (cinemática inversa, limites)
        2. Correção de articulações fora dos limites
        3. Ajuste de singularidades (pequenos ajustes de orientação)
        4. Correção básica de workspace (fallback)

        Args:
            pose: Lista [x, y, z, rx, ry, rz]

        Returns:
            pose_corrigida: Lista [x, y, z, rx, ry, rz] corrigida
        """
        print(f"🔧 Iniciando correção INTELIGENTE da pose: {[f'{p:.3f}' for p in pose]}")
        
        # 1. DIAGNÓSTICO COMPLETO
        diagnostics = self.diagnostic_pose_rejection(pose)
        
        if not diagnostics['pose_alcancavel']:
            print("❌ Pose impossível cinematicamente - tentando correções básicas")
            return self._correct_basic_workspace(pose)  # Fallback para método antigo
        
        corrected_pose = pose.copy()
        corrections_applied = []
        
        
        # 3. CORREÇÃO: Articulações problemáticas
        if diagnostics['joints_problematicas']:
            print("🔧 Corrigindo articulações fora dos limites...")
            
            joints = diagnostics['joints_calculadas'].copy()
            
            for joint_idx, name, valor, min_lim, max_lim in diagnostics['joints_problematicas']:
                # Corrigir articulação para dentro dos limites
                if valor < min_lim:
                    joints[joint_idx] = min_lim + 0.05  # Margem de segurança
                    corrections_applied.append(f"{name}: {valor:.3f} → {joints[joint_idx]:.3f} (limite mín)")
                elif valor > max_lim:
                    joints[joint_idx] = max_lim - 0.05  # Margem de segurança  
                    corrections_applied.append(f"{name}: {valor:.3f} → {joints[joint_idx]:.3f} (limite máx)")
            
            # Recalcular pose a partir das articulações corrigidas
            try:
                new_pose = self.rtde_c.getForwardKinematics(joints)
                if new_pose:
                    corrected_pose = new_pose
                    corrections_applied.append("Pose recalculada a partir de articulações corrigidas")
            except Exception as e:
                print(f"⚠️ Erro na cinemática direta: {e}")
        
        # 4. CORREÇÃO: Singularidades
        if diagnostics['singularidades']:
            print("🔧 Corrigindo singularidades...")
            
            # Ajustar orientação ligeiramente para sair da singularidade
            orientation_adjustments = [
                [0.05, 0, 0], [0, 0.05, 0], [0, 0, 0.05],
                [-0.05, 0, 0], [0, -0.05, 0], [0, 0, -0.05]
            ]
            
            for adjustment in orientation_adjustments:
                test_pose = corrected_pose.copy()
                test_pose[3] += adjustment[0]
                test_pose[4] += adjustment[1]  
                test_pose[5] += adjustment[2]
                
                # Testar se a nova orientação resolve o problema
                test_joints = self.rtde_c.getInverseKinematics(test_pose)
                if test_joints and self.rtde_c.isPoseWithinSafetyLimits(test_pose):
                    corrected_pose = test_pose
                    corrections_applied.append(f"Orientação ajustada: {adjustment}")
                    break
        
        # 5. CORREÇÃO FINAL: Workspace básico (mantida da versão original)
        corrected_pose = self._correct_basic_workspace(corrected_pose)
        
        # 6. RELATÓRIO DE CORREÇÕES
        if corrections_applied:
            print("🔧 Correções aplicadas:")
            for correction in corrections_applied:
                print(f"   • {correction}")
            print(f"🔧 Pose final corrigida: {[f'{p:.3f}' for p in corrected_pose]}")
        else:
            print("🔧 Nenhuma correção necessária")
            
        return corrected_pose

    def _correct_basic_workspace(self, pose):
        """Método auxiliar: correções básicas de workspace (código original)"""
        corrected_pose = pose.copy()
        corrections_applied = []
        
        x, y, z, rx, ry, rz = corrected_pose
        
        # Corrigir coordenadas para limites
        if x < self.workspace_limits['x_min']:
            corrected_pose[0] = self.workspace_limits['x_min'] + 0.01
            corrections_applied.append(f"X: {x:.3f} → {corrected_pose[0]:.3f}")
        elif x > self.workspace_limits['x_max']:
            corrected_pose[0] = self.workspace_limits['x_max'] - 0.01
            corrections_applied.append(f"X: {x:.3f} → {corrected_pose[0]:.3f}")
            
        if y < self.workspace_limits['y_min']:
            corrected_pose[1] = self.workspace_limits['y_min'] + 0.01
            corrections_applied.append(f"Y: {y:.3f} → {corrected_pose[1]:.3f}")
        elif y > self.workspace_limits['y_max']:
            corrected_pose[1] = self.workspace_limits['y_max'] - 0.01
            corrections_applied.append(f"Y: {y:.3f} → {corrected_pose[1]:.3f}")
            
        if z < self.workspace_limits['z_min']:
            corrected_pose[2] = self.workspace_limits['z_min'] + 0.01
            corrections_applied.append(f"Z: {z:.3f} → {corrected_pose[2]:.3f}")
        elif z > self.workspace_limits['z_max']:
            corrected_pose[2] = self.workspace_limits['z_max'] - 0.01
            corrections_applied.append(f"Z: {z:.3f} → {corrected_pose[2]:.3f}")

        # Correção de orientação
        rotation_magnitude = math.sqrt(rx**2 + ry**2 + rz**2)
        if rotation_magnitude > math.pi:
            factor = math.pi / rotation_magnitude * 0.95
            corrected_pose[3] = rx * factor
            corrected_pose[4] = ry * factor
            corrected_pose[5] = rz * factor
            corrections_applied.append(f"Rotação normalizada")
            
        return corrected_pose


    def _apply_drastic_corrections(self, pose, original_pose):
        """NOVO: Correções drásticas para poses impossíveis"""
        print("🚨 Aplicando correções DRÁSTICAS...")
        
        corrected = pose.copy()
        
        # 1. Mover para posição mais próxima do centro do workspace
        center_workspace = [0.4, 0.0, 0.3, 0.0, 3.14, 0.0]
        
        # Interpolar 50% em direção ao centro
        for i in range(3):  # Apenas posição, não orientação
            corrected[i] = pose[i] * 0.5 + center_workspace[i] * 0.5
            
        # 2. Garantir altura mínima segura
        min_safe_z = self.config.altura_base_ferro + self.config.margem_seguranca_base_ferro + 0.1
        if corrected[2] < min_safe_z:
            corrected[2] = min_safe_z
            
        print(f"🚨 Pose drasticamente corrigida: {[f'{p:.3f}' for p in corrected]}")
        return corrected

    def _apply_alternative_corrections(self, pose, attempt_number):
        """NOVO: Estratégias alternativas baseadas no número da tentativa"""
        print(f"🔧 Estratégia alternativa #{attempt_number + 1}")
        
        corrected = pose.copy()
        
        if attempt_number == 0:
            # Tentativa 1: Elevar significativamente
            corrected[2] += 0.05
            print(f"🔧 Elevando Z em 5cm: {corrected[2]:.3f}")
            
        elif attempt_number == 1:
            # Tentativa 2: Mover para posição mais central
            corrected[0] = 0.4  # X central
            corrected[1] = 0.0  # Y central
            corrected[2] = max(corrected[2], 0.3)  # Z seguro
            print(f"🔧 Movendo para posição central segura")
            
        elif attempt_number == 2:
            # Tentativa 3: Orientação mais conservadora
            corrected[3] = 0.0   # rx = 0
            corrected[4] = 3.14  # ry = π (TCP para baixo)
            corrected[5] = 0.0   # rz = 0
            print(f"🔧 Orientação conservadora aplicada")
            
        else:
            # Tentativa final: Pose home modificada
            home_pose = self.config.pose_home.copy()
            home_pose[0] = pose[0]  # Manter X desejado
            home_pose[1] = pose[1]  # Manter Y desejado
            corrected = home_pose
            print(f"🔧 Usando pose home modificada")
            
        return corrected

    def _poses_are_equal(self, pose1, pose2, tolerance=0.001):
        """AUXILIAR: Verifica se duas poses são iguais dentro da tolerância"""
        for i in range(6):
            if abs(pose1[i] - pose2[i]) > tolerance:
                return False
        return True

    def move_with_intermediate_points(self, target_pose, speed=None, acceleration=None, num_points=3):
        """
        Movimento com pontos intermediários (waypoints) para trajetos longos.

        RESPONSABILIDADE: Este método centraliza a lógica de movimento com waypoints.
        É usado por robot_service.move_with_intermediate_points() e outros componentes.

        Estratégia:
        1. Calcula pontos intermediários entre pose atual e pose alvo
        2. Executa movimento sequencial por cada ponto
        3. Usa interpolação linear para gerar waypoints
        4. Aplica correção inteligente em cada ponto

        Args:
            target_pose: Lista [x, y, z, rx, ry, rz]
            speed: Velocidade do movimento (opcional, usa padrão se None)
            acceleration: Aceleração do movimento (opcional, usa padrão se None)
            num_points: Número de pontos intermediários (padrão: 3)

        Returns:
            bool: True se movimento foi concluído com sucesso
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


    def enable_safety_mode(self, enable=True):
        """
        🔥 NOVA FUNÇÃO: Liga/desliga validações de segurança
        """
        self.enable_safety_validation = enable
        status = "HABILITADA" if enable else "DESABILITADA"
        print(f"🛡️ Validação de segurança {status}")

    def emergency_stop(self):
        """Parada de emergência"""
        try:
            if self.rtde_c:
                self.rtde_c.stopScript()
                self.em_movimento = False
                print("🚨 PARADA DE EMERGÊNCIA ATIVADA!")
                return True
        except Exception as e:
            print(f"❌ Erro na parada de emergência: {e}")
            return False

    def stop(self):
        """Para movimentos atuais"""
        try:
            if self.rtde_c and self.em_movimento:
                # ✅ ALTERAR para valor fixo ou adicionar campo na config:
                self.rtde_c.stopL(2.0)  # Desaceleração fixa
                self.em_movimento = False
                print("🛑 Robô parado com sucesso")
                return True
            return True
        except Exception as e:
            print(f"❌ Erro ao parar robô: {e}")
            return False

    def set_speed_parameters(self, speed, acceleration):
        """Ajusta parâmetros de velocidade"""
        self.speed = max(self.config.velocidade_minima, min(speed, self.config.velocidade_maxima))
        self.acceleration = max(self.config.aceleracao_minima, min(acceleration, self.config.aceleracao_maxima))

        print(f"⚙️ Parâmetros atualizados - Velocidade: {self.speed:.3f}, Aceleração: {self.acceleration:.3f}")
    
    def get_robot_status(self):
        """Obtém status detalhado do robô"""
        if not self.is_connected():
            return {"connected": False}
            
        try:
            status = {
                "connected": True,
                "pose": self.get_current_pose(),
                "joints": self.get_current_joints(),
                "em_movimento": self.em_movimento,
                "robot_mode": self.rtde_r.getRobotMode(),
                "safety_mode": self.rtde_r.getSafetyMode(),
                "safety_validation_enabled": self.enable_safety_validation
            }
            return status
        except Exception as e:
            print(f"❌ Erro ao obter status: {e}")
            return {"connected": False, "error": str(e)}

    def disconnect(self):
        """Desconecta do robô"""
        try:
            if self.rtde_c:
                self.rtde_c.stopScript()
                print("🔌 Desconectado do robô")
            self.em_movimento = False
        except Exception as e:
            print(f"❌ Erro ao desconectar: {e}")

    # ====================== FUNÇÕES DE DEBUG ======================
    
    def debug_movement_sequence(self, poses_list, test_only=False):
        """
        Debug de uma sequência de movimentos.
        DELEGA para URDiagnostics.
        """
        test_func = self.test_pose_validation if test_only else self.move_to_pose_safe
        return self.diagnostics.debug_movement_sequence(poses_list, test_func, test_only)

    def _elevate_pose(self, pose, elevation):
        """AUXILIAR: Eleva a pose em Z. DELEGA para URDiagnostics."""
        return self.diagnostics.elevate_pose(pose, elevation)

    def _move_to_center(self, pose):
        """AUXILIAR: Move pose para posição mais central. DELEGA para URDiagnostics."""
        return self.diagnostics.move_to_center(pose)

    def benchmark_correction_system(self):
        """
        Benchmark do sistema de correção com várias poses.
        DELEGA para URDiagnostics.
        """
        return self.diagnostics.benchmark_correction_system(
            rtde_c=self.rtde_c,
            correct_pose_func=self.correct_pose_automatically
        )

    # FUNÇÃO PARA USAR NO SEU CASO ESPECÍFICO
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