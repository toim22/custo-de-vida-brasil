"""Combustíveis e gás de cozinha: Levantamento de Preços de Combustíveis da ANP (semanal).

Lê as planilhas semanais publicadas pela ANP (série histórica e últimas semanas) e
grava dados/combustiveis.json com séries por Brasil, região e estado.
"""
import io
import re
from datetime import date, datetime

import pandas as pd

from comum import INICIO, UF_REGIAO, baixar, ler_json, norm, salvar_json, uf_por_nome

PAGINAS = [
    "https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/precos-revenda-e-de-distribuicao-combustiveis/serie-historica-do-levantamento-de-precos",
    "https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/levantamento-de-precos-de-combustiveis-ultimas-semanas-pesquisadas",
]
# Planilhas que interessam: séries semanais (Brasil, regiões, estados) e resumos semanais recentes.
PADRAO_LINK = re.compile(r"(semanal[-_](brasil|regioes|estados)|resumo[-_]semanal|semanal[-_]estados)[^\"']*\.xlsx?", re.I)

PRODUTOS = {
    "gasolina": {"nome": "Gasolina comum", "unidade": "litro", "anp": ["gasolina comum"]},
    "etanol": {"nome": "Etanol", "unidade": "litro", "anp": ["etanol hidratado"]},
    "diesel": {"nome": "Diesel S10", "unidade": "litro", "anp": ["oleo diesel s10", "diesel s10"]},
    "gnv": {"nome": "GNV", "unidade": "m³", "anp": ["gnv"]},
    "glp": {"nome": "Botijão de gás 13 kg", "unidade": "botijão", "anp": ["glp"]},
}
REGIOES_ANP = {"norte": "N", "nordeste": "NE", "centro oeste": "CO", "sudeste": "SE", "sul": "S"}


def produto_chave(txt):
    n = norm(txt)
    for chave, p in PRODUTOS.items():
        if any(n == a or n.startswith(a + " ") for a in p["anp"]):
            # "gasolina comum" não pode pegar "gasolina aditivada"; "oleo diesel" puro não é S10
            return chave
    return None


def links_planilhas():
    achados = []
    for pagina in PAGINAS:
        try:
            html = baixar(pagina).text
        except Exception as e:  # noqa: BLE001
            print("  aviso:", e)
            continue
        for m in re.finditer(r'href="([^"]+\.xlsx?)"', html, re.I):
            url = m.group(1)
            if url.startswith("/"):
                url = "https://www.gov.br" + url
            if PADRAO_LINK.search(url) and url not in achados:
                achados.append(url)
    return achados


def achar_cabecalho(bruto):
    for i in range(min(30, len(bruto))):
        linha = [norm(x) for x in bruto.iloc[i].tolist()]
        if "produto" in linha and any("preco medio revenda" in c for c in linha):
            return i
    return None


def para_data(v):
    if isinstance(v, (datetime, pd.Timestamp)):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    s = str(v).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def ler_planilha(conteudo, series):
    folhas = pd.read_excel(io.BytesIO(conteudo), sheet_name=None, header=None)
    lidas = 0
    for _, bruto in folhas.items():
        h = achar_cabecalho(bruto)
        if h is None:
            continue
        df = bruto.iloc[h + 1:].copy()
        df.columns = [norm(c) for c in bruto.iloc[h].tolist()]
        col_data = next((c for c in df.columns if c in ("data final", "data")), None)
        col_preco = next((c for c in df.columns if c.startswith("preco medio revenda")), None)
        col_estado = next((c for c in df.columns if c == "estado"), None)
        col_regiao = next((c for c in df.columns if c in ("regiao", "regiao ")), None)
        if not (col_data and col_preco):
            continue
        for _, r in df.iterrows():
            prod = produto_chave(r.get("produto"))
            dia = para_data(r.get(col_data))
            try:
                preco = float(str(r.get(col_preco)).replace(",", "."))
            except (TypeError, ValueError):
                continue
            if not prod or not dia or dia < INICIO or preco != preco or preco <= 0:
                continue
            if col_estado and str(r.get(col_estado)).strip() not in ("", "nan"):
                local = uf_por_nome(r.get(col_estado))
            elif col_regiao and str(r.get(col_regiao)).strip() not in ("", "nan"):
                local = REGIOES_ANP.get(norm(r.get(col_regiao)).replace("-", " "))
            else:
                local = "BR"
            if not local:
                continue
            series.setdefault(local, {}).setdefault(prod, {})[dia] = round(preco, 3)
            lidas += 1
    return lidas


def completar_agregados(series):
    """Se a ANP não trouxer Brasil ou regiões numa semana, usa a média simples dos estados (marcado na metodologia)."""
    datas = set()
    for uf in UF_REGIAO:
        for p in series.get(uf, {}).values():
            datas.update(p.keys())
    for prod in PRODUTOS:
        for dia in datas:
            por_regiao = {}
            todos = []
            for uf, reg in UF_REGIAO.items():
                v = series.get(uf, {}).get(prod, {}).get(dia)
                if v is not None:
                    por_regiao.setdefault(reg, []).append(v)
                    todos.append(v)
            if todos and dia not in series.setdefault("BR", {}).setdefault(prod, {}):
                series["BR"][prod][dia] = round(sum(todos) / len(todos), 3)
            for reg, vals in por_regiao.items():
                if dia not in series.setdefault(reg, {}).setdefault(prod, {}):
                    series[reg][prod][dia] = round(sum(vals) / len(vals), 3)


def coletar():
    anterior = ler_json("combustiveis", {}) or {}
    series = {}
    for local, prods in (anterior.get("series") or {}).items():
        for prod, pontos in prods.items():
            series.setdefault(local, {})[prod] = {d: v for d, v in pontos}

    links = links_planilhas()
    print(f"  {len(links)} planilhas encontradas")
    total = 0
    for url in links:
        try:
            n = ler_planilha(baixar(url).content, series)
            print(f"  {n:6d} linhas  {url.rsplit('/', 1)[-1]}")
            total += n
        except Exception as e:  # noqa: BLE001
            print("  aviso:", url, e)
    if total == 0 and not anterior:
        raise RuntimeError("nenhum preço da ANP foi lido")

    completar_agregados(series)
    saida = {
        "fonte": "ANP — Levantamento de Preços de Combustíveis",
        "fonte_url": PAGINAS[1],
        "produtos": {k: {"nome": v["nome"], "unidade": v["unidade"]} for k, v in PRODUTOS.items()},
        "series": {loc: {p: sorted([[d, v] for d, v in pts.items()]) for p, pts in prods.items()} for loc, prods in sorted(series.items())},
    }
    ult = max((pts[-1][0] for prods in saida["series"].values() for pts in prods.values() if pts), default=None)
    saida["atualizado"] = ult
    salvar_json("combustiveis", saida)
    return ult


if __name__ == "__main__":
    print(coletar())
