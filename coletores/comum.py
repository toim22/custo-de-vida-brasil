"""Funções usadas por todos os coletores."""
import json
import time
import unicodedata
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados"
CONFIG = RAIZ / "config"
DESCOBERTAS = RAIZ / "descobertas"
INICIO = "2023-01-01"  # início fixo dos dados (decisão do projeto)

UF_NOMES = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia", "CE": "Ceará",
    "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão", "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul", "MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
    "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo",
    "SE": "Sergipe", "TO": "Tocantins",
}
UF_REGIAO = {
    "AC": "N", "AP": "N", "AM": "N", "PA": "N", "RO": "N", "RR": "N", "TO": "N",
    "AL": "NE", "BA": "NE", "CE": "NE", "MA": "NE", "PB": "NE", "PE": "NE", "PI": "NE", "RN": "NE", "SE": "NE",
    "DF": "CO", "GO": "CO", "MT": "CO", "MS": "CO",
    "ES": "SE", "MG": "SE", "RJ": "SE", "SP": "SE",
    "PR": "S", "RS": "S", "SC": "S",
}
REGIAO_NOMES = {"N": "Norte", "NE": "Nordeste", "CO": "Centro-Oeste", "SE": "Sudeste", "S": "Sul"}
CAPITAL_UF = {
    "aracaju": "SE", "belem": "PA", "belo horizonte": "MG", "boa vista": "RR", "brasilia": "DF",
    "campo grande": "MS", "cuiaba": "MT", "curitiba": "PR", "florianopolis": "SC", "fortaleza": "CE",
    "goiania": "GO", "joao pessoa": "PB", "macapa": "AP", "maceio": "AL", "manaus": "AM", "natal": "RN",
    "palmas": "TO", "porto alegre": "RS", "porto velho": "RO", "recife": "PE", "rio branco": "AC",
    "rio de janeiro": "RJ", "salvador": "BA", "sao luis": "MA", "sao paulo": "SP", "teresina": "PI",
    "vitoria": "ES",
}

SESSAO = requests.Session()
SESSAO.headers.update({
    "User-Agent": "Mozilla/5.0 (compatible; custo-de-vida-brasil/1.0; +https://github.com)",
    "Accept-Language": "pt-BR,pt;q=0.9",
})


def norm(txt):
    """Minúsculas, sem acento e sem espaços repetidos. Usado para comparar nomes."""
    if txt is None:
        return ""
    t = unicodedata.normalize("NFKD", str(txt))
    t = "".join(c for c in t if not unicodedata.combining(c))
    return " ".join(t.lower().replace("\n", " ").split())


def uf_por_nome(nome):
    n = norm(nome)
    for sigla, nm in UF_NOMES.items():
        if n == norm(nm) or n == sigla.lower():
            return sigla
    return None


def baixar(url, tentativas=3, timeout=(15, 60), **kw):
    """GET com novas tentativas. Devolve o objeto Response ou levanta erro."""
    erro = None
    for i in range(tentativas):
        inicio = time.time()
        try:
            r = SESSAO.get(url, timeout=timeout, **kw)
            r.raise_for_status()
            print(f"    GET {r.status_code} {len(r.content):>9} bytes {time.time() - inicio:5.1f}s {url[:110]}", flush=True)
            return r
        except Exception as e:  # noqa: BLE001
            erro = e
            print(f"    GET falhou ({type(e).__name__}) {time.time() - inicio:5.1f}s {url[:110]}", flush=True)
            if i < tentativas - 1:
                time.sleep(3 * (i + 1))
    raise RuntimeError(f"falha ao baixar {url}: {erro}")


def ler_json(nome, padrao=None):
    p = DADOS / f"{nome}.json"
    if not p.exists():
        return padrao
    return json.loads(p.read_text(encoding="utf-8"))


def salvar_json(nome, obj):
    DADOS.mkdir(exist_ok=True)
    p = DADOS / f"{nome}.json"
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=False) + "\n", encoding="utf-8")


def config(nome):
    return json.loads((CONFIG / f"{nome}.json").read_text(encoding="utf-8"))


def media(valores):
    v = [x for x in valores if x is not None]
    return sum(v) / len(v) if v else None


def serie_ordenada(d):
    """{chave: valor} -> [[chave, valor], ...] em ordem."""
    return [[k, round(v, 4) if isinstance(v, float) else v] for k, v in sorted(d.items()) if v is not None]
