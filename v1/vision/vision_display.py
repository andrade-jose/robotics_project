"""
Vision Display - Gerenciador de Exibição de Visão
=================================================
Responsável por exibir a visão da câmera em tempo real usando OpenCV.
Tenta usar cv2.imshow() nativamente, com fallback para streaming web.
"""

import cv2
import numpy as np
import threading
import time
from typing import Optional, Callable
from http.server import HTTPServer, BaseHTTPRequestHandler
import io
import json

# COMENTADO: Handler HTTP para streaming MJPEG desabilitado
# class VisionDisplayHTTPHandler(BaseHTTPRequestHandler):
#     """Handler para servidor HTTP de streaming de vídeo MJPEG"""
#
#     # Variável de classe para compartilhar o frame entre threads
#     current_frame = None
#     frame_lock = threading.Lock()
#
#     def do_GET(self):
#         """Manipula requisições GET para streaming ou status"""
#         if self.path == '/stream.mjpg':
#             self.send_response(200)
#             self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
#             self.end_headers()
#
#             try:
#                 while True:
#                     with VisionDisplayHTTPHandler.frame_lock:
#                         if VisionDisplayHTTPHandler.current_frame is None:
#                             time.sleep(0.01)
#                             continue
#
#                         frame = VisionDisplayHTTPHandler.current_frame.copy()
#
#                     # Codificar frame como JPEG
#                     _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
#
#                     # Enviar como multipart
#                     self.wfile.write(b'--FRAME\r\n')
#                     self.wfile.write(b'Content-Type: image/jpeg\r\n')
#                     self.wfile.write(f'Content-Length: {len(buffer)}\r\n\r\n'.encode())
#                     self.wfile.write(buffer)
#                     self.wfile.write(b'\r\n')
#
#                     time.sleep(0.03)  # ~30 FPS
#
#             except Exception as e:
#                 pass
#
#         elif self.path == '/':
#             # Página HTML para visualizar o stream
#             html_str = '''<!DOCTYPE html>
# <html>
# <head>
#     <title>Tapatan Vision Stream</title>
#     <style>
#         body { font-family: Arial, sans-serif; text-align: center; background: #222; color: #fff; }
#         h1 { color: #4CAF50; }
#         img { max-width: 90vw; max-height: 80vh; border: 2px solid #4CAF50; margin-top: 20px; }
#         .info { margin-top: 20px; font-size: 14px; }
#     </style>
# </head>
# <body>
#     <h1>Tapatan Vision System - Real-time Stream</h1>
#     <p>Camera ArUco em tempo real</p>
#     <img src="/stream.mjpg" />
#     <div class="info">
#         <p>Abra esta pagina em qualquer navegador para ver o stream</p>
#         <p>URL: http://localhost:8080</p>
#     </div>
# </body>
# </html>'''
#             html = html_str.encode('utf-8')
#             self.send_response(200)
#             self.send_header('Content-Type', 'text/html; charset=utf-8')
#             self.send_header('Content-Length', len(html))
#             self.end_headers()
#             self.wfile.write(html)
#
#         else:
#             self.send_response(404)
#             self.end_headers()
#
#     def log_message(self, format, *args):
#         """Suprimir logs do servidor HTTP"""
#         pass


# Placeholder vazio para manter compatibilidade
class VisionDisplayHTTPHandler(BaseHTTPRequestHandler):
    """Handler HTTP desabilitado - streaming web foi comentado"""
    pass


class VisionDisplay:
    """
    Gerenciador de exibição de visão em tempo real.
    Suporta:
    - cv2.imshow() nativo (preferencial)
    - Streaming web MJPEG (fallback para ambientes headless)
    """

    def __init__(self, window_name: str = "Tapatan Vision System", use_web_stream: bool = True, web_port: int = 8080):
        """
        Inicializa o gerenciador de exibição.

        Args:
            window_name: Nome da janela OpenCV
            use_web_stream: Habilitar fallback para streaming web
            web_port: Porta para o servidor web de streaming
        """
        self.window_name = window_name
        self.use_web_stream = use_web_stream
        self.web_port = web_port

        self.display_active = False
        self.web_server = None
        self.web_thread = None
        self.use_web_mode = False

        # Tentar criar janela OpenCV
        self._try_create_window()

    def _try_create_window(self):
        """Tenta criar janela OpenCV, fallback para web se falhar"""
        try:
            # Testar se cv2.imshow() funciona
            test_img = np.zeros((100, 100, 3), dtype=np.uint8)
            cv2.imshow(self.window_name, test_img)
            cv2.waitKey(1)
            cv2.destroyWindow(self.window_name)

            self.display_active = True
            self.use_web_mode = False
            print(f"[VISAO] Modo nativo OpenCV habilitado")

        except Exception as e:
            # Fallback para streaming web
            if self.use_web_stream:
                print(f"[VISAO] OpenCV nativo não disponível, usando streaming web...")
                self._start_web_server()
            else:
                print(f"[VISAO] Aviso: Exibição de vídeo não disponível ({e})")
                self.display_active = False

    def _start_web_server(self):
        """Inicia servidor HTTP para streaming MJPEG"""
        # COMENTADO: Desabilitar streaming web temporariamente
        # try:
        #     self.web_server = HTTPServer(('0.0.0.0', self.web_port), VisionDisplayHTTPHandler)
        #     self.web_thread = threading.Thread(target=self.web_server.serve_forever, daemon=True)
        #     self.web_thread.start()
        #
        #     self.display_active = True
        #     self.use_web_mode = True
        #     print(f"[VISAO] Servidor de streaming iniciado em http://localhost:{self.web_port}")
        #
        # except Exception as e:
        #     print(f"[VISAO] Erro ao iniciar servidor web: {e}")
        #     self.display_active = False

        # Streaming web desabilitado
        print(f"[VISAO] Servidor de streaming web desabilitado")
        self.display_active = False

    def show_frame(self, frame: np.ndarray, wait_key_time: int = 1) -> Optional[int]:
        """
        Exibe um frame de vídeo.

        Args:
            frame: Frame OpenCV (BGR)
            wait_key_time: Tempo para esperar por entrada (ms)

        Returns:
            Código da tecla pressionada (OpenCV mode) ou None (web mode)
        """
        if not self.display_active:
            return None

        try:
            # COMENTADO: Modo web desabilitado
            # if self.use_web_mode:
            #     # Modo web: apenas atualizar o frame compartilhado
            #     with VisionDisplayHTTPHandler.frame_lock:
            #         VisionDisplayHTTPHandler.current_frame = frame.copy()
            #     return None
            #
            # else:
            if True:  # Apenas modo OpenCV nativo
                # Modo OpenCV nativo
                cv2.imshow(self.window_name, frame)
                key = cv2.waitKey(wait_key_time) & 0xFF
                return key if key != 255 else None

        except Exception as e:
            # COMENTADO: Fallback web desabilitado
            # if not self.use_web_mode:
            #     # Se OpenCV falhar, tentar web como fallback
            #     print(f"[VISAO] OpenCV falhou, tentando fallback web: {e}")
            #     self._start_web_server()
            #     return None
            print(f"[VISAO] Erro ao exibir frame: {e}")
            return None

    def close(self):
        """Fecha a exibição e libera recursos"""
        # COMENTADO: Cleanup do servidor web desabilitado
        # if self.use_web_mode:
        #     if self.web_server:
        #         self.web_server.shutdown()
        #         self.web_server = None
        #
        #     if self.web_thread:
        #         self.web_thread.join(timeout=2)
        #         self.web_thread = None
        #
        # else:
        if True:  # Apenas limpeza do OpenCV nativo
            try:
                cv2.destroyWindow(self.window_name)
            except:
                pass

        self.display_active = False

    def is_web_mode(self) -> bool:
        """Retorna True se usando modo web"""
        return self.use_web_mode

    def get_status(self) -> dict:
        """Retorna status da exibição"""
        return {
            'active': self.display_active,
            'mode': 'web' if self.use_web_mode else 'opencv',
            'window_name': self.window_name,
            'web_port': self.web_port if self.use_web_mode else None,
            'web_url': f"http://localhost:{self.web_port}" if self.use_web_mode else None
        }
