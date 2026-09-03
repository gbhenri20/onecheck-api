import json
import logging
import re
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)


def buscar_endereco_por_cep(cep: str) -> dict:
    """
    Consulta ViaCEP para obter dados do endereço a partir do CEP.
    Retorna dict com logradouro, bairro, cidade, estado ou vazio em caso de falha.
    """
    cep_numerico = re.sub(r"\D", "", cep or "")
    if len(cep_numerico) != 8:
        return {}

    url = f"https://viacep.com.br/ws/{cep_numerico}/json/"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "OneCheckAPI/1.0", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if not isinstance(data, dict) or data.get("erro"):
                return {}
            return {
                "logradouro": data.get("logradouro", ""),
                "bairro": data.get("bairro", ""),
                "cidade": data.get("localidade", ""),
                "estado": data.get("uf", ""),
            }
    except Exception as exc:
        logger.warning(f"[GeocodingService] Falha ao consultar ViaCEP ({url}): {exc}")
        return {}


def buscar_coordenadas(endereco_completo: str) -> dict | None:
    """
    Consulta Nominatim (OpenStreetMap) para obter latitude e longitude
    a partir de uma string de endereço.
    Retorna dict com latitude e longitude (como float) ou None em caso de falha.
    """
    if not endereco_completo or not endereco_completo.strip():
        return None

    query = urllib.parse.quote(endereco_completo.strip())
    url = f"https://nominatim.openstreetmap.org/search?q={query}&format=json&limit=1"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "OneCheckAPI/1.0", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if not isinstance(data, list) or len(data) == 0:
                return None
            primeiro = data[0]
            if not isinstance(primeiro, dict) or "lat" not in primeiro or "lon" not in primeiro:
                return None
            return {
                "latitude": float(primeiro["lat"]),
                "longitude": float(primeiro["lon"]),
            }
    except Exception as exc:
        logger.warning(f"[GeocodingService] Falha ao consultar Nominatim ({url}): {exc}")
        return None
