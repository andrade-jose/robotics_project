#!/usr/bin/env python3
"""
VISUAL MONITOR - VERSÃO INTEGRADA
=================================
Interface visual para monitoramento do sistema ArUco integrado ao robotics_project
Exibe detecções, calibração e status em tempo real
"""

import cv2
import numpy as np
import time
from typing import Dict, Any, Optional, Tuple, List

# Imports do projeto
from .vision_logger import VisionLogger
from .aruco_vision import ArUcoVisionSystem, MarkerInfo

class VisualMonitor:
    """
    Monitor visual para sistema de visão ArUco integrado ao projeto
    
    FUNCIONALIDADES:
    - Overlay de detecções em tempo real
    - Visualização de grupos de marcadores (cores diferentes)
    - Interface de calibração visual
    - Status do sistema na tela
    - Coordenadas do tabuleiro em tempo real
    - Integração com configurações do projeto
    """
    
    def __init__(self, vision_system: ArUcoVisionSystem):
        """
        Inicializa monitor visual
        
        Args:
            vision_system: Sistema ArUco já configurado
        """
        self.vision_system = vision_system
        self.logger = VisionLogger(__name__)
        
        # Importar configurações do projeto
        try:
            from config.config_completa import CONFIG
            self.config_visao = CONFIG['visao']
        except (ImportError, KeyError) as e:
            raise RuntimeError(f"Erro ao carregar configurações do projeto: {e}")
        
        # Configurações de visualização
        self._setup_visual_config()
        
        # Estado da interface
        self.show_debug = getattr(self.config_visao, 'enable_debug_view', False)
        self.show_coordinates = True
        self.show_status = True
        self.show_calibration = True
        
        # Informações de performance
        self.fps_display = 0.0
        self.last_fps_time = time.time()
        self.frame_count = 0
        
        self.logger.info("VisualMonitor inicializado")
    
    def _setup_visual_config(self):
        """Configura cores e estilos visuais"""
        # Cores para diferentes grupos de marcadores
        self.colors = {
            'reference': (0, 255, 255),      # Amarelo (marcadores de referência)
            'group1': (0, 0, 255),           # Vermelho (jogador 1)
            'group2': (255, 0, 0),           # Azul (jogador 2) 
            'unknown': (128, 128, 128),      # Cinza (marcadores desconhecidos)
            'text': (255, 255, 255),         # Branco (texto)
            'background': (0, 0, 0),         # Preto (fundo de texto)
            'calibrated': (0, 255, 0),       # Verde (sistema calibrado)
            'error': (0, 0, 255)             # Vermelho (erros)
        }
        
        # Configurações de fonte
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = 0.6
        self.font_thickness = 2
        self.text_color = self.colors['text']
        
        # Configurações de desenho
        self.marker_thickness = 3
        self.axis_length = 0.05  # 5cm para eixos dos marcadores
    
    def draw_detection_overlay(self, frame: np.ndarray, detection_result: Dict[str, Any]) -> np.ndarray:
        """
        Desenha overlay com todas as detecções no frame
        
        Args:
            frame: Frame original da câmera
            detection_result: Resultado de vision_system.detect_markers()
            
        Returns:
            Frame com overlay desenhado
        """
        if frame is None:
            return frame
        
        # Copia do frame para não modificar original
        display_frame = frame.copy()
        
        try:
            # Desenhar marcadores por grupo
            self._draw_marker_group(display_frame, detection_result.get('reference_markers', {}), 'reference')
            self._draw_marker_group(display_frame, detection_result.get('group1_markers', {}), 'group1')
            self._draw_marker_group(display_frame, detection_result.get('group2_markers', {}), 'group2')
            self._draw_marker_group(display_frame, detection_result.get('unknown_markers', {}), 'unknown')
            
            # Desenhar informações adicionais
            if self.show_status:
                self._draw_status_panel(display_frame, detection_result)
            
            if self.show_calibration:
                self._draw_calibration_info(display_frame)
            
            if self.show_coordinates:
                self._draw_coordinate_info(display_frame, detection_result)
            
            # Atualizar FPS
            self._update_fps_display()
            self._draw_fps(display_frame)
            
            return display_frame
            
        except Exception as e:
            self.logger.error(f"Erro ao desenhar overlay: {e}")
            return frame
    
    def _draw_marker_group(self, frame: np.ndarray, markers: Dict[int, MarkerInfo], group_type: str):
        """Desenha grupo específico de marcadores"""
        color = self.colors.get(group_type, self.colors['unknown'])
        
        for marker_id, marker_info in markers.items():
            try:
                # Desenhar contorno do marcador
                corners = marker_info.corners.astype(int)
                cv2.polylines(frame, [corners], True, color, self.marker_thickness)
                
                # Desenhar ID do marcador
                center = corners.mean(axis=0).astype(int)
                self._draw_text_with_background(
                    frame, f"ID:{marker_id}", 
                    tuple(center), color
                )
                
                # Desenhar eixos 3D se temos pose
                if hasattr(marker_info, 'position') and hasattr(marker_info, 'rotation'):
                    self._draw_marker_axes(frame, marker_info)
                
                # Desenhar coordenadas do tabuleiro se disponíveis
                board_coords = self.vision_system.get_board_coordinates(marker_info)
                if board_coords is not None:
                    coord_text = f"({board_coords[0]:.2f}, {board_coords[1]:.2f})"
                    coord_pos = (center[0], center[1] + 25)
                    self._draw_text_with_background(frame, coord_text, coord_pos, color)
                
            except Exception as e:
                self.logger.warning(f"Erro ao desenhar marcador {marker_id}: {e}")
    
    def _draw_marker_axes(self, frame: np.ndarray, marker_info: MarkerInfo):
        """Desenha eixos 3D do marcador"""
        try:
            # Verificar se temos dados válidos de pose
            if not hasattr(marker_info, 'position') or not hasattr(marker_info, 'rotation'):
                return
                
            rvec = marker_info.rotation
            tvec = marker_info.position
            
            # CORREÇÃO: Verificar se os vetores não são None e têm formato correto
            if rvec is None or tvec is None:
                return
                
            # CORREÇÃO: Garantir que são arrays 3x1
            if rvec.size == 3:
                rvec = rvec.reshape(3, 1)
            if tvec.size == 3:
                tvec = tvec.reshape(3, 1)
                
            # Pontos dos eixos no espaço 3D
            axis_points = np.array([
                [0, 0, 0],  # Origem
                [self.axis_length, 0, 0],  # Eixo X (vermelho)
                [0, self.axis_length, 0],  # Eixo Y (verde)
                [0, 0, -self.axis_length]  # Eixo Z (azul)
            ], dtype=np.float32)
            
            # Projetar para imagem
            axis_2d, _ = cv2.projectPoints(
                axis_points,
                rvec,
                tvec,
                self.vision_system.camera_matrix,
                self.vision_system.dist_coeffs
            )
            
            # Converter para inteiros
            axis_2d = axis_2d.reshape(-1, 2).astype(int)
            
            # CORREÇÃO: Verificar se temos pontos suficientes
            if len(axis_2d) < 4:
                return
                
            origin = tuple(axis_2d[0])
            
            # Desenhar eixos coloridos
            cv2.arrowedLine(frame, origin, tuple(axis_2d[1]), (0, 0, 255), 2)    # X - Vermelho
            cv2.arrowedLine(frame, origin, tuple(axis_2d[2]), (0, 255, 0), 2)    # Y - Verde  
            cv2.arrowedLine(frame, origin, tuple(axis_2d[3]), (255, 0, 0), 2)    # Z - Azul
            
        except Exception as e:
            self.logger.debug(f"Erro ao desenhar eixos: {e}")
    
    def _draw_text_with_background(self, frame: np.ndarray, text: str, position: Tuple[int, int], color: Tuple[int, int, int]):
        """Desenha texto com fundo para melhor visibilidade"""
        try:
            # CORREÇÃO: Converter qualquer array numpy para escalares inteiros
            if hasattr(position, '__iter__'):
                # Se for numpy array ou lista, extrair os primeiros dois elementos
                position_list = list(position)
                if len(position_list) >= 2:
                    x = int(float(position_list[0]))
                    y = int(float(position_list[1]))
                else:
                    self.logger.debug(f"Posição inválida: {position}")
                    return
            else:
                self.logger.debug(f"Posição não iterável: {position}")
                return

            # Calcular tamanho do texto
            text_size = cv2.getTextSize(
                text, self.font, self.font_scale, self.font_thickness
            )
            text_width, text_height = text_size[0]
            baseline = text_size[1]

            # Desenhar fundo (retângulo)
            padding = 5
            pt1 = (x - padding, y - text_height - padding)
            pt2 = (x + text_width + padding, y + baseline + padding)
            
            # Garantir coordenadas válidas
            pt1 = (max(0, pt1[0]), max(0, pt1[1]))
            pt2 = (min(frame.shape[1], pt2[0]), min(frame.shape[0], pt2[1]))
            
            # Verificar se as coordenadas são válidas
            if pt1[0] < pt2[0] and pt1[1] < pt2[1]:
                cv2.rectangle(frame, pt1, pt2, self.colors['background'], -1)

            # Desenhar texto
            cv2.putText(frame, text, (x, y), self.font, self.font_scale, color, self.font_thickness)

        except Exception as e:
            self.logger.debug(f"Erro ao desenhar texto '{text}' na posição {position}: {e}")
    
    def _draw_status_panel(self, frame: np.ndarray, detection_result: Dict[str, Any]):
        """Desenha painel de status no canto da tela"""
        try:
            # Posição do painel (canto superior esquerdo)
            panel_x, panel_y = 10, 30
            line_height = 25
            
            # Informações básicas
            status_lines = [
                f"Sistema: {'CALIBRADO' if self.vision_system.is_calibrated else 'NAO CALIBRADO'}",
                f"Detecções: {detection_result['detection_count']}",
                f"Referência: {len(detection_result.get('reference_markers', {}))}",
                f"Grupo 1: {len(detection_result.get('group1_markers', {}))}",
                f"Grupo 2: {len(detection_result.get('group2_markers', {}))}"
            ]
            
            # Desenhar cada linha
            for i, line in enumerate(status_lines):
                y_pos = panel_y + (i * line_height)
                color = self.colors['calibrated'] if 'CALIBRADO' in line and 'NAO' not in line else self.text_color
                self._draw_text_with_background(frame, line, (panel_x, y_pos), color)
            
        except Exception as e:
            self.logger.debug(f"Erro ao desenhar painel de status: {e}")
    
    def _draw_calibration_info(self, frame: np.ndarray):
        """Desenha informações de calibração"""
        if not self.vision_system.is_calibrated:
            return
        
        try:
            # Posição das informações de calibração (canto superior direito)
            frame_height, frame_width = frame.shape[:2]
            panel_x = frame_width - 250
            panel_y = 30
            line_height = 25
            
            calibration_info = [
                "SISTEMA CALIBRADO",
                f"Marcadores ref: {self.config_visao.reference_ids[:2]}",
                f"Escala: {self.vision_system.calibration_transform.get('scale_factor', 0):.3f}m"
            ]
            
            for i, info in enumerate(calibration_info):
                y_pos = panel_y + (i * line_height)
                self._draw_text_with_background(frame, info, (panel_x, y_pos), self.colors['calibrated'])
                
        except Exception as e:
            self.logger.debug(f"Erro ao desenhar info de calibração: {e}")
    
    def _draw_coordinate_info(self, frame: np.ndarray, detection_result: Dict[str, Any]):
        """Desenha informações de coordenadas dos marcadores"""
        try:
            # Posição para informações de coordenadas (parte inferior)
            frame_height, frame_width = frame.shape[:2]
            panel_y = frame_height - 100
            line_height = 20
            
            # Coletar marcadores de jogo (group1 e group2)
            game_markers = {}
            game_markers.update(detection_result.get('group1_markers', {}))
            game_markers.update(detection_result.get('group2_markers', {}))
            
            if not game_markers:
                return
            
            # Desenhar cabeçalho
            self._draw_text_with_background(frame, "COORDENADAS DO TABULEIRO:", (10, panel_y), self.text_color)
            
            # Desenhar coordenadas de cada marcador
            for i, (marker_id, marker_info) in enumerate(game_markers.items()):
                board_coords = self.vision_system.get_board_coordinates(marker_info)
                if board_coords is not None:
                    coord_text = f"ID {marker_id}: ({board_coords[0]:.2f}, {board_coords[1]:.2f})"
                    y_pos = panel_y + ((i + 1) * line_height)
                    
                    # Cor baseada no grupo
                    color = self.colors.get(marker_info.player_group, self.colors['unknown'])
                    self._draw_text_with_background(frame, coord_text, (10, y_pos), color)
                    
        except Exception as e:
            self.logger.debug(f"Erro ao desenhar coordenadas: {e}")
    
    def _update_fps_display(self):
        """Atualiza cálculo de FPS para display"""
        current_time = time.time()
        self.frame_count += 1
        
        # Calcular FPS a cada 1 segundo
        if current_time - self.last_fps_time >= 1.0:
            self.fps_display = self.frame_count / (current_time - self.last_fps_time)
            self.frame_count = 0
            self.last_fps_time = current_time
    
    def _draw_fps(self, frame: np.ndarray):
        """Desenha FPS no canto da tela"""
        try:
            fps_text = f"FPS: {self.fps_display:.1f}"
            frame_height = frame.shape[0]
            position = (10, frame_height - 20)
            
            self._draw_text_with_background(frame, fps_text, position, self.text_color)
            
        except Exception as e:
            self.logger.debug(f"Erro ao desenhar FPS: {e}")
    
    def draw_calibration_guide(self, frame: np.ndarray) -> np.ndarray:
        """
        Desenha guia visual para calibração do sistema
        
        Args:
            frame: Frame da câmera
            
        Returns:
            Frame com guia de calibração
        """
        guide_frame = frame.copy()
        
        try:
            frame_height, frame_width = frame.shape[:2]
            center_x, center_y = frame_width // 2, frame_height // 2
            
            # Desenhar instruções de calibração
            instructions = [
                "CALIBRACAO DO SISTEMA",
                "Posicione os marcadores de referência:",
                f"IDs necessários: {self.config_visao.reference_ids}",
                "Pressione 'c' para calibrar",
                "Pressione 'ESC' para sair"
            ]
            
            # Fundo semi-transparente
            overlay = guide_frame.copy()
            cv2.rectangle(overlay, (50, 50), (frame_width - 50, 200), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.7, guide_frame, 0.3, 0, guide_frame)
            
            # Desenhar instruções
            for i, instruction in enumerate(instructions):
                y_pos = 80 + (i * 25)
                cv2.putText(guide_frame, instruction, (60, y_pos), 
                           self.font, self.font_scale, self.colors['text'], self.font_thickness)
            
            # Desenhar cruz central para referência
            cv2.line(guide_frame, (center_x - 20, center_y), (center_x + 20, center_y), self.colors['reference'], 2)
            cv2.line(guide_frame, (center_x, center_y - 20), (center_x, center_y + 20), self.colors['reference'], 2)
            
            return guide_frame
            
        except Exception as e:
            self.logger.error(f"Erro ao desenhar guia de calibração: {e}")
            return frame
    
    def show_detection_summary(self, detection_result: Dict[str, Any]) -> str:
        """
        Cria resumo textual das detecções para log
        
        Args:
            detection_result: Resultado das detecções
            
        Returns:
            String com resumo das detecções
        """
        try:
            summary_lines = []
            
            # Resumo geral
            total = detection_result['detection_count']
            summary_lines.append(f"Total detectado: {total}")
            
            # Detalhes por grupo
            ref_count = len(detection_result.get('reference_markers', {}))
            g1_count = len(detection_result.get('group1_markers', {}))
            g2_count = len(detection_result.get('group2_markers', {}))
            
            if ref_count > 0:
                ref_ids = list(detection_result['reference_markers'].keys())
                summary_lines.append(f"Referência ({ref_count}): {ref_ids}")
            
            if g1_count > 0:
                g1_ids = list(detection_result['group1_markers'].keys())
                summary_lines.append(f"Grupo 1 ({g1_count}): {g1_ids}")
            
            if g2_count > 0:
                g2_ids = list(detection_result['group2_markers'].keys())
                summary_lines.append(f"Grupo 2 ({g2_count}): {g2_ids}")
            
            # Status de calibração
            calib_status = "CALIBRADO" if self.vision_system.is_calibrated else "NÃO CALIBRADO"
            summary_lines.append(f"Sistema: {calib_status}")
            
            return " | ".join(summary_lines)
            
        except Exception as e:
            self.logger.error(f"Erro ao criar resumo: {e}")
            return "Erro no resumo"
    
    def show_image(self, image: np.ndarray, window_name: str = "Vision System") -> bool:
        """
        Mostra imagem na janela com tratamento de erro robusto
        
        Returns:
            bool: True se conseguiu mostrar, False caso contrário
        """
        try:
            # Verificar se a imagem é válida
            if image is None or image.size == 0:
                self.logger.debug("Imagem vazia ou inválida")
                return False
                
            # Tentar mostrar a imagem
            cv2.imshow(window_name, image)
            
            # Verificar se a janela foi criada corretamente
            try:
                prop = cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE)
                return prop >= 0  # Retorna True se a janela está visível
            except:
                # Se não conseguiu verificar a propriedade, assume que funcionou
                return True
                
        except Exception as e:
            self.logger.warning(f"Display não disponível: {e}")
            return False

    def wait_key(self, delay: int = 1) -> int:
        """Espera por tecla com tratamento de erro robusto"""
        try:
            key = cv2.waitKey(delay) & 0xFF
            return key
        except Exception as e:
            self.logger.debug(f"Erro ao esperar tecla: {e}")
            return 113  # Retorna 'q' para sair
    def toggle_debug_view(self):
        """Alterna visualização de debug"""
        self.show_debug = not self.show_debug
        self.logger.info(f"Debug view: {'LIGADO' if self.show_debug else 'DESLIGADO'}")
    
    def toggle_coordinates(self):
        """Alterna exibição de coordenadas"""
        self.show_coordinates = not self.show_coordinates
        self.logger.info(f"Coordenadas: {'LIGADAS' if self.show_coordinates else 'DESLIGADAS'}")
    
    def toggle_status(self):
        """Alterna exibição de status"""
        self.show_status = not self.show_status
        self.logger.info(f"Status: {'LIGADO' if self.show_status else 'DESLIGADO'}")
    
    def get_visual_config(self) -> Dict[str, Any]:
        """Retorna configuração atual da visualização"""
        return {
            'show_debug': self.show_debug,
            'show_coordinates': self.show_coordinates,
            'show_status': self.show_status,
            'show_calibration': self.show_calibration,
            'fps_display': self.fps_display,
            'colors': self.colors.copy()
        }

# Teste se executado diretamente
if __name__ == "__main__":
    print("🧪 Teste do VisualMonitor")
    
    try:
        # Criar sistema de visão
        from .aruco_vision import ArUcoVisionSystem
        vision_system = ArUcoVisionSystem()
        
        # Criar monitor
        monitor = VisualMonitor(vision_system)
        
        # Teste com frame falso
        fake_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Simular detecção vazia
        empty_result = vision_system.detect_markers(fake_frame)
        
        # Desenhar overlay
        display_frame = monitor.draw_detection_overlay(fake_frame, empty_result)
        
        # Mostrar resumo
        summary = monitor.show_detection_summary(empty_result)
        print(f"Resumo: {summary}")
        
        # Mostrar configuração
        config = monitor.get_visual_config()
        print("Configuração visual:")
        for key, value in config.items():
            if key != 'colors':  # Não mostrar todas as cores
                print(f"  {key}: {value}")
        
        print("✅ VisualMonitor básico funcionando")
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()