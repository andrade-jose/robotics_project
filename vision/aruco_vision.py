#!/usr/bin/env python3
"""
ARUCO VISION SYSTEM - VERSÃO INTEGRADA AO ROBOTICS_PROJECT
=========================================================
Sistema de visão ArUco com mapeamento automático de tabuleiro 3x3 baseado em
distância configurável entre marcadores de referência.

INTEGRAÇÃO COMPLETA:
- Usa CONFIG['visao'] do config_completa.py
- Sistema de coordenadas dinâmico e flexível
- Mapeamento automático das 9 posições do tabuleiro 3x3
- Funciona em qualquer superfície com distância configurável
- Validação de área de trabalho robusta
- Logs reduzidos conforme solicitado
- Compatibilidade com estrutura do robotics_project
- Documentação clara e detalhada
"""

import cv2
import numpy as np
import time
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass

# Imports do projeto robotics_project
from .vision_logger import VisionLogger
from config.config_completa import ConfigVisao

@dataclass
class MarkerInfo:
    """Informações de um marcador detectado"""
    id: int
    position: np.ndarray
    rotation: np.ndarray
    corners: np.ndarray
    timestamp: float
    confidence: float

@dataclass
class GridPosition:
    """Posição calculada no grid 3x3"""
    index: int  # 0-8 (posições do tabuleiro)
    x_mm: float
    y_mm: float
    z_mm: float
    is_valid: bool
    confidence: float

class ArUcoVisionSystem:
    """
    Sistema principal de visão ArUco integrado ao robotics_project
    
    FUNCIONALIDADES PRINCIPAIS:
    - Detecção de marcadores de referência (0, 1) para definir sistema de coordenadas
    - Cálculo automático de grid 3x3 baseado em distância configurável
    - Grupos coloridos (2,4,6 = jogador1 / 3,5,7 = jogador2) para peças do jogo
    - Sistema flexível que funciona em qualquer superfície
    - Integração com config_completa.py do projeto
    - Validação automática da área de trabalho
    - Logs reduzidos conforme requisito do projeto
    """

    def __init__(self, 
                 config : Optional[ConfigVisao] = None,reference_distance_mm: Optional[float] = None,
                 calibration_file: Optional[str] = None,
                 enable_reduced_logs: bool = True):
        """
        Inicializa o sistema de visão ArUco flexível
        
        Args:
            config: Configurações do sistema
            calibration_file: Arquivo de calibração da câmera
            reference_distance_mm: Distância entre marcadores de referência em mm
            enable_debug_logs: Habilitar logs detalhados (False para produção)
        """
        self.config = config or ConfigVisao()
        self.logger = VisionLogger(__name__)

        # Configurações do sistema flexível
        self.configured_reference_distance_mm = reference_distance_mm or 150.0  # Padrão: 15cm
        self.grid_size = 3  # Tabuleiro 3x3
        self.calculated_grid_positions: List[GridPosition] = []
        self.enable_reduced_logs = enable_reduced_logs
        # Alias para compatibilidade com código existente
        self.enable_debug_logs = not enable_reduced_logs
        
        # Configurar detector ArUco
        self._setup_aruco()

        # Carregar calibração da câmera
        if calibration_file and self._load_camera_calibration(calibration_file):
            pass
        else:
            self._setup_camera_params()
        
        # Inicializar variáveis de estado
        self._init_state_variables()
        
        if not self.enable_reduced_logs:
            self.logger.info(f"Sistema ArUco Vision flexível inicializado - Distância ref: {self.configured_reference_distance_mm}mm")
    
    def set_reference_distance(self, distance_mm: float) -> bool:
        """
        Define a distância entre os marcadores de referência
        
        Args:
            distance_mm: Distância em milímetros entre marcadores ID 0 e 1
            
        Returns:
            bool: True se a distância foi definida com sucesso
        """
        if distance_mm <= 0:
            if self.enable_debug_logs:
                self.logger.error(f"Distância inválida: {distance_mm}mm")
            return False
            
        self.configured_reference_distance_mm = distance_mm
        
        # Recalcular grid se sistema já estiver calibrado
        if self.is_calibrated:
            self._calculate_grid_3x3()
            
        if self.enable_debug_logs:
            self.logger.info(f"Distância de referência definida: {distance_mm}mm")
        return True
    
    def get_reference_distance(self) -> float:
        """Retorna a distância configurada entre marcadores de referência"""
        return self.configured_reference_distance_mm
    
    def get_grid_positions(self) -> List[GridPosition]:
        """Retorna as posições calculadas do grid 3x3"""
        return self.calculated_grid_positions.copy()
    
    def get_grid_position_by_index(self, index: int) -> Optional[GridPosition]:
        """
        Retorna posição específica do grid por índice
        
        Args:
            index: Índice da posição (0-8)
            
        Returns:
            GridPosition ou None se índice inválido
        """
        if 0 <= index < len(self.calculated_grid_positions):
            return self.calculated_grid_positions[index]
        return None
    
    def is_position_in_work_area(self, x_mm: float, y_mm: float) -> bool:
        """
        Verifica se uma posição está dentro da área de trabalho válida
        
        Args:
            x_mm, y_mm: Coordenadas em milímetros
            
        Returns:
            bool: True se posição está dentro da área válida
        """
        if not self.is_calibrated:
            return False
            
        # Definir margem de segurança baseada na distância de referência
        margin = self.configured_reference_distance_mm * 0.1  # 10% da distância
        max_distance = self.configured_reference_distance_mm + margin
        
        # Verificar se está dentro dos limites do grid expandido
        return (abs(x_mm) <= max_distance and abs(y_mm) <= max_distance)
    
    def _load_camera_calibration(self, filepath: str) -> bool:
        """Carrega os parâmetros de calibração da câmera de um arquivo .npz"""
        try:
            with np.load(filepath) as data:
                self.camera_matrix = data['camera_matrix']
                self.dist_coeffs = data['dist_coeffs']
            if self.enable_debug_logs:
                self.logger.info(f"Parâmetros de calibração carregados de '{filepath}'")
            return True
        except FileNotFoundError:
            if self.enable_debug_logs:
                self.logger.warning(f"Arquivo de calibração '{filepath}' não encontrado.")
            return False
        except Exception as e:
            if self.enable_debug_logs:
                self.logger.warning(f"Erro ao carregar calibração: {e}")
            return False
    
    def _setup_aruco(self):
        """Configura detector ArUco usando configurações do projeto"""
        try:
            # Usar dicionário configurado no projeto
            self.aruco_dict = cv2.aruco.getPredefinedDictionary(self.config.aruco_dict_type)

            # Parâmetros de detecção otimizados para estabilidade
            self.parameters = cv2.aruco.DetectorParameters()

            # Configurações para detecção mais estável (reduz valores estranhos)
            self.parameters.adaptiveThreshWinSizeMin = 3
            self.parameters.adaptiveThreshWinSizeMax = 23
            self.parameters.adaptiveThreshWinSizeStep = 10
            self.parameters.adaptiveThreshConstant = 7

            # Filtros de qualidade mais rigorosos
            self.parameters.minMarkerPerimeterRate = 0.03
            self.parameters.maxMarkerPerimeterRate = 4.0
            self.parameters.polygonalApproxAccuracyRate = 0.03
            self.parameters.minCornerDistanceRate = 0.05
            self.parameters.minDistanceToBorder = 3

            # Criar detector ArUco com novo API (OpenCV 4.7+)
            self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.parameters)

            # Usar tamanho do marcador da configuração
            self.marker_size_meters = self.config.marker_size_meters

            if self.enable_debug_logs:
                self.logger.debug(f"ArUco configurado - tamanho: {self.marker_size_meters}m, dict: {self.config.aruco_dict_type}")

        except Exception as e:
            self.logger.error(f"Erro ao configurar detector ArUco: {e}")
            self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
            self.parameters = cv2.aruco.DetectorParameters()
            self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.parameters)
            raise
    
    def _setup_camera_params(self):
        """Configura parâmetros intrínsecos da câmera usando resolução do projeto"""
        # Usar resolução configurada no projeto
        width = self.config.frame_width
        height = self.config.frame_height
        
        # Estimativa melhorada da distância focal baseada na resolução
        fx = fy = max(width, height) * 0.7  # Aproximação mais precisa
        cx, cy = width // 2, height // 2
        
        self.camera_matrix = np.array([
            [fx, 0, cx],
            [0, fy, cy],
            [0, 0, 1]
        ], dtype=np.float64)
        self.dist_coeffs = np.zeros((5, 1), dtype=np.float64)
        
        if self.enable_debug_logs:
            self.logger.warning(f"Usando parâmetros padrão de câmera ({width}x{height}). Para melhor precisão, calibre a câmera.")
    
    def _init_state_variables(self):
        """Inicializa variáveis de estado do sistema usando configurações do projeto"""
        # Usar grupos configurados no projeto
        self.reference_ids = self.config.reference_ids
        self.group1_ids = self.config.group1_ids  # Jogador 1 (robô)
        self.group2_ids = self.config.group2_ids  # Jogador 2 (humano)
        
        # Marcadores detectados
        self.reference_markers: Dict[int, MarkerInfo] = {}
        self.group1_markers: Dict[int, MarkerInfo] = {}
        self.group2_markers: Dict[int, MarkerInfo] = {}
        
        # Sistema de coordenadas
        self.is_calibrated = False
        self.origin_3d = None
        self.x_vector = None
        self.y_vector = None
        self.z_vector_ref = None
        self.reference_distance_mm = 0
        self.scale_factor = 1.0  # NOVO: Fator de escala para correção
        
        # Estatísticas (logs reduzidos conforme solicitado)
        self.detection_stats = {
            'total_detections': 0,
            'reference_detections': 0,
            'group1_detections': 0,
            'group2_detections': 0,
            'last_detection_time': 0,
            'calibration_attempts': 0,
            'stable_detections': 0  # NOVO: Para filtragem de ruído
        }
        
        # Sistema de filtragem para estabilizar valores
        self.position_history: Dict[int, List[np.ndarray]] = {}
        self.history_size = 5  # Histórico para média móvel
        self.marker_stability: Dict[int, int] = {}  # Contador de estabilidade
        
        # Cache de calibração para evitar recálculos desnecessários
        self.calibration_cache = {
            'last_distance': 0,
            'last_positions': {},
            'is_stable': False
        }
        
        if self.enable_debug_logs:
            self.logger.debug(f"Sistema inicializado - Refs: {self.reference_ids}, G1: {self.group1_ids}, G2: {self.group2_ids}")

    def _estimate_marker_poses(self, corners, marker_size_meters):
        """
        Estima poses dos marcadores usando solvePnP (compatível com OpenCV 4.7+).
        Substitui o método deprecated estimatePoseSingleMarkers.

        Args:
            corners: Lista de corners dos marcadores
            marker_size_meters: Tamanho do marcador em metros

        Returns:
            rvecs: Lista de vetores de rotação
            tvecs: Lista de vetores de translação
        """
        rvecs = []
        tvecs = []

        # Definir corners 3D do marcador quadrado
        half_size = marker_size_meters / 2.0
        objPoints = np.array([
            [-half_size, half_size, 0],
            [half_size, half_size, 0],
            [half_size, -half_size, 0],
            [-half_size, -half_size, 0]
        ], dtype=np.float32)

        for corner_set in corners:
            # corner_set tem shape (1, 4, 2)
            imgPoints = corner_set[0].astype(np.float32)

            try:
                # Usar solvePnP para estimar pose
                success, rvec, tvec = cv2.solvePnP(
                    objPoints, imgPoints,
                    self.camera_matrix, self.dist_coeffs,
                    useExtrinsicGuess=False,
                    flags=cv2.SOLVEPNP_ITERATIVE
                )

                if success:
                    rvecs.append(rvec)
                    tvecs.append(tvec)
                else:
                    # Fallback para valores padrão se solvePnP falhar
                    rvecs.append(np.zeros((3, 1), dtype=np.float32))
                    tvecs.append(np.zeros((3, 1), dtype=np.float32))

            except Exception as e:
                if self.enable_debug_logs:
                    self.logger.debug(f"Erro ao estimar pose do marcador: {e}")
                # Adicionar valores padrão
                rvecs.append(np.zeros((3, 1), dtype=np.float32))
                tvecs.append(np.zeros((3, 1), dtype=np.float32))

        return rvecs, tvecs

    def detect_markers(self, frame: np.ndarray) -> dict:
        """
        Detecta todos os marcadores no frame

        Args:
            frame: Frame de vídeo da câmera

        Returns:
            dict: Dicionário com detecções {reference_markers, group1_markers, group2_markers, ...}
        """
        # Limpar detecções anteriores
        self.reference_markers.clear()
        self.group1_markers.clear()
        self.group2_markers.clear()

        # Detectar marcadores ArUco usando novo API (OpenCV 4.7+)
        corners, ids, rejected = self.detector.detectMarkers(frame)

        detections = {
            'reference_markers': {},
            'group1_markers': {},
            'group2_markers': {},
            'detection_count': 0,
            'timestamp': time.time(),
            'frame_shape': frame.shape if frame is not None else None
        }

        if ids is not None and len(ids) > 0:
            # Estimar poses de todos os marcadores usando novo método compatível
            rvecs, tvecs = self._estimate_marker_poses(corners, self.marker_size_meters)

            # Desenhar marcadores detectados no frame
            cv2.aruco.drawDetectedMarkers(frame, corners, ids)

            # Processar cada marcador detectado
            for i, marker_id in enumerate(ids):
                marker_id = marker_id[0]
                self._process_marker(marker_id, corners[i], rvecs[i], tvecs[i])

            # Calibrar sistema se ambos marcadores de referência detectados
            if len(self.reference_markers) == 2:
                success = self._calibrate_coordinate_system()
                if success and not self.calculated_grid_positions:
                    self._calculate_grid_3x3()

            # Atualizar estatísticas
            self._update_detection_stats()

            # Populer dicionário de retorno
            detections['reference_markers'] = self.reference_markers
            detections['group1_markers'] = self.group1_markers
            detections['group2_markers'] = self.group2_markers
            detections['detection_count'] = len(ids)

        return detections
    
    def _process_marker(self, marker_id: int, corners: np.ndarray, 
                       rvec: np.ndarray, tvec: np.ndarray):
        """Processa um marcador detectado e o classifica por grupo"""
        
        # Aplicar suavização na posição
        smoothed_position = self._apply_smoothing_filter(marker_id, tvec.flatten())
        
        # Criar info do marcador
        marker_info = MarkerInfo(
            id=marker_id,
            position=smoothed_position,
            rotation=rvec.flatten(),
            corners=corners,
            timestamp=time.time(),
            confidence=1.0  # Placeholder - poderia ser calculado baseado na detecção
        )
        
        # Classificar por grupo
        if marker_id in self.reference_ids:
            self.reference_markers[marker_id] = marker_info
        elif marker_id in self.group1_ids:
            self.group1_markers[marker_id] = marker_info
        elif marker_id in self.group2_ids:
            self.group2_markers[marker_id] = marker_info
    
    def _apply_smoothing_filter(self, marker_id: int, new_position: np.ndarray) -> np.ndarray:
        """Aplica filtro de média móvel para suavizar posições"""
        if marker_id not in self.position_history:
            self.position_history[marker_id] = []
        
        history = self.position_history[marker_id]
        history.append(new_position)
        
        # Manter apenas últimas N posições
        if len(history) > self.history_size:
            history.pop(0)
        
        # Retornar média das posições
        return np.mean(history, axis=0)
    
    def _calibrate_coordinate_system(self) -> bool:
        """
        Calibra sistema de coordenadas baseado nos marcadores de referência
        Usa a distância configurável ao invés de medir a distância real
        """
        if len(self.reference_markers) != 2:
            return False
        
        try:
            # Obter marcadores de referência
            marker_0 = self.reference_markers.get(0)
            marker_1 = self.reference_markers.get(1)
            
            if not marker_0 or not marker_1:
                return False
            
            # Definir origem no marcador 0
            self.origin_3d = marker_0.position
            
            # Calcular vetores do sistema de coordenadas
            x_vector_raw = marker_1.position - marker_0.position
            
            # IMPORTANTE: Usar distância configurada, não a medida real
            # Isso permite usar qualquer superfície com marcadores em qualquer distância
            measured_distance = np.linalg.norm(x_vector_raw)
            scale_factor = self.configured_reference_distance_mm / (measured_distance * 1000)
            
            # Aplicar fator de escala para normalizar para distância configurada
            self.x_vector = x_vector_raw / np.linalg.norm(x_vector_raw)
            
            # Y perpendicular ao X no plano horizontal
            self.y_vector = np.array([-self.x_vector[1], self.x_vector[0], 0])
            self.y_vector = self.y_vector / np.linalg.norm(self.y_vector)
            
            # Z perpendicular ao plano XY
            z_vector_ref = np.cross(self.x_vector, self.y_vector)
            self.z_vector_ref = z_vector_ref / np.linalg.norm(z_vector_ref)

            # Armazenar distância configurada (não medida)
            self.reference_distance_mm = self.configured_reference_distance_mm
            
            self.is_calibrated = True
            self.detection_stats['calibration_attempts'] += 1
            
            if self.enable_debug_logs:
                self.logger.info(f"Sistema calibrado - Distância configurada: {self.reference_distance_mm:.1f}mm")
            
            return True
            
        except Exception as e:
            if self.enable_debug_logs:
                self.logger.error(f"Erro na calibração: {e}")
            return False
    
    def _calculate_grid_3x3(self):
        """
        Calcula as 9 posições do grid 3x3 baseado no sistema de coordenadas calibrado
        
        Grid layout:
        0 1 2
        3 4 5  
        6 7 8
        """
        if not self.is_calibrated:
            if self.enable_debug_logs:
                self.logger.warning("Sistema não calibrado - não é possível calcular grid")
            return
        
        self.calculated_grid_positions.clear()
        
        # Configurar grid baseado na distância de referência
        grid_spacing = self.configured_reference_distance_mm / 2.0  # Espaçamento entre posições
        
        # Calcular posições do grid 3x3
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                index = row * self.grid_size + col
                
                # Coordenadas relativas ao centro do grid (posição 4)
                x_offset = (col - 1) * grid_spacing  # -1, 0, +1 * spacing
                y_offset = (row - 1) * grid_spacing  # -1, 0, +1 * spacing
                
                # Converter para coordenadas do sistema de referência
                x_mm = x_offset
                y_mm = y_offset
                z_mm = 0.0  # Grid no plano de referência
                
                # Validar se posição está na área de trabalho
                is_valid = self.is_position_in_work_area(x_mm, y_mm)
                
                # Criar posição do grid
                grid_position = GridPosition(
                    index=index,
                    x_mm=x_mm,
                    y_mm=y_mm,
                    z_mm=z_mm,
                    is_valid=is_valid,
                    confidence=1.0 if is_valid else 0.5
                )
                
                self.calculated_grid_positions.append(grid_position)
        
        if self.enable_debug_logs:
            valid_positions = sum(1 for pos in self.calculated_grid_positions if pos.is_valid)
            self.logger.info(f"Grid 3x3 calculado - {valid_positions}/9 posições válidas")
    
    def _update_detection_stats(self):
        """Atualiza estatísticas de detecção (logs reduzidos)"""
        self.detection_stats['total_detections'] += 1
        self.detection_stats['reference_detections'] = len(self.reference_markers)
        self.detection_stats['group1_detections'] = len(self.group1_markers)
        self.detection_stats['group2_detections'] = len(self.group2_markers)
        self.detection_stats['last_detection_time'] = time.time()
        
        # Log apenas ocasionalmente para reduzir spam
        if self.enable_debug_logs and self.detection_stats['total_detections'] % 100 == 0:
            self.logger.debug(f"Estatísticas: {self.detection_stats['total_detections']} detecções totais")
    
    def convert_to_reference_coordinates(self, world_position: np.ndarray, 
                                       project_to_plane: bool = True) -> Optional[Tuple[float, float, float]]:
        """
        Converte posição do mundo para sistema de coordenadas de referência
        
        Args:
            world_position: Posição 3D no sistema de coordenadas da câmera
            project_to_plane: Se True, projeta no plano (z=0)
            
        Returns:
            Tuple[x_mm, y_mm, z_mm] ou None se sistema não calibrado
        """
        if not self.is_calibrated:
            return None
        
        # Calcular posição relativa à origem
        relative_pos = world_position - self.origin_3d
        
        # Aplicar fator de escala baseado na distância configurada
        measured_distance = np.linalg.norm(self.reference_markers[1].position - self.reference_markers[0].position)
        scale_factor = self.configured_reference_distance_mm / (measured_distance * 1000)
        
        # Projetar nos eixos do sistema de referência
        x_mm = np.dot(relative_pos, self.x_vector) * 1000 * scale_factor
        y_mm = np.dot(relative_pos, self.y_vector) * 1000 * scale_factor
        
        if project_to_plane:
            z_mm = 0.0
        else:
            z_mm = np.dot(relative_pos, self.z_vector_ref) * 1000 * scale_factor
            
        return (x_mm, y_mm, z_mm)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Retorna status atual do sistema"""
        return {
            'is_calibrated': self.is_calibrated,
            'reference_distance_mm': self.reference_distance_mm,
            'configured_distance_mm': self.configured_reference_distance_mm,
            'grid_positions_calculated': len(self.calculated_grid_positions),
            'valid_grid_positions': sum(1 for pos in self.calculated_grid_positions if pos.is_valid),
            'markers_detected': {
                'reference': len(self.reference_markers),
                'group1': len(self.group1_markers),
                'group2': len(self.group2_markers)
            },
            'reference_ids_detected': list(self.reference_markers.keys()),
            'group1_ids_detected': list(self.group1_markers.keys()),
            'group2_ids_detected': list(self.group2_markers.keys()),
            'detection_stats': self.detection_stats.copy()
        }
    
    def get_marker_coordinates(self, project_to_plane: bool = True) -> Dict[str, List[Dict]]:
        """
        Retorna coordenadas de todos os marcadores no sistema de referência
        
        Args:
            project_to_plane: Se True, projeta coordenadas no plano (z=0)
            
        Returns:
            Dict com coordenadas organizadas por grupo
        """
        coordinates = {'reference': [], 'group1': [], 'group2': []}
        
        if not self.is_calibrated:
            return coordinates
        
        # Processar marcadores de todos os grupos
        all_markers = {**self.reference_markers, **self.group1_markers, **self.group2_markers}
        
        for marker_id, info in all_markers.items():
            coords = self.convert_to_reference_coordinates(info.position, project_to_plane=project_to_plane)
            if coords:
                marker_data = {
                    'id': marker_id, 
                    'x_mm': coords[0], 
                    'y_mm': coords[1],
                    'z_mm': coords[2], 
                    'confidence': info.confidence,
                    'timestamp': info.timestamp
                }
                
                # Classificar por grupo
                if marker_id in self.reference_ids:
                    coordinates['reference'].append(marker_data)
                elif marker_id in self.group1_ids:
                    coordinates['group1'].append(marker_data)
                elif marker_id in self.group2_ids:
                    coordinates['group2'].append(marker_data)
        
        return coordinates
    
    def reset_calibration(self):
        """Reseta calibração e grid calculado"""
        self.is_calibrated = False
        self.origin_3d = None
        self.x_vector = None
        self.y_vector = None
        self.z_vector_ref = None
        self.reference_distance_mm = 0
        self.calculated_grid_positions.clear()
        self.position_history.clear()
        
        if self.enable_debug_logs:
            self.logger.info("Calibração resetada")
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Retorna informações detalhadas para debug"""
        return {
            'system_calibrated': self.is_calibrated,
            'configured_distance_mm': self.configured_reference_distance_mm,
            'measured_distance_mm': self.reference_distance_mm,
            'grid_positions': len(self.calculated_grid_positions),
            'detection_stats': self.detection_stats,
            'reference_markers': len(self.reference_markers),
            'group1_markers': len(self.group1_markers),
            'group2_markers': len(self.group2_markers),
            'debug_logs_enabled': self.enable_debug_logs
        }