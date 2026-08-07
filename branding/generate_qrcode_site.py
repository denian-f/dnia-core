"""
Utilitario standalone (Sprint 24) para gerar o QR Code oficial de
embalagem do DNA Connect, apontando para https://app.denianfernandes.com.

Nao faz parte da aplicacao (nao importa nem altera nada de app/).
Uso: python branding/generate_qrcode_site.py
"""

import os

import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image

URL = "https://app.denianfernandes.com"
MIN_RESOLUTION_PX = 2000
BORDER_MODULES = 4  # quiet zone minima recomendada pela especificacao QR
SAIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qrcode-site.png")


def gerar_imagem():
    """
    Monta o QR Code em alta resolucao (>= 2000x2000px), com Error
    Correction H, fundo branco, modulos pretos e quiet zone correta
    para impressao. O box_size e calculado dinamicamente a partir do
    numero de modulos para garantir a resolucao minima exigida.
    """

    qr = qrcode.QRCode(
        error_correction=ERROR_CORRECT_H,
        box_size=10,
        border=BORDER_MODULES,
    )
    qr.add_data(URL)
    qr.make(fit=True)

    # get_matrix() ja inclui a quiet zone (border) nas bordas da matriz.
    matriz = qr.get_matrix()
    modulos_totais = len(matriz)

    box_size = -(-MIN_RESOLUTION_PX // modulos_totais)  # ceil division

    qr.box_size = box_size

    imagem = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    return imagem, matriz


def validar(imagem_salva_path: str, matriz):
    """
    Valida o arquivo gerado sem depender de bibliotecas externas de
    decodificacao de QR (fora do escopo permitido pela sprint): reabre
    o PNG salvo em disco e confere formato, resolucao minima e, para
    garantir que o conteudo e de fato decodificavel, reamostra o centro
    de cada modulo da imagem salva e compara com a matriz logica
    original gerada pela biblioteca qrcode (a matriz ja inclui a quiet
    zone nas bordas).
    """

    resultado = {
        "arquivo_criado": os.path.isfile(imagem_salva_path),
        "formato_png": False,
        "resolucao": None,
        "resolucao_ok": False,
        "decodificavel": False,
    }

    if not resultado["arquivo_criado"]:
        return resultado

    with Image.open(imagem_salva_path) as img:
        resultado["formato_png"] = img.format == "PNG"
        resultado["resolucao"] = img.size
        resultado["resolucao_ok"] = img.size[0] >= MIN_RESOLUTION_PX and img.size[1] >= MIN_RESOLUTION_PX

        largura, altura = img.size
        total_modulos_lado = len(matriz)
        box = largura / total_modulos_lado

        pixels = img.convert("L").load()

        combina = True
        for linha_idx, linha in enumerate(matriz):
            for col_idx, escuro in enumerate(linha):
                cx = int((col_idx + 0.5) * box)
                cy = int((linha_idx + 0.5) * box)
                valor = pixels[cx, cy]
                eh_escuro_na_imagem = valor < 128
                if eh_escuro_na_imagem != bool(escuro):
                    combina = False
                    break
            if not combina:
                break

        resultado["decodificavel"] = combina

    return resultado


def main():
    imagem, matriz = gerar_imagem()

    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    imagem.save(SAIDA, format="PNG")

    validacao = validar(SAIDA, matriz)
    tamanho_kb = os.path.getsize(SAIDA) / 1024

    print("=== DNA Connect - QR Code de embalagem (Sprint 24) ===")
    print(f"Arquivo criado: {validacao['arquivo_criado']}")
    print(f"Caminho: {SAIDA}")
    print(f"Formato PNG: {validacao['formato_png']}")
    print(f"Resolucao final: {validacao['resolucao'][0]}x{validacao['resolucao'][1]}px")
    print(f"Resolucao >= {MIN_RESOLUTION_PX}x{MIN_RESOLUTION_PX}px: {validacao['resolucao_ok']}")
    print(f"Tamanho em KB: {tamanho_kb:.2f} KB")
    print(f"URL codificada: {URL}")
    print(f"QR Code decodificavel (validacao estrutural modulo a modulo): {validacao['decodificavel']}")

    if not (validacao["arquivo_criado"] and validacao["formato_png"] and validacao["resolucao_ok"] and validacao["decodificavel"]):
        raise SystemExit("Validacao falhou - verifique as mensagens acima.")


if __name__ == "__main__":
    main()
