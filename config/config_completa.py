from dataclasses import dataclass, field
from typing import List, Tuple, Dict
import os
from enum import Enum
import math
import cv2

# Dicionário de limites das juntas
_UR3E_JOINT_LIMITS = {
    'base': (-2*math.pi, 2*math.pi),    # ±360°
    'shoulder': (-2*math.pi, 2*math.pi), # ±360°
    'elbow': (-math.pi, math.pi),       # ±180°
    'wrist1': (-2*math.pi, 2*math.pi),   # ±360°
    'wrist2': (-2*math.pi, 2*math.pi),   # ±360°
    'wrist3': (-2*math.pi, 2*math.pi)    # ±360°
}

@dataclass
class ConfigRobo:
    """Configurações completas e consolidadas para o robô UR3e."""

    # === CONEXÃO ===
    ip: str = "10.1.7.30"
    porta: int = 30004

    # === MODELO UR (Fixo em UR3e) ===
    limites_articulacoes: dict = field(default_factory=lambda: _UR3E_JOINT_LIMITS)

    # === MOVIMENTO BÁSICO ===
    # RECOMENDAÇÃO COMUNIDADE UR: Manter velocidades < 0.33 m/s para evitar C204A3
    velocidade_maxima: float = 0.15  # 15cm/s máximo (reduzido de 0.2)
    velocidade_normal: float = 0.08  # 8cm/s normal (reduzido de 0.1)
    velocidade_padrao: float = 0.08  # 8cm/s padrão (reduzido de 0.1)
    velocidade_lenta: float = 0.05   # 5cm/s lenta (mantido)
    velocidade_precisa: float = 0.03 # 3cm/s precisa (mantido)
    velocidade_minima: float = 0.01
    aceleracao_normal: float = 0.08  # Reduzida de 0.1 (mais suave)
    aceleracao_padrao: float = 0.08  # Reduzida de 0.1 (mais suave)
    altura_segura: float = 0.3
    altura_pegar: float = 0.05
    pausa_entre_movimentos: float = 1.0
    pausa_entre_jogadas: float = 2.0
    aceleracao_minima: float = 0.01
    aceleracao_maxima: float = 0.4  # Reduzida de 0.5 para evitar desacelerações abruptas
    desaceleracao_parada: float = 2.0
    max_mudanca_junta: float = 1.57  # 90 graus em radianos
    enable_safety_validation: bool = True
    
    # === POSE HOME ===
    pose_home: List[float] = field(default_factory=lambda: [0.3, 0.0, 0.25, 0.0, 3.14, 0.0])

    # === WORKSPACE E LIMITES ===
    limites_workspace: dict = field(default_factory=lambda: {
        'x_min': -0.5, 'x_max': 0.5, 'y_min': -0.5, 'y_max': 0.5,
        'z_min': 0.05, 'z_max': 0.6, 'rx_min': -math.pi, 'rx_max': math.pi,
        'ry_min': -math.pi, 'ry_max': math.pi, 'rz_min': -math.pi, 'rz_max': math.pi
    })
    
    # === CONFIGURAÇÕES DE MOVIMENTO INTELIGENTE E SEGURANÇA ===
    auto_calibrar: bool = False
    habilitar_correcao_automatica: bool = True
    habilitar_correcao_inteligente: bool = True
    habilitar_pontos_intermediarios: bool = True
    usar_pontos_intermediarios: bool = True
    passo_pontos_intermediarios: float = 0.1
    distancia_threshold_pontos_intermediarios: float = 0.3
    distancia_maxima_movimento: float = 0.8
    max_tentativas_movimento: int = 3
    max_tentativas_correcao: int = 3
    tentativas_validacao: int = 3
    modo_ultra_seguro: bool = False
    fator_velocidade_ultra_seguro: float = 0.5
    
    # === TIMEOUTS ===
    timeout_movimento: float = 30.0
    timeout_conexao: float = 10.0
    
    # === ESTRATÉGIAS E VALIDAÇÃO ===
    nivel_validacao_padrao: str = "advanced"
    estrategia_movimento_padrao: str = "smart_correction"
    estrategias_correcao: List[str] = field(default_factory=lambda: [
        "diagnostico_completo", "correcao_articulacoes",
        "correcao_singularidades", "correcao_workspace", "pontos_intermediarios",
        "movimento_ultra_lento"
    ])
    
    # === CONFIGURAÇÕES ESPECÍFICAS TAPATAN ===
    tapatan_config: dict = field(default_factory=lambda: {
        "altura_tabuleiro": 0.05, "altura_peca": 0.02,
        "espacamento_posicoes": 0.1, "validacao_pre_movimento": True,
        "estrategia_movimento_tapatan": "smart_correction",
        "usar_pontos_intermediarios_tapatan": True,
        "tabuleiro_offset_x": 0.30,  # 30cm à frente do robô
        "tabuleiro_offset_y": 0.00   # Centralizado em Y
    })
    
    # === LOGGING ===
    logging_verbose: bool = False

    def __post_init__(self):
        """Inicialização com valores calculados e validações."""
        self._ajustar_configuracoes_ambiente()
        self._validar_configuracoes_criticas()

    def _ajustar_configuracoes_ambiente(self):
        """Ajusta parâmetros para o UR3e e para o ambiente (simulação vs. real)."""
        if self.is_simulation_mode():
            print("[CONFIG] Detectado ambiente de SIMULACAO.")
        else:
            print("[CONFIG] Detectado ROBO REAL - aplicando configuracoes de seguranca.")

        print("[CONFIG] Aplicando configuracoes especificas para UR3e.")
        self.distancia_maxima_movimento = 0.6
        self.velocidade_normal = 0.05
        self.passo_pontos_intermediarios = 0.08

    def _validar_configuracoes_criticas(self):
        """Valida e ajusta limites para garantir a segurança do UR3e."""
        if self.limites_workspace['z_min'] < 0.01:
            print(f"[CONFIG] AVISO: z_min muito baixo, ajustando para 0.01m.")
            self.limites_workspace['z_min'] = 0.01

        max_reach_ur3e = 0.5
        for axis in ['x', 'y']:
            if abs(self.limites_workspace[f'{axis}_max']) > max_reach_ur3e:
                print(f"[CONFIG] AVISO: {axis}_max fora do alcance do UR3e, ajustando para +/-{max_reach_ur3e}m.")
                self.limites_workspace[f'{axis}_min'] = -max_reach_ur3e
                self.limites_workspace[f'{axis}_max'] = max_reach_ur3e
    
    # === MÉTODOS DE UTILIDADE ===
    def get_joint_limits_list(self) -> List[Tuple[float, float]]:
        """Retorna limites das articulações como lista de tuplas."""
        return list(self.limites_articulacoes.values())
    
    def get_safe_tcp_height(self) -> float:
        """Retorna altura mínima segura para TCP, com uma pequena margem."""
        return self.limites_workspace['z_min'] + 0.02
    
    def is_simulation_mode(self) -> bool:
        """Verifica se está em modo simulação pelo IP."""
        ip_lower = self.ip.lower()
        return "127.0.0.1" in ip_lower or "sim" in ip_lower or "localhost" in ip_lower

@dataclass
class ConfigVisao:
    """Configurações do sistema de visão ArUco."""
    marker_size_meters: float = 0.03
    aruco_dict_type: int = cv2.aruco.DICT_4X4_50
    camera_index: int = 1
    frame_width: int = 640
    frame_height: int = 480
    calibration_file: str = 'data/camera_calibration.npz'
    use_camera_calibration: bool = True
    enable_debug_view: bool = False
    
    reference_ids: List[int] = field(default_factory=lambda: [0, 1])
    group1_ids: List[int] = field(default_factory=lambda: [2, 4, 6])
    group2_ids: List[int] = field(default_factory=lambda: [3, 5, 7])
    
    def get_all_marker_ids(self) -> List[int]:
        """Retorna lista com todos os IDs de marcadores configurados."""
        return self.reference_ids + self.group1_ids + self.group2_ids

@dataclass 
class ConfigJogo:
    profundidade_ia: int = 3
    debug_mode: bool = False

@dataclass
class ConfigSistema:
    arquivo_calibracao: str = 'data/stereo_dataset/calib.pkl'
    pasta_logs: str = 'logs'
    pasta_dados: str = 'data'
    usar_camera_real: bool = False
    
    def __post_init__(self):
        """Garante que as pastas de logs e dados existam."""
        os.makedirs(self.pasta_logs, exist_ok=True)
        os.makedirs(self.pasta_dados, exist_ok=True)

class Jogador(Enum):
    VAZIO = 0
    JOGADOR1 = 1  # Robô/IA
    JOGADOR2 = 2  # Humano

class FaseJogo(Enum):
    COLOCACAO = "colocacao"
    MOVIMENTO = "movimento"
    JOGO_TERMINADO = "jogo_terminado"

# Instância global única para fácil acesso em todo o projeto.
CONFIG = {
    'robo': ConfigRobo(),
    'jogo': ConfigJogo(),
    'sistema': ConfigSistema(),
    'visao': ConfigVisao()
}
