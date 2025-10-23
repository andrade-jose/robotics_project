from typing import Dict, Tuple

def gerar_tabuleiro_tapatan(z: float = 0.03) -> Dict[str, Tuple[float, float, float]]:
    """
    Gera um dicionário com as coordenadas XYZ físicas do tabuleiro Tapatan.
    Assume uma folha A4 em paisagem (29.7 x 21 cm), com casas de 6 cm.
    As posições são centralizadas na folha.
    
    Retorna:
        Dict com chaves 'A1' a 'C3' e valores (x, y, z) em metros.
    """
    cm = lambda v: v / 100.0  # conversão para metros
    largura_folha = cm(29.7)
    altura_folha = cm(21.0)
    espacamento = cm(6.0)
    origem_x = (largura_folha - 2 * espacamento) / 2
    origem_y = (altura_folha - 2 * espacamento) / 2

    casas = {}
    linhas = ['C', 'B', 'A']  # linha de cima (C) para baixo (A)
    colunas = ['1', '2', '3']  # coluna da esquerda (1) para a direita (3)

    for i, linha in enumerate(linhas):
        for j, coluna in enumerate(colunas):
            nome = linha + coluna
            x = round(origem_x + j * espacamento, 4)
            y = round(origem_y + i * espacamento, 4)
            casas[nome] = (x, y, z)

    return casas
