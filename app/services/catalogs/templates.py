from jinja2 import Template

# 🎨 HTML PDF
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">

<style>

@page {
  size: A4;
  margin: 0;
}

body {
  margin: 0;
  font-family: Arial;
}

.page {
  width: 210mm;
  height: 297mm;
  position: relative;
  page-break-after: always;
  overflow: hidden;
}

/* 🔥 BACKGROUND CORRIGIDO */
.bg {
  position: absolute;
  top: -1px;
  left: -1px;
  right: -1px;
  bottom: -1px;
  z-index: 0;
}

.bg img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* 🔥 GARANTE QUE FICA POR CIMA */
.titulo, .subtitulo, .produto {
  position: absolute;
  z-index: 2;
}

/* 🔥 TITULO */
.titulo {
  position: absolute;
  top: 60px;
  left: 55%;
  transform: translateX(-50%);
  font-size: 26px;
  font-weight: bold;
  color: #242482;
  text-align: center;
  white-space: nowrap;
  z-index: 2;
}

/* 🔥 SUBTITULO */
.subtitulo {
  position: absolute;
  top: 100px;
  left: 52%;
  transform: translateX(-50%);

  width: 300px;
  text-align: center;

  font-size: 18px;
  font-style: italic;

  white-space: normal;
  word-wrap: break-word;
  line-height: 1.2;

  z-index: 2;
}

/* 🔥 PRODUTO */
.produto {
  position: absolute;
  transform: translateX(-50%);
  width: 160px;
  z-index: 2;
}

/* 🔥 CONTAINER DA IMAGEM */
.imagem-container {
  width: 197px;
  height: 197px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto;
}

/* 🔥 IMAGEM */
.imagem-container img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

/* 🔥 LINHA DIVISÓRIA */
.linha {
  width: 120%;
  height: 1px;
  background: #555;
  margin: 10px 0;
}

/* 🔥 CÓDIGO */
.codigo {
  font-weight: bold;
  font-size: 14px;
}

/* 🔥 PREÇO */
.preco {
  font-size: 14px;
}
</style>
</head>

<body>

{% for pagina in paginas %}
<div class="page">

  <!-- 🔥 BACKGROUND -->
  <div class="bg">
    <img src="{{ background }}">
  </div>

  <div class="titulo">{{ cidade }}</div>
  <div class="subtitulo">{{ pagina.linha }}</div>

  <!-- 🔥 LINHA 1 -->

  {% if pagina.p1_img %}
  <div class="produto" style="top: 178px; left: 16%;">
    <div class="imagem-container">
      <img src="{{ pagina.p1_img }}">
    </div>
    <div class="linha"></div>
    <div class="codigo">{{ pagina.p1_cod }}</div>
    <div class="preco">{{ pagina.p1_preco }}</div>
  </div>
  {% endif %}

  {% if pagina.p2_img %}
  <div class="produto" style="top: 178px; left: 50%;">
    <div class="imagem-container">
      <img src="{{ pagina.p2_img }}">
    </div>
    <div class="linha"></div>
    <div class="codigo">{{ pagina.p2_cod }}</div>
    <div class="preco">{{ pagina.p2_preco }}</div>
  </div>
  {% endif %}

  {% if pagina.p3_img %}
  <div class="produto" style="top: 178px; left: 84%;">
    <div class="imagem-container">
      <img src="{{ pagina.p3_img }}">
    </div>
    <div class="linha"></div>
    <div class="codigo">{{ pagina.p3_cod }}</div>
    <div class="preco">{{ pagina.p3_preco }}</div>
  </div>
  {% endif %}

  <!-- 🔥 LINHA 2 -->

  {% if pagina.p4_img %}
  <div class="produto" style="top: 493px; left: 16%;">
    <div class="imagem-container">
      <img src="{{ pagina.p4_img }}">
    </div>
    <div class="linha"></div>
    <div class="codigo">{{ pagina.p4_cod }}</div>
    <div class="preco">{{ pagina.p4_preco }}</div>
  </div>
  {% endif %}

  {% if pagina.p5_img %}
  <div class="produto" style="top: 493px; left: 50%;">
    <div class="imagem-container">
      <img src="{{ pagina.p5_img }}">
    </div>
    <div class="linha"></div>
    <div class="codigo">{{ pagina.p5_cod }}</div>
    <div class="preco">{{ pagina.p5_preco }}</div>
  </div>
  {% endif %}

  {% if pagina.p6_img %}
  <div class="produto" style="top: 493px; left: 84%;">
    <div class="imagem-container">
      <img src="{{ pagina.p6_img }}">
    </div>
    <div class="linha"></div>
    <div class="codigo">{{ pagina.p6_cod }}</div>
    <div class="preco">{{ pagina.p6_preco }}</div>
  </div>
  {% endif %}

  <!-- 🔥 LINHA 3 -->

  {% if pagina.p7_img %}
  <div class="produto" style="top: 808px; left: 16%;">
    <div class="imagem-container">
      <img src="{{ pagina.p7_img }}">
    </div>
    <div class="linha"></div>
    <div class="codigo">{{ pagina.p7_cod }}</div>
    <div class="preco">{{ pagina.p7_preco }}</div>
  </div>
  {% endif %}

  {% if pagina.p8_img %}
  <div class="produto" style="top: 808px; left: 50%;">
    <div class="imagem-container">
      <img src="{{ pagina.p8_img }}">
    </div>
    <div class="linha"></div>
    <div class="codigo">{{ pagina.p8_cod }}</div>
    <div class="preco">{{ pagina.p8_preco }}</div>
  </div>
  {% endif %}

  {% if pagina.p9_img %}
  <div class="produto" style="top: 808px; left: 84%;">
    <div class="imagem-container">
      <img src="{{ pagina.p9_img }}">
    </div>
    <div class="linha"></div>
    <div class="codigo">{{ pagina.p9_cod }}</div>
    <div class="preco">{{ pagina.p9_preco }}</div>
  </div>
  {% endif %}

</div>
{% endfor %}

</body>
</html>
"""

def render_catalog_template(
    cidade: str,
    paginas: list,
    background: str | None = None
):
    """
    Renderiza o HTML do catálogo utilizando Jinja2.
    """

    template = Template(
        HTML_TEMPLATE
    )

    return template.render(

        cidade=cidade,

        paginas=paginas,

        background=background

    )