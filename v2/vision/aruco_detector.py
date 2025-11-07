"""
ArUcoDetector - Módulo de detecção de marcadores ArUco

Responsabilidades:
- Detectar marcadores ArUco (6x6 250)
- Retornar centróides em formato (x, y)
- Validar detecções
- Logging detalhado

Sem dependências de câmera ou grid - apenas processa frames.
Simples, testável, isolado.

Uso:
    detector = ArUcoDetector(aruco_dict_size=6, marker_size=250)
    detections = detector.detect(frame)
    # Retorna: {marker_id: (centroid_x, centroid_y), ...}
"""

import cv2
import logging
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass


@dataclass
class Detection:
    """Detecção de um marcador ArUco."""
    marker_id: int
    centroid: Tuple[float, float]  # (x, y)
    corners: List[Tuple[float, float]]  # Lista dos 4 cantos
    confidence: float = 1.0


class ArUcoDetector:
    """
    Detector de marcadores ArUco.

    Características:
    - Detecta ArUco 6x6 250 (configurável)
    - Retorna centróides e cantos
    - Validação de detecções
    - Logging detalhado
    """

    def __init__(
        self,
        aruco_dict_size: int = 6,  # 6x6 bits
        marker_size: int = 250,  # Código 250
        logger: Optional[logging.Logger] = None,
    ):
        """
        Inicializa detector.

        Args:
            aruco_dict_size: Tamanho do dicionário ArUco (6 = 6x6)
            marker_size: Código do marcador (250 = padrão Tapatan)
            logger: Logger customizado (ou usa default)
        """
        self.aruco_dict_size = aruco_dict_size
        self.marker_size = marker_size
        self.detections_count = 0

        # Configurar dicionário ArUco
        try:
            # Para OpenCV 4.7+
            if hasattr(cv2.aruco, "getPredefinedDictionary"):
                self.aruco_dict = cv2.aruco.getPredefinedDictionary(
                    cv2.aruco.DICT_6X6_250
                )
                self.detector = cv2.aruco.ArucoDetector(self.aruco_dict)
            else:
                # Para OpenCV antigas (fallback)
                self.aruco_dict = cv2.aruco.getPredefinedDictionary(
                    cv2.aruco.DICT_6X6_250
                )
                self.detector = None  # Usar detectMarkers direto
        except Exception as e:
            raise RuntimeError(f"Erro ao configurar ArUco: {e}")

        # Logger
        if logger is None:
            self.logger = logging.getLogger(__name__)
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter("[%(levelname)s] %(message)s")
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
                self.logger.setLevel(logging.INFO)
        else:
            self.logger = logger

    def detect(self, frame) -> Dict[int, Detection]:
        """
        Detecta marcadores ArUco em um frame.

        Args:
            frame: numpy array (imagem OpenCV BGR)

        Returns:
            Dict {marker_id: Detection}
        """
        if frame is None:
            self.logger.warning("[ARUCO] Frame é None!")
            return {}

        if len(frame.shape) != 3:
            self.logger.warning("[ARUCO] Frame inválido!")
            return {}

        try:
            # Converter para escala de cinza se necessário
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                gray = frame

            # Detectar marcadores
            if self.detector is not None:
                # OpenCV 4.7+
                corners, ids, rejected = self.detector.detectMarkers(gray)
            else:
                # Fallback para versões antigas
                try:
                    corners, ids, rejected = cv2.aruco.detectMarkers(
                        gray, self.aruco_dict
                    )
                except AttributeError:
                    # Versão muito antiga
                    self.logger.error("[ARUCO] Versão OpenCV não suportada!")
                    return {}

            detections = {}

            if ids is not None and len(ids) > 0:
                for i, marker_id in enumerate(ids.flatten()):
                    corner = corners[i][0]  # 4 pontos
                    centroid = self._calculate_centroid(corner)

                    detections[int(marker_id)] = Detection(
                        marker_id=int(marker_id),
                        centroid=centroid,
                        corners=[tuple(pt) for pt in corner],
                        confidence=1.0,
                    )

                self.detections_count += 1
                self.logger.debug(f"[ARUCO] Detectados {len(detections)} marcadores")

            return detections

        except Exception as e:
            self.logger.error(f"[ARUCO] Erro na detecção: {e}")
            return {}

    def _calculate_centroid(self, corners: List[Tuple[float, float]]) -> Tuple[float, float]:
        """
        Calcula centróide de um marcador.

        Args:
            corners: Lista de 4 pontos [(x,y), ...]

        Returns:
            (centroid_x, centroid_y)
        """
        if len(corners) != 4:
            self.logger.warning("[ARUCO] Número inválido de cantos!")
            return (0.0, 0.0)

        try:
            x_coords = [pt[0] for pt in corners]
            y_coords = [pt[1] for pt in corners]

            centroid_x = sum(x_coords) / len(x_coords)
            centroid_y = sum(y_coords) / len(y_coords)

            return (float(centroid_x), float(centroid_y))

        except Exception as e:
            self.logger.error(f"[ARUCO] Erro ao calcular centróide: {e}")
            return (0.0, 0.0)

    def draw_detections(self, frame, detections: Dict[int, Detection]):
        """
        Desenha detecções no frame (para visualização).

        Args:
            frame: numpy array (será modificado in-place)
            detections: Dict de detecções

        Returns:
            Frame modificado
        """
        if frame is None:
            return frame

        try:
            frame_copy = frame.copy()

            for marker_id, detection in detections.items():
                # Desenhar centróide
                cx, cy = detection.centroid
                cv2.circle(frame_copy, (int(cx), int(cy)), 5, (0, 255, 0), -1)

                # Desenhar ID
                cv2.putText(
                    frame_copy,
                    f"ID:{marker_id}",
                    (int(cx) + 10, int(cy) - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    2,
                )

                # Desenhar cantos
                for corner in detection.corners:
                    cv2.circle(
                        frame_copy,
                        (int(corner[0]), int(corner[1])),
                        3,
                        (255, 0, 0),
                        -1,
                    )

            return frame_copy

        except Exception as e:
            self.logger.error(f"[ARUCO] Erro ao desenhar detecções: {e}")
            return frame

    def validate_detections(self, detections: Dict[int, Detection]) -> bool:
        """
        Valida detecções.

        Args:
            detections: Dict de detecções

        Returns:
            True se válido, False caso contrário
        """
        if not isinstance(detections, dict):
            self.logger.warning("[ARUCO] Detecções não é um dict!")
            return False

        if len(detections) == 0:
            return True  # Vazio é válido

        for marker_id, detection in detections.items():
            # Validar ID
            if not isinstance(marker_id, int) or marker_id < 0:
                self.logger.warning(f"[ARUCO] ID inválido: {marker_id}")
                return False

            # Validar centróide
            if not isinstance(detection.centroid, tuple) or len(detection.centroid) != 2:
                self.logger.warning(f"[ARUCO] Centróide inválido: {detection.centroid}")
                return False

            # Validar coordenadas
            cx, cy = detection.centroid
            if not isinstance(cx, (int, float)) or not isinstance(cy, (int, float)):
                self.logger.warning(f"[ARUCO] Coordenadas inválidas: ({cx}, {cy})")
                return False

            if cx < 0 or cy < 0:
                self.logger.warning(f"[ARUCO] Coordenadas negativas: ({cx}, {cy})")
                return False

        return True

    def get_stats(self) -> dict:
        """Retorna estatísticas de detecção."""
        return {
            "total_detections": self.detections_count,
            "aruco_dict_size": self.aruco_dict_size,
            "marker_size": self.marker_size,
        }


# ============================================================================
# Teste se executado diretamente
# ============================================================================

if __name__ == "__main__":
    print("[TESTE] Teste do ArUcoDetector")
    print("")

    try:
        # Criar detector
        detector = ArUcoDetector(aruco_dict_size=6, marker_size=250)
        print("[OK] Detector criado com sucesso")

        # Criar imagem de teste (branca)
        test_frame = cv2.imread("test_aruco_image.jpg")
        if test_frame is None:
            print("[AVISO] Usando frame branco para teste")
            test_frame = cv2.createImage((640, 480), cv2.CV_8UC3, (255, 255, 255))

        # Detectar
        detections = detector.detect(test_frame)
        print(f"[OK] Detecções encontradas: {len(detections)}")

        for marker_id, detection in detections.items():
            print(f"  - Marcador {marker_id}: centróide = {detection.centroid}")

        # Stats
        stats = detector.get_stats()
        print(f"\n[STATUS] Detector:")
        for key, value in stats.items():
            print(f"  - {key}: {value}")

    except Exception as e:
        print(f"[ERRO] Erro no teste: {e}")
        import traceback

        traceback.print_exc()

    print("\n[OK] Teste concluído")
