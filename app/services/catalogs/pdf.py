from pathlib import Path

from weasyprint import HTML


def gerar_pdf(html: str, cidade: str) -> Path:
    """
    Gera o PDF do catálogo.

    Args:
        html: HTML completo do catálogo.
        cidade: Nome da cidade.

    Returns:
        Caminho do PDF gerado.
    """

    output_dir = Path("temp")

    output_dir.mkdir(exist_ok=True)

    pdf_path = output_dir / f"catalog_{cidade}.pdf"

    HTML(
        string=html
    ).write_pdf(pdf_path)

    return pdf_path