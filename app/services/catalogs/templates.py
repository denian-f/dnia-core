def render_catalog_template(
    cidade: str,
    produtos: list,
    background: str | None = None
):
    """
    Gera o HTML do catálogo.
    """

    html = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">

    <head>
        <meta charset="UTF-8">

        <title>Catálogo</title>

        <style>

            body {{
                font-family: Arial, sans-serif;
                margin: 40px;
            }}

            h1 {{
                text-align: center;
            }}

            .produto {{

                border: 1px solid #ddd;

                padding: 15px;

                margin-bottom: 20px;

            }}

            img {{

                max-width: 180px;

            }}

        </style>

    </head>

    <body>

        <h1>Catálogo - {cidade}</h1>

        {"<p>Background encontrado.</p>" if background else ""}

    """

    for produto in produtos:

        html += f"""

        <div class="produto">

            <h2>{produto["codigo"]}</h2>

            <p>Linha: {produto["linha"]}</p>

            <p>Preço: {produto["preco"]}</p>

            <img src="{produto["imagem"]}">

        </div>

        """

    html += """

    </body>

    </html>

    """

    return html