"""Indicadores calculados por nós: preço estimado dos itens avulsos e o Churrasco pra 6.

Preço estimado = preço de partida (config/itens.json, mês âncora) corrigido mês a mês pela
variação oficial do IPCA daquele item. Para meses antes da âncora a conta é feita ao contrário.
Onde o IBGE não pesquisa (estados sem região metropolitana no IPCA), usa a variação nacional.
"""
from comum import config, ler_json, salvar_json


def meses_entre(variacoes):
    return sorted({m for pts in variacoes.values() for m, _ in pts})


def estimar(preco, mes_ancora, var_local, var_br):
    """var_*: {mes: variação %}. Devolve {mes: preço}."""
    meses = sorted(set(var_br) | set(var_local))
    if not meses:
        return {}
    v = lambda m: var_local.get(m, var_br.get(m, 0.0))  # noqa: E731
    if mes_ancora not in meses:
        # âncora fora da série: usa o mês publicado mais próximo
        mes_ancora = min(meses, key=lambda m: abs(int(m[:4]) * 12 + int(m[5:]) - int(mes_ancora[:4]) * 12 - int(mes_ancora[5:])))
    saida = {mes_ancora: preco}
    # para frente: preço do mês m = preço de m-1 × (1 + variação de m)
    p = preco
    for m in [x for x in meses if x > mes_ancora]:
        p = p * (1 + v(m) / 100)
        saida[m] = p
    # para trás: preço de m-1 = preço de m / (1 + variação de m)
    p = preco
    for m in sorted([x for x in meses if x <= mes_ancora], reverse=True):
        anterior = p / (1 + v(m) / 100)
        idx = meses.index(m)
        if idx > 0:
            saida[meses[idx - 1]] = anterior
        p = anterior
    return saida


def calcular():
    cfg = config("itens")
    ipca = ler_json("ipca")
    if not ipca:
        raise RuntimeError("ipca.json ainda não existe")
    series = ipca["series"]
    ancora = cfg["mes_ancora"]
    todos = dict(cfg["avulsos"])
    todos.update(cfg["churrasco"]["extras"])

    locais = set()
    for s in series.values():
        locais.update(s.keys())

    precos = {}  # chave -> local -> {mes: preço}
    for chave, it in todos.items():
        var = series.get(chave)
        if not var:
            continue
        br = dict((m, x) for m, x in var.get("BR", []))
        for loc in sorted(locais):
            loc_var = dict((m, x) for m, x in var.get(loc, []))
            if loc != "BR" and not loc_var:
                continue
            precos.setdefault(chave, {})[loc] = estimar(it["preco"], ancora, loc_var, br)

    avulsos = {
        "fonte": "Estimativa própria: preço de partida + variação mensal do IPCA (IBGE)",
        "mes_ancora": ancora,
        "ancora_provisoria": cfg.get("ancora_provisoria", False),
        "itens": {k: {"nome": v["nome"], "unidade": v["unidade"], "ipca": (ipca["categorias"].get(k) or {}).get("nome_ibge")} for k, v in cfg["avulsos"].items()},
        "series": {k: {loc: sorted([[m, round(p, 2)] for m, p in pts.items()]) for loc, pts in precos[k].items()} for k in cfg["avulsos"] if k in precos},
    }
    avulsos["atualizado"] = ipca.get("atualizado")
    salvar_json("avulsos", avulsos)

    ch = cfg["churrasco"]
    total = {}
    detalhe = {}
    for loc in sorted(locais):
        meses = None
        for it in ch["itens"]:
            pts = precos.get(it["chave"], {}).get(loc) or precos.get(it["chave"], {}).get("BR")
            if not pts:
                meses = set()
                break
            meses = set(pts) if meses is None else meses & set(pts)
        if not meses:
            continue
        for m in sorted(meses):
            soma = 0.0
            partes = {}
            for it in ch["itens"]:
                pts = precos.get(it["chave"], {}).get(loc) or precos[it["chave"]]["BR"]
                valor = pts[m] * it["qtd"]
                partes[it["chave"]] = round(valor, 2)
                soma += valor
            total.setdefault(loc, []).append([m, round(soma, 2)])
            if m == max(meses):
                detalhe[loc] = partes
    salvar_json("churrasco", {
        "fonte": "Estimativa própria: lista fixa × preços estimados (preço de partida + IPCA)",
        "pessoas": ch["pessoas"],
        "mes_ancora": ancora,
        "ancora_provisoria": cfg.get("ancora_provisoria", False),
        "itens": ch["itens"],
        "total": total,
        "ultimo_detalhe": detalhe,
        "atualizado": ipca.get("atualizado"),
    })
    return ipca.get("atualizado")


if __name__ == "__main__":
    print(calcular())
