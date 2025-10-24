"""
RobotDiagnostics - Sistema de Diagnóstico e Estatísticas do Robô
==================================================================
Responsável por toda análise, monitoramento e relatórios do sistema robótico:
- Estatísticas de movimentos
- Benchmarks e testes de performance
- Relatórios de segurança
- Exportação de histórico
- Análise e recomendações
"""

import json
import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


class RobotDiagnostics:
    """
    Gerencia diagnósticos, estatísticas e relatórios do sistema robótico.

    Responsabilidades:
    - Coletar e analisar estatísticas de movimentos
    - Gerar relatórios de segurança
    - Realizar benchmarks do sistema
    - Exportar histórico de movimentos
    - Fornecer recomendações baseadas em dados
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Inicializa o sistema de diagnósticos.

        Args:
            logger: Logger opcional
        """
        self.logger = logger or logging.getLogger('RobotDiagnostics')

        # Histórico e estatísticas
        self.movement_history: List[Dict[str, Any]] = []
        self.validation_stats: Dict[str, int] = {
            "total_validations": 0,
            "successful_validations": 0,
            "corrections_applied": 0,
            "movements_with_intermediate_points": 0
        }

        # Configuração de logging
        self.verbose_logging = False
        self.log_summary_only = True

    # ========== REGISTRO DE EVENTOS ==========

    def register_movement(self, movement_data: Dict[str, Any]):
        """
        Registra um movimento no histórico.

        Args:
            movement_data: Dicionário com dados do movimento
                - success: bool
                - strategy: str
                - duration: float
                - timestamp: float
                - etc.
        """
        self.movement_history.append(movement_data)
        if self.verbose_logging:
            self.logger.debug(f"Movimento registrado: {movement_data}")

    def register_validation(self, validation_data: Dict[str, Any]):
        """
        Registra uma validação no histórico.

        Args:
            validation_data: Dicionário com dados da validação
                - success: bool
                - corrected: bool
                - used_intermediate_points: bool
        """
        self.validation_stats["total_validations"] += 1

        if validation_data.get("success", False):
            self.validation_stats["successful_validations"] += 1

        if validation_data.get("corrected", False):
            self.validation_stats["corrections_applied"] += 1

        if validation_data.get("used_intermediate_points", False):
            self.validation_stats["movements_with_intermediate_points"] += 1

    # ========== ESTATÍSTICAS ==========

    def get_movement_statistics(self) -> Dict[str, Any]:
        """
        Retorna estatísticas detalhadas de movimentos.

        Returns:
            Dicionário com estatísticas completas
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

    def get_validation_statistics(self) -> Dict[str, Any]:
        """
        Retorna estatísticas específicas de validação.

        Returns:
            Dicionário com estatísticas de validação
        """
        return self.validation_stats.copy()

    # ========== RELATÓRIOS ==========

    def generate_safety_report(self, config: Dict[str, Any], robot_status: str) -> Dict[str, Any]:
        """
        Gera relatório de segurança detalhado.

        Args:
            config: Configuração atual do robô
            robot_status: Status atual do robô

        Returns:
            Dicionário com relatório completo de segurança
        """
        stats = self.get_movement_statistics()

        report = {
            "timestamp": time.time(),
            "robot_status": robot_status,
            "safety_configuration": {
                "validation_level": config.get("default_validation_level"),
                "movement_strategy": config.get("default_movement_strategy"),
                "auto_correction_enabled": config.get("enable_auto_correction"),
                "ultra_safe_mode": config.get("ultra_safe_mode")
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
        report["recommendations"] = self._generate_recommendations(report)

        return report

    def _generate_recommendations(self, report: Dict[str, Any]) -> List[str]:
        """
        Gera recomendações baseadas nos dados do relatório.

        Args:
            report: Relatório de segurança

        Returns:
            Lista de recomendações
        """
        recommendations = []

        # Análise de taxa de sucesso
        if report["performance_metrics"]["success_rate"] < 90:
            recommendations.append("⚠️ Considere usar ValidationLevel.COMPLETE para maior segurança")

        # Análise de correções
        if report["performance_metrics"]["correction_rate"] > 20:
            recommendations.append("⚠️ Alta taxa de correções - verifique configuração do workspace")

        # Análise de tempo de execução
        if report["performance_metrics"]["average_execution_time"] > 10:
            recommendations.append("⏱️ Tempo de execução alto - considere otimizar trajetórias")

        # Análise de movimentos com pontos intermediários
        if report["performance_metrics"]["intermediate_movement_rate"] > 50:
            recommendations.append("📊 Muitos movimentos com pontos intermediários - workspace pode estar muito restrito")

        # Análise de falhas
        if report["performance_metrics"]["success_rate"] < 80:
            recommendations.append("🚨 Taxa de sucesso crítica - revise configuração de segurança")

        if not recommendations:
            recommendations.append("✅ Sistema operando dentro dos parâmetros normais")

        return recommendations

    # ========== BENCHMARK ==========

    def analyze_benchmark_results(self, controller_results: Dict[str, Any],
                                  config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analisa resultados de benchmark do controller.

        Args:
            controller_results: Resultados do benchmark do URController
            config: Configuração atual

        Returns:
            Análise completa do benchmark
        """
        service_analysis = {
            "controller_results": controller_results,
            "service_config": {
                "validation_level": config.get("default_validation_level"),
                "correction_enabled": config.get("enable_auto_correction"),
            },
            "performance_rating": "unknown",
            "recommendations": []
        }

        # Calcular rating de performance
        if controller_results.get("total", 0) > 0:
            correction_rate = (controller_results.get("corrected_valid", 0) -
                            controller_results.get("original_valid", 0)) / controller_results.get("total", 1) * 100

            if correction_rate > 50:
                service_analysis["performance_rating"] = "⭐ EXCELENTE"
            elif correction_rate > 20:
                service_analysis["performance_rating"] = "✅ BOM"
            elif correction_rate > 0:
                service_analysis["performance_rating"] = "🟡 REGULAR"
            else:
                service_analysis["performance_rating"] = "❌ RUIM"

            # Recomendações baseadas no desempenho
            if correction_rate < 10:
                service_analysis["recommendations"].append(
                    "Sistema de correção pouco efetivo - revisar limites de workspace"
                )
            elif correction_rate > 80:
                service_analysis["recommendations"].append(
                    "Sistema de correção muito agressivo - considere relaxar validações"
                )

        return service_analysis

    # ========== EXPORTAÇÃO ==========

    def export_movement_history(self, robot_ip: str, config: Dict[str, Any],
                                filename: Optional[str] = None) -> str:
        """
        Exporta histórico de movimentos para arquivo JSON.

        Args:
            robot_ip: IP do robô
            config: Configuração atual
            filename: Nome do arquivo (opcional)

        Returns:
            Nome do arquivo criado ou string vazia se falhar
        """
        if filename is None:
            filename = f"movement_history_{int(time.time())}.json"

        export_data = {
            "export_timestamp": time.time(),
            "robot_ip": robot_ip,
            "config": config,
            "movement_history": self.movement_history,
            "validation_stats": self.validation_stats,
            "safety_report": self.generate_safety_report(config, "exported")
        }

        try:
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)

            self.logger.info(f"📊 Histórico exportado para {filename}")
            return filename

        except Exception as e:
            self.logger.error(f"❌ Erro ao exportar histórico: {e}")
            return ""

    # ========== GERENCIAMENTO ==========

    def reset_statistics(self):
        """Reseta todas as estatísticas."""
        self.movement_history.clear()
        self.validation_stats = {
            "total_validations": 0,
            "successful_validations": 0,
            "corrections_applied": 0,
            "movements_with_intermediate_points": 0
        }
        self.logger.info("📊 Estatísticas resetadas")

    def set_logging_mode(self, verbose: bool = False, summary_only: bool = True):
        """
        Configura modo de logging.

        Args:
            verbose: Se True, loga todos os detalhes
            summary_only: Se True, loga apenas resumos
        """
        self.verbose_logging = verbose
        self.log_summary_only = summary_only

        mode = "VERBOSE" if verbose else "RESUMO" if summary_only else "NORMAL"
        self.logger.info(f"📝 Modo de logging alterado para: {mode}")

    # ========== QUERIES ==========

    def get_recent_movements(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Retorna os movimentos mais recentes.

        Args:
            count: Número de movimentos a retornar

        Returns:
            Lista com movimentos recentes
        """
        return self.movement_history[-count:] if self.movement_history else []

    def get_failed_movements(self) -> List[Dict[str, Any]]:
        """
        Retorna todos os movimentos que falharam.

        Returns:
            Lista com movimentos falhos
        """
        return [m for m in self.movement_history if not m.get("success", False)]

    def get_summary(self) -> str:
        """
        Retorna resumo textual das estatísticas.

        Returns:
            String formatada com resumo
        """
        stats = self.get_movement_statistics()

        summary = f"""
╔══════════════════════════════════════════╗
║     RESUMO DE DIAGNÓSTICOS DO ROBÔ      ║
╠══════════════════════════════════════════╣
║ Total de Movimentos: {stats['total_movements']:>16} ║
║ Taxa de Sucesso:     {stats['success_rate']:>15.1f}% ║
║ Correções Aplicadas: {stats['validation_stats']['corrections_applied']:>16} ║
║ Validações Totais:   {stats['validation_stats']['total_validations']:>16} ║
╚══════════════════════════════════════════╝
        """
        return summary.strip()
