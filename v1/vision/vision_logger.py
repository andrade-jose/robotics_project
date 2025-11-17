#!/usr/bin/env python3
"""
VISION LOGGER - VERSÃO INTEGRADA
===============================
Sistema de logging específico para visão integrado ao robotics_project
Usa a pasta de logs configurada em CONFIG['sistema'].pasta_logs
"""

import logging
import os
from datetime import datetime
from typing import Optional

class VisionLogger:
    """
    Sistema de logging específico para visão integrado ao projeto
    
    FUNCIONALIDADES:
    - Usa pasta de logs do CONFIG['sistema']
    - Formatação consistente com o projeto
    - Níveis de log configuráveis
    - Rotação automática por data
    """
    
    def __init__(self, name: str, log_level: int = logging.INFO):
        """
        Inicializa o logger do sistema de visão
        
        Args:
            name: Nome do logger (normalmente __name__)
            log_level: Nível de log (logging.INFO, logging.DEBUG, etc.)
        """
        self.name = name
        self.logger = logging.getLogger(f"vision.{name}")
        self.log_level = log_level
        
        # Evitar duplicação de handlers
        if not self.logger.handlers:
            self._setup_logger()
    
    def _get_log_directory(self) -> str:
        """Obtém o diretório de logs das configurações do projeto"""
        try:
            from config.config_completa import CONFIG
            return CONFIG['sistema'].pasta_logs
        except (ImportError, KeyError, AttributeError):
            # Fallback caso não consiga acessar as configurações
            return 'logs'
    
    def _setup_logger(self):
        """Configura handlers e formatters do logger"""
        # Obter diretório de logs
        log_dir = self._get_log_directory()
        
        # Criar pasta de logs se não existir
        os.makedirs(log_dir, exist_ok=True)
        
        # Nome do arquivo com data atual
        today = datetime.now().strftime('%Y%m%d')
        log_file = os.path.join(log_dir, f"vision_{today}.log")
        
        # Handler para arquivo (todas as mensagens)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Handler para console (apenas INFO e acima)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.log_level)
        
        # Formatter detalhado para arquivo
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Formatter simplificado para console
        console_formatter = logging.Formatter(
            '%(asctime)s - VISION - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # Aplicar formatters
        file_handler.setFormatter(file_formatter)
        console_handler.setFormatter(console_formatter)
        
        # Adicionar handlers ao logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        self.logger.setLevel(logging.DEBUG)
        
        # Log inicial
        self.logger.info(f"VisionLogger inicializado para '{self.name}'")
    
    def debug(self, message: str):
        """Log de debug (desenvolvimento)"""
        self.logger.debug(f"[DEBUG] {message}")
    
    def info(self, message: str):
        """Log informativo (operação normal)"""
        self.logger.info(f"[INFO] {message}")
    
    def warning(self, message: str):
        """Log de aviso (situação atípica mas não crítica)"""
        self.logger.warning(f"[WARNING] {message}")
    
    def error(self, message: str):
        """Log de erro (falha operacional)"""
        self.logger.error(f"[ERROR] {message}")
    
    def critical(self, message: str):
        """Log crítico (falha grave do sistema)"""
        self.logger.critical(f"[CRITICAL] {message}")
    
    def detection(self, message: str):
        """Log específico para detecções (para análise posterior)"""
        self.logger.info(f"[DETECTION] {message}")
    
    def performance(self, message: str):
        """Log de performance (FPS, timing, etc.)"""
        self.logger.debug(f"[PERFORMANCE] {message}")
    
    def calibration(self, message: str):
        """Log de calibração do sistema"""
        self.logger.info(f"[CALIBRATION] {message}")
    
    def set_level(self, level: int):
        """
        Altera o nível de log do console (arquivo sempre mantém DEBUG)
        
        Args:
            level: Nível do logging (logging.DEBUG, INFO, WARNING, etc.)
        """
        for handler in self.logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                handler.setLevel(level)
        self.log_level = level
    
    def disable_console(self):
        """Desabilita output no console (mantém arquivo)"""
        for handler in self.logger.handlers[:]:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                self.logger.removeHandler(handler)
    
    def enable_console(self):
        """Reabilita output no console"""
        # Verificar se já tem console handler
        has_console = any(
            isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) 
            for h in self.logger.handlers
        )
        
        if not has_console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(self.log_level)
            console_formatter = logging.Formatter(
                '%(asctime)s - VISION - %(levelname)s - %(message)s',
                datefmt='%H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)

# Função de conveniência para criar logger com configurações padrão
def create_logger(name: str, console_level: int = logging.INFO) -> VisionLogger:
    """
    Cria um logger de visão com configurações padrão
    
    Args:
        name: Nome do logger
        console_level: Nível de log para console
        
    Returns:
        VisionLogger configurado
    """
    return VisionLogger(name, console_level)

# Logger padrão do módulo
logger = VisionLogger(__name__)

# Teste se executado diretamente
if __name__ == "__main__":
    print("[TEST] Teste do VisionLogger")

    # Criar logger de teste
    test_logger = VisionLogger("test")

    # Testar todos os níveis
    test_logger.debug("Mensagem de debug")
    test_logger.info("Sistema funcionando normalmente")
    test_logger.warning("Situação atípica detectada")
    test_logger.error("Erro na operação")
    test_logger.detection("Marcador ID=1 detectado em (100,200)")
    test_logger.performance("FPS: 30.5, Latência: 12ms")
    test_logger.calibration("Sistema calibrado com 2 marcadores de referência")

    print("[OK] Teste concluído - verifique os logs na pasta configurada")