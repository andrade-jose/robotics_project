#!/usr/bin/env python3
"""
CAMERA MANAGER - VERSÃO INTEGRADA
=================================
Gerencia captura de vídeo integrado ao robotics_project
Usa configurações de CONFIG['visao'] e CONFIG['sistema']
"""

import cv2
import numpy as np
import time
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass

# Imports do projeto
from .vision_logger import VisionLogger

@dataclass
class CameraInfo:
    """Informações de uma câmera detectada"""
    index: int
    name: str
    is_available: bool
    resolution: Tuple[int, int]
    fps: int
    backend: str

class CameraManager:
    """
    Gerenciador de câmeras integrado ao robotics_project
    
    FUNCIONALIDADES:
    - Usa configurações automáticas do CONFIG['visao']
    - Detecção automática de câmeras disponíveis
    - Configuração automática de parâmetros
    - Fallback automático entre câmeras
    - Monitoramento de performance
    - Integração com sistema de logs do projeto
    """
    
    def __init__(self):
        """Inicializa o gerenciador usando configurações do projeto"""
        # Importar configurações do projeto
        try:
            from config.config_completa import CONFIG
            self.config_visao = CONFIG['visao']
            self.config_sistema = CONFIG['sistema']
        except (ImportError, KeyError) as e:
            raise RuntimeError(f"Erro ao carregar configurações do projeto: {e}")
        
        # Inicializar logger
        self.logger = VisionLogger(__name__)
        
        # Estado da câmera
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_opened = False
        self.current_camera_index = -1
        self.current_camera_info: Optional[CameraInfo] = None
        
        # Estatísticas de performance
        self.frame_count = 0
        self.start_time = time.time()
        self.fps_actual = 0.0
        self.last_fps_calculation = time.time()
        
        # Cache de câmeras disponíveis
        self._available_cameras: List[CameraInfo] = []
        self._last_scan_time = 0
        self._scan_cache_duration = 30  # segundos
        
        self.logger.info("CameraManager inicializado com configurações do projeto")
    
    def initialize_camera(self, preferred_index: Optional[int] = None) -> bool:
        """
        Inicializa câmera com fallback automático
        
        Args:
            preferred_index: Índice preferencial (None = usar CONFIG['visao'])
            
        Returns:
            bool: True se câmera foi inicializada com sucesso
        """
        target_index = preferred_index if preferred_index is not None else self.config_visao.camera_index
        
        self.logger.info(f"Tentando inicializar câmera {target_index}")
        
        # Tentar câmera preferencial primeiro
        if self._try_initialize_camera(target_index):
            return True
        
        # Fallback: tentar câmeras disponíveis em ordem
        self.logger.warning(f"Câmera {target_index} falhou, tentando fallback automático...")
        
        available_cameras = self.scan_available_cameras()
        for camera_info in available_cameras:
            if camera_info.index != target_index and camera_info.is_available:
                self.logger.info(f"Tentando câmera fallback: {camera_info.index}")
                if self._try_initialize_camera(camera_info.index):
                    return True
        
        self.logger.error("Nenhuma câmera disponível encontrada")
        return False
    
    def _try_initialize_camera(self, camera_index: int) -> bool:
        """Tenta inicializar uma câmera específica"""
        try:
            # Fechar câmera anterior se existir
            if self.cap is not None:
                self.cap.release()
            
            # Tentar diferentes backends para melhor compatibilidade
            backends = [cv2.CAP_DSHOW, cv2.CAP_V4L2, cv2.CAP_ANY]
            
            for backend in backends:
                self.cap = cv2.VideoCapture(camera_index, backend)
                if self.cap.isOpened():
                    break
            
            if not self.cap or not self.cap.isOpened():
                return False
            
            # Configurar parâmetros da câmera
            success = self._configure_camera()
            if not success:
                self.cap.release()
                return False
            
            # Testar captura
            ret, frame = self.cap.read()
            if not ret or frame is None:
                self.cap.release()
                return False
            
            # Sucesso - atualizar estado
            self.is_opened = True
            self.current_camera_index = camera_index
            self.start_time = time.time()
            self.frame_count = 0
            
            # Obter informações da câmera
            backend_name = self._get_backend_name()
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = int(self.cap.get(cv2.CAP_PROP_FPS))
            
            self.current_camera_info = CameraInfo(
                index=camera_index,
                name=f"Camera_{camera_index}",
                is_available=True,
                resolution=(actual_width, actual_height),
                fps=actual_fps,
                backend=backend_name
            )
            
            self.logger.info(f"Câmera {camera_index} inicializada: {actual_width}x{actual_height}@{actual_fps}fps ({backend_name})")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao inicializar câmera {camera_index}: {e}")
            return False
    
    def _configure_camera(self) -> bool:
        """Configura parâmetros da câmera usando CONFIG['visao']"""
        try:
            # Aplicar configurações da resolução
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config_visao.frame_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config_visao.frame_height)
            self.cap.set(cv2.CAP_PROP_FPS, self.config_visao.fps)
            
            # Configurações adicionais para melhor performance
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Buffer mínimo para reduzir latência
            
            # Verificar se configurações foram aplicadas
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            if actual_width <= 0 or actual_height <= 0:
                self.logger.warning("Resolução da câmera inválida após configuração")
                return False
            
            self.logger.debug(f"Câmera configurada: {actual_width}x{actual_height}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao configurar câmera: {e}")
            return False
    
    def _get_backend_name(self) -> str:
        """Obtém nome do backend atual da câmera"""
        try:
            backend_id = int(self.cap.get(cv2.CAP_PROP_BACKEND))
            backend_names = {
                cv2.CAP_DSHOW: "DirectShow",
                cv2.CAP_V4L2: "V4L2", 
                cv2.CAP_GSTREAMER: "GStreamer",
                cv2.CAP_ANY: "Any"
            }
            return backend_names.get(backend_id, f"Backend_{backend_id}")
        except:
            return "Unknown"
    
    def scan_available_cameras(self, max_cameras: int = 10) -> List[CameraInfo]:
        """
        Escaneia câmeras disponíveis no sistema
        
        Args:
            max_cameras: Número máximo de câmeras para testar
            
        Returns:
            Lista de informações das câmeras encontradas
        """
        # Usar cache se ainda válido
        current_time = time.time()
        if (current_time - self._last_scan_time) < self._scan_cache_duration and self._available_cameras:
            return self._available_cameras
        
        self.logger.info("Escaneando câmeras disponíveis...")
        cameras = []
        
        for i in range(max_cameras):
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    # Testar se realmente funciona
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        fps = int(cap.get(cv2.CAP_PROP_FPS))
                        
                        camera_info = CameraInfo(
                            index=i,
                            name=f"Camera_{i}",
                            is_available=True,
                            resolution=(width, height),
                            fps=fps,
                            backend="Unknown"
                        )
                        cameras.append(camera_info)
                        self.logger.debug(f"Câmera {i} encontrada: {width}x{height}@{fps}fps")
                    
                    cap.release()
                else:
                    # Câmera não disponível
                    camera_info = CameraInfo(
                        index=i,
                        name=f"Camera_{i}",
                        is_available=False,
                        resolution=(0, 0),
                        fps=0,
                        backend="N/A"
                    )
                    cameras.append(camera_info)
                    
            except Exception as e:
                self.logger.debug(f"Erro ao testar câmera {i}: {e}")
        
        # Atualizar cache
        self._available_cameras = cameras
        self._last_scan_time = current_time
        
        available_count = sum(1 for c in cameras if c.is_available)
        self.logger.info(f"Scan concluído: {available_count} câmeras disponíveis de {len(cameras)} testadas")
        
        return cameras
    
    def capture_frame(self) -> Optional[np.ndarray]:
        """
        Captura um frame da câmera
        
        Returns:
            Frame capturado ou None se falhar
        """
        if not self.is_opened or self.cap is None:
            return None
        
        try:
            ret, frame = self.cap.read()
            if ret and frame is not None:
                self.frame_count += 1
                self._update_fps_stats()
                return frame
            else:
                self.logger.warning("Falha na captura do frame")
                return None
                
        except Exception as e:
            self.logger.error(f"Erro na captura: {e}")
            return None
    
    def _update_fps_stats(self):
        """Atualiza estatísticas de FPS"""
        current_time = time.time()
        if current_time - self.last_fps_calculation >= 1.0:  # Calcular a cada 1 segundo
            elapsed = current_time - self.start_time
            if elapsed > 0:
                self.fps_actual = self.frame_count / elapsed
                self.logger.performance(f"FPS atual: {self.fps_actual:.1f}")
            
            self.last_fps_calculation = current_time
    
    def get_camera_status(self) -> Dict[str, Any]:
        """Retorna status detalhado da câmera"""
        if not self.is_opened:
            return {
                'is_opened': False,
                'error': 'Câmera não inicializada'
            }
        
        return {
            'is_opened': True,
            'camera_index': self.current_camera_index,
            'camera_info': self.current_camera_info.__dict__ if self.current_camera_info else None,
            'frame_count': self.frame_count,
            'fps_actual': self.fps_actual,
            'uptime_seconds': time.time() - self.start_time,
        }
    
    def release(self):
        """Libera recursos da câmera"""
        if self.cap is not None:
            self.cap.release()
            self.logger.info(f"Câmera {self.current_camera_index} liberada")
        
        self.is_opened = False
        self.current_camera_index = -1
        self.current_camera_info = None

# Teste se executado diretamente
if __name__ == "__main__":
    print("🧪 Teste do CameraManager")
    
    try:
        # Criar gerenciador
        manager = CameraManager()
        
        # Escanear câmeras
        cameras = manager.scan_available_cameras()
        print(f"Câmeras encontradas: {len(cameras)}")
        for cam in cameras:
            status = "✅" if cam.is_available else "❌"
            print(f"  {status} Câmera {cam.index}: {cam.resolution[0]}x{cam.resolution[1]}")
        
        # Tentar inicializar
        if manager.initialize_camera():
            print("✅ Câmera inicializada com sucesso")
            
            # Capturar alguns frames de teste
            for i in range(5):
                frame = manager.capture_frame()
                if frame is not None:
                    print(f"Frame {i+1}: {frame.shape}")
                time.sleep(0.1)
            
            # Status final
            status = manager.get_camera_status()
            print(f"Status final: FPS={status.get('fps_actual', 0):.1f}")
            
        else:
            print("❌ Falha ao inicializar câmera")
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
    
    finally:
        try:
            manager.release()
        except:
            pass
        print("✅ Teste concluído")