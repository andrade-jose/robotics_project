"""
BoardTransformCalculator - Transformação Câmera → Tabuleiro

Responsabilidades:
- Receber CalibrationData (2 marcadores calibrados)
- Construir matriz de transformação de pixels → mm físicos
- Converter coordenadas pixel → coordenadas tabuleiro (x, y, 0)
- Fornecer operações inversas para verificação

Física:
- Origem: centro do marcador 0 (canto inferior esquerdo) = (0, 0, 0) no tabuleiro
- Eixo X: direção do marcador 0 para marcador 1
- Eixo Y: perpendicular a X no plano (rotação 90° contra-relógio)
- Eixo Z: normal ao plano (sempre (0, 0, 1))

Transformação:
1. Origem em pixels (marker0_center)
2. Escala (scale = distance_mm / distance_pixels)
3. Eixos X, Y como vetores unitários

Uso:
    from calibration_marker_detector import CalibrationMarkerDetector
    detector = CalibrationMarkerDetector(distance_mm=270.0)
    calibration = detector.detect(frame)

    transform = BoardTransformCalculator(calibration)
    board_pos = transform.pixel_to_board((pixel_x, pixel_y))
    # Retorna: (board_x_mm, board_y_mm, 0.0)
"""

import numpy as np
import logging
from typing import Optional, Tuple, Dict
from dataclasses import dataclass


@dataclass
class TransformMatrix:
    """Matriz de transformação câmera → tabuleiro."""
    origin_pixels: Tuple[float, float]  # Centro do marcador 0
    scale: float  # pixels_to_mm
    axis_x: np.ndarray  # Vetor unitário X
    axis_y: np.ndarray  # Vetor unitário Y
    axis_z: np.ndarray  # Vetor unitário Z (0,0,1)
    is_valid: bool
    confidence: float  # 0-1


class BoardTransformCalculator:
    """
    Calculador de transformação câmera → tabuleiro.

    Características:
    - Constrói matriz de transformação a partir de CalibrationData
    - Converte pixels → coordenadas tabuleiro (mm)
    - Operação inversa para verificação
    - Logging detalhado
    """

    def __init__(
        self,
        calibration,  # CalibrationData do detector
        logger: Optional[logging.Logger] = None,
    ):
        """
        Inicializa calculador de transformação.

        Args:
            calibration: CalibrationData com poses dos 2 marcadores
            logger: Logger customizado
        """
        if calibration is None:
            raise ValueError("CalibrationData não pode ser None")

        self.calibration = calibration
        self.transform_matrix = None
        self.is_initialized = False

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

        # Construir matriz de transformação
        self._build_transform_matrix()

    def _build_transform_matrix(self) -> bool:
        """
        Constrói a matriz de transformação usando CalibrationData.

        Etapas:
        1. Extrair origem (centro do marcador 0)
        2. Extrair escala (pixels_to_mm)
        3. Extrair eixos X, Y, Z (vetores unitários)
        4. Validar transformação
        """
        try:
            # Extrair eixos do calibrador
            axis_data = self._extract_axis_vectors()
            if axis_data is None:
                self.logger.error("[TRANSFORM] Falha ao extrair eixos")
                return False

            # Criar matriz de transformação
            self.transform_matrix = TransformMatrix(
                origin_pixels=self.calibration.marker0_pose.center,
                scale=self.calibration.scale,
                axis_x=axis_data["X"],
                axis_y=axis_data["Y"],
                axis_z=axis_data["Z"],
                is_valid=True,
                confidence=self.calibration.confidence,
            )

            self.is_initialized = True
            self.logger.info(
                f"[TRANSFORM] Matriz de transformação construída "
                f"(escala={self.calibration.scale:.4f} px/mm, "
                f"confiança={self.calibration.confidence:.2f})"
            )
            return True

        except Exception as e:
            self.logger.error(f"[TRANSFORM] Erro ao construir matriz: {e}")
            return False

    def _extract_axis_vectors(self) -> Optional[Dict]:
        """
        Extrai eixos X, Y, Z da CalibrationData.

        Returns:
            Dict com X, Y, Z como vetores unitários (ou None se erro)
        """
        try:
            # Eixo X: do marcador 0 para marcador 1
            x1, y1 = self.calibration.marker0_pose.center
            x2, y2 = self.calibration.marker1_pose.center

            vec_x = np.array([x2 - x1, y2 - y1, 0.0])
            norm_x = np.linalg.norm(vec_x)
            if norm_x > 0:
                vec_x = vec_x / norm_x
            else:
                self.logger.warning("[TRANSFORM] Eixo X com norma zero")
                return None

            # Eixo Y: perpendicular a X no plano XY
            # Rotacionar 90° contra-relógio: (x, y) → (-y, x)
            vec_y = np.array([-vec_x[1], vec_x[0], 0.0])
            norm_y = np.linalg.norm(vec_y)
            if norm_y > 0:
                vec_y = vec_y / norm_y

            # Eixo Z: normal ao plano (sempre cima)
            vec_z = np.array([0.0, 0.0, 1.0])

            return {"X": vec_x, "Y": vec_y, "Z": vec_z}

        except Exception as e:
            self.logger.error(f"[TRANSFORM] Erro ao extrair eixos: {e}")
            return None

    def pixel_to_board(self, pixel_coords: Tuple[float, float]) -> Tuple[float, float, float]:
        """
        Converte coordenadas pixel → coordenadas tabuleiro (mm).

        Algoritmo:
        1. Calcular vetor relativo do pixel até origem
        2. Projetar no eixo X: dot(relativo, axis_x) * scale
        3. Projetar no eixo Y: dot(relativo, axis_y) * scale
        4. Z sempre 0

        Args:
            pixel_coords: (x_pixel, y_pixel)

        Returns:
            (board_x_mm, board_y_mm, 0.0)
        """
        if not self.is_initialized or self.transform_matrix is None:
            self.logger.warning("[TRANSFORM] Transformação não inicializada")
            return (0.0, 0.0, 0.0)

        try:
            px, py = pixel_coords
            ox, oy = self.transform_matrix.origin_pixels

            # Vetor relativo do pixel até origem
            rel_vector = np.array([px - ox, py - oy, 0.0])

            # Projetar em X e Y
            board_x = np.dot(rel_vector, self.transform_matrix.axis_x) * self.transform_matrix.scale
            board_y = np.dot(rel_vector, self.transform_matrix.axis_y) * self.transform_matrix.scale

            return (float(board_x), float(board_y), 0.0)

        except Exception as e:
            self.logger.error(f"[TRANSFORM] Erro ao converter pixel→board: {e}")
            return (0.0, 0.0, 0.0)

    def board_to_pixel(self, board_coords: Tuple[float, float, float]) -> Tuple[float, float]:
        """
        Converte coordenadas tabuleiro → coordenadas pixel (operação inversa).

        Algoritmo:
        1. Escalar board_x, board_y por 1/scale
        2. Reconstruir vetor: x_rel = (board_x/scale) * axis_x + (board_y/scale) * axis_y
        3. Adicionar à origem

        Args:
            board_coords: (board_x_mm, board_y_mm, board_z_mm) - z_mm ignorado

        Returns:
            (x_pixel, y_pixel)
        """
        if not self.is_initialized or self.transform_matrix is None:
            self.logger.warning("[TRANSFORM] Transformação não inicializada")
            return (0.0, 0.0)

        try:
            board_x, board_y, _ = board_coords
            scale = self.transform_matrix.scale

            if scale == 0:
                self.logger.warning("[TRANSFORM] Escala zero, não posso inverter")
                return (0.0, 0.0)

            # Normalizar por escala
            x_rel_norm = board_x / scale
            y_rel_norm = board_y / scale

            # Reconstruir vetor relativo
            rel_vector = (
                x_rel_norm * self.transform_matrix.axis_x +
                y_rel_norm * self.transform_matrix.axis_y
            )

            # Adicionar à origem
            ox, oy = self.transform_matrix.origin_pixels
            pixel_x = ox + rel_vector[0]
            pixel_y = oy + rel_vector[1]

            return (float(pixel_x), float(pixel_y))

        except Exception as e:
            self.logger.error(f"[TRANSFORM] Erro ao converter board→pixel: {e}")
            return (0.0, 0.0)

    def get_transform_info(self) -> Dict:
        """Retorna informações da transformação."""
        if not self.is_initialized or self.transform_matrix is None:
            return {"is_initialized": False, "error": "Transformação não construída"}

        return {
            "is_initialized": True,
            "origin_pixels": self.transform_matrix.origin_pixels,
            "scale_px_per_mm": self.transform_matrix.scale,
            "scale_mm_per_px": 1.0 / self.transform_matrix.scale if self.transform_matrix.scale > 0 else 0.0,
            "axis_x": self.transform_matrix.axis_x.tolist(),
            "axis_y": self.transform_matrix.axis_y.tolist(),
            "axis_z": self.transform_matrix.axis_z.tolist(),
            "confidence": self.transform_matrix.confidence,
            "is_valid": self.transform_matrix.is_valid,
            "distance_mm": self.calibration.distance_mm,
            "distance_pixels": self.calibration.distance_pixels,
        }

    def validate_transform(self) -> bool:
        """
        Valida transformação fazendo roundtrip.

        Testa: pixel → board → pixel e verifica se volta perto do original
        """
        if not self.is_initialized:
            self.logger.warning("[TRANSFORM] Transformação não inicializada")
            return False

        try:
            # Testar alguns pontos chave
            test_points = [
                (0.0, 0.0),  # Origem
                (self.calibration.marker1_pose.center[0], self.calibration.marker1_pose.center[1]),  # Marker 1
            ]

            for pixel_point in test_points:
                # Converter para board
                board_point = self.pixel_to_board(pixel_point)

                # Converter de volta
                pixel_back = self.board_to_pixel(board_point)

                # Verificar distância
                dx = pixel_point[0] - pixel_back[0]
                dy = pixel_point[1] - pixel_back[1]
                distance = np.sqrt(dx**2 + dy**2)

                if distance > 1.0:  # Tolerância de 1 pixel
                    self.logger.warning(
                        f"[TRANSFORM] Roundtrip falhou para {pixel_point}: "
                        f"distância={distance:.2f}px"
                    )
                    return False

            self.logger.info("[TRANSFORM] Validação de transformação passou")
            return True

        except Exception as e:
            self.logger.error(f"[TRANSFORM] Erro ao validar transformação: {e}")
            return False


# ============================================================================
# Teste
# ============================================================================

if __name__ == "__main__":
    print("[TESTE] BoardTransformCalculator")
    print("")

    try:
        # Simular uma CalibrationData
        from dataclasses import dataclass

        @dataclass
        class MockMarkerPose:
            marker_id: int
            center: tuple
            corners: np.ndarray
            normal: tuple
            orientation_angle: float

        @dataclass
        class MockCalibrationData:
            marker0_pose: MockMarkerPose
            marker1_pose: MockMarkerPose
            distance_mm: float
            distance_pixels: float
            scale: float
            is_valid: bool
            confidence: float

        # Criar mock de calibração
        marker0 = MockMarkerPose(
            marker_id=0,
            center=(100.0, 100.0),  # Canto inferior esquerdo em pixels
            corners=np.array([[80, 80], [120, 80], [120, 120], [80, 120]]),
            normal=(0.0, 0.0, 1.0),
            orientation_angle=0.0,
        )

        marker1 = MockMarkerPose(
            marker_id=1,
            center=(370.0, 100.0),  # Canto superior direito em pixels (270px afastado)
            corners=np.array([[350, 80], [390, 80], [390, 120], [350, 120]]),
            normal=(0.0, 0.0, 1.0),
            orientation_angle=0.0,
        )

        calibration = MockCalibrationData(
            marker0_pose=marker0,
            marker1_pose=marker1,
            distance_mm=270.0,  # Distância real entre marcadores
            distance_pixels=270.0,  # Em pixels (simplificado)
            scale=1.0,  # 1 pixel = 1 mm (simplificado)
            is_valid=True,
            confidence=1.0,
        )

        # Criar transformador
        transform = BoardTransformCalculator(calibration)
        print("[OK] BoardTransformCalculator criado")

        # Testar conversões
        print("\nTestes de conversão:")
        test_pixels = [
            (100.0, 100.0),  # Origem (marker0)
            (370.0, 100.0),  # Marker1
            (235.0, 100.0),  # Centro entre os dois
        ]

        for pixel_point in test_pixels:
            board_point = transform.pixel_to_board(pixel_point)
            pixel_back = transform.board_to_pixel(board_point)
            print(f"  Pixel {pixel_point} → Board {board_point} → Pixel {pixel_back}")

        # Mostrar informações
        print("\n[INFO] Transformação:")
        info = transform.get_transform_info()
        for key, value in info.items():
            print(f"  - {key}: {value}")

        # Validar
        is_valid = transform.validate_transform()
        print(f"\n[STATUS] Transformação válida: {is_valid}")

    except Exception as e:
        print(f"[ERRO] {e}")
        import traceback

        traceback.print_exc()

    print("\n[OK] Teste concluído")
