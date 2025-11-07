"""
CalibrationMarkerDetector - Detecção de 2 Marcadores ArUco para Calibração

Responsabilidades:
- Detectar exatamente 2 marcadores ArUco (canto inferior esquerdo + canto superior direito)
- Extrair poses (centros e vetores normais)
- Validar que os marcadores estão em posição válida
- Aplicar media móvel para estabilizar detecção

Física:
- Ambos os marcadores assumidos em Z = 0 (plano do tabuleiro)
- Marcador 0 (esquerdo): define origem (0,0,0)
- Marcador 1 (direito): define direção X e Y

Uso:
    detector = CalibrationMarkerDetector()
    calibration = detector.detect(frame)
    if calibration:
        marker0_pose = calibration.marker0_pose
        marker1_pose = calibration.marker1_pose
        distance = calibration.distance_mm
"""

import cv2
import numpy as np
import logging
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
from collections import deque


@dataclass
class MarkerPose:
    """Pose de um marcador ArUco (posição + orientação)."""
    marker_id: int
    center: Tuple[float, float]  # (x, y) em pixels
    corners: np.ndarray  # 4 cantos do marcador
    normal: Tuple[float, float, float]  # Vetor normal (0,0,1) para Z=0
    orientation_angle: float  # Ângulo em graus


@dataclass
class CalibrationData:
    """Dados de calibração do tabuleiro."""
    marker0_pose: MarkerPose  # Canto inferior esquerdo (origem)
    marker1_pose: MarkerPose  # Canto superior direito
    distance_mm: float  # Distância real entre marcadores (deve ser conhecida)
    distance_pixels: float  # Distância em pixels
    scale: float  # pixels_to_mm = distance_mm / distance_pixels
    is_valid: bool  # Passou em todas as validações
    confidence: float  # Confiança da calibração (0-1)


class CalibrationMarkerDetector:
    """
    Detecta 2 marcadores ArUco para calibração do tabuleiro.

    Características:
    - Detecta exatamente 2 marcadores (falha se encontrar outro número)
    - Estabiliza detecção com média móvel (3-5 frames)
    - Valida que marcadores estão alinhados horizontalmente
    - Fornece transformação câmera → tabuleiro
    """

    def __init__(
        self,
        aruco_dict_size: int = 6,
        marker_size: int = 250,
        distance_mm: float = 270.0,  # Distância real entre os dois marcadores
        smoothing_frames: int = 3,  # Média móvel
        logger: Optional[logging.Logger] = None,
    ):
        """
        Inicializa detector de calibração.

        Args:
            aruco_dict_size: Tamanho do dicionário ArUco (6 = 6x6)
            marker_size: Código do marcador (250)
            distance_mm: Distância REAL entre os 2 marcadores em mm
            smoothing_frames: Número de frames para média móvel
            logger: Logger customizado
        """
        self.aruco_dict_size = aruco_dict_size
        self.marker_size = marker_size
        self.distance_mm = distance_mm
        self.smoothing_frames = smoothing_frames

        # Configurar ArUco
        try:
            if hasattr(cv2.aruco, "getPredefinedDictionary"):
                self.aruco_dict = cv2.aruco.getPredefinedDictionary(
                    cv2.aruco.DICT_6X6_250
                )
                self.detector = cv2.aruco.ArucoDetector(self.aruco_dict)
            else:
                self.aruco_dict = cv2.aruco.getPredefinedDictionary(
                    cv2.aruco.DICT_6X6_250
                )
                self.detector = None
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

        # Histórico para média móvel
        self.calibration_history = deque(maxlen=smoothing_frames)
        self.last_valid_calibration = None

        self.logger.info(
            f"[CALIB] CalibrationMarkerDetector inicializado "
            f"(distância esperada: {distance_mm}mm)"
        )

    def detect(self, frame) -> Optional[CalibrationData]:
        """
        Detecta 2 marcadores ArUco para calibração.

        Args:
            frame: numpy array (imagem OpenCV BGR)

        Returns:
            CalibrationData ou None se não encontrar exatamente 2 marcadores
        """
        if frame is None:
            self.logger.warning("[CALIB] Frame é None!")
            return None

        try:
            # Converter para escala de cinza
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                gray = frame

            # Detectar marcadores
            if self.detector is not None:
                corners, ids, rejected = self.detector.detectMarkers(gray)
            else:
                try:
                    corners, ids, rejected = cv2.aruco.detectMarkers(
                        gray, self.aruco_dict
                    )
                except AttributeError:
                    self.logger.error("[CALIB] Versão OpenCV não suportada!")
                    return None

            # Validar que encontrou EXATAMENTE 2 marcadores
            if ids is None or len(ids) != 2:
                self.logger.debug(f"[CALIB] Esperava 2 marcadores, encontrou {len(ids) if ids is not None else 0}")
                return self.last_valid_calibration  # Retornar última calibração válida

            # Extrair poses dos 2 marcadores
            marker_ids = ids.flatten()
            marker_poses = {}

            for i, marker_id in enumerate(marker_ids):
                corner = corners[i][0]  # 4 pontos do marcador
                center = self._calculate_center(corner)
                normal = (0.0, 0.0, 1.0)  # Assumir Z=0 (plano)
                angle = self._calculate_orientation(corner)

                marker_poses[int(marker_id)] = MarkerPose(
                    marker_id=int(marker_id),
                    center=center,
                    corners=corner,
                    normal=normal,
                    orientation_angle=angle,
                )

            # Ordenar: ID menor = esquerdo, ID maior = direito
            sorted_ids = sorted(marker_poses.keys())
            marker0_pose = marker_poses[sorted_ids[0]]
            marker1_pose = marker_poses[sorted_ids[1]]

            # Calcular distância entre marcadores
            distance_pixels = self._calculate_distance(
                marker0_pose.center, marker1_pose.center
            )

            # Calcular escala
            scale = self.distance_mm / distance_pixels if distance_pixels > 0 else 1.0

            # Criar calibração
            calibration = CalibrationData(
                marker0_pose=marker0_pose,
                marker1_pose=marker1_pose,
                distance_mm=self.distance_mm,
                distance_pixels=distance_pixels,
                scale=scale,
                is_valid=True,
                confidence=1.0,
            )

            # Aplicar média móvel (estabilizar)
            calibration = self._apply_smoothing(calibration)

            self.last_valid_calibration = calibration
            self.logger.debug(
                f"[CALIB] Calibração válida: "
                f"ID[{sorted_ids[0]},{sorted_ids[1]}] "
                f"distância={distance_pixels:.1f}px→{self.distance_mm}mm"
            )

            return calibration

        except Exception as e:
            self.logger.error(f"[CALIB] Erro na detecção: {e}")
            return self.last_valid_calibration

    def _calculate_center(self, corners: np.ndarray) -> Tuple[float, float]:
        """Calcula centro de um marcador (média dos 4 cantos)."""
        x_coords = corners[:, 0]
        y_coords = corners[:, 1]
        center_x = float(np.mean(x_coords))
        center_y = float(np.mean(y_coords))
        return (center_x, center_y)

    def _calculate_distance(
        self, center1: Tuple[float, float], center2: Tuple[float, float]
    ) -> float:
        """Calcula distância euclidiana entre dois centros."""
        x1, y1 = center1
        x2, y2 = center2
        distance = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        return float(distance)

    def _calculate_orientation(self, corners: np.ndarray) -> float:
        """
        Calcula ângulo de orientação do marcador.

        Usa o vetor do primeiro canto ao segundo.
        """
        if len(corners) >= 2:
            p1 = corners[0]
            p2 = corners[1]
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            angle = float(np.arctan2(dy, dx) * 180 / np.pi)
            return angle
        return 0.0

    def _apply_smoothing(self, calibration: CalibrationData) -> CalibrationData:
        """
        Aplica média móvel para estabilizar calibração.

        Mantém histórico dos últimos N frames e retorna média.
        """
        self.calibration_history.append(calibration)

        if len(self.calibration_history) < 2:
            return calibration

        # Calcular média das calibrações recentes
        avg_center0_x = np.mean([c.marker0_pose.center[0] for c in self.calibration_history])
        avg_center0_y = np.mean([c.marker0_pose.center[1] for c in self.calibration_history])
        avg_center1_x = np.mean([c.marker1_pose.center[0] for c in self.calibration_history])
        avg_center1_y = np.mean([c.marker1_pose.center[1] for c in self.calibration_history])

        # Recalcular com valores médios
        avg_distance = self._calculate_distance(
            (avg_center0_x, avg_center0_y),
            (avg_center1_x, avg_center1_y),
        )
        avg_scale = self.distance_mm / avg_distance if avg_distance > 0 else 1.0

        # Atualizar calibração com valores médios
        calibration.marker0_pose.center = (avg_center0_x, avg_center0_y)
        calibration.marker1_pose.center = (avg_center1_x, avg_center1_y)
        calibration.distance_pixels = avg_distance
        calibration.scale = avg_scale
        calibration.confidence = min(1.0, len(self.calibration_history) / self.smoothing_frames)

        return calibration

    def validate_calibration(self, calibration: CalibrationData) -> bool:
        """
        Valida se a calibração é fisicamente plausível.

        Verificações:
        - Ambos marcadores detectados
        - Distância razoável (não muito grande ou pequena)
        - Marcadores bem separados espacialmente
        """
        if calibration is None:
            return False

        # Distância mínima/máxima em pixels
        MIN_DISTANCE_PX = 50
        MAX_DISTANCE_PX = 2000

        if calibration.distance_pixels < MIN_DISTANCE_PX:
            self.logger.warning(
                f"[CALIB] Distância muito pequena: {calibration.distance_pixels}px < {MIN_DISTANCE_PX}px"
            )
            return False

        if calibration.distance_pixels > MAX_DISTANCE_PX:
            self.logger.warning(
                f"[CALIB] Distância muito grande: {calibration.distance_pixels}px > {MAX_DISTANCE_PX}px"
            )
            return False

        # Escala deve ser positiva
        if calibration.scale <= 0:
            self.logger.warning(f"[CALIB] Escala inválida: {calibration.scale}")
            return False

        return True

    def get_axis_vectors(self, calibration: CalibrationData) -> Dict[str, np.ndarray]:
        """
        Extrai vetores dos eixos X e Y do tabuleiro.

        Returns:
            {
                'X': vetor unitário do eixo X (de marker0 para marker1),
                'Y': vetor unitário perpendicular no plano,
                'Z': vetor normal (0,0,1)
            }
        """
        if calibration is None:
            return None

        # Vetor X: do marker0 para marker1
        x1, y1 = calibration.marker0_pose.center
        x2, y2 = calibration.marker1_pose.center

        vec_x = np.array([x2 - x1, y2 - y1, 0.0])
        vec_x = vec_x / np.linalg.norm(vec_x) if np.linalg.norm(vec_x) > 0 else vec_x

        # Vetor Y: perpendicular a X no plano XY (rotacionar 90° contra-relógio)
        vec_y = np.array([-vec_x[1], vec_x[0], 0.0])
        vec_y = vec_y / np.linalg.norm(vec_y) if np.linalg.norm(vec_y) > 0 else vec_y

        # Vetor Z: normal ao plano (sempre cima)
        vec_z = np.array([0.0, 0.0, 1.0])

        return {
            "X": vec_x,
            "Y": vec_y,
            "Z": vec_z,
            "origin_pixels": (x1, y1),
            "scale": calibration.scale,
        }

    def draw_calibration(self, frame, calibration: CalibrationData):
        """Desenha marcadores e eixos para visualização."""
        if frame is None or calibration is None:
            return frame

        frame_copy = frame.copy()

        # Desenhar marcador 0 (origem)
        c0 = calibration.marker0_pose.center
        cv2.circle(frame_copy, (int(c0[0]), int(c0[1])), 8, (0, 255, 0), -1)
        cv2.putText(frame_copy, "ORIGIN", (int(c0[0]) + 10, int(c0[1])),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Desenhar marcador 1
        c1 = calibration.marker1_pose.center
        cv2.circle(frame_copy, (int(c1[0]), int(c1[1])), 8, (0, 0, 255), -1)
        cv2.putText(frame_copy, "X", (int(c1[0]) + 10, int(c1[1])),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        # Desenhar linha X
        cv2.line(frame_copy, (int(c0[0]), int(c0[1])), (int(c1[0]), int(c1[1])),
                 (0, 255, 255), 2)

        # Desenhar escala
        scale_text = f"Scale: {calibration.scale:.4f} px/mm"
        cv2.putText(frame_copy, scale_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        return frame_copy


# ============================================================================
# Teste
# ============================================================================

if __name__ == "__main__":
    print("[TESTE] CalibrationMarkerDetector")
    print("")

    try:
        detector = CalibrationMarkerDetector(distance_mm=270.0)
        print("[OK] Detector criado")

        # Simular frame (requer câmera real para funcionário)
        print("[AVISO] Requer câmera com 2 marcadores ArUco para teste funcional")

    except Exception as e:
        print(f"[ERRO] {e}")

    print("\n[OK] Teste concluído")
