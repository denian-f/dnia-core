"""
Geolocalização aproximada por IP usando o banco local MaxMind GeoLite2
(City) — sem chamada de rede, sem enviar o IP a nenhum serviço
terceiro. O IP só existe na memória durante essa consulta; a função
que chama isto (ver analytics/service.py) nunca grava o IP em lugar
nenhum, só o resultado (país/região/cidade aproximados).

Se GEOLITE2_DATABASE_PATH não estiver configurada (ou o arquivo não
puder ser aberto), toda resolução retorna (None, None, None) — o
Analytics continua funcionando normalmente, só sem dado de
localização, até o arquivo ser configurado.
"""

import threading

from app.dna_connect.analytics import config

_leitor = None
_tentou_carregar = False
_lock = threading.Lock()


def _obter_leitor():

    global _leitor, _tentou_carregar

    if _tentou_carregar:
        return _leitor

    with _lock:

        if _tentou_carregar:
            return _leitor

        _tentou_carregar = True

        if not config.GEOLITE2_DATABASE_PATH:
            return None

        try:

            import geoip2.database

            _leitor = geoip2.database.Reader(config.GEOLITE2_DATABASE_PATH)

        except Exception:

            _leitor = None

    return _leitor


def resolver_localizacao(ip: str):
    """
    Retorna (country, region, city) aproximados a partir do IP, ou
    (None, None, None) se o banco não estiver disponível, o IP for
    inválido, ou não houver registro para ele (comum em IPs locais/de
    teste). country é o código ISO de 2 letras (ex: "BR").
    """

    if not ip:
        return None, None, None

    leitor = _obter_leitor()

    if not leitor:
        return None, None, None

    try:

        resposta = leitor.city(ip)

    except Exception:

        return None, None, None

    country = resposta.country.iso_code
    region = resposta.subdivisions.most_specific.name if resposta.subdivisions else None
    city = resposta.city.name

    return country, region, city
