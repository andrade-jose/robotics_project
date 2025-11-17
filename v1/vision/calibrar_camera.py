# salvar como: calibrar_camera.py
import cv2
import numpy as np
import glob
import time

# --- CONFIGURAÇÕES ---
CHESSBOARD_SIZE = (8, 5)  # Número de cantos internos (colunas, linhas)
SQUARE_SIZE_MM = 31      # Tamanho do lado de um quadrado do tabuleiro em mm

def calibrate_camera():
    """
    Executa o processo de calibração da câmera usando um feed de vídeo ao vivo.
    """
    # Critérios para o refinamento dos cantos
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

    # Preparar pontos do objeto, como (0,0,0), (1,0,0), (2,0,0) ....,(8,5,0)
    objp = np.zeros((CHESSBOARD_SIZE[0] * CHESSBOARD_SIZE[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:CHESSBOARD_SIZE[0], 0:CHESSBOARD_SIZE[1]].T.reshape(-1, 2)
    objp = objp * SQUARE_SIZE_MM # Converter para milímetros

    # Arrays para armazenar pontos de objeto e pontos de imagem de todas as imagens.
    objpoints = []  # Pontos 3D no espaço do mundo real
    imgpoints = []  # Pontos 2D no plano da imagem.

    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("Erro: Não foi possível abrir a câmera.")
        return

    print("\n--- INSTRUÇÕES ---")
    print("1. Mostre o tabuleiro de xadrez (9x6) para a câmera.")
    print("2. Mova o tabuleiro para diferentes posições e ângulos.")
    print("3. Pressione 'c' para capturar uma imagem quando os cantos forem detectados (o contorno fica verde).")
    print("4. Capture pelo menos 15-20 imagens para uma boa calibração.")
    print("5. Pressione 'q' para iniciar a calibração e sair.")
    print("------------------\n")

    captured_frames = 0
    last_capture_time = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Encontrar os cantos do tabuleiro de xadrez
        ret_corners, corners = cv2.findChessboardCorners(gray, CHESSBOARD_SIZE, None)

        display_frame = frame.copy()

        # Se os cantos forem encontrados, desenhe-os
        if ret_corners:
            cv2.drawChessboardCorners(display_frame, CHESSBOARD_SIZE, corners, ret_corners)
            
            # Capturar frame ao pressionar 'c' (com um intervalo para evitar capturas múltiplas)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('c') and (time.time() - last_capture_time > 1):
                last_capture_time = time.time()
                
                # Refinar as coordenadas dos cantos
                corners_refined = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
                
                objpoints.append(objp)
                imgpoints.append(corners_refined)
                
                captured_frames += 1
                print(f"Imagem {captured_frames} capturada!")
                # Mostra um feedback visual
                display_frame = cv2.putText(display_frame, f"Capturado! ({captured_frames})", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.imshow('Calibracao', display_frame)
                cv2.waitKey(500) # Pausa para ver o feedback

            elif key == ord('q'):
                break
        else:
             key = cv2.waitKey(1) & 0xFF
             if key == ord('q'):
                break


        cv2.putText(display_frame, f"Capturas: {captured_frames} (Pressione 'c')", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.imshow('Calibracao', display_frame)


    cap.release()
    cv2.destroyAllWindows()

    if captured_frames < 10:
        print("\nCalibração cancelada. Poucas imagens capturadas.")
        return

    print(f"\nCalibrando com {captured_frames} imagens... Aguarde.")
    
    # Realizar a calibração da câmera
    ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, gray.shape[::-1], None, None)

    if ret:
        print("\nCalibração bem-sucedida!")
        print("\nMatriz da Câmera (camera_matrix):")
        print(camera_matrix)
        print("\nCoeficientes de Distorção (dist_coeffs):")
        print(dist_coeffs)
        
        # Salvar os resultados
        output_file = 'camera_calibration.npz'
        np.savez(output_file, camera_matrix=camera_matrix, dist_coeffs=dist_coeffs)
        print(f"\nParâmetros de calibração salvos em '{output_file}'")

        # Calcular e exibir o erro de reprojeção
        mean_error = 0
        for i in range(len(objpoints)):
            imgpoints2, _ = cv2.projectPoints(objpoints[i], rvecs[i], tvecs[i], camera_matrix, dist_coeffs)
            error = cv2.norm(imgpoints[i], imgpoints2, cv2.NORM_L2) / len(imgpoints2)
            mean_error += error
        print(f"Erro total de reprojeção: {mean_error / len(objpoints)}")
        
    else:
        print("A calibração falhou.")

if __name__ == '__main__':
    calibrate_camera()