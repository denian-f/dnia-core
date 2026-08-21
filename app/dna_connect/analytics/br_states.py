"""
Layout aproximado (não geograficamente exato) dos estados brasileiros
em grade, para o mapa "tile-grid" do Analytics — cada estado vira um
quadrado colorido por intensidade de acesso, posicionado de forma
relativa parecida com o mapa real (norte no topo, sul embaixo, oeste
à esquerda, leste à direita). Não é um contorno geográfico preciso: é
a mesma ideia de "grid map" usada por veículos como a NPR para os EUA
— escolhida aqui porque não há como verificar visualmente neste
ambiente a precisão de um contorno geográfico real desenhado à mão.
"""

ESTADOS_GRID = [
    ("Roraima", "RR", 2, 0),
    ("Amapá", "AP", 5, 0),
    ("Amazonas", "AM", 1, 1),
    ("Pará", "PA", 4, 1),
    ("Maranhão", "MA", 6, 1),
    ("Ceará", "CE", 8, 1),
    ("Acre", "AC", 0, 2),
    ("Tocantins", "TO", 4, 2),
    ("Piauí", "PI", 6, 2),
    ("Rio Grande do Norte", "RN", 8, 2),
    ("Rondônia", "RO", 1, 3),
    ("Paraíba", "PB", 7, 3),
    ("Mato Grosso", "MT", 3, 4),
    ("Bahia", "BA", 6, 4),
    ("Pernambuco", "PE", 7, 4),
    ("Alagoas", "AL", 8, 4),
    ("Mato Grosso do Sul", "MS", 2, 5),
    ("Goiás", "GO", 4, 5),
    ("Distrito Federal", "DF", 5, 5),
    ("Sergipe", "SE", 7, 5),
    ("Minas Gerais", "MG", 5, 6),
    ("Espírito Santo", "ES", 6, 6),
    ("São Paulo", "SP", 4, 7),
    ("Rio de Janeiro", "RJ", 6, 7),
    ("Paraná", "PR", 4, 8),
    ("Santa Catarina", "SC", 4, 9),
    ("Rio Grande do Sul", "RS", 4, 10),
]

GRID_COLS = 9
GRID_ROWS = 11


def montar_mapa_estados(contagem_por_regiao: dict):
    """
    Junta a grade fixa de estados com a contagem real de acessos
    (chave = nome do estado, como retornado pelo GeoLite2). Estados
    sem nenhum acesso aparecem no grid vazios (total=0) — o grid
    inteiro é sempre desenhado, para as posições nunca "pularem".
    """

    maximo = max(contagem_por_regiao.values()) if contagem_por_regiao else 0

    resultado = []

    for nome, uf, col, row in ESTADOS_GRID:

        total = contagem_por_regiao.get(nome, 0)
        intensidade = (total / maximo) if maximo else 0

        # Sem acesso: quadrado quase invisível, só pra manter o
        # formato da grade visível. Com acesso: opacidade cresce com a
        # intensidade, mas nunca fica saturada demais (fica sempre
        # legível sob o texto do estado, exibido abaixo do quadrado,
        # não sobre ele).
        alpha = round(0.18 + intensidade * 0.62, 2) if total else 0.06

        resultado.append({
            "nome": nome,
            "uf": uf,
            "col": col,
            "row": row,
            "total": total,
            "alpha": alpha
        })

    return resultado
