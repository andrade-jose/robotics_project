"""
URDiagnostics - Sistema de Diagnóstico para Controlador UR
===========================================================
Responsável por diagnósticos e debugging do controlador UR:
- Diagnóstico de rejeição de poses
- Debug de sequências de movimento
- Benchmark do sistema de correção
"""

import math
import logging
from typing import List, Dict, Any, Optional, Tuple


class URDiagnostics:
    """
    Gerencia diagnósticos e debugging do controlador UR.

    Responsabilidades:
    - Diagnosticar por que poses são rejeitadas
    - Debugar sequências de movimento
    - Executar benchmarks do sistema de correção
    - Gerar relatórios detalhados
    """

    def __init__(self, config, logger: Optional[logging.Logger] = None):
        """
        Inicializa o sistema de diagnósticos.

        Args:
            config: Configuração do robô (ConfigRobo)
            logger: Logger opcional
        """
        self.config = config
        self.logger = logger or logging.getLogger('URDiagnostics')

    # ========== DIAGNÓSTICO DE POSES ==========

    def diagnostic_pose_rejection(self, pose: List[float], rtde_c, get_current_joints_func) -> Dict[str, Any]:
        """
        Diagnóstico avançado: identifica exatamente por que a pose foi rejeitada.

        Args:
            pose: Pose a diagnosticar [x, y, z, rx, ry, rz]
            rtde_c: Interface RTDE do controlador
            get_current_joints_func: Função para obter articulações atuais

        Returns:
            Dicionário com diagnóstico completo
        """
        print(f"🔍 DIAGNÓSTICO COMPLETO da pose: {[f'{p:.3f}' for p in pose]}")

        diagnostics = {
            'pose_original': pose,
            'pose_alcancavel': False,
            'joints_calculadas': None,
            'joints_problematicas': [],
            'singularidades': False,
            'conflitos_base_ferro': False,
            'sugestoes_correcao': []
        }

        try:
            # 1. TESTE: Cinemática Inversa
            print("1️⃣ Testando cinemática inversa...")
            joints = rtde_c.getInverseKinematics(pose)

            if joints is None or len(joints) == 0:
                print("❌ PROBLEMA: Cinemática inversa impossível")
                diagnostics['sugestoes_correcao'].append("Ajustar posição ou orientação")
                return diagnostics

            diagnostics['joints_calculadas'] = joints
            diagnostics['pose_alcancavel'] = True
            print(f"✅ Articulações calculadas: {[f'{j:.3f}' for j in joints]}")

            # 2. TESTE: Limites individuais das articulações
            print("2️⃣ Verificando limites das articulações...")
            current_joints = get_current_joints_func()

            joint_limits = list(self.config.limites_articulacoes.values())
            joint_names = ['Base', 'Shoulder', 'Elbow', 'Wrist1', 'Wrist2', 'Wrist3']

            # Verificar limites das articulações
            for i, (joint_val, (min_lim, max_lim), name) in enumerate(zip(joints, joint_limits, joint_names)):
                if joint_val < min_lim or joint_val > max_lim:
                    print(f"❌ {name}: {joint_val:.3f} fora do limite [{min_lim:.3f}, {max_lim:.3f}]")
                    diagnostics['joints_problematicas'].append((i, name, joint_val, min_lim, max_lim))
                else:
                    print(f"✅ {name}: {joint_val:.3f} OK")

            # 3. TESTE: Singularidades cinemáticas
            print("3️⃣ Verificando singularidades...")

            # Detectar singularidade de punho (wrist singularity)
            wrist_config = math.sqrt(joints[4]**2 + joints[5]**2)
            if wrist_config < 0.1:  # Muito próximo de singularidade
                print("⚠️ AVISO: Próximo à singularidade de punho")
                diagnostics['singularidades'] = True
                diagnostics['sugestoes_correcao'].append("Ajustar orientação do TCP")

            # Detectar singularidade de cotovelo (elbow singularity)
            if abs(joints[1]) < 0.1 and abs(joints[2]) < 0.1:
                print("⚠️ AVISO: Próximo à singularidade de cotovelo")
                diagnostics['singularidades'] = True

            # 4. TESTE: Mudanças extremas de articulação
            print("4️⃣ Verificando mudanças extremas...")
            if current_joints:
                max_change = self.config.distancia_maxima_movimento / 6  # Aproximação

                for i, (current, target, name) in enumerate(zip(current_joints, joints, joint_names)):
                    mudanca = abs(target - current)
                    if mudanca > max_change:
                        print(f"⚠️ {name}: Mudança grande {mudanca:.3f} > {max_change:.3f}")
                        diagnostics['sugestoes_correcao'].append(f"Movimento intermediário para {name}")

            # 5. GERAR RELATÓRIO FINAL
            print("\n📊 RELATÓRIO DE DIAGNÓSTICO:")
            print(f"   Cinemática possível: {'✅' if diagnostics['pose_alcancavel'] else '❌'}")
            print(f"   Articulações problemáticas: {len(diagnostics['joints_problematicas'])}")
            print(f"   Conflito base ferro: {'❌' if diagnostics['conflitos_base_ferro'] else '✅'}")
            print(f"   Singularidades detectadas: {'⚠️' if diagnostics['singularidades'] else '✅'}")

            if diagnostics['sugestoes_correcao']:
                print("🔧 SUGESTÕES DE CORREÇÃO:")
                for i, sugestao in enumerate(diagnostics['sugestoes_correcao'], 1):
                    print(f"   {i}. {sugestao}")

            return diagnostics

        except Exception as e:
            print(f"❌ Erro durante diagnóstico: {e}")
            diagnostics['sugestoes_correcao'].append("Verificar conexão com robô")
            return diagnostics

    # ========== BENCHMARK DO SISTEMA ==========

    def benchmark_correction_system(self, rtde_c, correct_pose_func) -> Dict[str, Any]:
        """
        Benchmark do sistema de correção com várias poses de teste.

        Args:
            rtde_c: Interface RTDE do controlador
            correct_pose_func: Função de correção automática de poses

        Returns:
            Dicionário com resultados do benchmark
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
            original_valid = rtde_c.isPoseWithinSafetyLimits(pose)
            if original_valid:
                results['original_valid'] += 1

            # Teste com correção
            corrected = correct_pose_func(pose)
            corrected_valid = rtde_c.isPoseWithinSafetyLimits(corrected)

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

    # ========== DEBUG DE SEQUÊNCIAS ==========

    def debug_movement_sequence(self, poses_list: List, test_func, test_only: bool = False) -> List[bool]:
        """
        Debug de uma sequência de movimentos.

        Args:
            poses_list: Lista de poses para testar
            test_func: Função para testar/mover cada pose
            test_only: Se True, apenas testa sem executar

        Returns:
            Lista de resultados (True/False para cada pose)
        """
        print(f"🐛 DEBUG: Testando sequência de {len(poses_list)} poses...")

        resultados = []
        for i, pose in enumerate(poses_list):
            print(f"\n--- POSE {i+1}/{len(poses_list)} ---")

            resultado = test_func(pose)
            resultados.append(resultado)

            if not resultado:
                print(f"❌ Sequência INTERROMPIDA na pose {i+1}")
                break

        aprovadas = sum(resultados)
        print(f"\n📊 RESULTADO DA SEQUÊNCIA:")
        print(f"   Poses aprovadas: {aprovadas}/{len(poses_list)}")
        print(f"   Taxa de sucesso: {(aprovadas/len(poses_list)*100):.1f}%")

        return resultados

    # ========== UTILIDADES ==========

    @staticmethod
    def elevate_pose(pose: List[float], elevation: float) -> List[float]:
        """
        Eleva a pose em Z.

        Args:
            pose: Pose original [x, y, z, rx, ry, rz]
            elevation: Elevação a adicionar

        Returns:
            Pose elevada
        """
        corrected = pose.copy()
        corrected[2] += elevation
        return corrected

    @staticmethod
    def move_to_center(pose: List[float]) -> List[float]:
        """
        Move pose para posição mais central do workspace.

        Args:
            pose: Pose original [x, y, z, rx, ry, rz]

        Returns:
            Pose centralizada
        """
        corrected = pose.copy()
        corrected[0] = 0.4  # X central
        corrected[1] = 0.0  # Y central
        corrected[2] = max(corrected[2], 0.3)  # Z mínimo seguro
        return corrected
